import os
import json
from datetime import datetime, timezone
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from google.auth.exceptions import RefreshError
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload
from lib.config import SCOPES


class LivestreamSetupError(RuntimeError):
    pass


def get_youtube_service():
    token_path = "config/token.json"
    client_secrets_path = "config/client_secrets.json"
    creds = None

    if os.path.exists(token_path):
        with open(token_path, "r") as f:
            token_data = json.load(f)
        creds = Credentials(
            None,
            refresh_token=token_data.get("refresh_token"),
            token_uri=token_data.get("token_uri"),
            client_id=token_data.get("client_id"),
            client_secret=token_data.get("client_secret"),
            scopes=SCOPES,
        )

    if creds and creds.refresh_token:
        try:
            creds.refresh(Request())
            with open(token_path, "w") as f:
                f.write(creds.to_json())
        except RefreshError:
            creds = None

    if not creds or not creds.valid:
        raise LivestreamSetupError(
            "YouTube credentials invalid. Re-run setup.py to refresh token."
        )

    return build(
        "youtube", "v3", credentials=creds, num_retries=3, cache_discovery=False
    )


def get_expected_channel_id():
    expected_channel_id = os.getenv("YOUTUBE_CHANNEL_ID", "").strip()
    return expected_channel_id or None


def get_authenticated_channel(youtube):
    response = (
        youtube.channels()
        .list(part="snippet,status", mine=True, maxResults=1)
        .execute()
    )

    items = response.get("items", [])
    if not items:
        raise LivestreamSetupError(
            "No YouTube channel was found for the authenticated account. "
            "Re-run setup.py and authorize the channel you want to use."
        )

    channel = items[0]
    snippet = channel.get("snippet", {})
    status = channel.get("status", {})

    return {
        "id": channel["id"],
        "title": snippet.get("title", "Unknown channel"),
        "custom_url": snippet.get("customUrl"),
        "long_uploads_status": status.get("longUploadsStatus"),
    }


def format_channel_summary(channel):
    lines = [f"Authenticated YouTube channel: {channel['title']} ({channel['id']})"]

    if channel.get("custom_url"):
        lines.append(f"Channel URL: https://www.youtube.com/{channel['custom_url']}")

    if channel.get("long_uploads_status"):
        lines.append(f"Long uploads status: {channel['long_uploads_status']}")

    return "\n".join(lines)


def validate_authenticated_channel(youtube, expected_channel_id=None):
    channel = get_authenticated_channel(youtube)
    print(format_channel_summary(channel))

    expected_channel_id = expected_channel_id or get_expected_channel_id()
    if expected_channel_id and channel["id"] != expected_channel_id:
        raise LivestreamSetupError(
            "The authenticated YouTube channel does not match YOUTUBE_CHANNEL_ID.\n"
            f"Expected: {expected_channel_id}\n"
            f"Got: {channel['id']}"
        )

    # Check live streaming eligibility
    try:
        status = (
            youtube.liveBroadcasts()
            .list(part="status", broadcastStatus="all", maxResults=1)
            .execute()
        )
    except HttpError as e:
        if e.resp.status == 403 and "liveStreamingNotEnabled" in str(e.content):
            raise LivestreamSetupError(
                "\n\nYOUTUBE LIVE STREAMING NOT ENABLED\n\n"
                "1. Go to https://youtube.com/verify and verify your phone number\n"
                "2. Wait 24 hours for live streaming permissions to activate\n"
                "3. You may need to create one manual live stream first to complete onboarding\n"
            )
        raise

    return youtube, channel


def create_live_broadcast(
    youtube, title, description, tags, channel=None, expected_channel_id=None
):
    scheduled_start = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")

    broadcast_body = {
        "snippet": {
            "title": title,
            "description": description,
            "scheduledStartTime": scheduled_start,
        },
        "contentDetails": {
            "enableAutoStart": True,
            "enableAutoStop": True,
            "enableDvr": True,
            "recordFromStart": True,
            "enableLowLatency": False,
        },
        "status": {
            "privacyStatus": "public",
            "selfDeclaredMadeForKids": False,
        },
    }

    try:
        broadcast = (
            youtube.liveBroadcasts()
            .insert(part="snippet,contentDetails,status", body=broadcast_body)
            .execute()
        )
    except HttpError as error:
        if _extract_http_error_reason(error) == "liveStreamingNotEnabled":
            channel = channel or get_authenticated_channel(youtube)
            raise LivestreamSetupError(
                _build_live_not_enabled_message(channel, expected_channel_id)
            ) from error
        raise

    broadcast_id = broadcast["id"]
    print(f"Broadcast created: {broadcast_id}")
    print(f"Watch at: https://www.youtube.com/watch?v={broadcast_id}")

    return broadcast_id


def create_live_stream(youtube, title):
    stream_body = {
        "snippet": {"title": f"{title} - Stream"},
        "cdn": {
            "frameRate": "30fps",
            "ingestionType": "rtmp",
            "resolution": "1080p",
        },
    }

    stream = (
        youtube.liveStreams().insert(part="snippet,cdn", body=stream_body).execute()
    )

    stream_id = stream["id"]
    ingestion_info = stream["cdn"]["ingestionInfo"]
    rtmp_url = ingestion_info["ingestionAddress"]
    stream_key = ingestion_info["streamName"]

    print(f"Stream created: {stream_id}")
    print(f"RTMP URL: {rtmp_url}")

    return stream_id, rtmp_url, stream_key


def bind_broadcast_to_stream(youtube, broadcast_id, stream_id):
    youtube.liveBroadcasts().bind(
        part="id,contentDetails", id=broadcast_id, streamId=stream_id
    ).execute()
    print(f"Broadcast {broadcast_id} bound to stream {stream_id}")


def apply_broadcast_metadata(youtube, broadcast_id, title, description, tags):
    try:
        response = youtube.videos().list(part="snippet", id=broadcast_id).execute()
        items = response.get("items", [])
        if not items:
            return False

        snippet = items[0].get("snippet", {})
        snippet["title"] = title
        snippet["description"] = description
        if tags:
            snippet["tags"] = tags
        snippet.setdefault("categoryId", "10")

        youtube.videos().update(
            part="snippet", body={"id": broadcast_id, "snippet": snippet}
        ).execute()
        print(f"Broadcast metadata applied: {broadcast_id}")
        return True
    except Exception as error:
        print(f"Warning: could not apply broadcast metadata: {error}")
        return False


def transition_broadcast(youtube, broadcast_id, status):
    try:
        youtube.liveBroadcasts().transition(
            broadcastStatus=status, id=broadcast_id, part="id,status"
        ).execute()
        print(f"Broadcast transitioned to: {status}")
        return True
    except Exception as e:
        print(f"Error transitioning broadcast to {status}: {e}")
        return False


def end_broadcast(youtube, broadcast_id):
    return transition_broadcast(youtube, broadcast_id, "complete")


def set_broadcast_thumbnail(youtube, broadcast_id, thumbnail_path):
    if not thumbnail_path or not os.path.exists(thumbnail_path):
        return False

    try:
        youtube.thumbnails().set(
            videoId=broadcast_id, media_body=MediaFileUpload(thumbnail_path)
        ).execute()
        print(f"Thumbnail uploaded: {thumbnail_path}")
        return True
    except Exception as error:
        print(f"Warning: could not upload thumbnail: {error}")
        return False


def setup_livestream(
    title, description, tags, youtube=None, channel=None, expected_channel_id=None
):
    youtube = youtube or get_youtube_service()
    channel = channel or validate_authenticated_channel(youtube, expected_channel_id)

    broadcast_id = create_live_broadcast(
        youtube,
        title,
        description,
        tags,
        channel=channel,
        expected_channel_id=expected_channel_id,
    )
    stream_id, rtmp_url, stream_key = create_live_stream(youtube, title)
    bind_broadcast_to_stream(youtube, broadcast_id, stream_id)
    apply_broadcast_metadata(youtube, broadcast_id, title, description, tags)

    return youtube, broadcast_id, rtmp_url, stream_key


def complete_livestream(youtube, broadcast_id):
    print("Ending broadcast...")
    end_broadcast(youtube, broadcast_id)
    print(
        f"Livestream complete! Recording saved at: https://www.youtube.com/watch?v={broadcast_id}"
    )
