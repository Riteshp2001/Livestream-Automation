export default function createMistLayersVisualizer(runtime) {
  const { TAU, ctx, palette, rgba, scopedRng, tempo, viewport } = runtime;
  const rng = scopedRng("mist_layers");
  const bands = Array.from({ length: 5 }, (_, index) => ({
    y: 0.18 + rng() * 0.62,
    speed: 0.05 + rng() * 0.04,
    amplitude: 12 + rng() * 22,
    waveCount: 0.7 + rng() * 0.75,
    thickness: 0.035 + rng() * 0.045,
    phase: rng() * TAU,
    colorIndex: index % palette.length,
    alpha: 0.11 + rng() * 0.05,
  }));

  return {
    id: "mist_layers",
    draw(t) {
      const previousMode = ctx.globalCompositeOperation;
      ctx.globalCompositeOperation = "screen";
      ctx.lineCap = "round";
      bands.forEach((band) => {
        const drift = Math.sin(t * band.speed * tempo + band.phase);
        const baseY = band.y * viewport.height + drift * 24;
        ctx.beginPath();
        for (let step = 0; step <= 40; step += 1) {
          const x = (step / 40) * viewport.width;
          const wavePhase = (x / viewport.width) * TAU * band.waveCount + t * band.speed * 1.05 + band.phase;
          const y = baseY + Math.sin(wavePhase) * band.amplitude;
          if (step === 0) ctx.moveTo(x, y);
          else ctx.lineTo(x, y);
        }
        ctx.strokeStyle = rgba(palette[band.colorIndex], band.alpha * (0.88 + 0.12 * drift));
        ctx.lineWidth = Math.min(viewport.width, viewport.height) * band.thickness;
        ctx.shadowBlur = 30;
        ctx.shadowColor = rgba(palette[band.colorIndex], band.alpha * 0.75);
        ctx.stroke();
      });
      ctx.shadowBlur = 0;
      ctx.globalCompositeOperation = previousMode;
    },
  };
}
