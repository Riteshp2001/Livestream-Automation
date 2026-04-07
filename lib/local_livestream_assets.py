import json
import subprocess
import textwrap
from tempfile import TemporaryDirectory
from datetime import datetime
from pathlib import Path


LOCAL_LIVESTREAM_ROOT = Path("assets") / "livestream"
LOCAL_LIVESTREAM_LIBRARY_DIR = LOCAL_LIVESTREAM_ROOT / "library"
LOCAL_LIVESTREAM_CURRENT_FILE = LOCAL_LIVESTREAM_ROOT / "current.txt"
LEGACY_VIDEO_PATH = LOCAL_LIVESTREAM_ROOT / "primary_video.mp4"
LEGACY_AUDIO_PATH = LOCAL_LIVESTREAM_ROOT / "primary_audio.mp3"
LEGACY_MANIFEST_PATH = LOCAL_LIVESTREAM_ROOT / "manifest.json"
STREAM_ARCHIVE_DIR = Path("videos") / "livestreams"
STREAM_THUMBNAIL_DIR = Path("videos") / "thumbnails"

VIDEO_EXTENSIONS = {".mp4", ".mov", ".mkv", ".webm"}
AUDIO_EXTENSIONS = {".mp3", ".wav", ".m4a", ".aac", ".flac", ".ogg"}
DEFAULT_BADGE_TEXT = "Symphony Station"


def _slugify(value):
    slug = "".join(char.lower() if char.isalnum() else "_" for char in value).strip("_")
    while "__" in slug:
        slug = slug.replace("__", "_")
    return slug or "livestream"


def _load_manifest(path):
    if not path.exists():
        return {}

    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _normalize_tags(tags):
    if not isinstance(tags, list):
        return []

    normalized = []
    for tag in tags:
        if isinstance(tag, str) and tag.strip():
            normalized.append(tag.strip())
    return normalized


def _first_supported_media_file(directory, extensions, preferred_stems):
    if not directory.exists():
        return None

    candidates = [
        path
        for path in directory.iterdir()
        if path.is_file() and path.suffix.lower() in extensions
    ]
    if not candidates:
        return None

    preferred = []
    for stem in preferred_stems:
        preferred.extend(
            sorted(
                [path for path in candidates if path.stem.lower() == stem],
                key=lambda path: path.name.lower(),
            )
        )
    if preferred:
        return preferred[0]

    return sorted(candidates, key=lambda path: path.name.lower())[0]


def _iter_candidate_pack_dirs():
    if not LOCAL_LIVESTREAM_LIBRARY_DIR.exists():
        return []

    pack_dirs = [
        path for path in LOCAL_LIVESTREAM_LIBRARY_DIR.iterdir() if path.is_dir()
    ]
    if not pack_dirs:
        return []

    ordered = []
    if LOCAL_LIVESTREAM_CURRENT_FILE.exists():
        selected_pack = LOCAL_LIVESTREAM_CURRENT_FILE.read_text(
            encoding="utf-8"
        ).strip()
        if selected_pack:
            selected_path = LOCAL_LIVESTREAM_LIBRARY_DIR / selected_pack
            if selected_path.exists() and selected_path.is_dir():
                ordered.append(selected_path)

    for pack_dir in sorted(
        pack_dirs, key=lambda path: path.stat().st_mtime, reverse=True
    ):
        if pack_dir not in ordered:
            ordered.append(pack_dir)

    return ordered


def _format_pack_name(pack_name):
    cleaned = pack_name.replace("_", " ").replace("-", " ").strip()
    return cleaned.title() if cleaned else "Approved Local Stream"


def _default_description(pack_label):
    return (
        f"A calm late-night stream built from approved local video and audio. "
        f"This {pack_label.lower()} session is designed to help you slow down, clear your thoughts, and ease into rest."
    )


def _build_hashtags(tags):
    hashtags = []
    for tag in tags:
        compact = "".join(char for char in tag.lower() if char.isalnum())
        if compact:
            hashtags.append(f"#{compact}")

    if "#symphonystation" not in hashtags:
        hashtags.append("#symphonystation")

    return " ".join(hashtags[:4])


def _strip_stream_markup(title):
    clean_title = title.replace("[LIVE]", "").strip()
    if "|" in clean_title:
        clean_title = clean_title.split("|", 1)[1].strip()
    return clean_title


def load_livestream_pack_assets(pack_dir):
    pack_dir = Path(pack_dir)
    video_path = _first_supported_media_file(
        pack_dir, VIDEO_EXTENSIONS, ("video", "visual", "background")
    )
    audio_path = _first_supported_media_file(
        pack_dir, AUDIO_EXTENSIONS, ("audio", "music", "ambience")
    )
    if not video_path or not audio_path:
        return None

    manifest = _load_manifest(pack_dir / "manifest.json")
    pack_label = _format_pack_name(pack_dir.name)
    title = manifest.get("title", f"{pack_label} [LIVE]")
    tags = _normalize_tags(manifest.get("tags")) or [
        "sleep music",
        "night ambience",
        "relaxing ambience",
        "Symphony.Station",
    ]

    return {
        "source": "library",
        "pack_name": pack_dir.name,
        "pack_dir": str(pack_dir),
        "video_path": str(video_path),
        "audio_path": str(audio_path),
        "video_name": video_path.name,
        "audio_name": audio_path.name,
        "title": title,
        "description": manifest.get("description", _default_description(pack_label)),
        "tags": tags,
        "thumbnail_title": manifest.get("thumbnail_title", _strip_stream_markup(title)),
        "thumbnail_subtitle": manifest.get("thumbnail_subtitle", pack_label),
        "badge_text": manifest.get("badge_text", DEFAULT_BADGE_TEXT),
    }


def discover_local_livestream_assets():
    for pack_dir in _iter_candidate_pack_dirs():
        assets = load_livestream_pack_assets(pack_dir)
        if assets:
            return assets

    if LEGACY_VIDEO_PATH.exists() and LEGACY_AUDIO_PATH.exists():
        manifest = _load_manifest(LEGACY_MANIFEST_PATH)
        title = manifest.get("title", "Symphony.Station Approved Local Stream [LIVE]")
        tags = _normalize_tags(manifest.get("tags")) or [
            "sleep music",
            "night ambience",
            "relaxing ambience",
            "Symphony.Station",
        ]
        return {
            "source": "legacy",
            "pack_name": "legacy-local-assets",
            "pack_dir": str(LOCAL_LIVESTREAM_ROOT),
            "video_path": str(LEGACY_VIDEO_PATH),
            "audio_path": str(LEGACY_AUDIO_PATH),
            "video_name": LEGACY_VIDEO_PATH.name,
            "audio_name": LEGACY_AUDIO_PATH.name,
            "title": title,
            "description": manifest.get(
                "description", _default_description("approved local")
            ),
            "tags": tags,
            "thumbnail_title": manifest.get(
                "thumbnail_title", _strip_stream_markup(title)
            ),
            "thumbnail_subtitle": manifest.get(
                "thumbnail_subtitle", "Approved local ambience"
            ),
            "badge_text": manifest.get("badge_text", DEFAULT_BADGE_TEXT),
        }

    return None


def generate_local_livestream_metadata(local_assets, duration_minutes):
    title = local_assets["title"].strip()
    if not title.endswith("[LIVE]"):
        title = f"{title} [LIVE]"

    intro = local_assets["description"].strip()
    hashtags = _build_hashtags(local_assets["tags"])
    fallback_description = (
        f"{title}\n"
        f"--------------------------------------------------------------\n"
        f"{intro}\n\n"
        f"Welcome to Symphony.Station.\n"
        f"Let the calm begin.\n\n"
        f"{hashtags}"
    )

    fallback_metadata = {
        "title": title,
        "description": fallback_description,
        "tags": local_assets["tags"],
        "thumbnail_title": local_assets["thumbnail_title"],
        "thumbnail_subtitle": local_assets["thumbnail_subtitle"],
        "badge_text": local_assets["badge_text"],
    }

    # --- Try Groq AI copy generation ---
    try:
        from lib.groq_copywriter import generate_stream_copy
        pack_label = _format_pack_name(local_assets.get("pack_name", ""))
        plan_mock = {
            "profile_id": local_assets.get("pack_name", "ambient"),
            "daypart": "night",
            "season": "winter",
            "render_mode": "prerender",
            "layers": [{"name": local_assets.get("pack_name", "ambient")}],
            "tags": local_assets["tags"][:8],
            "profile": {
                "display_name": pack_label,
                "title_parts": {
                    "headline": pack_label,
                    "descriptor": "Deep Focus & Sleep",
                    "channel_prefix": "Symphony.Station",
                },
                "thumbnail_parts": {
                    "title": local_assets["thumbnail_title"],
                    "subtitle": local_assets["thumbnail_subtitle"],
                },
            },
        }
        groq_result = generate_stream_copy(plan_mock, fallback_metadata, preview=False)
        if groq_result:
            print("[Groq] AI copy generated successfully.")
            return {
                "title": groq_result["title"],
                "description": groq_result["description"],
                "tags": local_assets["tags"],
                "thumbnail_title": groq_result["thumbnail_title"],
                "thumbnail_subtitle": groq_result["thumbnail_subtitle"],
                "badge_text": groq_result["badge_text"],
            }
    except Exception as groq_err:
        print(f"[Groq] Copy generation skipped: {groq_err}")

    return fallback_metadata



def build_stream_output_paths(title):
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    slug = _slugify(title)[:80]
    STREAM_ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)
    STREAM_THUMBNAIL_DIR.mkdir(parents=True, exist_ok=True)

    archive_path = STREAM_ARCHIVE_DIR / f"{timestamp}_{slug}.mp4"
    thumbnail_path = STREAM_THUMBNAIL_DIR / f"{timestamp}_{slug}.png"
    return str(archive_path), str(thumbnail_path)


def generate_stream_thumbnail(
    title, subtitle, output_path, video_path=None, badge_text=DEFAULT_BADGE_TEXT
):
    import hashlib
    from pathlib import Path
    from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont

    width, height = 1280, 720
    raw_title = title.replace("[LIVE]", "").strip().upper() or "CALM AMBIENCE"
    raw_subtitle = subtitle.strip() or "Symphony.Station"

    def extract_background_frame(source_video_path):
        from lib.stream_engine import get_ffmpeg_binary

        ffmpeg_binary = get_ffmpeg_binary()
        with TemporaryDirectory() as tmpdir:
            frame_path = Path(tmpdir) / "thumb-frame.png"
            for sample_time in ("8", "4", "1"):
                command = [
                    ffmpeg_binary,
                    "-hide_banner",
                    "-loglevel",
                    "error",
                    "-y",
                    "-ss",
                    sample_time,
                    "-i",
                    str(source_video_path),
                    "-frames:v",
                    "1",
                    "-vf",
                    "scale=1280:720:force_original_aspect_ratio=increase,crop=1280:720",
                    str(frame_path),
                ]
                result = subprocess.run(command, capture_output=True, text=True)
                if result.returncode == 0 and frame_path.exists():
                    return Image.open(frame_path).convert("RGB")
        raise RuntimeError("ffmpeg could not extract a thumbnail frame.")

    def create_local_background():
        background = Image.new("RGB", (width, height), (15, 17, 22))
        background_draw = ImageDraw.Draw(background)
        for y in range(height):
            mix = y / max(height - 1, 1)
            red = int(15 * (1 - mix) + 38 * mix)
            green = int(17 * (1 - mix) + 54 * mix)
            blue = int(22 * (1 - mix) + 72 * mix)
            background_draw.line((0, y, width, y), fill=(red, green, blue))
        return background

    # --- 1. SET UP THE CANVAS & BACKGROUND ---
    try:
        from lib.huggingface_thumbnail_background import generate_thumbnail_background

        image = generate_thumbnail_background(raw_title, raw_subtitle, badge_text)
        if image:
            image = image.resize((width, height), Image.Resampling.LANCZOS)
    except Exception:
        image = None

    if not image and video_path:
        try:
            image = extract_background_frame(video_path).resize(
                (width, height), Image.Resampling.LANCZOS
            )
        except Exception:
            image = None

    if not image:
        image = create_local_background()

    # Apply Cinematic Treatment
    image = ImageEnhance.Brightness(image).enhance(0.65)  # Darken for text pop
    image = image.filter(ImageFilter.GaussianBlur(12))  # Dreamy depth of field

    # Add a Vignette overlay
    vignette = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    v_draw = ImageDraw.Draw(vignette)
    for i in range(0, 400, 2):
        alpha = int((i / 400) ** 2 * 180)
        v_draw.ellipse(
            [-i, -i, width + i, height + i], outline=(0, 0, 0, alpha), width=2
        )
    image.paste(vignette, (0, 0), vignette)

    draw = ImageDraw.Draw(image)

    # --- 2. FONTS (Modern Stack) ---
    def get_font(size, bold=False):
        paths = (
            [
                # Windows fonts
                r"C:\Windows\Fonts\Inter-Bold.ttf",
                r"C:\Windows\Fonts\segoeuib.ttf",
                r"C:\Windows\Fonts\arialbd.ttf",
                # Linux/Ubuntu system fonts
                "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
                "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
                "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf",
            ]
            if bold
            else [
                # Windows fonts
                r"C:\Windows\Fonts\Inter-Regular.ttf",
                r"C:\Windows\Fonts\segoeui.ttf",
                r"C:\Windows\Fonts\arial.ttf",
                # Linux/Ubuntu system fonts
                "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
                "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
                "/usr/share/fonts/truetype/freefont/FreeSans.ttf",
            ]
        )
        for p in paths:
            if Path(p).exists():
                return ImageFont.truetype(p, size)
        return ImageFont.load_default()

    title_font = get_font(110, bold=True)
    meta_font = get_font(22, bold=True)  # For the small caps vibe
    hook_font = get_font(32)

    # --- 3. LAYOUT & TYPOGRAPHY ---
    margin_left = 100

    # Top Tag: "LATE NIGHT AMBIENCE" (Spaced out)
    # Use ASCII pipe instead of unicode bullet for cross-system font compatibility
    tag_text = "  |  ".join(["SLEEP", "FOCUS", "REST"]).upper()
    draw.text((margin_left, 160), tag_text, font=meta_font, fill=(255, 255, 255, 180))

    # Main Title: Massive and Impactful
    # Wrap text manually for design control
    wrapped_title = textwrap.fill(raw_title, width=12)
    draw.multiline_text(
        (margin_left - 4, 210),
        wrapped_title,
        font=title_font,
        fill=(255, 255, 255, 255),
        spacing=0,
    )

    # Calculate height for positioning the hook
    title_bbox = draw.multiline_textbbox(
        (margin_left, 210), wrapped_title, font=title_font, spacing=0
    )
    hook_y = title_bbox[3] + 40

    # The Hook: Minimalist with a thin accent line
    draw.line(
        (margin_left, hook_y, margin_left, hook_y + 60),
        fill=(255, 255, 255, 200),
        width=3,
    )
    draw.text(
        (margin_left + 25, hook_y + 12),
        raw_subtitle,
        font=hook_font,
        fill=(230, 230, 230, 255),
    )

    # --- 4. BRANDING & LIVE STATUS ---
    # Minimal "LIVE" indicator top right
    live_x, live_y = width - 180, 80
    # Pulse Glow
    draw.ellipse(
        (live_x - 5, live_y - 5, live_x + 20, live_y + 20), fill=(255, 60, 60, 60)
    )
    draw.ellipse((live_x, live_y, live_x + 15, live_y + 15), fill=(255, 60, 60, 255))
    draw.text(
        (live_x + 30, live_y - 5), "LIVE", font=meta_font, fill=(255, 255, 255, 255)
    )

    # Bottom Branding (Corner)
    draw.text(
        (width - 300, height - 80),
        f"© {badge_text.upper()}",
        font=meta_font,
        fill=(255, 255, 255, 100),
    )

    # --- 5. SAVE ---
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    image.convert("RGB").save(output_path, "PNG", quality=95)
    return output_path
