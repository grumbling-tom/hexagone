import { beforeEach, expect, type Mock, test, vi } from "vitest";
import { ApiError, HttpStatus } from "@/lib/fetch-client";

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

test("returns a retry error when the email provider fails (502)", async () => {
  (createLoginToken as Mock).mockRejectedValue(
    new ApiError(HttpStatus.BAD_GATEWAY, undefined),
  );

  const result = await requestLink({}, formData("user@example.com"));

  expect(result.error).toMatch(/couldn't send/i);
});

test("returns a generic error on other failures", async () => {
  (createLoginToken as Mock).mockRejectedValue(new Error("network down"));

  const result = await requestLink({}, formData("user@example.com"));

  expect(result.error).toMatch(/something went wrong/i);
});
