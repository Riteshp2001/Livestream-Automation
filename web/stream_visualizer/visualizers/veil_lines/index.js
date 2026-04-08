export default function createVeilLinesVisualizer(runtime) {
  const { TAU, ctx, palette, rgba, scopedRng, tempo, viewport } = runtime;
  const rng = scopedRng("veil_lines");
  const lines = Array.from({ length: 38 }, (_, index) => ({
    x: 0.05 + rng() * 0.9,
    y: rng(),
    length: 0.28 + rng() * 0.34,
    sway: 0.08 + rng() * 0.12,
    drift: 0.06 + rng() * 0.06,
    fall: 0.012 + rng() * 0.018,
    phase: rng() * TAU,
    width: 0.8 + rng() * 1.4,
    alpha: 0.08 + rng() * 0.12,
    colorIndex: index % palette.length,
    slant: 8 + rng() * 18,
  }));

  return {
    id: "veil_lines",
    draw(t) {
      ctx.lineCap = "round";
      lines.forEach((line) => {
        const x =
          line.x * viewport.width +
          Math.sin(t * line.sway * tempo + line.phase) * 26 +
          Math.cos(t * line.sway * 0.45 * tempo + line.phase * 1.3) * 8;
        const travel = (line.y + t * line.fall * tempo) % 1;
        const centerY =
          (0.06 + travel * 0.9 + Math.sin(t * line.drift * tempo + line.phase * 0.7) * 0.04) *
          viewport.height;
        const halfLength =
          ((line.length * viewport.height) / 2) * (0.88 + 0.16 * Math.sin(t * 0.18 * tempo + line.phase));
        const topY = centerY - halfLength;
        const bottomY = centerY + halfLength;
        const slant = Math.sin(t * line.drift * 0.65 * tempo + line.phase) * line.slant;
        const alpha = line.alpha * (0.82 + 0.18 * Math.sin(t * 0.22 * tempo + line.phase * 1.5));
        const gradient = ctx.createLinearGradient(x - slant, topY, x + slant, bottomY);
        gradient.addColorStop(0, rgba(palette[line.colorIndex], 0));
        gradient.addColorStop(0.45, rgba(palette[line.colorIndex], alpha * 0.9));
        gradient.addColorStop(0.5, rgba(palette[line.colorIndex], alpha));
        gradient.addColorStop(0.55, rgba(palette[line.colorIndex], alpha * 0.9));
        gradient.addColorStop(1, rgba(palette[line.colorIndex], 0));
        ctx.strokeStyle = gradient;
        ctx.lineWidth = line.width;
        ctx.beginPath();
        ctx.moveTo(x - slant, topY);
        ctx.lineTo(x + slant, bottomY);
        ctx.stroke();
      });
    },
  };
}
