import { beforeEach, expect, type Mock, test, vi } from "vitest";

const { mockRedirect } = vi.hoisted(() => ({ mockRedirect: vi.fn() }));

vi.mock("next/navigation", () => ({
  redirect: (url: string) => {
    mockRedirect(url);
    throw new Error("NEXT_REDIRECT");
  },
}));

vi.mock("@/__generated__/backend-client/user-sessions", () => ({
  createUserSession: vi.fn(),
}));

import { createUserSession } from "@/__generated__/backend-client/user-sessions";
import { verifyLogin } from "./verifyLogin";

function formData(token: string): FormData {
  const fd = new FormData();
  fd.set("token", token);
  return fd;
}

beforeEach(() => {
  vi.clearAllMocks();
});

test("consumes the token and redirects to /welcome on success", async () => {
  (createUserSession as Mock).mockResolvedValue({
    uid: "1",
    email: "user@example.com",
  });

  await expect(verifyLogin({}, formData("a-token"))).rejects.toThrow(
    "NEXT_REDIRECT",
  );

  expect(createUserSession).toHaveBeenCalledWith({ token: "a-token" });
  // /welcome is the onboarding gate (it bounces to /map for returning users).
  expect(mockRedirect).toHaveBeenCalledWith("/welcome");
});

test("returns an error and does not redirect on an invalid token", async () => {
  (createUserSession as Mock).mockRejectedValue(new Error("401"));

  const result = await verifyLogin({}, formData("a-token"));

  expect(result.error).toMatch(/invalid or has expired/i);
  expect(mockRedirect).not.toHaveBeenCalled();
});
