import { createVisualizers } from "./visualizers/index.js";

const canvas = document.getElementById("visualizer");
const shaderFrame = document.getElementById("shader-frame");
const ctx = canvas.getContext("2d", { alpha: false, desynchronized: true });
const params = new URLSearchParams(window.location.search);
const TAU = Math.PI * 2;
const DEFAULT_CONFIG = {
  seed: "default-seed",
  visualizer_id: "liquid_ribbons",
  palette: ["#0B172A", "#224870", "#5FA8D3", "#E4F1FE"],
  profile_id: "default",
  daypart: "night",
  season: "winter",
  active_count: 3,
};

function clamp(value, min, max) {
  return Math.max(min, Math.min(max, value));
}

function lerp(a, b, t) {
  return a + (b - a) * t;
}

function hashSeed(seed) {
  let h = 1779033703 ^ seed.length;
  for (let i = 0; i < seed.length; i += 1) {
    h = Math.imul(h ^ seed.charCodeAt(i), 3432918353);
    h = (h << 13) | (h >>> 19);
  }
  return () => {
    h = Math.imul(h ^ (h >>> 16), 2246822507);
    h = Math.imul(h ^ (h >>> 13), 3266489909);
    return (h ^= h >>> 16) >>> 0;
  };
}

function mulberry32(seed) {
  return function next() {
    let t = (seed += 0x6d2b79f5);
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

function parseConfig() {
  const encoded = params.get("config");
  if (!encoded) {
    return DEFAULT_CONFIG;
  }
  const decoded = atob(encoded.replace(/-/g, "+").replace(/_/g, "/"));
  return { ...DEFAULT_CONFIG, ...JSON.parse(decoded) };
}

function hexToRgb(hex) {
  const value = hex.replace("#", "");
  const full = value.length === 3 ? value.split("").map((part) => part + part).join("") : value;
  const int = parseInt(full, 16);
  return {
    r: (int >> 16) & 255,
    g: (int >> 8) & 255,
    b: int & 255,
  };
}

function rgba(hex, alpha) {
  const { r, g, b } = hexToRgb(hex);
  return `rgba(${r}, ${g}, ${b}, ${alpha})`;
}

function mixHex(a, b, amount) {
  const left = hexToRgb(a);
  const right = hexToRgb(b);
  const t = clamp(amount, 0, 1);
  const r = Math.round(lerp(left.r, right.r, t));
  const g = Math.round(lerp(left.g, right.g, t));
  const blue = Math.round(lerp(left.b, right.b, t));
  return `rgb(${r}, ${g}, ${blue})`;
}

function normalizePalette(colors) {
  if (!Array.isArray(colors) || colors.length === 0) {
    return DEFAULT_CONFIG.palette;
  }
  if (colors.length >= 4) {
    return colors.slice(0, 4);
  }
  const output = [...colors];
  while (output.length < 4) {
    output.push(output[output.length - 1]);
  }
  return output;
}

function buildSmoothClosedPath(points) {
  const path = new Path2D();
  const last = points[points.length - 1];
  const first = points[0];
  path.moveTo((last.x + first.x) / 2, (last.y + first.y) / 2);
  for (let i = 0; i < points.length; i += 1) {
    const current = points[i];
    const next = points[(i + 1) % points.length];
    const midX = (current.x + next.x) / 2;
    const midY = (current.y + next.y) / 2;
    path.quadraticCurveTo(current.x, current.y, midX, midY);
  }
  path.closePath();
  return path;
}

function markVisualizerReady() {
  if (!window.__visualizerReady) {
    window.__visualizerReady = true;
  }
}

const config = parseConfig();
const palette = normalizePalette(config.palette);
const seedSource = String(config.seed || DEFAULT_CONFIG.seed);
const activity = clamp((config.active_count || 3) / 3, 0.85, 1.45);
const tempo = clamp(0.5 + activity * 0.11, 0.58, 0.72);
const viewport = { width: 0, height: 0, dpr: 1 };
const pointerState = { x: -1, y: -1 };

window.addEventListener("mousemove", (event) => {
  pointerState.x = event.clientX;
  pointerState.y = event.clientY;
});

function scopedRng(scope) {
  return mulberry32(hashSeed(`${seedSource}:${scope}`)());
}

const backdropRng = scopedRng("backdrop");
const backdropState = {
  blooms: Array.from({ length: 7 }, (_, index) => ({
    x: 0.1 + backdropRng() * 0.8,
    y: 0.1 + backdropRng() * 0.8,
    radius: 0.16 + backdropRng() * 0.22,
    drift: 0.008 + backdropRng() * 0.012,
    phase: backdropRng() * TAU,
    alpha: 0.022 + backdropRng() * 0.035,
    colorIndex: index % palette.length,
  })),
  haze: Array.from({ length: 18 }, () => ({
    y: backdropRng(),
    alpha: 0.012 + backdropRng() * 0.02,
  })),
};

function resize() {
  const width = window.innerWidth;
  const height = window.innerHeight;
  const dpr = window.devicePixelRatio || 1;
  if (
    viewport.width === width &&
    viewport.height === height &&
    viewport.dpr === dpr
  ) {
    return;
  }

  viewport.width = width;
  viewport.height = height;
  viewport.dpr = dpr;
  canvas.width = Math.round(width * dpr);
  canvas.height = Math.round(height * dpr);
  canvas.style.width = `${width}px`;
  canvas.style.height = `${height}px`;
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
}

function drawBackground(t, options = {}) {
  const { monochrome = false } = options;
  const top = monochrome ? "rgb(6, 6, 7)" : mixHex(palette[0], "#020406", 0.72);
  const mid = monochrome ? "rgb(12, 13, 15)" : mixHex(palette[1], "#05070A", 0.68);
  const bottom = monochrome ? "rgb(9, 10, 11)" : mixHex(palette[2], "#050608", 0.7);

  const gradient = ctx.createLinearGradient(0, 0, 0, viewport.height);
  gradient.addColorStop(0, top);
  gradient.addColorStop(0.55, mid);
  gradient.addColorStop(1, bottom);
  ctx.fillStyle = gradient;
  ctx.fillRect(0, 0, viewport.width, viewport.height);

  backdropState.blooms.forEach((bloom, index) => {
    const x = (bloom.x + Math.sin(t * bloom.drift + bloom.phase) * 0.03) * viewport.width;
    const y = (bloom.y + Math.cos(t * bloom.drift * 0.92 + bloom.phase) * 0.026) * viewport.height;
    const radius = bloom.radius * Math.min(viewport.width, viewport.height);
    const alpha = bloom.alpha * (0.72 + 0.28 * Math.sin(t * 0.12 + index * 0.8));
    const gradientFill = ctx.createRadialGradient(x, y, 0, x, y, radius);
    const bloomColor = monochrome ? "#E5E7EB" : palette[bloom.colorIndex];
    gradientFill.addColorStop(0, rgba(bloomColor, alpha));
    gradientFill.addColorStop(0.55, rgba(bloomColor, alpha * 0.35));
    gradientFill.addColorStop(1, rgba(bloomColor, 0));
    ctx.fillStyle = gradientFill;
    ctx.beginPath();
    ctx.arc(x, y, radius, 0, TAU);
    ctx.fill();
  });

  ctx.strokeStyle = monochrome ? "rgba(255, 255, 255, 0.02)" : rgba(palette[3], 0.03);
  ctx.lineWidth = 1;
  backdropState.haze.forEach((line, index) => {
    const y = (line.y + Math.sin(t * 0.045 + index * 0.3) * 0.004) * viewport.height;
    ctx.globalAlpha = line.alpha * (0.8 + 0.2 * Math.sin(t * 0.1 + index * 0.35));
    ctx.beginPath();
    ctx.moveTo(0, y);
    ctx.lineTo(viewport.width, y);
    ctx.stroke();
  });
  ctx.globalAlpha = 1;

  const vignette = ctx.createRadialGradient(
    viewport.width / 2,
    viewport.height / 2,
    Math.min(viewport.width, viewport.height) * 0.1,
    viewport.width / 2,
    viewport.height / 2,
    Math.max(viewport.width, viewport.height) * 0.75,
  );
  vignette.addColorStop(0, "rgba(0, 0, 0, 0)");
  vignette.addColorStop(1, monochrome ? "rgba(0, 0, 0, 0.5)" : "rgba(0, 0, 0, 0.42)");
  ctx.fillStyle = vignette;
  ctx.fillRect(0, 0, viewport.width, viewport.height);
}

const runtime = {
  TAU,
  activity,
  buildSmoothClosedPath,
  clamp,
  ctx,
  palette,
  pointerState,
  rgba,
  scopedRng,
  tempo,
  viewport,
};

const visualizers = createVisualizers(runtime);
const activeVisualizer = visualizers[config.visualizer_id] || visualizers.liquid_ribbons;
let lastFrame = 0;

window.__visualizerReady = false;

function setupSurface() {
  if (activeVisualizer.type === "shader") {
    canvas.hidden = true;
    shaderFrame.hidden = false;
    shaderFrame.addEventListener(
      "load",
      () => {
        activeVisualizer.onLoad?.(shaderFrame, runtime);
        markVisualizerReady();
      },
      { once: true },
    );
    shaderFrame.src = activeVisualizer.src;
    return;
  }

  shaderFrame.hidden = true;
  canvas.hidden = false;
  resize();
  markVisualizerReady();
}

function render(frameTime) {
  const dt = lastFrame === 0 ? 1 / 60 : Math.min(0.05, (frameTime - lastFrame) / 1000);
  lastFrame = frameTime;
  const seconds = frameTime / 1000;

  if (activeVisualizer.type === "shader") {
    activeVisualizer.tick?.(seconds, dt, shaderFrame, runtime);
    requestAnimationFrame(render);
    return;
  }

  resize();
  drawBackground(seconds, { monochrome: activeVisualizer.id === "monochrome_rain" });
  activeVisualizer.draw(seconds, dt);
  requestAnimationFrame(render);
}

window.addEventListener("resize", () => {
  if (activeVisualizer.type !== "shader") {
    resize();
  }
});

setupSurface();
requestAnimationFrame(render);

// Realtime State Polling Bridge
let lastChatMessage = null;
async function pollStreamState() {
  try {
    const res = await fetch('http://127.0.0.1:' + window.location.port + '/api/state');
    if (res.ok) {
      const state = await res.json();
      
      const pomodoroDiv = document.getElementById('pomodoro-timer');
      const pomoStatus = document.getElementById('pomo-status');
      const pomoTime = document.getElementById('pomo-time');
      
      if (state.pomodoro) {
        pomodoroDiv.hidden = false;
        pomoStatus.textContent = state.mode || 'FOCUS';
        pomoTime.textContent = state.pomodoro;
      } else {
        pomodoroDiv.hidden = true;
      }

      const chatPopup = document.getElementById('chat-popup');
      const chatMsg = document.getElementById('chat-msg');
      if (state.chat_message && state.chat_message !== lastChatMessage) {
        lastChatMessage = state.chat_message;
        chatMsg.textContent = state.chat_message;
        chatPopup.classList.remove('hidden-fade');
        
        // Hide after 8 seconds
        setTimeout(() => {
          chatPopup.classList.add('hidden-fade');
        }, 8000);
      }
    }
  } catch (error) {
    // silently fail polling
  }
}

setInterval(pollStreamState, 1000);
