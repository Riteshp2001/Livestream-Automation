from __future__ import annotations

import os
from typing import Any


DEFAULT_CHAT_POLL_SECONDS = float(os.getenv("YOUTUBE_CHAT_POLL_DEFAULT_SEC", "5"))
RATE_LIMIT_BACKOFF_SECONDS = float(
    os.getenv("YOUTUBE_CHAT_RATE_LIMIT_BACKOFF_SEC", "15")
)
POLLING_SAFETY_MULTIPLIER = float(
    os.getenv("YOUTUBE_CHAT_POLL_SAFETY_MULTIPLIER", "1.10")
)


def classify_chat_poll_error(exc: Exception) -> str | None:
    text = str(exc)
    for reason in (
        "quotaExceeded",
        "rateLimitExceeded",
        "liveChatEnded",
        "liveChatDisabled",
        "liveChatNotFound",
    ):
        if reason in text:
            return reason
    return None


def next_poll_delay_seconds(response: dict[str, Any] | None) -> float:
    polling_interval_ms = 0
    if response:
        raw_value = response.get("pollingIntervalMillis")
        try:
            polling_interval_ms = max(0, int(raw_value))
        except (TypeError, ValueError):
            polling_interval_ms = 0

    delay_seconds = (
        polling_interval_ms / 1000 if polling_interval_ms else DEFAULT_CHAT_POLL_SECONDS
    )
    return max(1.0, delay_seconds * POLLING_SAFETY_MULTIPLIER)
