// vitest.config.ts
import { defineConfig, mergeConfig } from "vitest/config";
import viteConfig from "./vite.config";

export default defineConfig((configEnv) =>
  mergeConfig(
    viteConfig(configEnv), // resolve the function with Vitest's env
    defineConfig({
      test: {
        environment: "jsdom",
        globals: true,
        setupFiles: "./src/tests/setup.ts",
        css: false,
      },
    }),
  ),
);
