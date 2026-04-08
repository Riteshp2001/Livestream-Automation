# 🤖 Agent Kickstart Manual
**Target Audience:** Autonomous Agents, LLM Coding Assistants, and Humans reading the codebase for the first time.

Welcome to the Livestream Automation Engine. This application renders and orchestrates procedural infinite streaming of beautifully visualized lo-fi web apps directly to YouTube Live via FFmpeg.

## 🗂️ High-Level Directory Structure
In order to keep the codebase pristine, the project is sliced into very discrete domains:

- `/config/` 👉 Contains all static structural JSON configurations. This is where you modify definitions like `livestream_profiles.json` (defines allowable themes and colors) and YouTube auth `token.json`.
- `/data/` 👉 Contains all dynamic system state. Whenever the system runs, it logs to `stream_history.json` and updates `used_content.json` here.
- `/lib/` 👉 The core Python engine. Handles everything from orchestrating Playwright headless web browsers (`browser_visualizer.py`), setting up RTMP FFMPEG encoding (`stream_engine.py`), creating audio (`audio_generation/`), and spinning up daemons for interaction (`stream_interactions.py`).
- `/web/stream_visualizer/` 👉 The Frontend Application. This is a simple HTML/JS/CSS structure parsed locally by Playwright. It paints gorgeous procedural Shaders out onto a WebGL canvas and manages Pomodoro UI overlays. Note that it executes locally at `http://127.0.0.1:<PORT>/` via the Python `SimpleHTTPRequestHandler`.
- `/assets/` & `/videos/` 👉 Offline caches for downloaded youtube content or generated backing tracks.

## ⚙️ Architecture & Data Pipelines
The engine runs synchronously, passing states through these core pipes when you run `python main.py livestream`:

1. **Authentication & Metadata** (`lib/livestream.py` & `lib/livestream_metadata.py`): Reaches out to YouTube Data API to establish a broadcast. Identifies the "Vibe" and "Palette" for the stream.
2. **Playwright Visualizer Context** (`lib/browser_visualizer.py`): A Python local HTTP web server fires up, hosting the files in `web/stream_visualizer/`. A headless chromium instance accesses the UI URL. The UI renders at 1080p.
3. **The Global State Bridge (`/api/state`)**: The Python HTTP server has a custom `do_GET` trap that listens on `/api/state` and returns the `LIVE_STREAM_STATE` dict cache. The Javascript `app.js` fetches this state every `1000ms`, dynamically updating the Pomodoro clock and Chat overlay elements on the WebGL canvas.
4. **Daemon Interactivity** (`lib/stream_interactions.py` & `lib/ai_dj.py`): Background Python threads run concurrently. One thread pushes Pomodoro focus countdowns mathematically into the `LIVE_STREAM_STATE`. The other polls YouTube Live Chat API looking for viewer commands like `!rain` to insert into the pipeline.
5. **FFMPEG RTMP Encoder** (`lib/stream_engine.py`): FFmpeg pipes the raw headless Chromium stream back out natively into the YouTube RTMP ingestion endpoint, marrying it perfectly with lo-fi beats.

## 🚀 Before You Modify...
If you are an agent tasked with extending the codebase, remember:
- When changing core visualizers, always update `config/livestream_profiles.json`. If you add a nonexistent visualizer there, it'll crash.
- Ensure audio generation changes pipe neatly into `data/stream_sound_catalog.json`.
- Do not run `cat` in your toolsets. Read this file natively!
