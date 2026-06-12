/// <reference types="vitest" />
import { fileURLToPath } from "node:url";
import react from "@vitejs/plugin-react";
import { defineConfig } from "vitest/config";

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      // Mirror the tsconfig "@/*" -> "./src/*" alias for tests.
      "@": fileURLToPath(new URL("./src", import.meta.url)),
      // Neutralise the `server-only` guard so server modules can be imported
      // (and mocked) under the happy-dom test environment.
      "server-only": fileURLToPath(
        new URL("./src/test/server-only-stub.ts", import.meta.url),
      ),
    },
  },
  test: {
    // App Router route files (and their co-located tests) live at apps/web/app/;
    // features/lib live under src/; middleware.ts sits at the project root.
    include: [
      "src/**/*.test.{ts,tsx}",
      "app/**/*.test.{ts,tsx}",
      "middleware.test.ts",
    ],
    environment: "happy-dom",
    setupFiles: ["src/test/setup.ts"],
    coverage: {
      provider: "v8",
      include: ["src/**/*.{ts,tsx}", "app/**/*.{ts,tsx}"],
      exclude: ["**/*.test.{ts,tsx}", "src/test/**"],
    },
  },
});
