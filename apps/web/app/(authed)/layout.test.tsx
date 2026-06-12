import { render, screen } from "@testing-library/react";
import { beforeEach, expect, type Mock, test, vi } from "vitest";
import { ApiError, HttpStatus } from "@/lib/fetch-client";
import AuthedLayout from "./layout";

const { mockRedirect } = vi.hoisted(() => ({ mockRedirect: vi.fn() }));

vi.mock("next/navigation", () => ({
  // redirect() throws a control-flow signal in Next — mirror that so the layout
  // stops at the redirect rather than falling through.
  redirect: (url: string) => {
    mockRedirect(url);
    throw new Error("NEXT_REDIRECT");
  },
  usePathname: () => "/map",
}));

vi.mock("@/__generated__/backend-client/users", () => ({
  getCurrentUser: vi.fn(),
}));

vi.mock("./actions", () => ({ logout: vi.fn() }));

import { getCurrentUser } from "@/__generated__/backend-client/users";

beforeEach(() => {
  vi.clearAllMocks();
});

test("renders nav and child route when authenticated", async () => {
  (getCurrentUser as Mock).mockResolvedValue({
    id: "1",
    email: "test@example.com",
  });

  render(await AuthedLayout({ children: <p>Protected content</p> }));

  expect(screen.getByText("Protected content")).toBeInTheDocument();
  expect(screen.getByRole("navigation")).toBeInTheDocument();
});

test("redirects to /login when the session is present but invalid", async () => {
  (getCurrentUser as Mock).mockRejectedValue(
    new ApiError(HttpStatus.UNAUTHORIZED, {}),
  );

  await expect(
    AuthedLayout({ children: <p>Protected content</p> }),
  ).rejects.toThrow();

  expect(mockRedirect).toHaveBeenCalledWith("/login");
});
