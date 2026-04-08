import json
import os
import sys
import time

from lib.generated_stream_runtime import (
    create_generated_pack,
    generate_example_sets,
    generate_profile_reviews,
    generate_test_videos,
    resolve_stream_plan,
    start_live_generated_stream,
)
from lib.local_livestream_assets import (
    build_stream_output_paths,
    discover_local_livestream_assets,
    generate_local_livestream_metadata,
    generate_stream_thumbnail,
)
from lib.stream_generation import build_stream_metadata


DEFAULT_VISUAL_LOOP_SECONDS = 20 * 60


def append_stream_history(stream_log):
    log_file = "data/stream_history.json"
    try:
        with open(log_file, "r", encoding="utf-8") as handle:
            history = json.load(handle)
    except (FileNotFoundError, json.JSONDecodeError):
        history = {"streams": []}
    history.setdefault("streams", []).append(stream_log)
    with open(log_file, "w", encoding="utf-8") as handle:
        json.dump(history, handle, indent=4)
    print(f"\nStream logged to {log_file}")


def _visual_loop_seconds():
    return int(float(os.getenv("STREAM_VISUAL_LOOP_MINUTES", "20")) * 60)


def _stream_duration_minutes(configured_duration_minutes):
    override_duration = os.getenv("STREAM_DURATION_MINUTES")
    return (
        float(override_duration) if override_duration else configured_duration_minutes
    )


def _generated_stream_env_options():
    return {
        "requested_profile_id": os.getenv("STREAM_PROFILE_ID") or None,
        "explicit_seed": os.getenv("STREAM_SEED") or None,
        "timezone_name": os.getenv("STREAM_TIMEZONE") or None,
        "force_daypart": os.getenv("STREAM_FORCE_DAYPART") or None,
        "force_season": os.getenv("STREAM_FORCE_SEASON") or None,
    }


def _run_pack_livestream(
    local_assets, duration_minutes, expected_channel_id, extra_history=None
):
    from lib.livestream import (
        complete_livestream,
        get_youtube_service,
        validate_authenticated_channel,
        set_broadcast_thumbnail,
        setup_livestream,
    )
    from lib.stream_engine import start_rtmp_stream

    duration_seconds = int(duration_minutes * 60)
    metadata = generate_local_livestream_metadata(local_assets, duration_minutes)
    archive_path, thumbnail_path = build_stream_output_paths(metadata["title"])
    generate_stream_thumbnail(
        metadata["thumbnail_title"],
        metadata["thumbnail_subtitle"],
        thumbnail_path,
        video_path=local_assets["video_path"],
        badge_text=metadata["badge_text"],
    )

    youtube = get_youtube_service()
    youtube, channel = validate_authenticated_channel(youtube, expected_channel_id)
    youtube, broadcast_id, rtmp_url, stream_key = setup_livestream(
        metadata["title"],
        metadata["description"],
        metadata["tags"],
        youtube=youtube,
        channel=channel,
        expected_channel_id=expected_channel_id,
    )
    set_broadcast_thumbnail(youtube, broadcast_id, thumbnail_path)

    try:
        stream_exit_code = start_rtmp_stream(
            local_assets["video_path"],
            local_assets["audio_path"],
            rtmp_url,
            stream_key,
            duration_seconds,
            local_recording_path=archive_path,
        )
    finally:
        time.sleep(10)
        complete_livestream(youtube, broadcast_id)

    if stream_exit_code not in (0, None):
        raise RuntimeError(f"ffmpeg streaming failed with exit code {stream_exit_code}")

    history_entry = {
        "broadcast_id": broadcast_id,
        "theme": "Local Asset Livestream",
        "asset_pack": local_assets["pack_name"],
        "title": metadata["title"],
        "duration_minutes": duration_minutes,
        "video_file": local_assets["video_name"],
        "audio_file": local_assets["audio_name"],
        "thumbnail_file": thumbnail_path,
        "archive_file": archive_path,
        "url": f"https://www.youtube.com/watch?v={broadcast_id}",
    }
    if extra_history:
        history_entry.update(extra_history)
    append_stream_history(history_entry)
    print(f"Recording available at: https://www.youtube.com/watch?v={broadcast_id}")


def _run_external_livestream(duration_minutes, expected_channel_id):
    from lib.content_handler import (
        load_used_content,
        save_used_content,
        search_and_download_meditation_video,
        search_and_download_music,
    )
    from lib.livestream import (
        complete_livestream,
        get_youtube_service,
        validate_authenticated_channel,
        set_broadcast_thumbnail,
        setup_livestream,
    )
    from lib.livestream_metadata import (
        generate_livestream_metadata,
        get_audio_query,
        get_video_query,
        load_themes,
        pick_random_theme,
    )
    from lib.stream_engine import start_rtmp_stream

    themes_data = load_themes()
    used_content = load_used_content()
    theme = pick_random_theme(themes_data)
    video_query = get_video_query(theme)
    audio_query = get_audio_query(theme)
    video_url = search_and_download_meditation_video(
        used_content["videos"], video_query, quality="large"
    )
    if not video_url:
        video_url = search_and_download_meditation_video(
            used_content["videos"], video_query, quality="medium"
        )
    if not video_url:
        video_url = search_and_download_meditation_video(
            used_content["videos"], "cozy rain night", quality="large"
        )
    if not video_url:
        print("FATAL: Could not download any video. Aborting livestream.")
        sys.exit(1)
    audio_url, _ = search_and_download_music(audio_query, used_content["audios"])
    if not audio_url:
        audio_url, _ = search_and_download_music("rain ambient", used_content["audios"])
    if not audio_url:
        print("FATAL: Could not download any audio. Aborting livestream.")
        sys.exit(1)
    used_content["videos"].append(video_url)
    used_content["audios"].append(audio_url)
    save_used_content(used_content)

    metadata = generate_livestream_metadata(theme, duration_minutes)
    archive_path, thumbnail_path = build_stream_output_paths(metadata["title"])
    generate_stream_thumbnail(
        metadata["title"], theme["vibe"], thumbnail_path, video_path="video.mp4"
    )
    youtube = get_youtube_service()
    youtube, channel = validate_authenticated_channel(youtube, expected_channel_id)
    youtube, broadcast_id, rtmp_url, stream_key = setup_livestream(
        metadata["title"],
        metadata["description"],
        metadata["tags"],
        youtube=youtube,
        channel=channel,
        expected_channel_id=expected_channel_id,
    )
    set_broadcast_thumbnail(youtube, broadcast_id, thumbnail_path)
    try:
        stream_exit_code = start_rtmp_stream(
            "video.mp4",
            "music.mp3",
            rtmp_url,
            stream_key,
            int(duration_minutes * 60),
            local_recording_path=archive_path,
        )
    finally:
        time.sleep(10)
        complete_livestream(youtube, broadcast_id)
    if stream_exit_code not in (0, None):
        raise RuntimeError(f"ffmpeg streaming failed with exit code {stream_exit_code}")
    append_stream_history(
        {
            "broadcast_id": broadcast_id,
            "theme": theme["name"],
            "title": metadata["title"],
            "duration_minutes": duration_minutes,
            "video_query": video_query,
            "audio_query": audio_query,
            "thumbnail_file": thumbnail_path,
            "archive_file": archive_path,
            "url": f"https://www.youtube.com/watch?v={broadcast_id}",
        }
    )
    print(f"Recording available at: https://www.youtube.com/watch?v={broadcast_id}")


def run_livestream_mode():
    import sys

    def print_status(msg):
        print(f"[STATUS] {msg}")
        sys.stdout.flush()

    from lib.livestream import (
        complete_livestream,
        LivestreamSetupError,
        get_youtube_service,
        validate_authenticated_channel,
        set_broadcast_thumbnail,
        setup_livestream,
    )
    from lib.livestream_metadata import load_themes

    print_status("Starting livestream setup")

    themes_data = load_themes()
    print_status(
        f"Loaded themes: {len(themes_data.get('themes', []))} themes available"
    )

    duration_minutes = _stream_duration_minutes(themes_data["stream_duration_minutes"])
    print_status(f"Stream duration: {duration_minutes} minutes")

    expected_channel_id = os.getenv("YOUTUBE_CHANNEL_ID")
    print_status(
        f"Expected channel ID: {'configured' if expected_channel_id else 'not configured'}"
    )

    content_source = (
        os.getenv("STREAM_CONTENT_SOURCE", "generated").strip().lower() or "generated"
    )
    render_mode = (
        os.getenv("STREAM_RENDER_MODE", "prerender").strip().lower() or "prerender"
    )
    print_status(f"Content source: {content_source}, render mode: {render_mode}")

    if content_source == "generated":
        if render_mode == "live":
            try:
                print_status("Resolving stream plan")
                plan = resolve_stream_plan(
                    duration_seconds=_visual_loop_seconds(),
                    render_mode="live",
                    **_generated_stream_env_options(),
                )
                print_status("Stream plan resolved successfully")

                print_status("Building stream metadata")
                metadata = build_stream_metadata(
                    plan, display_duration_seconds=int(duration_minutes * 60)
                )
                print_status(f"Metadata built: {metadata['title']}")

                archive_path, thumbnail_path = build_stream_output_paths(
                    metadata["title"]
                )
                print_status(
                    f"Output paths: archive={archive_path}, thumbnail={thumbnail_path}"
                )

                print_status("Generating stream thumbnail")
                generate_stream_thumbnail(
                    metadata["thumbnail_title"],
                    metadata["thumbnail_subtitle"],
                    thumbnail_path,
                    badge_text=metadata["badge_text"],
                )
                print_status("Thumbnail generated")

                print_status("Preparing YouTube livestream service")
                youtube = get_youtube_service()
                youtube, channel = validate_authenticated_channel(
                    youtube, expected_channel_id
                )
                print_status(f"Authenticated to YouTube channel: {channel['title']}")

                print_status("Creating YouTube broadcast")
                youtube, broadcast_id, rtmp_url, stream_key = setup_livestream(
                    metadata["title"],
                    metadata["description"],
                    metadata["tags"],
                    youtube=youtube,
                    channel=channel,
                    expected_channel_id=expected_channel_id,
                )
                print_status(f"Broadcast created: {broadcast_id}")
                print_status(f"RTMP URL: {rtmp_url}")

                print_status("Setting broadcast thumbnail")
                set_broadcast_thumbnail(youtube, broadcast_id, thumbnail_path)
                print_status("Thumbnail set on broadcast")

                try:
                    print_status("Starting live stream encoder")
                    print_status(f"RTMP URL: {rtmp_url}")
                    print_status(f"Stream key: {'***' if stream_key else 'MISSING'}")
                    print_status(f"Plan layers: {len(plan.get('layers', []))}")

                    # ── Fetch live chat ID for poll scheduler ─────────────────────
                    live_chat_id = None
                    try:
                        bc_info = youtube.liveBroadcasts().list(
                            part="snippet", id=broadcast_id
                        ).execute()
                        items = bc_info.get("items", [])
                        if items:
                            live_chat_id = items[0]["snippet"].get("liveChatId")
                        if live_chat_id:
                            print_status(f"Live chat ID: {live_chat_id}")
                            from lib.live_audio_switcher import post_stream_intro_comment
                            post_stream_intro_comment(youtube, live_chat_id)
                        else:
                            print_status("Warning: could not fetch live chat ID — polls disabled")
                    except Exception as chat_err:
                        print_status(f"Chat setup error: {chat_err} — polls disabled")

                    # ── Pomodoro + AI DJ overlay threads (still active) ──────────
                    try:
                        from lib.stream_interactions import start_pomodoro_thread
                        from lib.ai_dj import start_ai_dj_thread
                        start_pomodoro_thread()
                        start_ai_dj_thread()
                        print_status("Overlay threads started")
                    except Exception as mod_err:
                        print_status(f"Could not start interaction overlays: {mod_err}")

                    result = start_live_generated_stream(
                        duration_seconds         = int(duration_minutes * 60),
                        display_duration_seconds = int(duration_minutes * 60),
                        rtmp_url                 = rtmp_url,
                        stream_key               = stream_key,
                        archive_path             = archive_path,
                        plan                     = plan,
                        youtube_service          = youtube,
                        live_chat_id             = live_chat_id,
                    )

                    print_status(f"Stream completed successfully: {result}")
                except Exception as e:
                    print_status(f"STREAM FAILED: {type(e).__name__}: {str(e)}")
                    import traceback

                    traceback.print_exc()
                    raise
                finally:
                    print_status("Encoder process exited")
                    time.sleep(10)
                    complete_livestream(youtube, broadcast_id)

                if result["exit_code"] not in (0, None):
                    raise RuntimeError(
                        f"Live generated stream failed with exit code {result['exit_code']}"
                    )
                append_stream_history(
                    {
                        "broadcast_id": broadcast_id,
                        "theme": result["plan"]["profile"]["display_name"],
                        "title": metadata["title"],
                        "duration_minutes": duration_minutes,
                        "render_mode": "live",
                        "profile_id": result["plan"]["profile_id"],
                        "seed": result["plan"]["seed"],
                        "visualizer_id": result["plan"]["visualizer_id"],
                        "thumbnail_file": thumbnail_path,
                        "archive_file": archive_path,
                        "url": f"https://www.youtube.com/watch?v={broadcast_id}",
                    }
                )
                print(
                    f"Recording available at: https://www.youtube.com/watch?v={broadcast_id}"
                )
                return
            except LivestreamSetupError as error:
                print(f"FATAL: {error}")
                sys.exit(1)
            except Exception as error:
                print(
                    f"Generated live mode failed. Falling back to prerender/manual path. Reason: {error}"
                )

        try:
            generated = create_generated_pack(
                duration_seconds=_visual_loop_seconds(),
                display_duration_seconds=int(duration_minutes * 60),
                render_mode="prerender",
                preview=False,
                **_generated_stream_env_options(),
            )
            if generated["assets"]:
                _run_pack_livestream(
                    generated["assets"],
                    duration_minutes,
                    expected_channel_id,
                    extra_history={
                        "theme": generated["plan"]["profile"]["display_name"],
                        "render_mode": "prerender",
                        "profile_id": generated["plan"]["profile_id"],
                        "seed": generated["plan"]["seed"],
                        "visualizer_id": generated["plan"]["visualizer_id"],
                        "generated_pack_dir": generated["output_dir"],
                    },
                )
                return
        except LivestreamSetupError as error:
            print(f"FATAL: {error}")
            sys.exit(1)
        except Exception as error:
            print(
                f"Generated prerender mode failed. Falling back to manual/external path. Reason: {error}"
            )

    if content_source in {"generated", "manual"}:
        local_assets = discover_local_livestream_assets()
        if local_assets:
            _run_pack_livestream(local_assets, duration_minutes, expected_channel_id)
            return

    _run_external_livestream(duration_minutes, expected_channel_id)


def run_generate_pack_mode():
    result = create_generated_pack(
        duration_seconds=_visual_loop_seconds(),
        display_duration_seconds=int(_stream_duration_minutes(20) * 60),
        render_mode=os.getenv("STREAM_RENDER_MODE", "prerender"),
        **_generated_stream_env_options(),
    )
    print(
        json.dumps(
            {"output_dir": result["output_dir"], "metadata": result["metadata"]},
            indent=2,
        )
    )


def run_generate_example_sets_mode():
    outputs = generate_example_sets()
    print(
        json.dumps(
            [
                {
                    "output_dir": item["output_dir"],
                    "profile_id": item["plan"]["profile_id"],
                    "variant": item["plan"]["example_variant_id"],
                }
                for item in outputs
            ],
            indent=2,
        )
    )


def run_generate_test_videos_mode():
    outputs = generate_test_videos()
    print(
        json.dumps(
            [
                {
                    "output_dir": item["output_dir"],
                    "profile_id": item["plan"]["profile_id"],
                    "variant": item["plan"]["example_variant_id"],
                }
                for item in outputs
            ],
            indent=2,
        )
    )


def run_generate_profile_reviews_mode():
    outputs = generate_profile_reviews()
    print(
        json.dumps(
            [
                {
                    "output_dir": item["output_dir"],
                    "profile_id": item["plan"]["profile_id"],
                    "variant": item["plan"]["example_variant_id"],
                }
                for item in outputs
            ],
            indent=2,
        )
    )


def run_resolve_stream_profile_mode():
    plan = resolve_stream_plan(
        duration_seconds=_visual_loop_seconds(),
        render_mode=os.getenv("STREAM_RENDER_MODE", "prerender"),
        **_generated_stream_env_options(),
    )
    metadata = build_stream_metadata(
        plan,
        display_duration_seconds=int(_stream_duration_minutes(20) * 60),
    )
    print(json.dumps({"plan": plan, "metadata": metadata}, indent=2))
