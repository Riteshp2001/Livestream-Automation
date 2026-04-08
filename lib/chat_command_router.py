"""
chat_command_router.py
─────────────────────────────────────────────────────────────────────────────
Genre-aware poll registry for chat-driven audio voting.

Profiles are grouped by genre. When building a poll, only profiles from the
SAME genre cluster as the currently playing profile are offered as options.
This keeps polls contextually relevant — sleep viewers get sleep options,
nature viewers get nature options, etc.
"""
from __future__ import annotations

# ── Genre → list of (display_label, profile_id) ──────────────────────────────
#
# Each genre bucket is a self-contained "vibe world". Poll options are drawn
# exclusively from the same bucket as the current profile.
#
GENRE_REGISTRY: dict[str, list[tuple[str, str]]] = {

    # ── Night / Sleep / Deep Rest ─────────────────────────────────────────────
    "sleep": [
        ("🌧️  Rain on a Window",      "rain_sleep_window"),
        ("⛈️  Thunderstorm Deep Rest", "thunder_rain_deep_rest"),
        ("🌙  Deep Brown Sleep",       "deep_brown_sleep"),
        ("❄️  Snow & Fire Night",      "snow_fire_night"),
        ("🌊  Alpine Wind Sleep",      "alpine_wind_sleep"),
        ("🚂  Night Train",            "train_night_journey"),
        ("✈️  Plane Cabin Drift",      "plane_cabin_drift"),
    ],

    # ── Animals / Nature — Night ───────────────────────────────────────────────
    "night_nature": [
        ("🦗  Cricket Night",          "night_crickets_sleep"),
        ("🐸  Frog Pond",              "frog_pond_night"),
        ("🦉  Owl Forest Night",       "owl_forest_night"),
        ("🌾  Wetland Chorus Dusk",    "wetland_chorus_dusk"),
        ("🌲  Ancient Forest Animals", "ancient_forest_animals"),
        ("🐋  Whale Song Ocean",       "whale_song_deep_ocean"),
    ],

    # ── Animals / Nature — Dawn & Day ─────────────────────────────────────────
    "day_nature": [
        ("🐦  Dawn Birdsong",          "dawn_birdsong"),
        ("🌿  Tropical Bird Sanctuary","tropical_bird_sanctuary"),
        ("🌴  Jungle Rain Retreat",    "jungle_rain_retreat"),
        ("🌲  Ancient Forest Animals", "ancient_forest_animals"),
        ("🦗  Summer Cricket Garden",  "summer_cricket_garden"),
        ("🌅  Coastal Fog Morning",    "coastal_fog_morning"),
    ],

    # ── Water / Ocean / Flow ──────────────────────────────────────────────────
    "water": [
        ("🌊  Ocean Night Drift",      "ocean_night_drift"),
        ("🌅  River Meditation",       "river_meditation"),
        ("🌊  Coastal Fog Morning",    "coastal_fog_morning"),
        ("🔵  Underwater Dreamscape",  "underwater_dreamscape"),
        ("🌧️  Rain on a Window",       "rain_sleep_window"),
        ("🌿  Forest Water Calm",      "forest_water_calm"),
    ],

    # ── Fire / Cozy / Warm ────────────────────────────────────────────────────
    "cozy": [
        ("🔥  Moonlit Fire Meditation","moonlit_fire_meditation"),
        ("❄️  Snow & Fire Night",      "snow_fire_night"),
        ("🕯️  Fireplace Reading Room", "fireplace_reading_room"),
        ("🌧️  Rain on a Window",       "rain_sleep_window"),
        ("🚂  Night Train",            "train_night_journey"),
    ],

    # ── Focus / Study / Work ──────────────────────────────────────────────────
    "focus": [
        ("☕  Cozy Cafe Evening",      "cafe_focus_evening"),
        ("📚  Library Rain",           "library_focus_rain"),
        ("🖥️  Office Focus",           "office_focus_hum"),
        ("🌅  River Meditation",       "river_meditation"),
        ("🌧️  Monsoon Study Desk",     "monsoon_study_desk"),
    ],

    # ── Meditation / Ambient / Binaural ──────────────────────────────────────
    "meditation": [
        ("🐋  Whale Song Ocean",       "whale_song_deep_ocean"),
        ("🔵  Underwater Dreamscape",  "underwater_dreamscape"),
        ("🌅  River Meditation",       "river_meditation"),
        ("🔥  Moonlit Fire Med.",      "moonlit_fire_meditation"),
        ("🌲  Forest Water Calm",      "forest_water_calm"),
        ("🌊  Autumn Leaf Walk",       "autumn_leaf_walk"),
    ],
}

# ── Flat profile_id → genre lookup ────────────────────────────────────────────
_PROFILE_TO_GENRE: dict[str, str] = {}
for _genre, _entries in GENRE_REGISTRY.items():
    for _, _pid in _entries:
        # First genre wins (for profiles that appear in multiple)
        _PROFILE_TO_GENRE.setdefault(_pid, _genre)

# ── All labels for reverse lookups ────────────────────────────────────────────
PROFILE_LABELS: dict[str, str] = {}
for _entries in GENRE_REGISTRY.values():
    for _label, _pid in _entries:
        PROFILE_LABELS.setdefault(_pid, _label)


def get_genre(profile_id: str) -> str:
    """Return the genre of a profile, defaulting to 'sleep'."""
    return _PROFILE_TO_GENRE.get(profile_id, "sleep")


def get_poll_candidates(
    current_profile_id: str | None,
    count: int = 5,
    rng_seed: int | None = None,
) -> list[tuple[str, str]]:
    """
    Return `count` (label, profile_id) pairs for a poll.

    - Options are drawn ONLY from the same genre as the current profile
    - Current profile is always included (labeled as 'now playing') so
      viewers can vote to keep the current vibe
    - No duplicates
    """
    import random

    genre = get_genre(current_profile_id) if current_profile_id else "sleep"
    pool = list(GENRE_REGISTRY.get(genre, GENRE_REGISTRY["sleep"]))

    rng = random.Random(rng_seed)
    rng.shuffle(pool)

    chosen: list[tuple[str, str]] = []

    # Always slot in the current profile first
    if current_profile_id:
        for label, pid in pool:
            if pid == current_profile_id:
                chosen.append((f"{label}  ✦ now playing", pid))
                break

    for label, pid in pool:
        if len(chosen) >= count:
            break
        if pid not in {p for _, p in chosen}:
            chosen.append((label, pid))

    # If genre pool was too small, pad from a neighbour genre (shouldn't happen
    # with our registry, but better safe than a crash)
    if len(chosen) < count:
        fallback_genre = "sleep" if genre != "sleep" else "night_nature"
        for label, pid in GENRE_REGISTRY.get(fallback_genre, []):
            if len(chosen) >= count:
                break
            if pid not in {p for _, p in chosen}:
                chosen.append((label, pid))

    rng.shuffle(chosen)
    return chosen[:count]


def format_poll_message(
    candidates: list[tuple[str, str]],
    vote_window_seconds: int = 120,
) -> str:
    """Build the text-based poll message posted to YouTube live chat."""
    mins = vote_window_seconds // 60
    lines = [
        "🗳️  VIBE VOTE — what plays next?",
        f"Type a number to vote. Closes in {mins} min:",
        "",
    ]
    number_emojis = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣"]
    for index, (label, _) in enumerate(candidates):
        emoji = number_emojis[index] if index < len(number_emojis) else f"{index + 1}."
        lines.append(f"{emoji}  {label}")
    lines += [
        "",
        "Most votes wins · 1 vote per person 🎧",
    ]
    return "\n".join(lines)


def format_result_message(
    winning_label: str,
    vote_count: int,
    next_poll_minutes: int = 10,
) -> str:
    """Announce the poll winner in chat."""
    clean = winning_label.replace("  ✦ now playing", "").strip()
    noun = "vote" if vote_count == 1 else "votes"
    return (
        f"🎵 Switching to {clean}! ({vote_count} {noun}) "
        f"Next vote in {next_poll_minutes} min 🕐"
    )
