import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, expect, type Mock, test, vi } from "vitest";
import { AppRoutes } from "./App";

vi.mock("@/__generated__/backend-client/users", async (importOriginal) => {
  const actual =
    await importOriginal<
      typeof import("@/__generated__/backend-client/users")
    >();
  return {
    ...actual,
    useGetCurrentUser: vi.fn(),
  };
});

import { useGetCurrentUser } from "@/__generated__/backend-client/users";

function renderWithProviders(route: string) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={[route]}>
        <AppRoutes />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

beforeEach(() => {
  vi.clearAllMocks();
});

test("redirects unauthenticated users to login", () => {
  (useGetCurrentUser as Mock).mockReturnValue({
    data: undefined,
    isLoading: false,
  });

  renderWithProviders("/");
  expect(screen.getByRole("heading", { name: "Log in" })).toBeInTheDocument();
});

test("renders dashboard for authenticated users", () => {
  (useGetCurrentUser as Mock).mockReturnValue({
    data: { id: "1", email: "test@example.com" },
    isLoading: false,
  });

  renderWithProviders("/");
  expect(
    screen.getByRole("heading", { name: "Dashboard" }),
  ).toBeInTheDocument();
});

test("renders settings for authenticated users", () => {
  (useGetCurrentUser as Mock).mockReturnValue({
    data: { id: "1", email: "test@example.com" },
    isLoading: false,
  });

  renderWithProviders("/settings");
  expect(screen.getByRole("heading", { name: "Settings" })).toBeInTheDocument();
});
