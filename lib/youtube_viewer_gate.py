from __future__ import annotations

import os
import threading
import time

from lib.browser_visualizer import LIVE_STREAM_STATE


MIN_VIEWERS_FOR_CHAT_AUTOMATION = int(
    os.getenv("YOUTUBE_MIN_VIEWERS_FOR_CHAT_AUTOMATION", "15")
)
VIEWER_COUNT_REFRESH_SECONDS = int(
    os.getenv("YOUTUBE_VIEWER_COUNT_REFRESH_SEC", "900")
)


class ViewerThresholdGate:
    def __init__(
        self,
        youtube_service,
        broadcast_id: str,
        *,
        state_label: str = "chat automation",
    ) -> None:
        self._yt = youtube_service
        self._broadcast_id = broadcast_id
        self._state_label = state_label
        self._lock = threading.Lock()
        self._last_checked_at = 0.0
        self._last_viewers = 0

    @property
    def refresh_seconds(self) -> int:
        return VIEWER_COUNT_REFRESH_SECONDS

    @property
    def min_viewers(self) -> int:
        return MIN_VIEWERS_FOR_CHAT_AUTOMATION

    def current_viewers(self, *, force: bool = False) -> int:
        now = time.time()
        with self._lock:
            if (
                not force
                and self._last_checked_at
                and now - self._last_checked_at < VIEWER_COUNT_REFRESH_SECONDS
            ):
                return self._last_viewers

        viewers = self._fetch_current_viewers()
        with self._lock:
            self._last_checked_at = now
            self._last_viewers = viewers

        LIVE_STREAM_STATE["current_viewers"] = viewers
        LIVE_STREAM_STATE["chat_automation_enabled"] = viewers > MIN_VIEWERS_FOR_CHAT_AUTOMATION
        return viewers

    def is_enabled(self, *, force: bool = False) -> bool:
        viewers = self.current_viewers(force=force)
        enabled = viewers > MIN_VIEWERS_FOR_CHAT_AUTOMATION
        if enabled:
            LIVE_STREAM_STATE["chat_automation_status"] = (
                f"Chat automation enabled at {viewers} viewers."
            )
        else:
            LIVE_STREAM_STATE["chat_automation_status"] = (
                f"Chat automation paused until viewers exceed {MIN_VIEWERS_FOR_CHAT_AUTOMATION}. Current: {viewers}."
            )
        return enabled

    def _fetch_current_viewers(self) -> int:
        response = (
            self._yt.videos()
            .list(
                part="liveStreamingDetails",
                id=self._broadcast_id,
                fields="items/liveStreamingDetails/concurrentViewers",
            )
            .execute()
        )
        items = response.get("items", [])
        if not items:
            return 0

        live_details = items[0].get("liveStreamingDetails", {})
        raw_value = live_details.get("concurrentViewers")
        try:
            return max(0, int(raw_value))
        except (TypeError, ValueError):
            return 0
