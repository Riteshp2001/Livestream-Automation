"""
groq_symphony_director.py
─────────────────────────────────────────────────────────────────────────────
Autonomous Symphony Director powered by Groq.

When USE_GROQ_SYMPHONY_DIRECTOR=1 is set, Groq will autonomously decide:
  • Which stream profile to use (e.g. rain_sleep_window, ocean_night_drift …)
  • Which visualizer to render
  • Which palette/color-mood to choose
  • Which daypart/season to force (overriding the real clock)
  • The  "soothing_reasoning" it used to make those picks

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

load_dotenv()

GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
DEFAULT_GROQ_MODEL = "llama-3.3-70b-versatile"

# ── Soothing sound profiles that Groq is allowed to weight heavily ──────────
SOOTHING_PROFILE_HINTS = [
    "rain_sleep_window",
    "ocean_night_drift",
    "snow_fire_night",
    "river_meditation",
    "jungle_rain_retreat",
    "moonlit_fire_meditation",
    "coastal_fog_morning",
    "whale_blue_meditation",
    "deep_brown_sleep",
    "underwater_dreamscape",
    "alpine_wind_sleep",
    "forest_water_calm",
    "thunder_rain_deep_rest",
    "summer_cricket_garden",
    "dawn_birdsong_focus",
]

SOOTHING_VISUALIZER_HINTS = [
    "aurora",
    "breathing_orb",
    "mist_layers",
    "ink_diffusion",
    "liquid_ribbons",
    "horizon_reflection",
    "veil_lines",
    "particle_drift",
    "rotating_mandala",
    "constellation",
]

VALID_DAYPARTS = ["dawn", "morning", "afternoon", "evening", "night", "late_night"]
VALID_SEASONS  = ["spring", "summer", "autumn", "winter"]


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

    system_prompt = (
        "You are the Autonomous Symphony Director for a 24/7 ambience streaming channel called 'Symphony.Station'. "
        "Your sole purpose is to decide what kind of deeply soothing and relaxing symphony music video should play RIGHT NOW. "
        "You have full creative authority — your decision is final and autonomous. "
        "The goal is the most calming, immersive, sleep- or meditation-inducing experience possible.\n\n"
        "You will receive a JSON menu of all available stream profiles and visualizers. "
        "You must return a JSON object (and ONLY that JSON, no other text) with these exact keys:\n"
        "  • profile_id      — must be one of the profile ids in the menu\n"
        "  • visualizer_id   — must be one of the allowed_visualizers for the chosen profile\n"
        "  • palette_id      — must be one of the palette_ids for the chosen profile\n"
        "  • daypart         — must be one of: dawn, morning, afternoon, evening, night, late_night\n"
        "  • season          — must be one of: spring, summer, autumn, winter\n"
        "  • soothing_reasoning — a single evocative sentence (max 120 chars) explaining WHY this combination\n"
        "                         is the most soothing right now (written as if speaking to the viewer)\n\n"
        "Guidelines:\n"
        "  - Always bias towards sleep, deep relaxation, and gentle meditation experiences.\n"
        "  - Night and late_night dayparts produce the most calming atmospheres.\n"
        "  - Visualizers like aurora, breathing_orb, mist_layers, ink_diffusion, liquid_ribbons are the most soothing.\n"
        "  - Rain, ocean, fire, and nature profiles produce the most relaxing soundscapes.\n"
        "  - Pick the combination that a tired listener would find most healing at THIS moment.\n"
        "  - Be creative — vary your picks each time based on your internal sense of what feels right.\n"
        "CRITICAL: Return valid JSON only. No markdown, no explanation outside the JSON."
    )

    user_prompt = json.dumps(
        {
            "task": "Decide the most soothing symphony stream to generate right now.",
            "profiles_menu": profiles_menu,
            "all_visualizers": sorted(visualizer_ids),
            "soothing_profile_hints": SOOTHING_PROFILE_HINTS,
            "soothing_visualizer_hints": SOOTHING_VISUALIZER_HINTS,
        },
        ensure_ascii=True,
        indent=None,
    )

    return system_prompt, user_prompt


def _validate_decision(decision: dict, profiles_data: dict, visualizer_ids: set) -> dict:
    """Validate Groq's decision against available options; fill in safe defaults if needed."""
    profiles = {p["id"]: p for p in profiles_data.get("profiles", [])}

    # Validate / fallback profile
    profile_id = decision.get("profile_id", "")
    if profile_id not in profiles:
        profile_id = random.choice(SOOTHING_PROFILE_HINTS)
        while profile_id not in profiles:
            profile_id = random.choice(list(profiles.keys()))
    profile = profiles[profile_id]

    # Validate / fallback visualizer
    allowed_visualizers = set(profile.get("allowed_visualizers", []))
    visualizer_id = decision.get("visualizer_id", "")
    if visualizer_id not in allowed_visualizers:
        soothing_overlap = [v for v in SOOTHING_VISUALIZER_HINTS if v in allowed_visualizers]
        visualizer_id = soothing_overlap[0] if soothing_overlap else list(allowed_visualizers)[0]

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

    season = decision.get("season", "winter")
    if season not in VALID_SEASONS or season not in profile.get("seasons", VALID_SEASONS):
        season = profile.get("seasons", ["winter"])[0]

    reasoning = str(decision.get("soothing_reasoning", "Groq selected the most soothing ambience for this moment."))[:140]

    return {
        "profile_id": profile_id,
        "visualizer_id": visualizer_id,
        "palette_id": palette_id,
        "daypart": daypart,
        "season": season,
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
            print(f"[GroqDirector] Asking Groq to autonomously pick the most soothing symphony… (attempt {attempt})")
            response = requests.post(
                GROQ_API_URL,
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": model,
                    "temperature": 0.85,   # Higher temp = more creative, autonomous picks
                    "max_tokens": 512,
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
            # Strip markdown fences if present
            raw_content = raw_content.replace("```json", "").replace("```", "").strip()
            decision_raw = json.loads(raw_content, strict=False)
            decision = _validate_decision(decision_raw, profiles_data, visualizer_ids)
            print(
                f"[GroqDirector] ✅ Decision: profile={decision['profile_id']} | "
                f"visualizer={decision['visualizer_id']} | "
                f"{decision['daypart']} {decision['season']}\n"
                f"[GroqDirector] 💭 \"{decision['soothing_reasoning']}\""
            )
            return decision
        except Exception as exc:
            print(f"[GroqDirector] Attempt {attempt} failed: {exc}")
            if attempt <= retries:
                time.sleep(2 ** attempt)

    print("[GroqDirector] All attempts failed — falling back to standard stream plan selection.")
    return None
