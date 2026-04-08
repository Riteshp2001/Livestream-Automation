export default function createMorphingPolygonVisualizer(runtime) {
  const { TAU, buildSmoothClosedPath, ctx, palette, rgba, scopedRng, tempo, viewport } = runtime;
  const rng = scopedRng("morphing_polygon");
  const freqs = Array.from({ length: 8 }, () => 0.24 + rng() * 0.28);
  const phases = Array.from({ length: 8 }, () => rng() * TAU);

  return {
    id: "morphing_polygon",
    draw(t) {
      const phase = t * (TAU / 24) * tempo;
      const centerX = viewport.width / 2;
      const centerY = viewport.height / 2;
      const baseRadius = Math.min(viewport.width, viewport.height) * 0.24;
      const morphAmplitude = baseRadius * 0.08;
      const points = Array.from({ length: freqs.length }, (_, index) => {
        const angle = (index / freqs.length) * TAU - Math.PI / 2;
        const radius = baseRadius + morphAmplitude * Math.sin(phase * freqs[index] + phases[index]);
        return {
          x: centerX + Math.cos(angle) * radius,
          y: centerY + Math.sin(angle) * radius,
        };
      });

      const path = buildSmoothClosedPath(points);
      const gradient = ctx.createLinearGradient(
        centerX - baseRadius,
        centerY - baseRadius,
        centerX + baseRadius,
        centerY + baseRadius,
      );
      gradient.addColorStop(0, rgba(palette[0], 0.5));
      gradient.addColorStop(0.35, rgba(palette[1], 0.58));
      gradient.addColorStop(0.7, rgba(palette[2], 0.5));
      gradient.addColorStop(1, rgba(palette[0], 0.5));

      ctx.fillStyle = rgba(palette[3], 0.08);
      ctx.strokeStyle = gradient;
      ctx.lineWidth = 2.5;
      ctx.fill(path);
      ctx.stroke(path);
    },
  };
}
