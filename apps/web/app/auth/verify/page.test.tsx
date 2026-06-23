import { render, screen } from "@testing-library/react";
import type { ReactNode } from "react";
import { beforeEach, expect, type Mock, test, vi } from "vitest";
import { ApiError, HttpStatus } from "@/lib/fetch-client";

const { mockRedirect } = vi.hoisted(() => ({ mockRedirect: vi.fn() }));

vi.mock("next/navigation", () => ({
  redirect: (url: string) => {
    mockRedirect(url);
    throw new Error("NEXT_REDIRECT");
  },
}));

vi.mock("next/link", () => ({
  default: ({ children }: { children: ReactNode }) => (
    <a href="/login">{children}</a>
  ),
}));

vi.mock("@/__generated__/backend-client/users", () => ({
  getCurrentUser: vi.fn(),
}));

vi.mock("@/features/auth/server/verifyLogin", () => ({
  verifyLogin: vi.fn().mockResolvedValue({}),
}));

import { getCurrentUser } from "@/__generated__/backend-client/users";
import VerifyPage from "./page";

beforeEach(() => {
  vi.clearAllMocks();
});

test("redirects to /welcome when the visitor is already signed in", async () => {
  (getCurrentUser as Mock).mockResolvedValue({
    uid: "1",
    email: "a@example.com",
  });

  await expect(
    VerifyPage({ searchParams: Promise.resolve({ token: "a-token" }) }),
  ).rejects.toThrow("NEXT_REDIRECT");
  expect(mockRedirect).toHaveBeenCalledWith("/welcome");
});

test("renders the verifier when not signed in", async () => {
  (getCurrentUser as Mock).mockRejectedValue(
    new ApiError(HttpStatus.UNAUTHORIZED, undefined),
  );

  render(
    await VerifyPage({ searchParams: Promise.resolve({ token: "a-token" }) }),
  );

  expect(screen.getByText(/signing you in/i)).toBeInTheDocument();
  expect(mockRedirect).not.toHaveBeenCalled();
});
