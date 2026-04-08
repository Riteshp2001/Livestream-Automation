export default function createParticleDriftVisualizer(runtime) {
  const { TAU, ctx, palette, rgba, scopedRng, tempo, viewport } = runtime;
  const rng = scopedRng("particle_drift");
  const particles = Array.from({ length: 60 }, (_, index) => ({
    x: rng(),
    y: rng(),
    speed: 0.012 + rng() * 0.022,
    radius: 1.8 + rng() * 2.4,
    colorIndex: index % palette.length,
    driftPhase: rng() * TAU,
  }));

  return {
    id: "particle_drift",
    draw(t, dt) {
      particles.forEach((particle) => {
        particle.y -= particle.speed * dt * tempo;
        particle.x += Math.sin(t * 0.1 + particle.driftPhase) * 0.00035;
        if (particle.y < -0.03) {
          particle.y = 1.03;
          particle.x = rng();
        }
        if (particle.x < -0.05) particle.x += 1.1;
        if (particle.x > 1.05) particle.x -= 1.1;

        ctx.fillStyle = rgba(palette[particle.colorIndex], 0.42);
        ctx.beginPath();
        ctx.arc(particle.x * viewport.width, particle.y * viewport.height, particle.radius, 0, TAU);
        ctx.fill();
      });
    },
  };
}
