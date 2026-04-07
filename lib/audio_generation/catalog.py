from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path


BASE_SOUND_CATALOG_PATH = Path("data/stream_sound_catalog.json")
GENERATED_SOUND_ROOT = Path("assets") / "stream_sounds" / "generated"
GENERATED_SOUND_CATALOG_DIR = GENERATED_SOUND_ROOT / "catalogs"
REQUIRED_SOUND_FIELDS = {
    "id",
    "name",
    "category",
    "path",
    "license_source",
    "license_note",
    "default_mode",
    "loop_safe",
    "tags",
}


def _read_catalog_payload(path: Path):
    with path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, dict):
        raise ValueError(f"Sound catalog {path} must contain a JSON object.")
    sounds = payload.get("sounds", [])
    if not isinstance(sounds, list):
        raise ValueError(f"Sound catalog {path} must define a 'sounds' list.")
    return payload


def iter_sound_catalog_paths():
    yield BASE_SOUND_CATALOG_PATH
    if GENERATED_SOUND_CATALOG_DIR.exists():
        for path in sorted(GENERATED_SOUND_CATALOG_DIR.glob("*.json")):
            yield path


def _resolve_sound_path(sound):
    sound_path = Path(sound["path"])
    return sound_path if sound_path.is_absolute() else Path.cwd() / sound_path


def _validate_sound_entry(sound, source_path: Path):
    missing_fields = REQUIRED_SOUND_FIELDS - set(sound)
    if missing_fields:
        raise ValueError(
            f"Sound entry from {source_path} is missing required fields: {sorted(missing_fields)}"
        )
    if not isinstance(sound["tags"], list):
        raise ValueError(f"Sound entry {sound['id']} from {source_path} must use a list for tags.")
    if sound["default_mode"] not in {"continuous", "burst"}:
        raise ValueError(
            f"Sound entry {sound['id']} from {source_path} has invalid default_mode {sound['default_mode']!r}."
        )
    resolved_path = _resolve_sound_path(sound)
    if not resolved_path.exists():
        raise FileNotFoundError(
            f"Sound entry {sound['id']} from {source_path} points to a missing file: {resolved_path}"
        )


def load_merged_sound_catalog():
    merged = {}
    for catalog_path in iter_sound_catalog_paths():
        payload = _read_catalog_payload(catalog_path)
        for sound in payload["sounds"]:
            _validate_sound_entry(sound, catalog_path)
            sound_id = sound["id"]
            if sound_id in merged:
                raise ValueError(
                    f"Duplicate sound id {sound_id!r} found while loading {catalog_path}."
                )
            merged[sound_id] = sound
    return merged


def generated_catalog_path(generator_id: str):
    return GENERATED_SOUND_CATALOG_DIR / f"{generator_id}.json"


def read_generated_catalog(generator_id: str):
    path = generated_catalog_path(generator_id)
    if not path.exists():
        return {"generator": generator_id, "sounds": []}
    return _read_catalog_payload(path)


def upsert_generated_catalog(generator_id: str, sounds, metadata=None):
    path = generated_catalog_path(generator_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    existing_payload = read_generated_catalog(generator_id)
    merged = {sound["id"]: sound for sound in existing_payload.get("sounds", [])}
    for sound in sounds:
        merged[sound["id"]] = sound
    payload = {
        "generator": generator_id,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "sounds": [merged[key] for key in sorted(merged)],
    }
    if metadata:
        payload["metadata"] = metadata
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2)
    return payload
