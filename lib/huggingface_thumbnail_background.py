from __future__ import annotations

import os

from dotenv import load_dotenv


DEFAULT_HF_IMAGE_MODEL = "black-forest-labs/FLUX.1-schnell"
DEFAULT_HF_IMAGE_PROVIDER = "hf-inference"

load_dotenv()


def _enabled():
    return os.getenv("USE_HF_THUMBNAILS", "0").strip().lower() in {"1", "true", "yes", "on"}


def generate_thumbnail_background(title, subtitle, badge_text):
    if not _enabled():
        return None

    model_seed = hash(title) % 100000 
    prompt = (
        "Create a premium 16:9 YouTube ambience thumbnail background with zero text, zero letters, zero logos, "
        "zero watermark, and zero UI. The art direction must be minimalistic yet instantly eye-catching. "
        "Use one clear focal subject or one clear environmental moment only, not a busy collage. "
        "Keep the left 38 percent of the image clean and readable with strong negative space for title overlay. "
        "Place the focal energy on the center-right or right side. "
        "Use a dark cinematic palette, soft atmospheric depth, subtle volumetric light, and elegant contrast. "
        "The image should feel calm, expensive, modern, and clickable for a sleep, focus, or meditation livestream. "
        f"Scene title: {title}. Supporting mood: {subtitle}. Brand tone: {badge_text}. "
    )
    
    # We use pollinations.ai for 100% free, zero-auth image generation.
    import urllib.request
    import urllib.parse
    from PIL import Image
    from io import BytesIO
    
    encoded_prompt = urllib.parse.quote(prompt)
    url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?width=1920&height=1080&nologo=true&seed={model_seed}"
    
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=30) as response:
            image_data = response.read()
            image = Image.open(BytesIO(image_data))
            return image.convert("RGB")
    except Exception as e:
        print(f"Free generation failed: {e}")
        return None
