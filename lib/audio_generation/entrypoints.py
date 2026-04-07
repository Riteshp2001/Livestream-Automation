from __future__ import annotations

import json
import sys

from lib.audio_generation.supriya_generator import env_generate_supriya_sounds, get_supriya_runtime_status


def run_audio_generator_status_mode():
    print(json.dumps({"supriya": get_supriya_runtime_status()}, indent=2))


def run_generate_supriya_sounds_mode():
    try:
        result = env_generate_supriya_sounds()
    except RuntimeError as error:
        print(f"FATAL: {error}")
        sys.exit(1)
    print(json.dumps(result, indent=2))
