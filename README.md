<div align="center">

<img src="https://readme-typing-svg.demolab.com?font=Fira+Code&weight=700&size=28&pause=1000&color=A78BFA&center=true&vCenter=true&width=700&lines=Symphony.Station+Livestream+Engine;24%2F7+Autonomous+AI+Livestreaming;Powered+by+Playwright+%2B+FFmpeg+%2B+Groq" alt="Typing SVG" />

<br/>

[![YouTube Channel](https://img.shields.io/badge/▶️%20SUBSCRIBE%20ON%20YOUTUBE-FF0000?style=for-the-badge&logo=youtube&logoColor=white)](https://www.youtube.com/@Symphony.Station)
[![GitHub Actions](https://img.shields.io/badge/GitHub%20Actions-LIVE%2024%2F7-2088FF?style=for-the-badge&logo=githubactions&logoColor=white)](https://github.com/Riteshp2001/Livestream-Automation/actions)
[![License: MIT](https://img.shields.io/badge/License-MIT-green?style=for-the-badge)](LICENSE)
[![Python 3.11](https://img.shields.io/badge/Python-3.11-blue?style=for-the-badge&logo=python&logoColor=white)](https://python.org)

<br/>

> **A fully autonomous, AI-powered livestreaming engine** that generates visuals, picks audio, writes viral titles and descriptions, renders thumbnails, and streams to YouTube — entirely hands-free, 24/7, for free.

</div>

---

## 🎬 Watch Live on YouTube

<div align="center">

### 🔔 [**► SYMPHONY.STATION — Lo-Fi, Rain & Ambience Streams**](https://www.youtube.com/@Symphony.Station)

> Deep focus beats · Rain sounds · Study music · Sleep vibes  
> **Subscribe and hit the bell** so you never miss a new atmospheric stream dropping!

| Vibe | When | Hours |
|------|------|-------|
| 🌧️ Midnight Rain & Lo-Fi Focus | Daily | 5h+ |
| 🌿 Forest Ambience & Study Beats | Daily | 5h+ |
| 🌙 Night Sky & Sleep Music | Daily | 5h+ |
| ☕ Cozy Café Ambience | Daily | 5h+ |

</div>

---

## ✨ What This Does

This engine powers the **Symphony.Station** YouTube channel end-to-end:

```
1. Picks a themed profile   →  rain, forest, café, space, etc.
2. Renders a shader visual  →  100+ WebGL shaders via headless Playwright
3. Generates or picks audio →  Freesound / Pixabay / Supriya procedural audio
4. Writes viral metadata    →  Hook-based titles + descriptions via Groq LLaMA
5. Generates a thumbnail    →  Pollinations.ai (free, no quota)
6. Streams to YouTube       →  via FFmpeg RTMP
7. Chains the next run      →  Waits 30 min → auto-triggers next 5h stream
```

No manual intervention. Fully driven by GitHub Actions.

---

## 🏗️ Project Structure

```text
Livestream-Automation/
├── 📁 config/                    # Static configuration
│   ├── livestream_profiles.json  # All stream themes & visual profiles
│   └── livestream_themes.json    # Vibe metadata per theme
│
├── 📁 data/                      # Runtime state (gitignored where sensitive)
│   ├── auto.json                 # Automation settings
│   ├── stream_sound_catalog.json # All registered audio assets
│   └── used_content.json         # Tracks used URLs to avoid repeats
│
├── 📁 lib/                       # Core Python engine
│   ├── browser_visualizer.py     # Playwright headless renderer + state HTTP bridge
│   ├── livestream_entrypoints.py # Main orchestrator
│   ├── groq_copywriter.py        # AI viral title & description generator
│   ├── huggingface_thumbnail_background.py  # Free thumbnail image gen (Pollinations.ai)
│   ├── stream_interactions.py    # Pomodoro timer + YouTube chat polling
│   ├── ai_dj.py                  # AI Radio Host drop-ins
│   ├── stream_generation.py      # Profile resolution & pack building
│   ├── stream_engine.py          # FFmpeg RTMP encoder
│   └── audio_generation/         # Supriya procedural audio synthesis
│
├── 📁 web/stream_visualizer/     # Frontend WebGL visualizer
│   ├── index.html                # UI with Pomodoro + chat overlays
│   ├── app.js                    # State polling, shader runner
│   ├── styles.css                # Cinematic vignette + overlay styles
│   ├── shaders/radiant/          # 100+ WebGL ambient shaders
│   └── visualizers/              # Canvas-based animated scenes
│
├── 📁 assets/stream_sounds/      # Local audio library (.ogg)
├── 📁 .github/workflows/         # GitHub Actions pipeline
├── AGENT_KICKSTART.md            # AI agent onboarding guide
├── main.py                       # CLI entry point
└── setup.py                      # First-time local setup wizard
```

---

## 🚀 Quick Start

### Local Run

```bash
# 1. Install dependencies
pip install -r requirements.txt
python -m playwright install chromium

# 2. First-time setup (YouTube auth + .env)
python setup.py

# 3. Run a livestream
python main.py --livestream

# Other modes
python main.py --generate-pack           # Pre-render a visual pack
python main.py --resolve-stream-profile  # Preview what tonight's stream will be
python main.py --generate-test-videos    # Render a short test clip
```

### GitHub Actions (Recommended — Unlimited Free Minutes on Public Repo)

Add these secrets to your repository:

| Secret | Description |
|--------|-------------|
| `CLIENT_SECRETS_JSON` | Base64-encoded `client_secrets.json` from Google Cloud |
| `TOKEN_JSON` | Base64-encoded `token.json` from OAuth flow |
| `YOUTUBE_CHANNEL_ID` | Your YouTube channel ID |
| `PIXABAY_API_KEY` | [pixabay.com/api](https://pixabay.com/api/docs/) |
| `FREESOUND_API_KEY` | [freesound.org/apiv2](https://freesound.org/apiv2/) |
| `GROQ_API_KEY` | [console.groq.com](https://console.groq.com) — free tier available |
| `HF_TOKEN` | [huggingface.co/settings/tokens](https://huggingface.co/settings/tokens) |

Then trigger the workflow manually from the **Actions** tab. It runs 5 hours, waits 30 minutes, then self-chains forever.

---

## 🧠 Interactive Stream Features

| Feature | Description |
|--------|-------------|
| ⏱️ **Pomodoro Timer** | Elegant floating clock showing 50 min focus / 10 min break cycles |
| 💬 **Live Chat Commands** | Viewers type `!rain`, `!chill`, `!storm` to trigger visual changes |
| 🎙️ **AI DJ Drop-ins** | Periodic atmospheric messages pushed to the stream overlay |
| 🌐 **HTTP State Bridge** | Python pushes state to `/api/state` which the WebGL frontend polls every second |

---

## ⚙️ Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `STREAM_DURATION_MINUTES` | `300` | Length of each stream |
| `STREAM_RENDER_MODE` | `prerender` | `prerender` or `live` |
| `STREAM_CONTENT_SOURCE` | `generated` | `generated`, `manual`, or `external` |
| `STREAM_PROFILE_ID` | auto | Force a specific profile |
| `STREAM_TIMEZONE` | `America/Chicago` | Affects day/night profile selection |
| `USE_GROQ_COPY` | `1` | Enable AI-generated titles & descriptions |
| `USE_HF_THUMBNAILS` | `true` | Enable AI thumbnail generation |
| `STREAM_FORCE_DAYPART` | — | Override: `morning`, `night`, `afternoon` |

---

## 🎵 Audio Attribution & Credits

Audio assets used in this project are sourced from the following platforms under their respective licenses:

### [Freesound.org](https://freesound.org)
All sounds sourced via the **Freesound API** are used under their individual **Creative Commons** licenses. Each sound's specific license (CC0, CC BY, CC BY-NC) is tracked at download time.

> 📌 **Freesound** is a collaborative database of Creative Commons licensed sounds.  
> Visit: [https://freesound.org](https://freesound.org)  
> License info per sound: [https://freesound.org/help/faq/](https://freesound.org/help/faq/)

### [Pixabay.com](https://pixabay.com)
Video and ambient footage is sourced via the **Pixabay API** under the **Pixabay License**.

> 📌 Under the Pixabay License, content can be used **for free for commercial and non-commercial use**, without attribution required — though attribution is always appreciated.  
> Visit: [https://pixabay.com/service/license-summary/](https://pixabay.com/service/license-summary/)

### Bundled `.ogg` Audio Files (`assets/stream_sounds/`)
Ambient sound layers bundled in this repo (rain, fireplace, café, nature, etc.) are sourced from open and permissive creative commons audio libraries. If you are a creator whose work is included and have concerns, please [open an issue](https://github.com/Riteshp2001/Livestream-Automation/issues).

---

## 🛠️ Tech Stack

| Component | Technology |
|-----------|-----------|
| Rendering | Playwright + Chromium (headless) |
| Encoding | FFmpeg (RTMP to YouTube) |
| Shaders | WebGL / GLSL (100+ radiant shaders) |
| AI Copy | Groq Cloud — LLaMA 3.3 70B |
| Thumbnails | Pollinations.ai (free, no key needed) |
| Audio Synth | Supriya + SuperCollider |
| Automation | GitHub Actions (self-chaining, 5h loops) |
| Platform | YouTube Live API v3 |

---

## 📄 License

[MIT](LICENSE) — Fork it, remix it, stream it.

---

<div align="center">

### Made with ❤️ by [Ritesh Pandit](https://riteshdpandit.vercel.app/)

**If this powers your stream, leave a ⭐ and subscribe to the channel!**

[![YouTube Channel](https://img.shields.io/badge/🎵%20Symphony.Station%20on%20YouTube-Subscribe%20Now-FF0000?style=for-the-badge&logo=youtube)](https://www.youtube.com/@Symphony.Station)

</div>
