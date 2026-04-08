from __future__ import annotations

import importlib.util
import json
import os
import shutil
import subprocess
from pathlib import Path

from lib.audio_generation.catalog import GENERATED_SOUND_ROOT, upsert_generated_catalog
from lib.audio_generation.supriya_presets import SUPRIYA_PRESETS, get_supriya_preset, list_supriya_presets
from lib.stream_engine import get_ffmpeg_binary


SUPRIYA_GENERATOR_ID = "supriya"
SUPRIYA_SOUND_ROOT = GENERATED_SOUND_ROOT / SUPRIYA_GENERATOR_ID
DEFAULT_SAMPLE_RATE = 44100


def _truthy(value):
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


def _scsynth_path():
    return shutil.which("scsynth") or shutil.which("scsynth.exe")


def get_supriya_runtime_status():
    ffmpeg_path = None
    ffmpeg_error = None
    try:
        ffmpeg_path = get_ffmpeg_binary()
    except Exception as error:
        ffmpeg_error = str(error)

    scsynth_path = _scsynth_path()
    supriya_installed = importlib.util.find_spec("supriya") is not None
    return {
        "generator": SUPRIYA_GENERATOR_ID,
        "fit_for_repo": True,
        "fit_summary": (
            "Supriya is a good fit for repo-owned procedural ambient audio renders; "
            "it is not a source library for natural field recordings."
        ),
        "supriya_installed": supriya_installed,
        "scsynth_path": scsynth_path,
        "ffmpeg_path": ffmpeg_path,
        "ffmpeg_error": ffmpeg_error,
        "can_render": bool(supriya_installed and scsynth_path and ffmpeg_path),
        "preset_count": len(SUPRIYA_PRESETS),
        "presets": list_supriya_presets(),
    }


def _require_runtime():
    status = get_supriya_runtime_status()
    if not status["supriya_installed"]:
        raise RuntimeError(
            "Supriya is not installed. Run 'pip install -r requirements.txt' to add the Python package."
        )
    if not status["scsynth_path"]:
        raise RuntimeError(
            "SuperCollider scsynth was not found on PATH. Install SuperCollider to render Supriya presets."
        )
    if not status["ffmpeg_path"]:
        raise RuntimeError(f"FFmpeg is unavailable: {status['ffmpeg_error'] or 'unknown error'}")
    return status


def _import_supriya():
    import supriya
    from supriya.ugens import (
        BPF,
        BrownNoise,
        FreeVerb,
        LFPulse,
        LPF,
        Mix,
        Out,
        Pan2,
        PinkNoise,
        Pulse,
        RLPF,
        SinOsc,
        SynthDefBuilder,
        VarSaw,
    )

    return {
        "module": supriya,
        "BPF": BPF,
        "BrownNoise": BrownNoise,
        "FreeVerb": FreeVerb,
        "LFPulse": LFPulse,
        "LPF": LPF,
        "Mix": Mix,
        "Out": Out,
        "Pan2": Pan2,
        "PinkNoise": PinkNoise,
        "Pulse": Pulse,
        "RLPF": RLPF,
        "SinOsc": SinOsc,
        "SynthDefBuilder": SynthDefBuilder,
        "VarSaw": VarSaw,
    }


def _build_deep_drone(api):
    with api["SynthDefBuilder"](amp=0.14, base_frequency=55, out=0) as builder:
        oscillators = api["VarSaw"].ar(
            frequency=builder["base_frequency"] * (1.0, 1.4983, 2.002),
            width=(0.21, 0.35, 0.49),
        )
        source = api["Mix"].new(oscillators) * 0.2
        sweep = api["SinOsc"].kr(frequency=0.013) * 600 + 1400
        filtered = api["LPF"].ar(source=source, frequency=sweep)
        wet = api["FreeVerb"].ar(source=filtered, mix=0.32, room_size=0.86, damping=0.48)
        stereo = api["Pan2"].ar(source=wet * builder["amp"], position=api["SinOsc"].kr(frequency=0.006) * 0.35)
        api["Out"].ar(bus=builder["out"], source=stereo)
    return builder.build(name="repo:supriya:deep-drone"), {}


def _build_pink_cloud(api):
    with api["SynthDefBuilder"](amp=0.18, color=1450, out=0) as builder:
        source = api["PinkNoise"].ar() * 0.55
        sweep = api["SinOsc"].kr(frequency=0.017) * 500 + builder["color"]
        band = api["BPF"].ar(source=source, frequency=sweep, reciprocal_of_q=0.22)
        softened = api["LPF"].ar(source=band, frequency=4200)
        wet = api["FreeVerb"].ar(source=softened, mix=0.28, room_size=0.74, damping=0.56)
        stereo = api["Pan2"].ar(source=wet * builder["amp"], position=api["SinOsc"].kr(frequency=0.0045) * 0.28)
        api["Out"].ar(bus=builder["out"], source=stereo)
    return builder.build(name="repo:supriya:pink-cloud"), {}


def _build_meditation_pulse(api):
    with api["SynthDefBuilder"](amp=0.12, base_frequency=108, out=0) as builder:
        pulse = api["Pulse"].ar(
            frequency=(builder["base_frequency"], builder["base_frequency"] * 1.5),
            width=0.37,
        )
        tone = api["Mix"].new(pulse) * 0.14
        undertone = api["SinOsc"].ar(frequency=builder["base_frequency"] * 0.5) * 0.06
        gate = api["LFPulse"].kr(frequency=0.32, width=0.22)
        source = (tone + undertone) * (gate * 0.6 + 0.4)
        filtered = api["RLPF"].ar(
            source=source,
            frequency=api["SinOsc"].kr(frequency=0.014) * 360 + 980,
            reciprocal_of_q=0.18,
        )
        wet = api["FreeVerb"].ar(source=filtered, mix=0.26, room_size=0.7, damping=0.52)
        stereo = api["Pan2"].ar(source=wet * builder["amp"], position=api["SinOsc"].kr(frequency=0.0075) * 0.22)
        api["Out"].ar(bus=builder["out"], source=stereo)
    return builder.build(name="repo:supriya:meditation-pulse"), {}


def _build_brown_tide(api):
    with api["SynthDefBuilder"](amp=0.2, brightness=620, out=0) as builder:
        source = api["BrownNoise"].ar() * 0.65
        filtered = api["RLPF"].ar(
            source=source,
            frequency=api["SinOsc"].kr(frequency=0.009) * 180 + builder["brightness"],
            reciprocal_of_q=0.12,
        )
        softened = api["LPF"].ar(source=filtered, frequency=1600)
        wet = api["FreeVerb"].ar(source=softened, mix=0.22, room_size=0.68, damping=0.45)
        stereo = api["Pan2"].ar(source=wet * builder["amp"], position=api["SinOsc"].kr(frequency=0.0035) * 0.18)
        api["Out"].ar(bus=builder["out"], source=stereo)
    return builder.build(name="repo:supriya:brown-tide"), {}


def _build_black_hole_voice(api):
    with api["SynthDefBuilder"](amp=0.11, base_frequency=92, out=0) as builder:
        vibrato = api["SinOsc"].kr(frequency=0.18) * 2.2
        phonation = api["VarSaw"].ar(
            frequency=(
                builder["base_frequency"] + vibrato,
                builder["base_frequency"] * 1.004 + vibrato * 0.72,
            ),
            width=(0.48, 0.53),
        )
        voice_source = api["Mix"].new(phonation) * 0.11 + api["PinkNoise"].ar() * 0.06
        formant_shift = api["SinOsc"].kr(frequency=0.012) * 90
        formants = api["Mix"].new(
            (
                api["BPF"].ar(
                    source=voice_source,
                    frequency=460 + formant_shift,
                    reciprocal_of_q=0.045,
                )
                * 1.0,
                api["BPF"].ar(
                    source=voice_source,
                    frequency=920 + formant_shift * 0.68,
                    reciprocal_of_q=0.06,
                )
                * 0.72,
                api["BPF"].ar(
                    source=voice_source,
                    frequency=2480 - formant_shift * 0.42,
                    reciprocal_of_q=0.085,
                )
                * 0.38,
            )
        )
        undertow = api["RLPF"].ar(
            source=api["BrownNoise"].ar() * 0.2,
            frequency=api["SinOsc"].kr(frequency=0.009) * 80 + 190,
            reciprocal_of_q=0.11,
        )
        hush = api["SinOsc"].kr(frequency=0.028) * 0.08 + 0.92
        shaped = api["LPF"].ar(source=(formants + undertow * 0.65) * hush, frequency=2900)
        wet = api["FreeVerb"].ar(source=shaped, mix=0.38, room_size=0.92, damping=0.72)
        stereo = api["Pan2"].ar(source=wet * builder["amp"], position=api["SinOsc"].kr(frequency=0.0042) * 0.18)
        api["Out"].ar(bus=builder["out"], source=stereo)
    return builder.build(name="repo:supriya:black-hole-voice"), {}


PRESET_BUILDERS = {
    "black-hole-voice": _build_black_hole_voice,
    "deep-drone": _build_deep_drone,
    "pink-cloud": _build_pink_cloud,
    "meditation-pulse": _build_meditation_pulse,
    "brown-tide": _build_brown_tide,
}


def _sound_paths(preset):
    preset_dir = SUPRIYA_SOUND_ROOT / preset.family
    return preset_dir / f"{preset.id}.wav", preset_dir / f"{preset.id}.ogg"


def _catalog_sound_entry(preset, ogg_path: Path, duration_seconds: int):
    return {
        "id": f"supriya_{preset.id.replace('-', '_')}",
        "name": preset.name,
        "category": preset.category,
        "path": ogg_path.as_posix(),
        "license_source": "Repo-owned procedural audio rendered via Supriya",
        "license_note": (
            "Generated locally from in-repo Supriya preset definitions. "
            "Re-rendering requires the Supriya Python package and SuperCollider scsynth."
        ),
        "default_mode": preset.default_mode,
        "loop_safe": preset.loop_safe,
        "tags": list(preset.tags) + [f"{duration_seconds}s"],
    }


def _render_score_to_wav(score, wav_path: Path, duration_seconds: int, sample_rate: int):
    from supriya.io import render as render_score

    wav_path.parent.mkdir(parents=True, exist_ok=True)
    output_path, exit_code = render_score(
        score,
        output_file_path=wav_path,
        duration=duration_seconds,
        header_format="wav",
        sample_format="int24",
        sample_rate=sample_rate,
    )
    if exit_code != 0 or not output_path:
        raise RuntimeError(f"Supriya render failed for {wav_path.name} with exit code {exit_code}.")
    return Path(output_path)


def _transcode_wav_to_ogg(wav_path: Path, ogg_path: Path, duration_seconds: int):
    ffmpeg_binary = get_ffmpeg_binary()
    fade_in = min(1.5, max(0.15, duration_seconds * 0.01))
    fade_out = min(4.0, max(0.5, duration_seconds * 0.02))
    fade_out_start = max(0.0, duration_seconds - fade_out)
    cmd = [
        ffmpeg_binary,
        "-hide_banner",
        "-loglevel",
        "error",
        "-y",
        "-i",
        str(wav_path),
        "-af",
        f"afade=t=in:st=0:d={fade_in},afade=t=out:st={fade_out_start}:d={fade_out}",
        "-c:a",
        "libvorbis",
        "-q:a",
        "5",
        str(ogg_path),
    ]
    subprocess.run(cmd, check=True)
    return ogg_path


def _build_score(preset_id: str, duration_seconds: int):
    api = _import_supriya()
    score = api["module"].Score(output_bus_channel_count=2)
    synthdef, kwargs = PRESET_BUILDERS[preset_id](api)
    with score.at(0):
        with score.add_synthdefs(synthdef):
            score.add_synth(synthdef=synthdef, **kwargs)
    with score.at(duration_seconds):
        score.do_nothing()
    return score


def generate_supriya_sounds(preset_id=None, duration_seconds=None, force=False, keep_wav=False, sample_rate=DEFAULT_SAMPLE_RATE):
    status = _require_runtime()
    preset_ids = sorted(SUPRIYA_PRESETS) if not preset_id or preset_id == "all" else [get_supriya_preset(preset_id).id]
    generated = []

    for current_preset_id in preset_ids:
        preset = get_supriya_preset(current_preset_id)
        render_duration = int(duration_seconds or preset.default_duration_seconds)
        wav_path, ogg_path = _sound_paths(preset)
        if ogg_path.exists() and not force:
            generated.append(
                {
                    "preset_id": preset.id,
                    "status": "existing",
                    "duration_seconds": render_duration,
                    "sound": _catalog_sound_entry(preset, ogg_path, render_duration),
                }
            )
            continue
        score = _build_score(preset.id, render_duration)
        _render_score_to_wav(score, wav_path, render_duration, sample_rate)
        _transcode_wav_to_ogg(wav_path, ogg_path, render_duration)
        if not keep_wav and wav_path.exists():
            wav_path.unlink()
        generated.append(
            {
                "preset_id": preset.id,
                "status": "rendered",
                "duration_seconds": render_duration,
                "sound": _catalog_sound_entry(preset, ogg_path, render_duration),
            }
        )

    payload = upsert_generated_catalog(
        SUPRIYA_GENERATOR_ID,
        [item["sound"] for item in generated],
        metadata={
            "runtime": {
                "supriya_installed": status["supriya_installed"],
                "scsynth_path": status["scsynth_path"],
                "ffmpeg_path": status["ffmpeg_path"],
            }
        },
    )
    return {
        "generator": SUPRIYA_GENERATOR_ID,
        "generated": generated,
        "catalog_path": str((GENERATED_SOUND_ROOT / "catalogs" / f"{SUPRIYA_GENERATOR_ID}.json").resolve()),
        "catalog_size": len(payload["sounds"]),
        "runtime": status,
    }


def summarize_supriya_status_json():
    return json.dumps(get_supriya_runtime_status(), indent=2)


def env_generate_supriya_sounds():
    preset_id = (os.getenv("SUPRIYA_PRESET_ID") or "").strip() or None
    duration_seconds = os.getenv("SUPRIYA_DURATION_SECONDS")
    force = _truthy(os.getenv("SUPRIYA_FORCE_REGENERATE", "false"))
    keep_wav = _truthy(os.getenv("SUPRIYA_KEEP_WAV", "false"))
    sample_rate = int(os.getenv("SUPRIYA_SAMPLE_RATE", str(DEFAULT_SAMPLE_RATE)))
    return generate_supriya_sounds(
        preset_id=preset_id,
        duration_seconds=int(duration_seconds) if duration_seconds else None,
        force=force,
        keep_wav=keep_wav,
        sample_rate=sample_rate,
    )
