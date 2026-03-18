import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { beforeEach, expect, type Mock, test, vi } from "vitest";
import ProtectedRoute from "./ProtectedRoute";

vi.mock("@/lib/auth", () => ({
  useAuthContext: vi.fn(),
}));

import { useAuthContext } from "@/lib/auth";

function renderWithRouter() {
  const queryClient = new QueryClient();
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={["/"]}>
        <Routes>
          <Route element={<ProtectedRoute />}>
            <Route path="/" element={<p>Protected content</p>} />
          </Route>
          <Route path="/login" element={<p>Sign in page</p>} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

beforeEach(() => {
  vi.clearAllMocks();
});

test("shows loading indicator while auth state is pending", () => {
  (useAuthContext as Mock).mockReturnValue({
    isSignedIn: false,
    isLoaded: false,
  });

  renderWithRouter();
  expect(screen.getByText("Loading")).toBeInTheDocument();
});

test("redirects to sign-in when not authenticated", () => {
  (useAuthContext as Mock).mockReturnValue({
    isSignedIn: false,
    isLoaded: true,
  });

  renderWithRouter();
  expect(screen.getByText("Sign in page")).toBeInTheDocument();
});

test("renders nav and child route when authenticated", () => {
  (useAuthContext as Mock).mockReturnValue({
    isSignedIn: true,
    isLoaded: true,
    signOut: vi.fn(),
  });

  renderWithRouter();
  expect(screen.getByText("Protected content")).toBeInTheDocument();
  expect(screen.getByRole("navigation")).toBeInTheDocument();
});
