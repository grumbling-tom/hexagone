// @vitest-environment node
// env.ts validates at *import* time and uses `typeof window` to decide
// server vs client access, so these run in the node environment (no `window`)
// and reset modules to re-trigger validation per case.
import { expect, test, vi } from "vitest";

async function loadEnv() {
  vi.resetModules();
  return (await import("@/config/env")).env;
}

test("BACKEND_ORIGIN defaults to the local backend when unset", async () => {
  vi.stubEnv("BACKEND_ORIGIN", "");
  const env = await loadEnv();
  expect(env.BACKEND_ORIGIN).toBe("http://localhost:8000");
});

test("BACKEND_ORIGIN takes an explicit origin", async () => {
  vi.stubEnv("BACKEND_ORIGIN", "http://hexagone-backend:8000");
  const env = await loadEnv();
  expect(env.BACKEND_ORIGIN).toBe("http://hexagone-backend:8000");
});

test("a non-URL BACKEND_ORIGIN fails validation at import", async () => {
  vi.stubEnv("BACKEND_ORIGIN", "not-a-url");
  vi.resetModules();
  vi.spyOn(console, "error").mockImplementation(() => {});
  await expect(import("@/config/env")).rejects.toThrow(
    "Invalid environment variables",
  );
});
