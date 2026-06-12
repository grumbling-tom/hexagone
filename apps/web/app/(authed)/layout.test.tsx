import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";
import { beforeEach, expect, type Mock, test, vi } from "vitest";
import AuthedLayout from "./layout";

const { mockReplace } = vi.hoisted(() => ({ mockReplace: vi.fn() }));

vi.mock("next/navigation", () => ({
  useRouter: () => ({ replace: mockReplace }),
  usePathname: () => "/map",
}));

vi.mock("@/__generated__/backend-client/users", async (importOriginal) => {
  const actual =
    await importOriginal<
      typeof import("@/__generated__/backend-client/users")
    >();
  return { ...actual, useGetCurrentUser: vi.fn() };
});

import { useGetCurrentUser } from "@/__generated__/backend-client/users";

function renderLayout(children: ReactNode) {
  const queryClient = new QueryClient();
  return render(
    <QueryClientProvider client={queryClient}>
      <AuthedLayout>{children}</AuthedLayout>
    </QueryClientProvider>,
  );
}

beforeEach(() => {
  vi.clearAllMocks();
});

test("shows loading indicator while auth state is pending", () => {
  (useGetCurrentUser as Mock).mockReturnValue({
    data: undefined,
    isLoading: true,
  });

  renderLayout(<p>Protected content</p>);
  expect(screen.getByText("Loading")).toBeInTheDocument();
});

test("redirects to /login when not authenticated", async () => {
  (useGetCurrentUser as Mock).mockReturnValue({
    data: undefined,
    isLoading: false,
  });

  renderLayout(<p>Protected content</p>);
  await waitFor(() => expect(mockReplace).toHaveBeenCalledWith("/login"));
  expect(screen.queryByText("Protected content")).not.toBeInTheDocument();
});

test("renders nav and child route when authenticated", () => {
  (useGetCurrentUser as Mock).mockReturnValue({
    data: { id: "1", email: "test@example.com" },
    isLoading: false,
  });

  renderLayout(<p>Protected content</p>);
  expect(screen.getByText("Protected content")).toBeInTheDocument();
  expect(screen.getByRole("navigation")).toBeInTheDocument();
});
