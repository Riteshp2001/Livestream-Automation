import threading
import time
import datetime
from lib.browser_visualizer import LIVE_STREAM_STATE

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
            
            while True:
                time.sleep(5) # Poll every 5s per API quota limits
                try:
                    request = youtube_service.liveChatMessages().list(
                        liveChatId=live_chat_id,
                        part="snippet,authorDetails",
                        pageToken=next_page_token
                    )
                    response = request.execute()
                    
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
                    print(f"Chat Polling Error: {e}")
                    
        except Exception as e:
            print(f"Failed to start chat polling: {e}")

    t = threading.Thread(target=chat_loop, daemon=True)
    t.start()
    return t
