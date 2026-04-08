from __future__ import annotations

import re
from difflib import SequenceMatcher
from pathlib import Path

import requests

from lib.audio_generation.catalog import GENERATED_SOUND_ROOT, read_generated_catalog, upsert_generated_catalog
from lib.config import FREESOUND_API_KEY


FREESOUND_GENERATOR_ID = "freesound"
FREESOUND_SOUND_ROOT = GENERATED_SOUND_ROOT / FREESOUND_GENERATOR_ID
SIMILARITY_THRESHOLD = 8.0
LOOP_TAGS = {"loop", "loops", "loopable", "seamless", "perfect-loop", "perfect_loop"}


def _tokenize(value):
    return {part for part in re.split(r"[^a-z0-9]+", str(value).lower()) if part}


def _ordered_tokens(value):
    return [part for part in re.split(r"[^a-z0-9]+", str(value).lower()) if part]


def _sound_tokens(sound):
    tokens = set()
    tokens |= _tokenize(sound.get("id", ""))
    tokens |= _tokenize(sound.get("name", ""))
    tokens |= _tokenize(sound.get("category", ""))
    for tag in sound.get("tags", []):
        tokens |= _tokenize(tag)
    return tokens


def find_similar_catalog_sound(requested_sound_id, sound_catalog):
    requested_token_list = _ordered_tokens(requested_sound_id)
    requested_tokens = set(requested_token_list)
    if not requested_tokens:
        return None

    requested_text = requested_sound_id.replace("_", " ").replace("-", " ").lower()
    leading_token = requested_token_list[0]
    best_sound = None
    best_score = 0.0

    for sound in sound_catalog.values():
        candidate_tokens = _sound_tokens(sound)
        overlap = len(requested_tokens & candidate_tokens)
        if overlap == 0:
            continue

        candidate_text = " ".join(
            [
                str(sound.get("id", "")),
                str(sound.get("name", "")),
                str(sound.get("category", "")),
                " ".join(str(tag) for tag in sound.get("tags", [])),
            ]
        ).lower()
        ratio = SequenceMatcher(None, requested_text, candidate_text).ratio()
        first_token_bonus = 3.0 if leading_token in candidate_tokens else 0.0
        score = overlap * 3.0 + ratio * 5.0 + first_token_bonus

        if score > best_score:
            best_score = score
            best_sound = sound

    if best_score < SIMILARITY_THRESHOLD:
        return None
    return best_sound


def _generated_sound_id(requested_sound_id):
    return f"freesound_{requested_sound_id.strip().lower().replace('-', '_')}"


def _existing_generated_sound(requested_sound_id):
    payload = read_generated_catalog(FREESOUND_GENERATOR_ID)
    expected_id = _generated_sound_id(requested_sound_id)
    for sound in payload.get("sounds", []):
        if sound.get("id") == expected_id:
            return sound
    return None


def _freesound_query(requested_sound_id):
    query = requested_sound_id.replace("_", " ").replace("-", " ").strip()
    return f"{query} ambient loop"


def _preview_url(sound_details):
    previews = sound_details.get("previews", {})
    return (
        previews.get("preview-hq-mp3")
        or previews.get("preview-lq-mp3")
        or previews.get("preview-hq-ogg")
        or previews.get("preview-lq-ogg")
    )


def _download_preview(preview_url, destination: Path):
    destination.parent.mkdir(parents=True, exist_ok=True)
    response = requests.get(preview_url, stream=True, timeout=60)
    response.raise_for_status()
    with destination.open("wb") as handle:
        for chunk in response.iter_content(chunk_size=8192):
            if chunk:
                handle.write(chunk)


def _choose_best_freesound_result(results, requested_sound_id):
    requested_tokens = _tokenize(requested_sound_id)
    best_result = None
    best_score = float("-inf")

    for sound_details in results:
        preview_url = _preview_url(sound_details)
        if not preview_url:
            continue

        tags = {str(tag).lower() for tag in sound_details.get("tags", [])}
        candidate_tokens = set(tags)
        candidate_tokens |= _tokenize(sound_details.get("name", ""))
        overlap = len(requested_tokens & candidate_tokens)
        loop_bonus = 8.0 if tags & LOOP_TAGS else 0.0
        duration_bonus = min(float(sound_details.get("duration") or 0.0), 120.0) / 30.0
        score = overlap * 3.0 + loop_bonus + duration_bonus

        if score > best_score:
            best_score = score
            best_result = sound_details

    return best_result


def fetch_freesound_sound(requested_sound_id):
    existing = _existing_generated_sound(requested_sound_id)
    if existing:
        return existing
    if not FREESOUND_API_KEY:
        return None

    query = _freesound_query(requested_sound_id)
    search_response = requests.get(
        "https://freesound.org/apiv2/search/text/",
        params={
            "query": query,
            "sort": "rating_desc",
            "page_size": 8,
            "token": FREESOUND_API_KEY,
        },
        timeout=30,
    )
    search_response.raise_for_status()
    search_payload = search_response.json()

    detailed_results = []
    for result in search_payload.get("results", []):
        sound_id = result.get("id")
        if not sound_id:
            continue
        details_response = requests.get(
            f"https://freesound.org/apiv2/sounds/{sound_id}/",
            params={"token": FREESOUND_API_KEY},
            timeout=30,
        )
        if details_response.ok:
            detailed_results.append(details_response.json())

    chosen = _choose_best_freesound_result(detailed_results, requested_sound_id)
    if not chosen:
        return None

    generated_id = _generated_sound_id(requested_sound_id)
    preview_url = _preview_url(chosen)
    extension = Path(preview_url.split("?")[0]).suffix or ".mp3"
    output_path = FREESOUND_SOUND_ROOT / f"{generated_id}{extension}"
    _download_preview(preview_url, output_path)

    tags = list(dict.fromkeys(
        list(chosen.get("tags", []))
        + requested_sound_id.replace("-", "_").split("_")
        + ["freesound", requested_sound_id]
    ))
    loop_safe = bool({str(tag).lower() for tag in chosen.get("tags", [])} & LOOP_TAGS)

    sound = {
        "id": generated_id,
        "name": chosen.get("name") or requested_sound_id.replace("_", " ").title(),
        "category": requested_sound_id.split("_", 1)[0],
        "path": output_path.as_posix(),
        "license_source": f"Freesound ({chosen.get('license', 'license unknown')})",
        "license_note": (
            f"Auto-fetched from Freesound for missing requested sound id '{requested_sound_id}'. "
            f"Original Freesound sound id: {chosen.get('id')}."
        ),
        "default_mode": "continuous",
        "loop_safe": loop_safe,
        "tags": tags,
    }

    upsert_generated_catalog(
        FREESOUND_GENERATOR_ID,
        [sound],
        metadata={
            "source": "Freesound API",
            "query": query,
            "requested_sound_id": requested_sound_id,
        },
    )
    return sound


def resolve_sound_reference(requested_sound_id, sound_catalog):
    if requested_sound_id in sound_catalog:
        return sound_catalog[requested_sound_id]

    similar = find_similar_catalog_sound(requested_sound_id, sound_catalog)
    if similar:
        print(
            f"[AudioFallback] Requested sound '{requested_sound_id}' missing; "
            f"using similar catalog sound '{similar['id']}'."
        )
        return similar

    fetched = fetch_freesound_sound(requested_sound_id)
    if fetched:
        sound_catalog[fetched["id"]] = fetched
        print(
            f"[AudioFallback] Requested sound '{requested_sound_id}' missing; "
            f"downloaded Freesound fallback '{fetched['id']}'."
        )
        return fetched

    raise KeyError(
        f"Requested sound '{requested_sound_id}' was not found in the catalog, "
        "no similar local sound matched, and Freesound did not return a usable fallback."
    )
