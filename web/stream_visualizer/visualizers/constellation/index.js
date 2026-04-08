export default function createConstellationVisualizer(runtime) {
  const { TAU, ctx, palette, rgba, scopedRng, tempo, viewport } = runtime;
  const rng = scopedRng("constellation");
  const stars = Array.from({ length: 45 }, () => {
    const angle = rng() * TAU;
    const speed = 0.0025 + rng() * 0.005;
    return {
      x: rng(),
      y: rng(),
      vx: Math.cos(angle) * speed,
      vy: Math.sin(angle) * speed,
      radius: 1.4 + rng() * 1.8,
    };
  });

  return {
    id: "constellation",
    draw(_, dt) {
      const threshold = Math.min(viewport.width, viewport.height) * 0.19;
      const thresholdSq = threshold * threshold;

      stars.forEach((star) => {
        star.x = (star.x + star.vx * dt * tempo + 1) % 1;
        star.y = (star.y + star.vy * dt * tempo + 1) % 1;
      });

      ctx.lineWidth = 1;
      for (let i = 0; i < stars.length; i += 1) {
        for (let j = i + 1; j < stars.length; j += 1) {
          const ax = stars[i].x * viewport.width;
          const ay = stars[i].y * viewport.height;
          const bx = stars[j].x * viewport.width;
          const by = stars[j].y * viewport.height;
          const dx = ax - bx;
          const dy = ay - by;
          const distSq = dx * dx + dy * dy;
          if (distSq < thresholdSq) {
            const alpha = (1 - Math.sqrt(distSq) / threshold) * 0.34;
            ctx.strokeStyle = rgba(palette[1], alpha);
            ctx.beginPath();
            ctx.moveTo(ax, ay);
            ctx.lineTo(bx, by);
            ctx.stroke();
          }
        }
      }

      stars.forEach((star, index) => {
        ctx.fillStyle = rgba(palette[index % palette.length], 0.72);
        ctx.beginPath();
        ctx.arc(star.x * viewport.width, star.y * viewport.height, star.radius, 0, TAU);
        ctx.fill();
      });
    },
  };
}
