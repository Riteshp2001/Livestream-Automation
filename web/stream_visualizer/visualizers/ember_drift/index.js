export default function createEmberDriftVisualizer(runtime) {
  const { TAU, ctx, palette, rgba, scopedRng, tempo, viewport } = runtime;
  const rng = scopedRng("ember_drift");
  const embers = Array.from({ length: 34 }, (_, index) => ({
    x: 0.1 + rng() * 0.8,
    y: 0.68 + rng() * 0.28,
    speed: 0.014 + rng() * 0.028,
    radius: 1.2 + rng() * 3.2,
    wobble: 0.08 + rng() * 0.12,
    phase: rng() * TAU,
    alpha: 0.04 + rng() * 0.14,
    colorIndex: index % Math.min(3, palette.length),
  }));

  return {
    id: "ember_drift",
    draw(t, dt) {
      embers.forEach((ember) => {
        ember.y -= ember.speed * dt * tempo;
        if (ember.y < -0.08) {
          ember.y = 1.05;
          ember.x = 0.1 + rng() * 0.8;
        }
        const x = ember.x * viewport.width + Math.sin(t * ember.wobble * tempo + ember.phase) * 12;
        const y = ember.y * viewport.height;
        const gradient = ctx.createRadialGradient(x, y, 0, x, y, ember.radius * 8);
        gradient.addColorStop(0, rgba(palette[ember.colorIndex], ember.alpha));
        gradient.addColorStop(0.5, rgba(palette[(ember.colorIndex + 1) % palette.length], ember.alpha * 0.35));
        gradient.addColorStop(1, rgba(palette[ember.colorIndex], 0));
        ctx.fillStyle = gradient;
        ctx.beginPath();
        ctx.arc(x, y, ember.radius * 8, 0, TAU);
        ctx.fill();
      });
    },
  };
}
