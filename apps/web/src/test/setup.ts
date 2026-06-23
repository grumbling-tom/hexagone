import "@testing-library/jest-dom/vitest";
import { cleanup } from "@testing-library/react";
import { afterEach, vi } from "vitest";

// Unmount React trees between tests so the DOM doesn't accumulate across
// renders (otherwise queries can match elements from a previous test).
afterEach(() => {
  cleanup();
});

vi.stubGlobal(
  "fetch",
  vi.fn(() => Promise.reject(new Error("fetch not mocked"))),
);
