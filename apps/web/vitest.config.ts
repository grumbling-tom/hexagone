/// <reference types="vitest" />
import { getViteConfig } from "astro/config";

export default getViteConfig({
  // @ts-expect-error - 'test' does not exist in type 'UserConfig'
  // https://github.com/withastro/astro/issues/12053 🤷
  test: {
    include: ["src/**/*.test.{ts,tsx}"],
    environment: "happy-dom",
    setupFiles: ["src/test/setup.ts"],
    coverage: {
      provider: "v8",
      include: ["src/**/*.{ts,tsx}"],
      exclude: ["src/**/*.test.{ts,tsx}", "src/test/**", "src/env.d.ts"],
    },
  },
});
