export default function createRadialRingsVisualizer(runtime) {
  const { TAU, ctx, palette, rgba, scopedRng, tempo, viewport } = runtime;
  const rng = scopedRng("radial_rings");
  const phases = Array.from({ length: 6 }, () => rng());
  const strokeWidths = Array.from({ length: 6 }, () => 1.2 + rng() * 0.7);
  const speeds = Array.from({ length: 6 }, () => 0.35 + rng() * 0.18);

  return {
    id: "radial_rings",
    draw(t) {
      const centerX = viewport.width / 2;
      const centerY = viewport.height / 2;
      const maxRadius = Math.max(viewport.width, viewport.height) * 0.5;
      const cycle = t * (1 / 18) * tempo;
      ctx.lineCap = "round";

      for (let i = 0; i < phases.length; i += 1) {
        const normalized = (cycle * speeds[i] + phases[i]) % 1;
        const radius = normalized * maxRadius;
        const alpha = Math.sin(normalized * Math.PI) * 0.52;
        ctx.strokeStyle = rgba(palette[i % palette.length], alpha);
        ctx.lineWidth = strokeWidths[i];
        ctx.beginPath();
        ctx.arc(centerX, centerY, radius, 0, TAU);
        ctx.stroke();
      }
    },
  };
}
