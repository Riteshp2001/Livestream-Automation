export default function createHorizonReflectionVisualizer(runtime) {
  const { TAU, ctx, palette, rgba, scopedRng, tempo, viewport } = runtime;
  const rng = scopedRng("horizon_reflection");
  const ripples = Array.from({ length: 7 }, (_, index) => ({
    offset: index * 18 + rng() * 8,
    speed: 0.055 + rng() * 0.05,
    amplitude: 3.2 + index * 1.6 + rng() * 1.4,
    waveCount: 1.1 + rng() * 0.5,
    phase: rng() * TAU,
  }));
  const diskX = 0.28 + rng() * 0.44;
  const diskSize = 0.045 + rng() * 0.03;

  return {
    id: "horizon_reflection",
    draw(t) {
      const horizonY = viewport.height * 0.58;
      const diskRadius = Math.min(viewport.width, viewport.height) * diskSize;
      const diskCx = viewport.width * diskX;
      const diskCy = horizonY - viewport.height * 0.14;

      const glow = ctx.createLinearGradient(0, horizonY - 60, 0, horizonY + 120);
      glow.addColorStop(0, rgba(palette[3], 0));
      glow.addColorStop(0.4, rgba(palette[2], 0.14));
      glow.addColorStop(1, rgba(palette[0], 0));
      ctx.fillStyle = glow;
      ctx.fillRect(0, horizonY - 60, viewport.width, 180);

      const diskGradient = ctx.createRadialGradient(diskCx, diskCy, 0, diskCx, diskCy, diskRadius);
      diskGradient.addColorStop(0, rgba(palette[3], 0.16));
      diskGradient.addColorStop(1, rgba(palette[3], 0));
      ctx.fillStyle = diskGradient;
      ctx.beginPath();
      ctx.arc(diskCx, diskCy, diskRadius, 0, TAU);
      ctx.fill();

      ctx.lineCap = "round";
      ripples.forEach((ripple, index) => {
        const y = horizonY + ripple.offset + Math.sin(t * ripple.speed * tempo + ripple.phase) * 4;
        ctx.beginPath();
        for (let step = 0; step <= 44; step += 1) {
          const x = (step / 44) * viewport.width;
          const wave = Math.sin((x / viewport.width) * TAU * ripple.waveCount + t * ripple.speed * tempo + ripple.phase) * ripple.amplitude;
          if (step === 0) ctx.moveTo(x, y + wave);
          else ctx.lineTo(x, y + wave);
        }
        ctx.strokeStyle = rgba(palette[index % palette.length], 0.1 - index * 0.008);
        ctx.lineWidth = 1.1 + index * 0.12;
        ctx.stroke();
      });
    },
  };
}
