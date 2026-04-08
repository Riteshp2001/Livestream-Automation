function drawPetalRing(ctx, rgba, TAU, centerX, centerY, petalCount, innerRadius, outerRadius, rotation, color, alpha) {
  ctx.fillStyle = rgba(color, alpha);
  const angleStep = TAU / petalCount;

  for (let i = 0; i < petalCount; i += 1) {
    const angle = i * angleStep + rotation;
    const tipX = centerX + Math.cos(angle) * outerRadius;
    const tipY = centerY + Math.sin(angle) * outerRadius;
    const leftAngle = angle - angleStep * 0.35;
    const rightAngle = angle + angleStep * 0.35;
    const cp1X = centerX + Math.cos(leftAngle) * innerRadius * 1.2;
    const cp1Y = centerY + Math.sin(leftAngle) * innerRadius * 1.2;
    const cp2X = centerX + Math.cos(rightAngle) * innerRadius * 1.2;
    const cp2Y = centerY + Math.sin(rightAngle) * innerRadius * 1.2;
    const baseLeftX = centerX + Math.cos(leftAngle) * innerRadius * 0.5;
    const baseLeftY = centerY + Math.sin(leftAngle) * innerRadius * 0.5;
    const baseRightX = centerX + Math.cos(rightAngle) * innerRadius * 0.5;
    const baseRightY = centerY + Math.sin(rightAngle) * innerRadius * 0.5;

    ctx.beginPath();
    ctx.moveTo(baseLeftX, baseLeftY);
    ctx.quadraticCurveTo(cp1X, cp1Y, tipX, tipY);
    ctx.quadraticCurveTo(cp2X, cp2Y, baseRightX, baseRightY);
    ctx.closePath();
    ctx.fill();
  }
}

export default function createRotatingMandalaVisualizer(runtime) {
  const { TAU, ctx, palette, rgba, scopedRng, tempo, viewport } = runtime;
  const rng = scopedRng("rotating_mandala");
  const ringPhases = Array.from({ length: 3 }, () => rng() * TAU);
  const petalCounts = [5 + Math.floor(rng() * 2), 7 + Math.floor(rng() * 2), 10 + Math.floor(rng() * 3)];

  return {
    id: "rotating_mandala",
    draw(t) {
      const phase = t * (TAU / 34) * tempo;
      const centerX = viewport.width / 2;
      const centerY = viewport.height / 2;
      const base = Math.min(viewport.width, viewport.height) * 0.32;

      drawPetalRing(ctx, rgba, TAU, centerX, centerY, petalCounts[0], base * 0.15, base * 0.42, phase * 0.55 + ringPhases[0], palette[0], 0.34);
      drawPetalRing(ctx, rgba, TAU, centerX, centerY, petalCounts[1], base * 0.28, base * 0.68, -phase * 0.34 + ringPhases[1], palette[1], 0.26);
      drawPetalRing(ctx, rgba, TAU, centerX, centerY, petalCounts[2], base * 0.46, base * 0.88, phase * 0.22 + ringPhases[2], palette[2], 0.18);

      ctx.fillStyle = rgba(palette[3], 0.55);
      ctx.beginPath();
      ctx.arc(centerX, centerY, base * 0.1, 0, TAU);
      ctx.fill();

      ctx.fillStyle = rgba(palette[0], 0.8);
      ctx.beginPath();
      ctx.arc(centerX, centerY, base * 0.04, 0, TAU);
      ctx.fill();
    },
  };
}
