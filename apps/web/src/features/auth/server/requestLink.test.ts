import { beforeEach, expect, type Mock, test, vi } from "vitest";

vi.mock("@/__generated__/backend-client/login-tokens", () => ({
  createLoginToken: vi.fn(),
}));

import { createLoginToken } from "@/__generated__/backend-client/login-tokens";
import { requestLink } from "./requestLink";

function formData(email: string): FormData {
  const fd = new FormData();
  fd.set("email", email);
  return fd;
}

beforeEach(() => {
  vi.clearAllMocks();
});

test("returns the sent state on success", async () => {
  (createLoginToken as Mock).mockResolvedValue(undefined);

  const result = await requestLink({}, formData("user@example.com"));

  expect(result).toEqual({ sent: true });
  expect(createLoginToken).toHaveBeenCalledWith({ email: "user@example.com" });
});

test("returns a retry error on any failure", async () => {
  (createLoginToken as Mock).mockRejectedValue(new Error("network down"));

  const result = await requestLink({}, formData("user@example.com"));

  expect(result.error).toMatch(/couldn't send/i);
});
