import time
import threading
from lib.browser_visualizer import LIVE_STREAM_STATE

def start_ai_dj_thread():
    def ai_dj_loop():
        messages = [
            "🎙️ Hey everyone, thanks for tuning in to Symphony.Station.",
            "🎙️ Don't forget to take a breather. You're doing great.",
            "🎙️ If you're deep in focus, remember: one step at a time.",
            "🎙️ Night block engaged. Keep that momentum.",
            "🎙️ Like the vibe? Drop a !chill or !rain in the chat.",
            "🎙️ Hope your coffee is warm and your mind is clear."
        ]
        
        while True:
            # Wait 35-45 minutes between bits (scaled down for demo logic, let's just use 45 mins)
            time.sleep(45 * 60)
            
            import random
            msg = random.choice(messages)
            
            # Since we don't have an intense TTS model rigged into the audio mixer loop yet, 
            # we will elegantly handle this by pushing the AI DJ text as a primary notification.
            # (In the future, we could trigger an ElevenLabs TTS generation and play it via PyAudio!)
            LIVE_STREAM_STATE["chat_message"] = msg

    t = threading.Thread(target=ai_dj_loop, daemon=True)
    t.start()
    return t
