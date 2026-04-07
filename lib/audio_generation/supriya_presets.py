from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class SupriyaPreset:
    id: str
    name: str
    family: str
    description: str
    category: str
    default_duration_seconds: int
    default_mode: str
    loop_safe: bool
    tags: tuple[str, ...]

    def to_dict(self):
        return asdict(self)


SUPRIYA_PRESETS = {
    preset.id: preset
    for preset in (
        SupriyaPreset(
            id="deep-drone",
            name="Supriya Deep Drone",
            family="drones",
            description="A slowly shifting low drone bed for sleep and deep-focus layers.",
            category="procedural",
            default_duration_seconds=1800,
            default_mode="continuous",
            loop_safe=False,
            tags=("supriya", "generated", "drone", "sleep", "focus", "ambient"),
        ),
        SupriyaPreset(
            id="pink-cloud",
            name="Supriya Pink Cloud",
            family="textures",
            description="Filtered pink-noise wash for soft masking and atmospheric mixes.",
            category="procedural",
            default_duration_seconds=1800,
            default_mode="continuous",
            loop_safe=False,
            tags=("supriya", "generated", "pink-noise", "texture", "masking", "calm"),
        ),
        SupriyaPreset(
            id="meditation-pulse",
            name="Supriya Meditation Pulse",
            family="pulses",
            description="A soft tonal pulse bed that sits under meditation and mindful visuals.",
            category="procedural",
            default_duration_seconds=1800,
            default_mode="continuous",
            loop_safe=False,
            tags=("supriya", "generated", "pulse", "meditation", "ambient", "tonal"),
        ),
        SupriyaPreset(
            id="brown-tide",
            name="Supriya Brown Tide",
            family="textures",
            description="Low brown-noise movement for sleep masking and deep night streams.",
            category="procedural",
            default_duration_seconds=1800,
            default_mode="continuous",
            loop_safe=False,
            tags=("supriya", "generated", "brown-noise", "sleep", "masking", "night"),
        ),
        SupriyaPreset(
            id="black-hole-voice",
            name="Supriya Black Hole Voice",
            family="voices",
            description="A calm voice-like formant drone with a deep-space undertow for cosmic ambient mixes.",
            category="procedural",
            default_duration_seconds=1800,
            default_mode="continuous",
            loop_safe=False,
            tags=("supriya", "generated", "voice-like", "cosmic", "black-hole", "ambient", "calm"),
        ),
    )
}


def get_supriya_preset(preset_id: str):
    try:
        return SUPRIYA_PRESETS[preset_id]
    except KeyError as error:
        raise ValueError(f"Unknown Supriya preset id: {preset_id}") from error


def list_supriya_presets():
    return [SUPRIYA_PRESETS[key].to_dict() for key in sorted(SUPRIYA_PRESETS)]
