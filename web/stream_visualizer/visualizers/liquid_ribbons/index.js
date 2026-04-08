export default function createLiquidRibbonsVisualizer(runtime) {
  const { TAU, ctx, palette, rgba, scopedRng, tempo, viewport } = runtime;
  const rng = scopedRng("liquid_ribbons");
  const offsets = Array.from({ length: 6 }, () => rng() * TAU);

  return {
    id: "liquid_ribbons",
    draw(t) {
      const ribbonCount = offsets.length;
      const spacing = viewport.height / (ribbonCount + 1);
      const phase = t * (TAU / 24) * tempo;
      ctx.lineCap = "round";
      ctx.lineWidth = 4.5;

      for (let i = 0; i < ribbonCount; i += 1) {
        const baseY = spacing * (i + 1);
        ctx.beginPath();
        for (let step = 0; step <= 60; step += 1) {
          const x = (step / 60) * viewport.width;
          const wave = Math.sin((x / (viewport.width / 3.2)) * TAU + phase + offsets[i]) * 14;
          const pulse = 1 + 0.18 * Math.sin(phase * 1.2 + i * 0.6);
          const y = baseY + wave * pulse;
          if (step === 0) {
            ctx.moveTo(x, y);
          } else {
            ctx.lineTo(x, y);
          }
        }

        const gradient = ctx.createLinearGradient(0, baseY - 30, viewport.width, baseY + 30);
        gradient.addColorStop(0, rgba(palette[i % palette.length], 0.16));
        gradient.addColorStop(0.5, rgba(palette[(i + 1) % palette.length], 0.68));
        gradient.addColorStop(1, rgba(palette[i % palette.length], 0.16));
        ctx.strokeStyle = gradient;
        ctx.shadowBlur = 12;
        ctx.shadowColor = rgba(palette[(i + 1) % palette.length], 0.1);
        ctx.stroke();
      }

      ctx.shadowBlur = 0;
    },
  };
}
