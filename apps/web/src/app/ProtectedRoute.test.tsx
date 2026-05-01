import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { beforeEach, expect, type Mock, test, vi } from "vitest";
import ProtectedRoute from "./ProtectedRoute";

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

function renderWithRouter() {
  const queryClient = new QueryClient();
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={["/"]}>
        <Routes>
          <Route element={<ProtectedRoute />}>
            <Route path="/" element={<p>Protected content</p>} />
          </Route>
          <Route path="/login" element={<p>Login page</p>} />
        </Routes>
      </MemoryRouter>
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

  renderWithRouter();
  expect(screen.getByText("Loading")).toBeInTheDocument();
});

test("redirects to /login when not authenticated", () => {
  (useGetCurrentUser as Mock).mockReturnValue({
    data: undefined,
    isLoading: false,
  });

  renderWithRouter();
  expect(screen.getByText("Login page")).toBeInTheDocument();
});

test("renders nav and child route when authenticated", () => {
  (useGetCurrentUser as Mock).mockReturnValue({
    data: { id: "1", email: "test@example.com" },
    isLoading: false,
  });

  renderWithRouter();
  expect(screen.getByText("Protected content")).toBeInTheDocument();
  expect(screen.getByRole("navigation")).toBeInTheDocument();
});
