import "@testing-library/jest-dom/vitest";
import { cleanup } from "@testing-library/react";
import { afterEach, vi } from "vitest";

vi.stubGlobal(
  "fetch",
  vi.fn(() => Promise.reject(new Error("fetch not mocked"))),
);

// Vitest doesn't auto-detect testing-library cleanup the way Jest does, so
// the rendered DOM bleeds between tests in the same file. Force cleanup.
afterEach(() => {
  cleanup();
});
