import threading
import time
from lib.browser_visualizer import LIVE_STREAM_STATE
from lib.youtube_chat_polling import (
    DEFAULT_CHAT_POLL_SECONDS,
    RATE_LIMIT_BACKOFF_SECONDS,
    classify_chat_poll_error,
    next_poll_delay_seconds,
)
from lib.youtube_viewer_gate import ViewerThresholdGate

def start_pomodoro_thread():
    def pomodoro_loop():
        # 50 min focus, 10 min break.
        focus_seconds = 50 * 60
        break_seconds = 10 * 60
        
        while True:
            # Focus Phase
            for remaining in range(focus_seconds, -1, -1):
                mins, secs = divmod(remaining, 60)
                LIVE_STREAM_STATE["pomodoro"] = f"{mins:02d}:{secs:02d}"
                LIVE_STREAM_STATE["mode"] = "FOCUS"
                time.sleep(1)
            
            # Break Phase
            for remaining in range(break_seconds, -1, -1):
                mins, secs = divmod(remaining, 60)
                LIVE_STREAM_STATE["pomodoro"] = f"{mins:02d}:{secs:02d}"
                LIVE_STREAM_STATE["mode"] = "BREAK"
                time.sleep(1)

    t = threading.Thread(target=pomodoro_loop, daemon=True)
    t.start()
    return t

def start_chat_polling_thread(broadcast_id, youtube_service=None):
    def chat_loop():
        if not youtube_service or not broadcast_id:
            return
            
        try:
            # Fetch the liveChatId from broadcast
            broadcast_response = youtube_service.liveBroadcasts().list(
                part="snippet",
                id=broadcast_id
            ).execute()
            
            if not broadcast_response["items"]: return
            
            live_chat_id = broadcast_response["items"][0]["snippet"].get("liveChatId")
            if not live_chat_id: return
            
            next_page_token = None
            poll_delay = DEFAULT_CHAT_POLL_SECONDS
            viewer_gate = ViewerThresholdGate(youtube_service, broadcast_id, state_label="chat polling")
            viewer_gate_enabled = None
            
            while True:
                try:
                    chat_enabled = viewer_gate.is_enabled()
                except Exception as e:
                    reason = classify_chat_poll_error(e)
                    if reason == "quotaExceeded":
                        print("Chat polling stopped: quota exhausted during viewer check.")
                        return
                    print(f"Chat polling viewer check failed: {e}")
                    time.sleep(viewer_gate.refresh_seconds)
                    continue

                if chat_enabled != viewer_gate_enabled:
                    viewers = viewer_gate.current_viewers()
                    if chat_enabled:
                        print(f"Chat polling enabled at {viewers} viewers.")
                    else:
                        print(f"Chat polling paused below threshold: {viewers} viewers (need > {viewer_gate.min_viewers}).")
                    viewer_gate_enabled = chat_enabled

                if not chat_enabled:
                    LIVE_STREAM_STATE["chat_message"] = (
                        f"Chat polling paused until viewers exceed {viewer_gate.min_viewers}."
                    )
                    poll_delay = DEFAULT_CHAT_POLL_SECONDS
                    time.sleep(viewer_gate.refresh_seconds)
                    continue

                time.sleep(poll_delay)
                try:
                    request = youtube_service.liveChatMessages().list(
                        liveChatId=live_chat_id,
                        part="snippet,authorDetails",
                        pageToken=next_page_token
                    )
                    response = request.execute()
                    poll_delay = next_poll_delay_seconds(response)
                    
                    next_page_token = response.get("nextPageToken")
                    
                    for item in response.get("items", []):
                        msg = item["snippet"]["displayMessage"]
                        author = item["authorDetails"]["displayName"]
                        
                        if msg.startswith("!"):
                            # Command detected
                            cmd = msg.lower().strip()
                            if cmd == "!rain":
                                LIVE_STREAM_STATE["chat_message"] = f"🌧️ {author} summoned rain"
                            elif cmd == "!chill":
                                LIVE_STREAM_STATE["chat_message"] = f"❄️ {author} chilled the vibe"
                            elif cmd == "!superchat":
                                LIVE_STREAM_STATE["chat_message"] = f"🎉 Thanks {author}!"
                            else:
                                LIVE_STREAM_STATE["chat_message"] = f"💬 {author}: {msg}"
                            
                except Exception as e:
                    reason = classify_chat_poll_error(e)
                    if reason == "quotaExceeded":
                        print("Chat polling stopped: YouTube API quota exhausted.")
                        return
                    if reason == "rateLimitExceeded":
                        poll_delay = max(poll_delay, RATE_LIMIT_BACKOFF_SECONDS)
                        print(f"Chat polling backed off after rate limit: {e}")
                        continue
                    if reason in {"liveChatEnded", "liveChatDisabled", "liveChatNotFound"}:
                        print(f"Chat polling stopped: {e}")
                        return
                    print(f"Chat Polling Error: {e}")
                    
        except Exception as e:
            print(f"Failed to start chat polling: {e}")

    t = threading.Thread(target=chat_loop, daemon=True)
    t.start()
    return t
