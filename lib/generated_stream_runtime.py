from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
import time
from pathlib import Path

from lib.browser_visualizer import LiveVisualizerSession, render_visualizer_video
from lib.local_livestream_assets import generate_stream_thumbnail, load_livestream_pack_assets
from lib.stream_engine import get_ffmpeg_binary, start_browser_capture_stream
from lib.stream_generation import (
    build_stream_metadata,
    build_stream_plan,
    load_livestream_profiles,
    load_sound_catalog,
)


GENERATED_LIBRARY_DIR = Path("assets") / "livestream" / "library"
EXAMPLE_SET_DIR = Path("videos") / "example_sets"
TEST_STREAM_DIR = Path("videos") / "test_streams"
PROFILE_REVIEW_DIR = Path("videos") / "profile_reviews"
LIVE_RUNTIME_DIR = Path("videos") / "live_runtime"
DEFAULT_AUDIO_TARGET_LUFS = float(os.getenv("STREAM_AUDIO_TARGET_LUFS", "-18"))
DEFAULT_AUDIO_TRUE_PEAK = float(os.getenv("STREAM_AUDIO_TRUE_PEAK", "-2.0"))
DEFAULT_AUDIO_TARGET_LRA = float(os.getenv("STREAM_AUDIO_TARGET_LRA", "7"))
DEFAULT_TEST_VIDEO_VARIANTS = [
    ("rain_sleep_window", "night_autumn"),
    ("ocean_night_drift", "night_summer"),
    ("snow_fire_night", "late_night_winter"),
    ("cafe_focus_evening", "evening_autumn"),
    ("coastal_fog_morning", "dawn_spring"),
    ("deep_brown_sleep", "late_night_winter"),
]


def _write_json(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2)


def _pack_is_complete(output_dir, preview=False):
    output_dir = Path(output_dir)
    required = {
        "manifest.json",
        "mix.json",
        "thumbnail_preview.png",
        "preview_audio.mp3" if preview else "audio.mp3",
        "preview_video.mp4" if preview else "video.mp4",
    }
    return all((output_dir / name).exists() for name in required)


def _build_render_config(plan):
    return {
        "seed": plan["seed"],
        "visualizer_id": plan["visualizer_id"],
        "palette": plan["palette"]["colors"],
        "profile_id": plan["profile_id"],
        "daypart": plan["daypart"],
        "season": plan["season"],
        "active_count": plan["active_count"],
    }


def _mix_audio_layers(layers, output_path, duration_seconds):
    ffmpeg_binary = get_ffmpeg_binary()
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    cmd = [ffmpeg_binary, "-hide_banner", "-loglevel", "error", "-y"]
    filters = []
    mix_labels = []

    for index, layer in enumerate(layers):
        if layer["mode"] == "continuous" and not layer["loop_safe"]:
            cmd.extend(["-i", layer["path"]])
        else:
            cmd.extend(["-stream_loop", "-1", "-i", layer["path"]])
        if layer["mode"] == "continuous":
            label = f"mix_{index}"
            source_filter = "apad,atrim" if not layer["loop_safe"] else "atrim"
            filters.append(
                f"[{index}:a]{source_filter}=duration={duration_seconds},volume={layer['volume']}[{label}]"
            )
            mix_labels.append(f"[{label}]")
            continue

        events = layer.get("events", [])
        if not events:
            continue
        split_labels = [f"src_{index}_{event_index}" for event_index in range(len(events))]
        filters.append(f"[{index}:a]asplit={len(events)}{''.join(f'[{label}]' for label in split_labels)}")
        for event_index, event in enumerate(events):
            label = f"burst_{index}_{event_index}"
            delay = int(event["start"] * 1000)
            fade_in = max(0.05, float(event["fade_in"]))
            fade_out = max(0.05, float(event["fade_out"]))
            duration = max(0.5, float(event["duration"]))
            fade_out_start = max(0.0, duration - fade_out)
            filters.append(
                f"[{split_labels[event_index]}]atrim=duration={duration},"
                f"volume={layer['volume']},"
                f"afade=t=in:st=0:d={fade_in},"
                f"afade=t=out:st={fade_out_start}:d={fade_out},"
                f"adelay={delay}|{delay}[{label}]"
            )
            mix_labels.append(f"[{label}]")

    if not mix_labels:
        raise RuntimeError("No audio layers were selected for this stream plan.")

    loudnorm_filter = (
        f"loudnorm=I={DEFAULT_AUDIO_TARGET_LUFS}:TP={DEFAULT_AUDIO_TRUE_PEAK}:LRA={DEFAULT_AUDIO_TARGET_LRA}"
    )
    if len(mix_labels) == 1:
        filters.append(f"{mix_labels[0]}atrim=duration={duration_seconds},{loudnorm_filter}[mixout]")
    else:
        filters.append(
            f"{''.join(mix_labels)}amix=inputs={len(mix_labels)}:duration=longest:normalize=0,"
            f"atrim=duration={duration_seconds},{loudnorm_filter}[mixout]"
        )

    cmd.extend(
        [
            "-filter_complex",
            ";".join(filters),
            "-map",
            "[mixout]",
            "-c:a",
            "libmp3lame",
            "-b:a",
            "192k",
            str(output_path),
        ]
    )
    subprocess.run(cmd, check=True)
    return str(output_path)


def resolve_stream_plan(
    duration_seconds,
    render_mode="prerender",
    requested_profile_id=None,
    explicit_seed=None,
    timezone_name=None,
    force_daypart=None,
    force_season=None,
    variant=None,
):
    return build_stream_plan(
        sound_catalog=load_sound_catalog(),
        profiles_data=load_livestream_profiles(),
        duration_seconds=duration_seconds,
        render_mode=render_mode,
        timezone_name=timezone_name,
        requested_profile_id=requested_profile_id,
        explicit_seed=explicit_seed,
        force_daypart=force_daypart,
        force_season=force_season,
        variant=variant,
    )


def create_generated_pack(
    duration_seconds,
    display_duration_seconds=None,
    output_dir=None,
    render_mode="prerender",
    requested_profile_id=None,
    explicit_seed=None,
    timezone_name=None,
    force_daypart=None,
    force_season=None,
    preview=False,
    variant=None,
):
    plan = resolve_stream_plan(
        duration_seconds=duration_seconds,
        render_mode=render_mode,
        requested_profile_id=requested_profile_id,
        explicit_seed=explicit_seed,
        timezone_name=timezone_name,
        force_daypart=force_daypart,
        force_season=force_season,
        variant=variant,
    )
    metadata = build_stream_metadata(
        plan,
        preview=preview,
        display_duration_seconds=display_duration_seconds,
    )
    seed_slug = plan["seed"].replace(":", "-").replace("/", "-")[:32]
    output_dir = Path(output_dir) if output_dir else GENERATED_LIBRARY_DIR / f"generated-{plan['timestamp_token']}-{plan['profile_id']}-{seed_slug}"
    output_dir.mkdir(parents=True, exist_ok=True)
    audio_name = "preview_audio.mp3" if preview else "audio.mp3"
    video_name = "preview_video.mp4" if preview else "video.mp4"
    thumb_name = "thumbnail_preview.png"

    audio_path = _mix_audio_layers(plan["layers"], output_dir / audio_name, duration_seconds)
    video_path = render_visualizer_video(_build_render_config(plan), str(output_dir / video_name), duration_seconds)
    generate_stream_thumbnail(
        metadata["thumbnail_title"],
        metadata["thumbnail_subtitle"],
        str(output_dir / thumb_name),
        video_path=video_path,
        badge_text=metadata["badge_text"],
    )
    _write_json(output_dir / "mix.json", plan)
    _write_json(output_dir / "manifest.json", metadata)
    return {
        "output_dir": str(output_dir),
        "audio_path": audio_path,
        "video_path": video_path,
        "thumbnail_path": str(output_dir / thumb_name),
        "plan": plan,
        "metadata": metadata,
        "assets": load_livestream_pack_assets(output_dir),
    }


def generate_example_sets(preview_duration_seconds=None):
    profiles_data = load_livestream_profiles()
    preview_duration_seconds = preview_duration_seconds or int(os.getenv("EXAMPLE_SET_DURATION_SECONDS", "45"))
    EXAMPLE_SET_DIR.mkdir(parents=True, exist_ok=True)
    outputs = []
    for index, profile in enumerate(profiles_data["profiles"], start=1):
        for variant in profile["example_variants"]:
            folder = EXAMPLE_SET_DIR / f"{index:02d}_{profile['id']}__{variant['id']}"
            if _pack_is_complete(folder, preview=True):
                outputs.append(
                    {
                        "output_dir": str(folder),
                        "plan": {"profile_id": profile["id"], "example_variant_id": variant["id"]},
                    }
                )
                continue
            outputs.append(
                create_generated_pack(
                    duration_seconds=preview_duration_seconds,
                    output_dir=folder,
                    render_mode="prerender",
                    requested_profile_id=profile["id"],
                    explicit_seed=variant["seed"],
                    force_daypart=variant["daypart"],
                    force_season=variant["season"],
                    preview=True,
                    variant=variant,
                )
            )
    return outputs


def generate_test_videos(preview_duration_seconds=None, variant_pairs=None):
    profiles_data = load_livestream_profiles()
    preview_duration_seconds = preview_duration_seconds or int(os.getenv("TEST_VIDEO_DURATION_SECONDS", "18"))
    variant_pairs = variant_pairs or DEFAULT_TEST_VIDEO_VARIANTS
    TEST_STREAM_DIR.mkdir(parents=True, exist_ok=True)
    outputs = []

    for index, (profile_id, variant_id) in enumerate(variant_pairs, start=1):
        profile = next((item for item in profiles_data["profiles"] if item["id"] == profile_id), None)
        if not profile:
            raise ValueError(f"Unknown test-video profile id: {profile_id}")
        variant = next((item for item in profile["example_variants"] if item["id"] == variant_id), None)
        if not variant:
            raise ValueError(f"Unknown test-video variant id {variant_id} for profile {profile_id}")

        folder = TEST_STREAM_DIR / f"{index:02d}_{profile_id}__{variant_id}"
        if _pack_is_complete(folder, preview=True):
            outputs.append(
                {
                    "output_dir": str(folder),
                    "plan": {"profile_id": profile_id, "example_variant_id": variant_id},
                }
            )
            continue
        outputs.append(
            create_generated_pack(
                duration_seconds=preview_duration_seconds,
                output_dir=folder,
                render_mode="prerender",
                requested_profile_id=profile_id,
                explicit_seed=variant["seed"],
                force_daypart=variant["daypart"],
                force_season=variant["season"],
                preview=True,
                variant=variant,
            )
        )
    return outputs


def generate_profile_reviews(preview_duration_seconds=None):
    profiles_data = load_livestream_profiles()
    preview_duration_seconds = preview_duration_seconds or int(os.getenv("PROFILE_REVIEW_DURATION_SECONDS", "60"))
    PROFILE_REVIEW_DIR.mkdir(parents=True, exist_ok=True)
    outputs = []

    for index, profile in enumerate(profiles_data["profiles"], start=1):
        variant = profile["example_variants"][0]
        folder = PROFILE_REVIEW_DIR / f"{index:02d}_{profile['id']}__{variant['id']}"
        if _pack_is_complete(folder, preview=True):
            outputs.append(
                {
                    "output_dir": str(folder),
                    "plan": {"profile_id": profile["id"], "example_variant_id": variant["id"]},
                }
            )
            continue
        outputs.append(
            create_generated_pack(
                duration_seconds=preview_duration_seconds,
                output_dir=folder,
                render_mode="prerender",
                requested_profile_id=profile["id"],
                explicit_seed=variant["seed"],
                force_daypart=variant["daypart"],
                force_season=variant["season"],
                preview=True,
                variant=variant,
            )
        )
    return outputs


class XvfbSession:
    def __init__(self, display=":99", width=1920, height=1080):
        self.display = display
        self.width = width
        self.height = height
        self.process = None
        self.wm_process = None

    def start(self):
        if os.name != "posix":
            raise RuntimeError("Live browser capture is supported on Linux runners only.")
        xvfb_binary = shutil.which("Xvfb")
        if not xvfb_binary:
            raise RuntimeError("Xvfb is required for live browser capture mode.")
        self.process = subprocess.Popen(
            [xvfb_binary, self.display, "-screen", "0", f"{self.width}x{self.height}x24", "-ac", "-nocursor"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        time.sleep(2)
        openbox_binary = shutil.which("openbox")
        if openbox_binary:
            env = os.environ.copy()
            env["DISPLAY"] = self.display
            
            # Write Openbox config to fiercely force borderless fullscreen
            openbox_config_dir = Path.home() / ".config" / "openbox"
            openbox_config_dir.mkdir(parents=True, exist_ok=True)
            rc_xml = openbox_config_dir / "rc.xml"
            rc_xml.write_text('''<?xml version="1.0" encoding="UTF-8"?>
<openbox_config xmlns="http://openbox.org/3.4/rc">
  <applications>
    <application class="*">
      <decor>no</decor>
      <fullscreen>yes</fullscreen>
      <maximized>true</maximized>
    </application>
  </applications>
</openbox_config>''')
            
            self.wm_process = subprocess.Popen(
                [openbox_binary, "--config-file", str(rc_xml)], 
                env=env, 
                stdout=subprocess.DEVNULL, 
                stderr=subprocess.DEVNULL
            )
            time.sleep(1)
        return self

    def stop(self):
        if hasattr(self, 'wm_process') and self.wm_process:
            self.wm_process.terminate()
            self.wm_process.wait()
        if self.process:
            self.process.terminate()
            try:
                self.process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                self.process.kill()


def start_live_generated_stream(
    duration_seconds,
    rtmp_url,
    stream_key,
    archive_path=None,
    display_duration_seconds=None,
    plan=None,
):
    plan = plan or resolve_stream_plan(duration_seconds=duration_seconds, render_mode="live")
    metadata = build_stream_metadata(
        plan,
        preview=False,
        display_duration_seconds=display_duration_seconds,
    )
    LIVE_RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=LIVE_RUNTIME_DIR) as tmpdir:
        audio_path = _mix_audio_layers(plan["layers"], Path(tmpdir) / "audio.mp3", plan["duration_seconds"])
        _write_json(Path(tmpdir) / "mix.json", plan)
        _write_json(Path(tmpdir) / "manifest.json", metadata)
        xvfb = XvfbSession().start()
        display = xvfb.display
        original_display = os.environ.get("DISPLAY")
        os.environ["DISPLAY"] = display
        session = None
        try:
            session = LiveVisualizerSession(_build_render_config(plan)).start()
            exit_code = start_browser_capture_stream(
                display=display,
                audio_file=audio_path,
                rtmp_url=rtmp_url,
                stream_key=stream_key,
                duration_seconds=duration_seconds,
                local_recording_path=archive_path,
            )
        finally:
            if session:
                session.stop()
            if original_display is None:
                os.environ.pop("DISPLAY", None)
            else:
                os.environ["DISPLAY"] = original_display
            xvfb.stop()
    return {"exit_code": exit_code, "plan": plan, "metadata": metadata}
