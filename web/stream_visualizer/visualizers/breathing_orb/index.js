export default function createBreathingOrbVisualizer(runtime) {
  const { TAU, clamp, ctx, palette, rgba, scopedRng, tempo, viewport } = runtime;
  const rng = scopedRng("breathing_orb");
  const phase = rng() * TAU;
  const wobbleFreq = 0.75 + rng() * 0.4;
  const wobbleAmp = 0.012 + rng() * 0.016;

  return {
    id: "breathing_orb",
    draw(t) {
      const cycle = t * (TAU / 14) * tempo;
      const centerX = viewport.width / 2;
      const centerY = viewport.height / 2;
      const base = Math.min(viewport.width, viewport.height);
      const minRadius = base * 0.15;
      const maxRadius = base * 0.31;
      const pulse = (Math.sin(cycle + phase) + 1) / 2;
      const wobble = wobbleAmp * base * Math.sin(cycle * wobbleFreq + phase * 1.3);
      const radius = clamp(minRadius + (maxRadius - minRadius) * pulse + wobble, minRadius * 0.8, maxRadius * 1.08);

      for (let ring = 2; ring >= 1; ring -= 1) {
        ctx.strokeStyle = rgba(palette[3], clamp(0.18 - ring * 0.05, 0.03, 0.12));
        ctx.lineWidth = 4.8 - ring * 1.2;
        ctx.beginPath();
        ctx.arc(centerX, centerY, radius + ring * 14, 0, TAU);
        ctx.stroke();
      }

      const gradient = ctx.createRadialGradient(centerX, centerY, 0, centerX, centerY, radius);
      gradient.addColorStop(0, rgba(palette[0], 0.88));
      gradient.addColorStop(0.55, rgba(palette[1], 0.56));
      gradient.addColorStop(1, rgba(palette[2], 0));
      ctx.fillStyle = gradient;
      ctx.beginPath();
      ctx.arc(centerX, centerY, radius, 0, TAU);
      ctx.fill();

      ctx.strokeStyle = rgba(palette[0], 0.48);
      ctx.lineWidth = 2;
      ctx.beginPath();
      ctx.arc(centerX, centerY, radius * 0.6, 0, TAU);
      ctx.stroke();
    },
  };
}
