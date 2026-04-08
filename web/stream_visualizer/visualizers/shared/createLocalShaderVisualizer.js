export default function createLocalShaderVisualizer(id, shaderPath, options = {}) {
  const { filter = "none", removeOverlay = false } = options;

  return {
    id,
    type: "shader",
    src: `./shaders/local/${shaderPath}`,
    onLoad(frame) {
      const doc = frame.contentDocument;

      if (removeOverlay) {
        const overlay = doc?.querySelector("#ui, .label");
        if (overlay) {
          overlay.remove();
        }
      }

      if (doc) {
        let cursorOverride = doc.getElementById("stream-cursor-override");
        if (!cursorOverride) {
          cursorOverride = doc.createElement("style");
          cursorOverride.id = "stream-cursor-override";
          cursorOverride.textContent = `
            html,
            body,
            canvas,
            iframe,
            * {
              cursor: none !important;
            }
          `;
          doc.head?.appendChild(cursorOverride);
        }
      }

      frame.style.filter = filter;
      frame.style.cursor = "none";
    },
  };
}
