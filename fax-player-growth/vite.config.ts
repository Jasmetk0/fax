import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig(({ mode }) => {
  const isEmbed = mode === "embed";

  return {
    plugins: [react()],
    build: isEmbed
      ? {
          emptyOutDir: false,
          lib: {
            entry: "src/embed.ts",
            name: "SquashEngine",
            formats: ["iife"],
            fileName: () => "squash-engine",
          },
          rollupOptions: {
            output: {
              entryFileNames: "squash-engine.iife.js",
              assetFileNames: (assetInfo) =>
                assetInfo.name?.endsWith(".css")
                  ? "squash-engine-player-growth.css"
                  : "assets/[name]-[hash][extname]",
            },
          },
        }
      : {
          rollupOptions: {},
        },
    test: {
      environment: "jsdom",
      globals: true,
      setupFiles: ["./tests/setup.ts"],
    },
  };
});
