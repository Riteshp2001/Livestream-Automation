import json
import random


def load_themes():
    with open('config/livestream_themes.json', 'r') as f:
        return json.load(f)


def pick_random_theme(themes_data):
    theme = random.choice(themes_data['themes'])
    print(f"Selected theme: {theme['name']}")
    return theme


def get_video_query(theme):
    return random.choice(theme['video_queries'])


def get_audio_query(theme):
    return random.choice(theme['audio_queries'])


def generate_livestream_metadata(theme, duration_minutes):
    hours_label = f"{int(duration_minutes // 60)} Hour" if duration_minutes >= 60 else f"{int(duration_minutes)} Min"
    if duration_minutes >= 120:
        hours_label += "s"
    title = f"Symphony Station | {hours_label} {theme['name']} Ambience [LIVE]"

    description = (
        f"{title}\n"
        f"--------------------------------------------------------------\n"
        f"\u25ba Welcome to Symphony Station! \U0001f319\n"
        f"Are you looking for a calm and comforting place to relax, slow your thoughts, and settle into restful sleep? You are in the right space.\n\n"
        f"\u25ba Tonight's stream is built around {theme['name'].lower()} visuals and gentle ambient sound designed to help you unwind, study, meditate, or rest.\n\n"
        f"\u25ba Visual mood: {theme['vibe']}\n\n"
        f"\u25ba Perfect for:\n"
        f"  \u2022 Sleep and bedtime wind-down\n"
        f"  \u2022 Quiet reading and journaling\n"
        f"  \u2022 Studying and deep focus\n"
        f"  \u2022 Stress relief and relaxation\n"
        f"  \u2022 Peaceful background ambience\n\n"
        f"\u25ba Subscribe to Symphony Station and turn on notifications for more calming ambience, night visuals, and sleep-safe streams.\n\n"
        f"#sleepmusic #nightambience #relaxingambience #symphonystation"
    )

    tags = [
        "sleep music", "rain sounds", "relaxing ambience", "study ambience",
        "night ambience", "deep sleep", "peaceful background", "stress relief",
        "reading ambience", "calm sounds", "bedtime ambience",
        theme['name'].lower()
    ]

    return {
        'title': title,
        'description': description,
        'tags': tags,
        'theme_name': theme['name'],
        'duration_minutes': duration_minutes
    }

