"""
groq_symphony_director.py
─────────────────────────────────────────────────────────────────────────────
Autonomous Symphony Director powered by Groq.

When USE_GROQ_SYMPHONY_DIRECTOR=1 is set, Groq will autonomously decide:
  • Which stream profile to use (e.g. rain_sleep_window, ocean_night_drift …)
  • Which visualizer to render
  • Which palette/color-mood to choose
  • Which daypart/season to force (overriding the real clock)
  • The "soothing_reasoning" it used to make those picks

Groq receives the full menu of available profiles + visualizers and returns
a structured JSON decision that is then injected into the stream plan.

Usage
-----
  from lib.groq_symphony_director import get_groq_symphony_decision
  decision = get_groq_symphony_decision(profiles_data, visualizer_ids)
  # → { "profile_id": "...", "visualizer_id": "...", "daypart": "...",
  #     "season": "...",  "palette_id": "...", "soothing_reasoning": "..." }
"""

from __future__ import annotations

import json
import os
import random
import time

import requests
from dotenv import load_dotenv

from lib.groq_json import parse_groq_json

load_dotenv()

GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
DEFAULT_GROQ_MODEL = "llama-3.3-70b-versatile"

# ── Quality profile hints — the best-sounding profiles Groq should favour ───
QUALITY_PROFILE_HINTS = [
    # Animal-dominant (highest priority — richest, most human-ear-pleasing)
    "night_crickets_sleep",
    "dawn_birdsong",
    "frog_pond_night",
    "whale_song_deep_ocean",
    "owl_forest_night",
    "tropical_bird_sanctuary",
    "wetland_chorus_dusk",
    "ancient_forest_animals",
    # Premium nature profiles
    "ocean_night_drift",
    "river_meditation",
    "forest_water_calm",
    "jungle_rain_retreat",
    "moonlit_fire_meditation",
    "underwater_dreamscape",
    "coastal_fog_morning",
    "whale_blue_meditation",
    "snow_fire_night",
    "dawn_birdsong_focus",
    "summer_cricket_garden",
    # Atmospheric (good but not animal-led)
    "rain_sleep_window",
    "alpine_wind_sleep",
    "fireplace_reading_room",
    "autumn_leaf_walk",
]

QUALITY_VISUALIZER_HINTS = [
    "aurora",
    "breathing_orb",
    "mist_layers",
    "ink_diffusion",
    "liquid_ribbons",
    "horizon_reflection",
    "particle_drift",
    "constellation",
    "rotating_mandala",
    "veil_lines",
]

VALID_DAYPARTS = ["dawn", "morning", "afternoon", "evening", "night", "late_night"]
VALID_SEASONS  = ["spring", "summer", "autumn", "winter"]

_SYSTEM_PROMPT = (
    "You are the Autonomous Symphony Director for a 24/7 ambience streaming channel called 'Symphony.Station'."
    " Your sole purpose is to select the BEST POSSIBLE stream profile right now — not a random one, not a mediocre one."
    " You are a world-class sound curator. Every choice must be intentional, beautiful, and deeply considered.\n\n"

    "QUALITY PRINCIPLES (non-negotiable):\n"
    "  1. The primary soundscape must be rich, natural, and immersive — not just noise or weather.\n"
    "  2. Animal sounds (birds, crickets, frogs, whales, owls) are the highest quality bed layers — prefer them when available.\n"
    "  3. Nature profiles (forest, ocean, river, rainforest, garden) are far superior to pure noise profiles.\n"
    "  4. Binaural beats MUST be paired with beautiful nature sounds so they feel medicinal, not clinical.\n"
    "  5. Noise-only or weather-wall profiles are last resort. Never pick them when richer alternatives exist.\n"
    "  6. The best sound experience makes the listener feel like they are SOMEWHERE real — a moonlit garden, a forest creek, an ocean shore.\n\n"

    "You will receive a JSON menu of all available stream profiles and visualizers."
    " Return ONLY a valid JSON object with these exact keys:\n"
    "  - profile_id        : must be one of the profile ids in the menu\n"
    "  - visualizer_id     : must be one of the allowed_visualizers for the chosen profile\n"
    "  - palette_id        : must be one of the palette_ids for the chosen profile\n"
    "  - daypart           : must be one of: dawn, morning, afternoon, evening, night, late_night\n"
    "  - season            : must be one of: spring, summer, autumn, winter\n"
    "  - soothing_reasoning: one evocative sentence (max 120 chars) explaining your choice as if speaking to the listener\n\n"

    "Selection Guidelines:\n"
    "  - Animal-dominant profiles (crickets, birds, frogs, whale) = highest priority for beauty.\n"
    "  - Nature-water profiles (ocean, river, waterfall, rainforest) = excellent choices.\n"
    "  - Fire + nature profiles (fireplace, campfire) = excellent for evening and night.\n"
    "  - Mixed nature + light weather = good. Pure weather/noise profiles = only if nothing better fits.\n"
    "  - Night and late_night dayparts are the most calming. Prefer them unless morning/dawn animals fit better.\n"
    "  - Vary your picks intelligently. Never repeat the same obvious choice. Surprise the listener beautifully.\n"
    "  - The listener deserves the BEST, not random filler. Act accordingly.\n\n"

    "CRITICAL: Return valid JSON only. No markdown, no explanation outside the JSON object."
)


def _build_director_prompt(profiles_data: dict, visualizer_ids: set) -> tuple[str, str]:
    """Build the system + user prompts sent to Groq."""

    profiles_menu = [
        {
            "id": p["id"],
            "display_name": p["display_name"],
            "allowed_dayparts": p.get("dayparts", []),
            "allowed_seasons":  p.get("seasons", []),
            "allowed_visualizers": p.get("allowed_visualizers", []),
            "palette_ids": [pal["id"] for pal in p.get("palette_sets", [])],
        }
        for p in profiles_data.get("profiles", [])
    ]

    user_prompt = json.dumps(
        {
            "task": "Select the highest-quality, most beautiful symphony stream to generate right now.",
            "profiles_menu": profiles_menu,
            "all_visualizers": sorted(visualizer_ids),
            "quality_profile_hints": QUALITY_PROFILE_HINTS,
            "quality_visualizer_hints": QUALITY_VISUALIZER_HINTS,
        },
        ensure_ascii=True,
        indent=None,
    )

    return _SYSTEM_PROMPT, user_prompt


def _validate_decision(decision: dict, profiles_data: dict, visualizer_ids: set) -> dict:
    """Validate Groq's decision against available options; fill in safe defaults if needed."""
    profiles = {p["id"]: p for p in profiles_data.get("profiles", [])}

    # Validate / fallback profile — prefer quality hints on fallback
    profile_id = decision.get("profile_id", "")
    if profile_id not in profiles:
        # Try quality hints first
        for hint in QUALITY_PROFILE_HINTS:
            if hint in profiles:
                profile_id = hint
                break
        else:
            profile_id = random.choice(list(profiles.keys()))
    profile = profiles[profile_id]

    # Validate / fallback visualizer
    allowed_visualizers = set(profile.get("allowed_visualizers", []))
    visualizer_id = decision.get("visualizer_id", "")
    if visualizer_id not in allowed_visualizers:
        quality_overlap = [v for v in QUALITY_VISUALIZER_HINTS if v in allowed_visualizers]
        visualizer_id = quality_overlap[0] if quality_overlap else list(allowed_visualizers)[0]

    # Validate / fallback palette
    palette_ids = [pal["id"] for pal in profile.get("palette_sets", [])]
    palette_id = decision.get("palette_id", "")
    if palette_id not in palette_ids:
        palette_id = palette_ids[0] if palette_ids else None

    # Validate daypart and season
    daypart = decision.get("daypart", "night")
    if daypart not in VALID_DAYPARTS or daypart not in profile.get("dayparts", VALID_DAYPARTS):
        overlap = [d for d in ["night", "late_night", "evening"] if d in profile.get("dayparts", [])]
        daypart = overlap[0] if overlap else profile.get("dayparts", ["night"])[0]

    season = decision.get("season", "spring")
    if season not in VALID_SEASONS or season not in profile.get("seasons", VALID_SEASONS):
        season = profile.get("seasons", ["spring"])[0]

    reasoning = str(
        decision.get("soothing_reasoning", "Groq selected the finest ambience for this moment.")
    )[:140]

    return {
        "profile_id":        profile_id,
        "visualizer_id":     visualizer_id,
        "palette_id":        palette_id,
        "daypart":           daypart,
        "season":            season,
        "soothing_reasoning": reasoning,
    }


def get_groq_symphony_decision(
    profiles_data: dict,
    visualizer_ids: set,
    *,
    retries: int = 2,
) -> dict | None:
    """
    Ask Groq to autonomously decide the most soothing symphony stream.

    Returns a validated decision dict, or None if Groq is not configured
    or USE_GROQ_SYMPHONY_DIRECTOR env var is not enabled.
    """
    if os.getenv("USE_GROQ_SYMPHONY_DIRECTOR", "0").strip().lower() not in {"1", "true", "yes", "on"}:
        return None

    api_key = os.getenv("GROQ_API_KEY", "").strip()
    if not api_key:
        print("[GroqDirector] GROQ_API_KEY not set — skipping autonomous decision.")
        return None

    model = os.getenv("GROQ_MODEL", DEFAULT_GROQ_MODEL).strip() or DEFAULT_GROQ_MODEL
    system_prompt, user_prompt = _build_director_prompt(profiles_data, visualizer_ids)

    for attempt in range(1, retries + 2):
        try:
            print(f"[GroqDirector] Selecting best symphony stream… (attempt {attempt})")
            response = requests.post(
                GROQ_API_URL,
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type":  "application/json",
                },
                json={
                    "model":       model,
                    "temperature": 0.75,   # Slightly lower = more consistent high-quality picks
                    "max_tokens":  512,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user",   "content": user_prompt},
                    ],
                },
                timeout=45,
            )
            response.raise_for_status()
            payload = response.json()
            raw_content = payload["choices"][0]["message"]["content"].strip()
            decision_raw = parse_groq_json(raw_content)
            decision = _validate_decision(decision_raw, profiles_data, visualizer_ids)
            print(
                f"[GroqDirector] ✅ Decision: profile={decision['profile_id']} | "
                f"visualizer={decision['visualizer_id']} | "
                f"{decision['daypart']} {decision['season']}\n"
                f"[GroqDirector] 💭 \"{decision['soothing_reasoning']}\""
            )
            return decision
        except json.JSONDecodeError as exc:
            print(f"[GroqDirector] Attempt {attempt} — JSON parse error: {exc}")
        except requests.HTTPError as exc:
            print(f"[GroqDirector] Attempt {attempt} — HTTP error: {exc}")
        except Exception as exc:
            print(f"[GroqDirector] Attempt {attempt} — Unexpected error: {exc}")

        if attempt <= retries:
            time.sleep(2 ** attempt)

    print("[GroqDirector] All attempts failed — falling back to standard stream plan selection.")
    return None
