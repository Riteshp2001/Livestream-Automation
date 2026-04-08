export default function createParticleEqualizerVisualizer(runtime) {
  const { TAU, ctx, palette, rgba, scopedRng, tempo, viewport } = runtime;
  const rng = scopedRng("particle_equalizer");
  const columns = Array.from({ length: 18 }, (_, index) => ({
    x: 0.08 + (index / 17) * 0.84,
    phase: rng() * TAU,
    speed: 0.16 + rng() * 0.12,
    height: 0.18 + rng() * 0.22,
    radius: 1.4 + rng() * 1.8,
    density: 10 + Math.floor(rng() * 8),
    colorIndex: index % palette.length,
  }));

  return {
    id: "particle_equalizer",
    draw(t) {
      const centerY = viewport.height * 0.55;
      columns.forEach((column) => {
        const travel = (0.45 + 0.12 * Math.sin(t * column.speed * tempo + column.phase)) * column.height * viewport.height;
        for (let i = 0; i < column.density; i += 1) {
          const progress = i / Math.max(1, column.density - 1);
          const distance = progress * travel;
          const topY = centerY - distance;
          const bottomY = centerY + distance;
          const alpha = (1 - progress) * 0.22;
          const xJitter = Math.sin(t * 0.08 * tempo + column.phase + i * 0.16) * 4;
          ctx.fillStyle = rgba(palette[column.colorIndex], alpha);
          ctx.beginPath();
          ctx.arc(column.x * viewport.width + xJitter, topY, column.radius, 0, TAU);
          ctx.fill();
          ctx.beginPath();
          ctx.arc(column.x * viewport.width + xJitter, bottomY, column.radius, 0, TAU);
          ctx.fill();
        }
      });
    },
  };
}
