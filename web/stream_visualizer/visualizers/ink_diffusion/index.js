export default function createInkDiffusionVisualizer(runtime) {
  const { TAU, ctx, palette, rgba, scopedRng, tempo, viewport } = runtime;
  const rng = scopedRng("ink_diffusion");
  const blobs = Array.from({ length: 4 }, (_, index) => ({
    x: rng(),
    y: rng(),
    age: index / 4,
    colorIndex: index % palette.length,
  }));

  return {
    id: "ink_diffusion",
    draw(_, dt) {
      const maxRadius = Math.min(viewport.width, viewport.height) * 0.34;
      blobs.forEach((blob) => {
        blob.age += 0.065 * dt * tempo;
        if (blob.age >= 1) {
          blob.age = 0;
          blob.x = rng();
          blob.y = rng();
        }

        const radius = maxRadius * blob.age;
        const alpha = Math.sin(Math.PI * blob.age);
        const centerX = blob.x * viewport.width;
        const centerY = blob.y * viewport.height;
        const gradient = ctx.createRadialGradient(centerX, centerY, 0, centerX, centerY, radius);
        gradient.addColorStop(0, rgba(palette[blob.colorIndex], alpha * 0.46));
        gradient.addColorStop(0.5, rgba(palette[(blob.colorIndex + 1) % palette.length], alpha * 0.12));
        gradient.addColorStop(1, rgba(palette[blob.colorIndex], 0));
        ctx.fillStyle = gradient;
        ctx.beginPath();
        ctx.arc(centerX, centerY, radius, 0, TAU);
        ctx.fill();
      });
    },
  };
}
