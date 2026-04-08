import sys
sys.dont_write_bytecode = True
import json
from lib.livestream import get_youtube_service


def setup_channel():
    youtube = get_youtube_service()

    # First, get current channel info
    current = youtube.channels().list(
        part='snippet,brandingSettings,status',
        mine=True
    ).execute()

    if not current['items']:
        print("ERROR: No YouTube channel found for this account.")
        return

    channel = current['items'][0]
    channel_id = channel['id']
    print(f"Found channel: {channel_id}")
    print(f"Current name: {channel.get('snippet', {}).get('title', 'N/A')}")

    # ─── Channel Branding Settings ───
    branding = {
        'id': channel_id,
        'brandingSettings': {
            'channel': {
                'title': 'Cozy Lo-fi Beats',
                'description': (
                    'Welcome to Cozy Lo-fi Beats \u2728\n\n'
                    'Your 24/7 sanctuary for lo-fi hip hop music, cozy study vibes, '
                    'and peaceful atmospheres.\n\n'
                    'Imagine a warm study room at night \u2014 rain streaking down the window, '
                    'a soft amber desk lamp glowing, a steaming ceramic mug beside your books, '
                    'and a sleeping tabby cat curled up on the bookshelf. '
                    'Studio Ghibli-inspired visuals meet chill beats to help you study, '
                    'work, relax, and sleep.\n\n'
                    '\u2615 What you will find here:\n'
                    '  \u2022 Live lo-fi hip hop streams every 2 hours\n'
                    '  \u2022 Cozy rain & ambient study sessions\n'
                    '  \u2022 Relaxing nature soundscapes\n'
                    '  \u2022 Cinematic lo-fi atmospheres\n'
                    '  \u2022 Sleep & meditation music\n\n'
                    '\U0001f4da Perfect for studying, coding, reading, working, or just vibing.\n\n'
                    '\U0001f514 Subscribe & hit the bell so you never miss a cozy stream!\n\n'
                    '#lofi #studybeats #chill #cozy #rain #ambient #ghibli'
                ),
                'keywords': (
                    'lofi lo-fi "hip hop" "study beats" "chill beats" cozy rain '
                    '"study music" "relaxing music" ambient "Studio Ghibli" anime '
                    '"sleep music" "coding music" "focus music" "lo-fi radio" '
                    '"beats to study to" "beats to relax to" "rainy day" '
                    '"coffee shop" vibes peaceful calm'
                ),
                'defaultLanguage': 'en',
                'country': 'IN',
            }
        }
    }

    # Update channel branding
    print("\nUpdating channel branding...")
    youtube.channels().update(
        part='brandingSettings',
        body=branding
    ).execute()
    print("Channel branding updated!")

    # ─── Default Upload Settings ───
    # Set default category, tags, description for all future uploads
    print("\nSetting default upload settings...")
    defaults_body = {
        'id': channel_id,
        'brandingSettings': {
            'channel': branding['brandingSettings']['channel'],
        }
    }

    youtube.channels().update(
        part='brandingSettings',
        body=defaults_body
    ).execute()
    print("Default upload settings configured!")

    # ─── Create Playlists ───
    playlists_to_create = [
        {
            'title': '\U0001f319 Rainy Night Study Sessions',
            'description': 'Cozy rainy night lo-fi streams for deep focus and relaxation.'
        },
        {
            'title': '\u2615 Coffee Shop Vibes',
            'description': 'Warm coffee shop ambiance with chill lo-fi beats.'
        },
        {
            'title': '\U0001f3b5 Lo-fi Livestream Recordings',
            'description': 'All past lo-fi livestream recordings. Cozy vibes on demand.'
        },
        {
            'title': '\U0001f4da Study & Focus Music',
            'description': 'Long-form lo-fi music sessions perfect for studying and working.'
        },
        {
            'title': '\U0001f30c Sleep & Relaxation',
            'description': 'Peaceful ambient soundscapes and lo-fi beats for sleep and meditation.'
        },
        {
            'title': '\U0001f343 Nature & Rain Ambiance',
            'description': 'Rain sounds, forest ambiance, and nature-inspired lo-fi sessions.'
        }
    ]

    # Get existing playlists to avoid duplicates
    existing = youtube.playlists().list(
        part='snippet',
        mine=True,
        maxResults=50
    ).execute()
    existing_titles = [p['snippet']['title'] for p in existing.get('items', [])]

    print("\nCreating playlists...")
    for pl in playlists_to_create:
        if pl['title'] in existing_titles:
            print(f"  Skipped (exists): {pl['title']}")
            continue

        youtube.playlists().insert(
            part='snippet,status',
            body={
                'snippet': {
                    'title': pl['title'],
                    'description': pl['description'],
                },
                'status': {
                    'privacyStatus': 'public'
                }
            }
        ).execute()
        print(f"  Created: {pl['title']}")

    # ─── Print Summary ───
    print("\n" + "=" * 60)
    print("  CHANNEL SETUP COMPLETE!")
    print("=" * 60)
    print(f"\n  Channel ID: {channel_id}")
    print(f"  Channel URL: https://www.youtube.com/channel/{channel_id}")
    print(f"  Name: Cozy Lo-fi Beats")
    print(f"  Playlists created: {len(playlists_to_create)}")
    print(f"\n  Next steps:")
    print(f"  1. Upload a profile picture manually (API can't do this)")
    print(f"  2. Upload a channel banner at YouTube Studio")
    print(f"  3. Enable live streaming at https://www.youtube.com/features")
    print(f"  4. Wait 24 hours, then run: python main.py --livestream")
    print("=" * 60)


if __name__ == "__main__":
    setup_channel()
