export default function createAuroraVisualizer(runtime) {
  const { TAU, ctx, palette, rgba, scopedRng, tempo, viewport } = runtime;
  const rng = scopedRng("aurora");
  const bands = Array.from({ length: 3 }, () => ({
    speed: 0.08 + rng() * 0.1,
    phase: rng() * TAU,
    centerRatio: 0.18 + rng() * 0.64,
    waveFreq: 0.7 + rng() * 0.45,
  }));

  return {
    id: "aurora",
    draw(t) {
      const cycle = t * (TAU / 38) * tempo;
      const bandWidth = viewport.width * 0.42;
      const previousMode = ctx.globalCompositeOperation;
      ctx.globalCompositeOperation = "screen";

      bands.forEach((band, index) => {
        const centerX = (band.centerRatio + 0.12 * Math.sin(cycle * band.speed + band.phase)) * viewport.width;
        const path = new Path2D();
        for (let step = 0; step <= 40; step += 1) {
          const progress = step / 40;
          const y = progress * viewport.height;
          const wave = Math.sin(progress * band.waveFreq * Math.PI + cycle * band.speed * 2 + band.phase) * 12;
          const left = centerX - bandWidth / 2 + wave;
          if (step === 0) {
            path.moveTo(left, y);
          } else {
            path.lineTo(left, y);
          }
        }
        for (let step = 40; step >= 0; step -= 1) {
          const progress = step / 40;
          const y = progress * viewport.height;
          const wave = Math.sin(progress * band.waveFreq * Math.PI + cycle * band.speed * 2 + band.phase) * 12;
          path.lineTo(centerX + bandWidth / 2 + wave, y);
        }
        path.closePath();

        const gradient = ctx.createLinearGradient(0, 0, 0, viewport.height);
        gradient.addColorStop(0, rgba(palette[index % palette.length], 0));
        gradient.addColorStop(0.25, rgba(palette[index % palette.length], 0.12));
        gradient.addColorStop(0.5, rgba(palette[(index + 1) % palette.length], 0.28));
        gradient.addColorStop(0.75, rgba(palette[index % palette.length], 0.12));
        gradient.addColorStop(1, rgba(palette[index % palette.length], 0));
        ctx.fillStyle = gradient;
        ctx.fill(path);
      });

      ctx.globalCompositeOperation = previousMode;
    },
  };
}
