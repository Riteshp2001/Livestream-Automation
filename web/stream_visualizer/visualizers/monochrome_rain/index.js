import createLocalShaderVisualizer from "../shared/createLocalShaderVisualizer.js";

export default function createMonochromeRainVisualizer() {
  return createLocalShaderVisualizer("monochrome_rain", "monochrome_rain/index.html");
}
