from __future__ import annotations

import hashlib
import json
import os
import random
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from lib.audio_generation.catalog import load_merged_sound_catalog
from lib.radiant_shader_ids import RADIANT_SHADER_IDS

# Groq autonomous director — imported lazily to avoid hard dep when disabled
def _maybe_get_groq_symphony_decision(profiles_data, visualizer_ids):
    try:
        from lib.groq_symphony_director import get_groq_symphony_decision
        return get_groq_symphony_decision(profiles_data, visualizer_ids)
    except Exception as exc:
        print(f"[GroqDirector] Import/call failed: {exc}")
        return None


LIVESTREAM_PROFILES_PATH = Path("config/livestream_profiles.json")
DEFAULT_TIMEZONE = "America/Chicago"
SUPPORTED_VISUALIZER_IDS = {
    "aurora",
    "breathing_orb",
    "constellation",
    "ember_drift",
    "horizon_reflection",
    "ink_diffusion",
    "liquid_ribbons",
    "mist_layers",
    "monochrome_rain",
    "particle_drift",
    "particle_equalizer",
    "radial_rings",
    "rotating_mandala",
    "veil_lines",
    "morphing_polygon",
} | RADIANT_SHADER_IDS
VALID_DAYPARTS = {"dawn", "morning", "afternoon", "evening", "night", "late_night"}
VALID_SEASONS = {"spring", "summer", "autumn", "winter"}
ROLE_VOLUME_RANGES = {
    "bed": (0.38, 0.54),
    "secondary": (0.12, 0.26),
    "noise": (0.05, 0.14),
    "binaural": (0.03, 0.08),
    "accent": (0.04, 0.10),
}
COZY_SOUND_GAIN_MULTIPLIERS = {
    "nature_thunder": 0.62,
    "nature_whale": 0.74,
    "nature_cat": 0.58,
    "things_keyboard": 0.58,
    "things_typewriter": 0.52,
    "things_clock": 0.5,
    "things_wind_chimes": 0.64,
    "things_singing_bowl": 0.7,
    "noise_white": 0.82,
    "rain_heavy_rain": 0.9,
}
PROFILE_TITLE_STRATEGY = {
    "rain_sleep_window": {
        "sound_focus": "Soft Rain on a Warm Window",
        "benefits": "Deep Sleep & Relaxation",
    },
    "thunder_rain_deep_rest": {
        "sound_focus": "Thunderstorm White Noise",
        "benefits": "Deep Sleep & Relaxation",
    },
    "forest_water_calm": {
        "sound_focus": "Forest Creek & Waterfall Sounds",
        "benefits": "Study, Relaxation & Sleep",
    },
    "ocean_night_drift": {
        "sound_focus": "Ocean Waves at Night",
        "benefits": "Deep Sleep & Relaxation",
    },
    "snow_fire_night": {
        "sound_focus": "Fireplace, Snow & Wind Sounds",
        "benefits": "Deep Sleep & Relaxation",
    },
    "river_meditation": {
        "sound_focus": "Flowing River Sounds",
        "benefits": "Meditation, Relaxation & Sleep",
    },
    "library_focus_rain": {
        "sound_focus": "Library Rain Ambience",
        "benefits": "Study, Focus & Relaxation",
    },
    "cafe_focus_evening": {
        "sound_focus": "Cozy Cafe Rain Ambience",
        "benefits": "Study, Focus & Relaxation",
    },
    "train_night_journey": {
        "sound_focus": "Night Train Sounds",
        "benefits": "Sleep, Study & Relaxation",
    },
    "underwater_dreamscape": {
        "sound_focus": "Deep Ocean Ambience",
        "benefits": "Sleep, Meditation & Relaxation",
    },
    "fireplace_reading_room": {
        "sound_focus": "Fireplace Library Ambience",
        "benefits": "Reading, Focus & Relaxation",
    },
    "monsoon_study_desk": {
        "sound_focus": "Monsoon Desk Rain Sounds",
        "benefits": "Study, Focus & Deep Work",
    },
    "summer_cricket_garden": {
        "sound_focus": "Crickets, Frogs & Garden Night Sounds",
        "benefits": "Sleep & Relaxation",
    },
    "alpine_wind_sleep": {
        "sound_focus": "Mountain Wind & Snow Sounds",
        "benefits": "Deep Sleep & Relaxation",
    },
    "office_focus_hum": {
        "sound_focus": "Office Room Tone & Keyboard Ambience",
        "benefits": "Focus, Study & Deep Work",
    },
    "plane_cabin_drift": {
        "sound_focus": "Airplane Cabin Noise",
        "benefits": "Sleep & Relaxation",
    },
    "jungle_rain_retreat": {
        "sound_focus": "Rainforest Rain & Jungle Sounds",
        "benefits": "Sleep & Relaxation",
    },
    "autumn_leaf_walk": {
        "sound_focus": "Autumn Forest Walk Sounds",
        "benefits": "Focus, Relaxation & Calm",
    },
    "dawn_birdsong_focus": {
        "sound_focus": "Morning Birdsong & River Sounds",
        "benefits": "Focus, Study & Calm",
    },
    "storm_train_window": {
        "sound_focus": "Train Window Rain & Thunder",
        "benefits": "Deep Sleep & Relaxation",
    },
    "moonlit_fire_meditation": {
        "sound_focus": "Night Fireplace Ambience",
        "benefits": "Meditation, Sleep & Relaxation",
    },
    "coastal_fog_morning": {
        "sound_focus": "Foggy Ocean Morning Sounds",
        "benefits": "Calm, Focus & Relaxation",
    },
    "whale_blue_meditation": {
        "sound_focus": "Whale Calls & Deep Ocean Sounds",
        "benefits": "Meditation, Sleep & Relaxation",
    },
    "deep_brown_sleep": {
        "sound_focus": "Brown Noise & Sound Masking",
        "benefits": "Deep Sleep",
    },
}


def load_sound_catalog():
    return load_merged_sound_catalog()


def load_livestream_profiles():
    with LIVESTREAM_PROFILES_PATH.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    validate_livestream_profiles(payload)
    return payload


def validate_livestream_profiles(payload, sound_catalog=None):
    profiles = payload.get("profiles", [])
    seen_ids = set()
    for profile in profiles:
        profile_id = profile["id"]
        if profile_id in seen_ids:
            raise ValueError(f"Duplicate livestream profile id: {profile_id}")
        seen_ids.add(profile_id)

        palette_ids = {palette["id"] for palette in profile.get("palette_sets", [])}
        allowed_visualizers = set(profile.get("allowed_visualizers", []))
        if not allowed_visualizers:
            raise ValueError(
                f"Profile {profile_id} must define at least one allowed visualizer."
            )
        unknown_visualizers = allowed_visualizers - SUPPORTED_VISUALIZER_IDS
        if unknown_visualizers:
            raise ValueError(
                f"Profile {profile_id} uses unsupported visualizers: {sorted(unknown_visualizers)}"
            )

        dayparts = set(profile.get("dayparts", []))
        seasons = set(profile.get("seasons", []))
        if not dayparts or dayparts - VALID_DAYPARTS:
            raise ValueError(
                f"Profile {profile_id} has invalid dayparts: {sorted(dayparts)}"
            )
        if not seasons or seasons - VALID_SEASONS:
            raise ValueError(
                f"Profile {profile_id} has invalid seasons: {sorted(seasons)}"
            )

        variants = profile.get("example_variants", [])
        if len(variants) != 2:
            raise ValueError(
                f"Profile {profile_id} must define exactly 2 example variants."
            )
        for variant in variants:
            if variant["palette_id"] not in palette_ids:
                raise ValueError(
                    f"Profile {profile_id} example variant {variant['id']} references unknown palette {variant['palette_id']}."
                )
            if variant["visualizer_id"] not in allowed_visualizers:
                raise ValueError(
                    f"Profile {profile_id} example variant {variant['id']} references disallowed visualizer {variant['visualizer_id']}."
                )
            if variant["daypart"] not in dayparts:
                raise ValueError(
                    f"Profile {profile_id} example variant {variant['id']} references unsupported daypart {variant['daypart']}."
                )
            if variant["season"] not in seasons:
                raise ValueError(
                    f"Profile {profile_id} example variant {variant['id']} references unsupported season {variant['season']}."
                )

        layer_configs = profile.get("layers", {})
        unknown_roles = set(layer_configs) - set(ROLE_VOLUME_RANGES)
        if unknown_roles:
            raise ValueError(
                f"Profile {profile_id} defines unsupported audio layer roles: {sorted(unknown_roles)}"
            )
        if sound_catalog:
            available_sound_ids = set(sound_catalog)
            for role, config in layer_configs.items():
                unknown_sounds = set(config.get("sounds", [])) - available_sound_ids
                if unknown_sounds:
                    raise ValueError(
                        f"Profile {profile_id} role {role} references unknown sound ids: {sorted(unknown_sounds)}"
                    )


def resolve_daypart(local_now):
    minutes = local_now.hour * 60 + local_now.minute
    if 300 <= minutes <= 479:
        return "dawn"
    if 480 <= minutes <= 719:
        return "morning"
    if 720 <= minutes <= 1019:
        return "afternoon"
    if 1020 <= minutes <= 1259:
        return "evening"
    if minutes >= 1260 or minutes <= 59:
        return "night"
    return "late_night"


def resolve_season(local_now):
    month = local_now.month
    if month in (3, 4, 5):
        return "spring"
    if month in (6, 7, 8):
        return "summer"
    if month in (9, 10, 11):
        return "autumn"
    return "winter"


def resolve_stream_context(
    timezone_name=None, now=None, force_daypart=None, force_season=None
):
    timezone_name = timezone_name or os.getenv("STREAM_TIMEZONE") or DEFAULT_TIMEZONE
    zone = ZoneInfo(timezone_name)
    local_now = now.astimezone(zone) if now else datetime.now(zone)
    daypart = (
        force_daypart or os.getenv("STREAM_FORCE_DAYPART") or resolve_daypart(local_now)
    )
    season = (
        force_season or os.getenv("STREAM_FORCE_SEASON") or resolve_season(local_now)
    )
    metadata = {
        "timezone": timezone_name,
        "local_now": local_now.isoformat(),
        "timestamp_token": local_now.strftime("%Y%m%dT%H%M"),
        "daypart": daypart,
        "season": season,
    }
    return metadata


def seed_to_int(seed_text):
    return int(hashlib.sha256(str(seed_text).encode("utf-8")).hexdigest()[:16], 16)


def derive_seed(context_token, profile_id=None, explicit_seed=None):
    if explicit_seed:
        return str(explicit_seed)
    github_run_id = os.getenv("GITHUB_RUN_ID", "local")
    label = profile_id or "auto"
    return f"{label}-{context_token}-{github_run_id}"


def resolve_profile(
    profiles_data, daypart, season, requested_profile_id=None, selection_seed=None
):
    profiles = profiles_data["profiles"]
    if requested_profile_id:
        for profile in profiles:
            if profile["id"] == requested_profile_id:
                return profile
        raise ValueError(f"Unknown profile id: {requested_profile_id}")

    both = [p for p in profiles if daypart in p["dayparts"] and season in p["seasons"]]
    daypart_only = [p for p in profiles if daypart in p["dayparts"]]
    candidates = both or daypart_only or profiles
    rng = random.Random(seed_to_int(selection_seed or f"{daypart}-{season}"))
    total = sum(max(1, int(candidate.get("weight", 1))) for candidate in candidates)
    pick = rng.uniform(0, total)
    cursor = 0.0
    for candidate in candidates:
        cursor += max(1, int(candidate.get("weight", 1)))
        if pick <= cursor:
            return candidate
    return candidates[-1]


def _dedupe_tags(values):
    seen = set()
    output = []
    for value in values:
        tag = str(value).strip()
        if tag and tag.lower() not in seen:
            seen.add(tag.lower())
            output.append(tag)
    return output


def _volume_for_role(role, rng, sound_id=None):
    low, high = ROLE_VOLUME_RANGES[role]
    volume = rng.uniform(low, high)
    if sound_id:
        volume *= COZY_SOUND_GAIN_MULTIPLIERS.get(sound_id, 1.0)
    return round(max(0.02, min(0.62, volume)), 3)


def _build_burst_events(rng, duration_seconds):
    if duration_seconds <= 60:
        count = 1
    elif duration_seconds <= 300:
        count = rng.randint(1, 2)
    else:
        count = rng.randint(2, min(6, max(2, duration_seconds // 180)))
    latest = max(4.0, duration_seconds - 8.0)
    positions = sorted(rng.uniform(3.0, latest) for _ in range(count))
    events = []
    for start in positions:
        clip_duration = round(rng.uniform(2.4, 6.4), 2)
        fade_out = 0.8 if clip_duration > 1.6 else clip_duration / 2
        events.append(
            {
                "start": round(start, 2),
                "duration": clip_duration,
                "fade_in": 0.35,
                "fade_out": round(fade_out, 2),
            }
        )
    return events


def choose_layers(profile, sound_catalog, rng, duration_seconds):
    layers = []
    for role in ("bed", "secondary", "noise", "binaural", "accent"):
        config = profile["layers"].get(role, {})
        sounds = list(config.get("sounds", []))
        if not sounds:
            continue
        max_count = min(int(config.get("max", 0)), len(sounds))
        min_count = min(int(config.get("min", 0)), max_count)
        if max_count <= 0:
            continue
        count = rng.randint(min_count, max_count)
        if role == "bed" and count == 0:
            count = 1
        for sound_id in rng.sample(sounds, count):
            sound = sound_catalog[sound_id]
            mode = (
                "burst"
                if sound["default_mode"] == "burst" or role == "accent"
                else "continuous"
            )
            layer = {
                "sound_id": sound_id,
                "name": sound["name"],
                "category": sound["category"],
                "path": sound["path"],
                "role": role,
                "mode": mode,
                "volume": _volume_for_role(role, rng, sound_id=sound_id),
                "loop_safe": bool(sound["loop_safe"]),
                "license_source": sound["license_source"],
            }
            if mode == "burst":
                layer["events"] = _build_burst_events(rng, duration_seconds)
            layers.append(layer)
    return layers


def _select_by_id(values, selected_id):
    for value in values:
        if value["id"] == selected_id:
            return value
    raise ValueError(f"Unknown selection id: {selected_id}")


def _title_strategy(profile_id):
    return PROFILE_TITLE_STRATEGY.get(profile_id, {})


def _build_stream_title(profile, preview=False):
    strategy = _title_strategy(profile["id"])
    headline = profile["title_parts"]["headline"].strip()
    sound_focus = (
        strategy.get("sound_focus")
        or profile["thumbnail_parts"]["subtitle"].strip().title()
    )
    benefits = strategy.get("benefits") or "Sleep, Study & Relaxation"
    suffix = "[PREVIEW]" if preview else "[LIVE]"
    title = f"{headline} | {sound_focus} for {benefits} {suffix}"
    if len(title) <= 100:
        return title
    title = f"{headline} | {sound_focus} | {benefits} {suffix}"
    if len(title) <= 100:
        return title
    compact_benefits = benefits.replace("Relaxation", "Relax")
    return f"{headline} | {sound_focus} | {compact_benefits} {suffix}"[:100].rstrip()


def _build_stream_summary(profile):
    strategy = _title_strategy(profile["id"])
    channel_hook = (
        profile["title_parts"].get("channel_prefix", "Symphony Station").strip()
    )
    sound_focus = (
        strategy.get("sound_focus") or profile["thumbnail_parts"]["subtitle"].strip()
    )
    benefits = strategy.get("benefits") or "Sleep, study, and relaxation"
    return channel_hook, sound_focus, benefits


def build_stream_plan(
    sound_catalog,
    profiles_data,
    duration_seconds,
    render_mode="prerender",
    timezone_name=None,
    requested_profile_id=None,
    explicit_seed=None,
    force_daypart=None,
    force_season=None,
    variant=None,
):
    validate_livestream_profiles(profiles_data, sound_catalog=sound_catalog)

    # ── Groq Autonomous Symphony Director ─────────────────────────────────
    # When USE_GROQ_SYMPHONY_DIRECTOR=1 and no explicit overrides are given,
    # ask Groq to decide the most soothing profile/visualizer/palette/daypart.
    groq_decision = None
    if not variant and not requested_profile_id and not force_daypart and not force_season:
        groq_decision = _maybe_get_groq_symphony_decision(
            profiles_data, SUPPORTED_VISUALIZER_IDS
        )
    if groq_decision:
        # Groq overrides clock-based daypart/season and random profile selection
        force_daypart   = groq_decision["daypart"]
        force_season    = groq_decision["season"]
        requested_profile_id = groq_decision["profile_id"]
    # ── End Groq Director ──────────────────────────────────────────────────

    context = resolve_stream_context(
        timezone_name=timezone_name,
        force_daypart=variant["daypart"] if variant else force_daypart,
        force_season=variant["season"] if variant else force_season,
    )
    selection_seed = explicit_seed or (
        variant["seed"] if variant else derive_seed(context["timestamp_token"])
    )
    profile = resolve_profile(
        profiles_data,
        context["daypart"],
        context["season"],
        requested_profile_id=requested_profile_id,
        selection_seed=selection_seed,
    )
    final_seed = derive_seed(
        context["timestamp_token"],
        profile_id=profile["id"],
        explicit_seed=explicit_seed or (variant["seed"] if variant else None),
    )
    rng = random.Random(seed_to_int(final_seed))

    # Palette: Groq decision > variant > RNG
    if groq_decision and groq_decision.get("palette_id"):
        try:
            palette = _select_by_id(profile["palette_sets"], groq_decision["palette_id"])
        except ValueError:
            palette = rng.choice(profile["palette_sets"])
    elif variant and variant.get("palette_id"):
        palette = _select_by_id(profile["palette_sets"], variant["palette_id"])
    else:
        palette = rng.choice(profile["palette_sets"])

    # Visualizer: Groq decision > variant > RNG
    allowed_visualizers = profile["allowed_visualizers"]
    if groq_decision and groq_decision.get("visualizer_id") in allowed_visualizers:
        visualizer_id = groq_decision["visualizer_id"]
    elif variant and variant.get("visualizer_id"):
        visualizer_id = variant["visualizer_id"]
    else:
        visualizer_id = rng.choice(allowed_visualizers)

    layers = choose_layers(profile, sound_catalog, rng, duration_seconds)
    continuous_layers = [layer for layer in layers if layer["mode"] == "continuous"]
    tags = _dedupe_tags(
        profile["tags"]
        + [
            profile["display_name"],
            context["daypart"],
            context["season"],
            "Symphony Station",
        ]
    )
    metadata = {
        "profile_id": profile["id"],
        "profile": profile,
        "seed": final_seed,
        "render_mode": render_mode,
        "duration_seconds": duration_seconds,
        "duration_minutes": round(duration_seconds / 60, 2),
        "daypart": context["daypart"],
        "season": context["season"],
        "timezone": context["timezone"],
        "timestamp_token": context["timestamp_token"],
        "visualizer_id": visualizer_id,
        "palette": palette,
        "layers": layers,
        "active_count": max(1, len(continuous_layers) or len(layers)),
        "tags": tags,
        "example_variant_id": variant["id"] if variant else None,
        "context": context,
        # Groq director metadata (None if director was not used)
        "groq_symphony_decision": groq_decision,
    }
    return metadata


def build_stream_metadata(plan, preview=False, display_duration_seconds=None):
    profile = plan["profile"]
    effective_duration = (
        display_duration_seconds
        if display_duration_seconds is not None
        else plan["duration_seconds"]
    )
    hours = int(effective_duration // 3600)
    if preview:
        duration_label = "Preview"
    elif hours >= 1:
        duration_label = f"{hours} Hour{'s' if hours != 1 else ''}"
    else:
        duration_label = f"{int(effective_duration // 60)} Min"
    title = _build_stream_title(profile, preview=preview)
    channel_hook, sound_focus, benefits = _build_stream_summary(profile)
    layer_summary = ", ".join(layer["name"] for layer in plan["layers"][:5])
    description = (
        f"{title}\n"
        "--------------------------------------------------------------\n"
        f"{channel_hook}.\n"
        f"{sound_focus} for {benefits.lower()}.\n"
        f"{profile['title_parts']['descriptor']}\n\n"
        f"Stream length: {duration_label}\n\n"
        f"Ambient layers include: {layer_summary}\n\n"
        "----------------------------------------\n"
        "🔊 Turn on the stream and relax. No ads, no interruptions.\n"
        "💤 Perfect for sleeping, studying, working, or meditation.\n"
        "🎵 24/7 continuous stream available at Symphony Station."
    )
    metadata = {
        "title": title,
        "description": description,
        "thumbnail_title": profile["thumbnail_parts"]["title"],
        "badge_text": profile["title_parts"].get("channel_prefix", "Symphony.Station"),
        "thumbnail_subtitle": f"{profile['thumbnail_parts']['subtitle']} | {plan['daypart'].replace('_', ' ').title()} {plan['season'].title()}",
        "tags": plan["tags"],
        "profile_id": plan["profile_id"],
        "seed": plan["seed"],
        "render_mode": plan["render_mode"],
        "visualizer_id": plan["visualizer_id"],
        "palette": plan["palette"],
        "daypart": plan["daypart"],
        "season": plan["season"],
        "timezone": plan["timezone"],
        "sound_layers": plan["layers"],
    }
    try:
        from lib.groq_copywriter import generate_stream_copy

        ai_copy = generate_stream_copy(plan, metadata, preview=preview)
        if ai_copy:
            metadata.update(ai_copy)
    except Exception:
        pass
    return metadata
