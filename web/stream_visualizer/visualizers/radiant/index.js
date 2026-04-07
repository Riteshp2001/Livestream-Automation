import { radiantShaderCatalog } from "./catalog.js";
import createRadiantShaderVisualizer from "./shared/createRadiantShaderVisualizer.js";

export function createRadiantVisualizers(runtime) {
  return Object.fromEntries(
    radiantShaderCatalog.map((shader) => [shader.id, createRadiantShaderVisualizer(runtime, shader)]),
  );
}
