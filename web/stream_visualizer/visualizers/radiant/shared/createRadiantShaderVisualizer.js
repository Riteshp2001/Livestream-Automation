const schemeFilters = {
  amber: "none",
  mono: "grayscale(1)",
  blue: "hue-rotate(175deg)",
  rose: "hue-rotate(300deg) saturate(1.1)",
  emerald: "hue-rotate(90deg) saturate(1.2)",
  arctic: "hue-rotate(180deg) saturate(0.5) brightness(1.1)",
};

export default function createRadiantShaderVisualizer(runtime, shader) {
  return {
    id: shader.id,
    type: "shader",
    src: `./shaders/radiant/${shader.path}`,
    onLoad(frame) {
      const doc = frame.contentDocument;
      const label = doc?.querySelector(".label");
      if (label) {
        label.remove();
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

      frame.style.filter = schemeFilters[shader.scheme] || "none";
      frame.style.cursor = "none";
    },
  };
}
