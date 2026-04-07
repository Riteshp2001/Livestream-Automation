export default function createLocalShaderVisualizer(id, shaderPath, options = {}) {
  const { filter = "none", removeOverlay = false } = options;

  return {
    id,
    type: "shader",
    src: `./shaders/local/${shaderPath}`,
    onLoad(frame) {
      if (removeOverlay) {
        const overlay = frame.contentDocument?.querySelector("#ui, .label");
        if (overlay) {
          overlay.remove();
        }
      }

      frame.style.filter = filter;
    },
  };
}
