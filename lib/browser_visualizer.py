import base64
import json
import os
import socketserver
import threading
from functools import partial
from http.server import SimpleHTTPRequestHandler
from pathlib import Path
from tempfile import TemporaryDirectory

from lib.stream_engine import transcode_video


VISUALIZER_WEB_ROOT = Path("web") / "stream_visualizer"


class _ThreadingTCPServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    allow_reuse_address = True


LIVE_STREAM_STATE = {
    "pomodoro": "",
    "mode": "",
    "weather_override": None,
    "palette_override": None,
    "chat_message": None,
}

class _QuietRequestHandler(SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/api/state':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.send_header('Cache-Control', 'no-store')
            self.end_headers()
            self.wfile.write(json.dumps(LIVE_STREAM_STATE).encode('utf-8'))
        else:
            super().do_GET()

    def log_message(self, format, *args):
        return


class VisualizerHttpServer:
    def __init__(self, root_dir):
        self.root_dir = str(root_dir)
        self.server = None
        self.thread = None
        self.port = None

    def start(self):
        handler = partial(_QuietRequestHandler, directory=self.root_dir)
        self.server = _ThreadingTCPServer(("127.0.0.1", 0), handler)
        self.port = self.server.server_address[1]
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        return self

    def stop(self):
        if self.server:
            self.server.shutdown()
            self.server.server_close()
        if self.thread:
            self.thread.join(timeout=1)

    def page_url(self, config):
        encoded = base64.urlsafe_b64encode(json.dumps(config).encode("utf-8")).decode(
            "ascii"
        )
        return f"http://127.0.0.1:{self.port}/index.html?config={encoded}"


def _playwright():
    try:
        from playwright.sync_api import sync_playwright

        return sync_playwright
    except Exception as error:
        raise RuntimeError(
            "Playwright is required for the stream visualizer. Install requirements and run `python -m playwright install chromium`."
        ) from error


def render_visualizer_video(
    config, output_path, duration_seconds, width=1920, height=1080
):
    sync_playwright = _playwright()
    last_error = None
    for attempt in range(1, 4):
        server = VisualizerHttpServer(VISUALIZER_WEB_ROOT).start()
        try:
            with TemporaryDirectory() as tmpdir:
                with sync_playwright() as playwright:
                    browser = playwright.chromium.launch(headless=True)
                    context = browser.new_context(
                        viewport={"width": width, "height": height},
                        record_video_dir=tmpdir,
                        record_video_size={"width": width, "height": height},
                    )
                    page = context.new_page()
                    page.goto(server.page_url(config), wait_until="domcontentloaded")
                    page.wait_for_function(
                        "window.__visualizerReady === true", timeout=90000
                    )
                    page.wait_for_timeout(int(duration_seconds * 1000) + 1200)
                    page.close()
                    context.close()
                    browser.close()

                videos = sorted(Path(tmpdir).glob("*.webm"))
                if not videos:
                    raise RuntimeError(
                        "The visualizer recording step did not produce a video file."
                    )
                transcode_video(
                    str(videos[-1]),
                    output_path,
                    timeout_seconds=max(300, int(duration_seconds) + 180),
                )
                return output_path
        except Exception as error:
            last_error = error
            if attempt == 3:
                raise
        finally:
            server.stop()
    raise last_error


class LiveVisualizerSession:
    def __init__(self, config, width=1920, height=1080):
        self.config = config
        self.width = width
        self.height = height
        self.server = None
        self.playwright = None
        self.browser = None
        self.context = None
        self.page = None
        self.user_data_dir = None

    def start(self):
        self.server = VisualizerHttpServer(VISUALIZER_WEB_ROOT).start()
        sync_playwright = _playwright()
        self.playwright = sync_playwright().start()
        page_url = self.server.page_url(self.config)
        self.user_data_dir = TemporaryDirectory()
        self.context = self.playwright.chromium.launch_persistent_context(
            self.user_data_dir.name,
            headless=False,
            viewport={"width": self.width, "height": self.height},
            args=[
                f"--app={page_url}",
                f"--window-size={self.width},{self.height}",
                "--autoplay-policy=no-user-gesture-required",
                "--start-fullscreen",
                "--kiosk",
                "--no-first-run",
                "--no-default-browser-check",
                "--disable-infobars",
                "--disable-notifications",
                "--disable-extensions",
                "--disable-default-apps",
                "--disable-popup-blocking",
                "--window-position=0,0",
                "--hide-scrollbars",
                "--disable-translate",
                "--mute-audio",
                "--disable-background-timer-throttling",
                "--disable-renderer-backgrounding",
                "--disable-backgrounding-occluded-windows",
                "--disable-features=TranslateUI,Infobars,DownloadBubble",
                "--disable-frame-rate-limit",
                "--disable-gpu-vsync",
                "--disable-window-decorations",
                "--chrome-frame",
                "--noerrdialogs",
                "--disable-session-crashed-bubble",
            ],
        )
        self.browser = self.context.browser
        self.page = self.context.pages[0] if self.context.pages else self.context.new_page()
        if self.page.url != page_url:
            self.page.goto(page_url, wait_until="load")
        else:
            self.page.wait_for_load_state("load")
        self.page.wait_for_function("window.__visualizerReady === true", timeout=60000)
        self.page.bring_to_front()
        self.page.evaluate(
            """
            async () => {
                const root = document.documentElement;
                if (document.fullscreenElement !== root) {
                    try {
                        await root.requestFullscreen();
                    } catch (error) {
                        // Browser-level fullscreen fallback is handled below.
                    }
                }
            }
            """
        )
        try:
            self.page.keyboard.press("F11")
        except Exception:
            pass
        self.page.wait_for_timeout(500)
        return self

    def stop(self):
        if self.page:
            try:
                self.page.close()
            except Exception:
                pass
            self.page = None
        if self.context:
            try:
                self.context.close()
            except Exception:
                pass
            self.context = None
            self.browser = None
        elif self.browser:
            try:
                self.browser.close()
            except Exception:
                pass
            self.browser = None
        if self.playwright:
            try:
                self.playwright.stop()
            except Exception:
                pass
            self.playwright = None
        if self.server:
            self.server.stop()
            self.server = None
        if self.user_data_dir:
            self.user_data_dir.cleanup()
            self.user_data_dir = None
