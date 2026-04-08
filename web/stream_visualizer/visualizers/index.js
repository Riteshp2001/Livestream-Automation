import createAuroraVisualizer from "./aurora/index.js";
import createBreathingOrbVisualizer from "./breathing_orb/index.js";
import createConstellationVisualizer from "./constellation/index.js";
import createEmberDriftVisualizer from "./ember_drift/index.js";
import createHorizonReflectionVisualizer from "./horizon_reflection/index.js";
import createInkDiffusionVisualizer from "./ink_diffusion/index.js";
import createLiquidRibbonsVisualizer from "./liquid_ribbons/index.js";
import createMistLayersVisualizer from "./mist_layers/index.js";
import createMonochromeRainVisualizer from "./monochrome_rain/index.js";
import createMorphingPolygonVisualizer from "./morphing_polygon/index.js";
import createParticleDriftVisualizer from "./particle_drift/index.js";
import createParticleEqualizerVisualizer from "./particle_equalizer/index.js";
import createRadialRingsVisualizer from "./radial_rings/index.js";
import { createRadiantVisualizers } from "./radiant/index.js";
import createRotatingMandalaVisualizer from "./rotating_mandala/index.js";
import createVeilLinesVisualizer from "./veil_lines/index.js";

export function createVisualizers(runtime) {
  return {
    liquid_ribbons: createLiquidRibbonsVisualizer(runtime),
    breathing_orb: createBreathingOrbVisualizer(runtime),
    radial_rings: createRadialRingsVisualizer(runtime),
    particle_drift: createParticleDriftVisualizer(runtime),
    rotating_mandala: createRotatingMandalaVisualizer(runtime),
    constellation: createConstellationVisualizer(runtime),
    morphing_polygon: createMorphingPolygonVisualizer(runtime),
    aurora: createAuroraVisualizer(runtime),
    ink_diffusion: createInkDiffusionVisualizer(runtime),
    monochrome_rain: createMonochromeRainVisualizer(runtime),
    mist_layers: createMistLayersVisualizer(runtime),
    veil_lines: createVeilLinesVisualizer(runtime),
    horizon_reflection: createHorizonReflectionVisualizer(runtime),
    ember_drift: createEmberDriftVisualizer(runtime),
    particle_equalizer: createParticleEqualizerVisualizer(runtime),
    ...createRadiantVisualizers(runtime),
  };
}
