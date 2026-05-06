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

vi.mock("@/__generated__/backend-client/uploads", () => ({
  useListUploads: vi.fn(() => ({
    data: undefined,
    isLoading: true,
    isError: false,
  })),
  useCreateUpload: vi.fn(() => ({
    mutateAsync: vi.fn(),
    isPending: false,
  })),
}));

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

test("renders map page for authenticated users", () => {
  (useGetCurrentUser as Mock).mockReturnValue({
    data: { id: "1", email: "test@example.com" },
    isLoading: false,
  });

  renderWithProviders("/");
  expect(
    screen.getByRole("heading", { name: "Your map will appear here" }),
  ).toBeInTheDocument();
});

test("renders uploads page for authenticated users", () => {
  (useGetCurrentUser as Mock).mockReturnValue({
    data: { id: "1", email: "test@example.com" },
    isLoading: false,
  });

  renderWithProviders("/uploads");
  expect(
    screen.getByRole("heading", { name: "Upload a GPX file" }),
  ).toBeInTheDocument();
});
