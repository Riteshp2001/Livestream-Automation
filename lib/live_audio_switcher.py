"""
live_audio_switcher.py
─────────────────────────────────────────────────────────────────────────────
Segment-based live audio hot-swap engine + 10-minute poll scheduler.

Architecture
────────────
  LiveAudioSwitcher
    - Maintains a dynamic ffmpeg concat playlist (playlist.txt)
    - Background thread continuously pre-renders 60-second audio segments
    - When a vote winner arrives, the next segment uses the new profile
    - Seamless switch — no RTMP interruption, no silence

  LivePollScheduler
    - Every POLL_INTERVAL_SECONDS (default: 600 = 10 min), triggers a vote
    - Posts a genre-filtered poll to YouTube live chat
    - Collects votes for VOTE_WINDOW_SECONDS (default: 120 = 2 min)
    - Per-user dedup — only first vote per user per poll counts
    - Winner is announced + queued for audio switch
    - Tally shown in visualizer overlay during voting

Both classes are designed to run as daemon threads alongside the main stream.
"""
from __future__ import annotations

import os
import queue
import threading
import time
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass  # avoid circular imports from stream_generation

# ── Configuration (all overridable via env vars) ──────────────────────────────
SEGMENT_SECONDS     = int(os.getenv("STREAM_SEGMENT_SECONDS",   "60"))   # audio segment length
POLL_INTERVAL_SEC   = int(os.getenv("STREAM_POLL_INTERVAL_SEC", "600"))  # 10 min between polls
VOTE_WINDOW_SEC     = int(os.getenv("STREAM_VOTE_WINDOW_SEC",   "120"))  # 2 min voting window
POLL_OPTIONS_COUNT  = int(os.getenv("STREAM_POLL_OPTIONS",      "5"))    # choices per poll


# ── Shared live state (read by visualizer overlay) ────────────────────────────
try:
    from lib.browser_visualizer import LIVE_STREAM_STATE
except ImportError:
    LIVE_STREAM_STATE: dict = {}   # type: ignore[assignment]


class VoteCollector:
    """
    Collects chat votes during a single poll window.
    - One vote per user (first vote counts, subsequent ignored)
    - Thread-safe
    """

    def __init__(self, candidates: list[tuple[str, str]]) -> None:
        # candidates: [(label, profile_id), ...]
        self.candidates = candidates
        # Build lookup: "1"/"2"/... → profile_id
        self._choice_map: dict[str, str] = {
            str(i + 1): pid for i, (_, pid) in enumerate(candidates)
        }
        self._votes: dict[str, str] = {}   # user_id → profile_id
        self._lock = threading.Lock()

    def add_vote(self, user_id: str, raw_message: str) -> bool:
        """
        Try to record a vote from `user_id`.
        `raw_message` should be the chat message text ("1", "2", … "5").
        Returns True if vote was accepted, False if invalid or duplicate.
        """
        choice = raw_message.strip()
        profile_id = self._choice_map.get(choice)
        if not profile_id:
            return False
        with self._lock:
            if user_id in self._votes:
                return False  # Already voted
            self._votes[user_id] = profile_id
        return True

    def tally(self) -> tuple[str, int] | None:
        """Return (winning_profile_id, vote_count) or None if no votes."""
        with self._lock:
            if not self._votes:
                return None
            counts: dict[str, int] = {}
            for pid in self._votes.values():
                counts[pid] = counts.get(pid, 0) + 1
            winner = max(counts, key=lambda p: counts[p])
            return winner, counts[winner]

    def get_overlay_tally(self, remaining_seconds: int) -> str:
        """Return a one-line tally string for the visualizer overlay."""
        with self._lock:
            counts: dict[str, int] = {}
            for pid in self._votes.values():
                counts[pid] = counts.get(pid, 0) + 1
        if not counts:
            return f"🗳️ Voting open — {remaining_seconds}s remaining. Type 1-{len(self.candidates)}!"
        parts = []
        for label, pid in self.candidates:
            n = counts.get(pid, 0)
            if n:
                clean = label.replace("  ✦ now playing", "").strip()
                # Shorten label to emoji + first word only
                short = " ".join(clean.split()[:2])
                parts.append(f"{short}: {n}")
        tally_str = " | ".join(parts) if parts else "no votes yet"
        return f"🗳️ {tally_str} — {remaining_seconds}s left"


class LiveAudioSwitcher:
    """
    Manages the dynamic ffmpeg concat playlist for seamless audio switching.

    Usage:
        switcher = LiveAudioSwitcher(initial_plan, sound_catalog, profiles_data, tmpdir)
        playlist_path = switcher.start()   # returns path to playlist.txt
        # ... pass playlist_path to start_browser_capture_stream()
        switcher.request_switch(new_profile_id)   # called when vote winner is decided
        switcher.stop()
    """

    def __init__(
        self,
        initial_plan: dict,
        sound_catalog: dict,
        profiles_data: dict,
        work_dir: str | Path,
    ) -> None:
        self._current_plan  = initial_plan
        self._sound_catalog = sound_catalog
        self._profiles_data = profiles_data
        self._work_dir      = Path(work_dir)
        self._work_dir.mkdir(parents=True, exist_ok=True)

        self._playlist_path = self._work_dir / "playlist.txt"
        self._switch_queue: queue.Queue[str] = queue.Queue(maxsize=1)
        self._stop_event    = threading.Event()
        self._seg_index     = 0
        self._thread: threading.Thread | None = None

    @property
    def playlist_path(self) -> str:
        return str(self._playlist_path)

    def start(self) -> str:
        """Start the segment-render thread and return the playlist path."""
        # Write placeholder so ffmpeg can open the file immediately
        self._playlist_path.write_text("", encoding="utf-8")
        self._thread = threading.Thread(target=self._render_loop, daemon=True, name="AudioSwitcher")
        self._thread.start()
        return self.playlist_path

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=10)

    def request_switch(self, profile_id: str) -> None:
        """
        Queue a profile switch. Only one switch can be pending at a time.
        If the queue is full (switch already pending), the new request is dropped.
        """
        try:
            self._switch_queue.put_nowait(profile_id)
            print(f"[AudioSwitcher] Switch queued → {profile_id}")
            LIVE_STREAM_STATE["chat_message"] = f"🎵 Switching to {profile_id.replace('_', ' ')} next segment…"
        except queue.Full:
            print(f"[AudioSwitcher] Switch already pending, ignoring {profile_id}")

    def _next_plan(self) -> dict:
        """
        Return the plan for the next segment.
        If a switch is queued, re-resolve from the new profile; else continue current.
        """
        from lib.stream_generation import build_stream_plan

        try:
            new_profile_id = self._switch_queue.get_nowait()
            print(f"[AudioSwitcher] Applying switch → {new_profile_id}")
            self._current_plan = build_stream_plan(
                sound_catalog=self._sound_catalog,
                profiles_data=self._profiles_data,
                duration_seconds=SEGMENT_SECONDS,
                render_mode="live",
                requested_profile_id=new_profile_id,
            )
            LIVE_STREAM_STATE["profile_id"]  = new_profile_id
            LIVE_STREAM_STATE["visualizer_id"] = self._current_plan.get("visualizer_id", "")
            LIVE_STREAM_STATE["palette"]       = self._current_plan.get("palette", {}).get("colors", [])
        except queue.Empty:
            # Re-resolve current profile for the next segment (keeps variation fresh)
            from lib.stream_generation import build_stream_plan
            self._current_plan = build_stream_plan(
                sound_catalog=self._sound_catalog,
                profiles_data=self._profiles_data,
                duration_seconds=SEGMENT_SECONDS,
                render_mode="live",
                requested_profile_id=self._current_plan["profile_id"],
            )
        return self._current_plan

    def _render_segment(self, plan: dict) -> Path:
        """Render one audio segment and return its path."""
        from lib.generated_stream_runtime import _mix_audio_layers   # local import avoids circular

        self._seg_index += 1
        seg_path = self._work_dir / f"seg_{self._seg_index:04d}_{plan['profile_id']}.mp3"
        print(f"[AudioSwitcher] Rendering segment {self._seg_index} ({plan['profile_id']}) → {seg_path.name}")
        _mix_audio_layers(plan["layers"], seg_path, SEGMENT_SECONDS)
        return seg_path

    def _append_to_playlist(self, seg_path: Path) -> None:
        """Append a new segment to the concat playlist (ffmpeg reads it live)."""
        # ffmpeg concat demuxer requires forward-slash paths and single quotes
        posix_path = seg_path.as_posix()
        with self._playlist_path.open("a", encoding="utf-8") as f:
            f.write(f"file '{posix_path}'\n")

    def _render_loop(self) -> None:
        """
        Main render loop:
        1. Pre-render next segment
        2. Append to playlist
        3. Sleep until ~5s before the current segment ends
        4. Repeat
        """
        # Pre-render the very first two segments so ffmpeg has immediate audio
        for _ in range(2):
            if self._stop_event.is_set():
                return
            plan = self._next_plan()
            seg  = self._render_segment(plan)
            self._append_to_playlist(seg)

        while not self._stop_event.is_set():
            # Sleep for segment duration minus 10s buffer for render time
            countdown = SEGMENT_SECONDS - 10
            while countdown > 0 and not self._stop_event.is_set():
                time.sleep(1)
                countdown -= 1

            if self._stop_event.is_set():
                break

            plan = self._next_plan()
            seg  = self._render_segment(plan)
            self._append_to_playlist(seg)


class LivePollScheduler:
    """
    Posts a genre-specific community poll to YouTube live chat every 10 minutes.

    - 2-minute voting window
    - Per-user dedup
    - Tally shown in visualizer overlay
    - Winner queued for audio switch via LiveAudioSwitcher.request_switch()
    """

    def __init__(
        self,
        youtube_service,
        live_chat_id: str,
        audio_switcher: LiveAudioSwitcher,
        current_profile_id: str,
    ) -> None:
        self._yt          = youtube_service
        self._chat_id     = live_chat_id
        self._switcher    = audio_switcher
        self._profile_id  = current_profile_id
        self._stop_event  = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self) -> "LivePollScheduler":
        self._thread = threading.Thread(target=self._scheduler_loop, daemon=True, name="PollScheduler")
        self._thread.start()
        return self

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=5)

    def notify_current_profile(self, profile_id: str) -> None:
        """Called after each successful audio switch to keep genre context fresh."""
        self._profile_id = profile_id

    def _post_chat_message(self, text: str) -> None:
        """Post a message to the YouTube live chat."""
        try:
            self._yt.liveChatMessages().insert(
                part="snippet",
                body={
                    "snippet": {
                        "liveChatId": self._chat_id,
                        "type": "textMessageEvent",
                        "textMessageDetails": {"messageText": text},
                    }
                },
            ).execute()
        except Exception as exc:
            print(f"[PollScheduler] Failed to post chat message: {exc}")

    def _run_poll(self) -> None:
        from lib.chat_command_router import (
            get_poll_candidates,
            format_poll_message,
            format_result_message,
            PROFILE_LABELS,
        )

        candidates = get_poll_candidates(
            current_profile_id=self._profile_id,
            count=POLL_OPTIONS_COUNT,
            rng_seed=int(time.time()),
        )
        poll_text = format_poll_message(candidates, vote_window_seconds=VOTE_WINDOW_SEC)
        self._post_chat_message(poll_text)
        print(f"[PollScheduler] Poll posted for profile={self._profile_id}")

        collector = VoteCollector(candidates)

        # ── Collect votes for VOTE_WINDOW_SEC ────────────────────────────────
        next_page_token = None
        deadline = time.time() + VOTE_WINDOW_SEC

        while time.time() < deadline and not self._stop_event.is_set():
            remaining = int(deadline - time.time())
            # Update overlay tally
            LIVE_STREAM_STATE["chat_message"] = collector.get_overlay_tally(remaining)

            try:
                req = self._yt.liveChatMessages().list(
                    liveChatId=self._chat_id,
                    part="snippet,authorDetails",
                    pageToken=next_page_token,
                )
                resp = req.execute()
                next_page_token = resp.get("nextPageToken")
                for item in resp.get("items", []):
                    msg    = item["snippet"]["displayMessage"].strip()
                    uid    = item["authorDetails"]["channelId"]
                    accepted = collector.add_vote(uid, msg)
                    if accepted:
                        uname = item["authorDetails"]["displayName"]
                        print(f"[PollScheduler] Vote: {uname} → {msg}")
            except Exception as exc:
                print(f"[PollScheduler] Chat read error: {exc}")

            time.sleep(5)  # poll every 5s (YouTube API quota friendly)

        # ── Tally ─────────────────────────────────────────────────────────────
        result = collector.tally()
        if result:
            winning_pid, vote_count = result
            winning_label = PROFILE_LABELS.get(winning_pid, winning_pid.replace("_", " "))
            result_msg = format_result_message(winning_label, vote_count, next_poll_minutes=POLL_INTERVAL_SEC // 60)
            self._post_chat_message(result_msg)
            print(f"[PollScheduler] Winner: {winning_pid} ({vote_count} votes)")
            self._switcher.request_switch(winning_pid)
            self.notify_current_profile(winning_pid)
            LIVE_STREAM_STATE["chat_message"] = f"🎵 {winning_label.strip()} won the vote! Switching soon…"
        else:
            # No votes — keep current
            self._post_chat_message("🎵 No votes this round — keeping the current vibe! Next vote soon 🕐")
            print("[PollScheduler] No votes received — keeping current profile")
            LIVE_STREAM_STATE["chat_message"] = "No votes — keeping current vibe 🎧"

    def _scheduler_loop(self) -> None:
        """
        Main scheduler:
        - Wait POLL_INTERVAL_SEC between polls
        - Deduct VOTE_WINDOW_SEC so each cycle is exactly POLL_INTERVAL_SEC total
        """
        # First poll after a warm-up delay (give viewers time to join)
        warm_up = 60  # 1 minute after stream start
        print(f"[PollScheduler] First poll in {warm_up}s…")
        self._stop_event.wait(warm_up)

        while not self._stop_event.is_set():
            self._run_poll()
            # Wait the remainder of the interval (poll already took VOTE_WINDOW_SEC)
            wait_after = max(0, POLL_INTERVAL_SEC - VOTE_WINDOW_SEC)
            print(f"[PollScheduler] Next poll in {wait_after}s")
            self._stop_event.wait(wait_after)


def post_stream_intro_comment(youtube_service, live_chat_id: str) -> None:
    """
    Post a single minimalistic instructions message to YouTube live chat
    at stream start so viewers know how to participate.
    """
    msg = (
        "🎵 You control the vibe!\n"
        "Every 10 min I'll post a poll — type the number to vote.\n"
        "Most votes wins and the soundscape switches 🎧\n"
        "One vote per person · genre-matched options only"
    )
    try:
        youtube_service.liveChatMessages().insert(
            part="snippet",
            body={
                "snippet": {
                    "liveChatId": live_chat_id,
                    "type": "textMessageEvent",
                    "textMessageDetails": {"messageText": msg},
                }
            },
        ).execute()
        print("[PollScheduler] Intro comment posted to live chat.")
    except Exception as exc:
        print(f"[PollScheduler] Could not post intro comment: {exc}")
