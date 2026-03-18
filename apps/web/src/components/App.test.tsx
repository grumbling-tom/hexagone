import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, expect, type Mock, test, vi } from "vitest";
import { AppRoutes } from "./App";

vi.mock("@/lib/auth", () => ({
  useAuthContext: vi.fn(),
}));

vi.mock("@clerk/clerk-react", () => ({
  RedirectToSignIn: () => <p>Sign in redirect</p>,
  SignIn: () => <p>Clerk Sign In</p>,
}));

vi.mock("@/__generated__/backend-client/health", () => ({
  useGetHealth: vi.fn(() => ({
    data: undefined,
    isLoading: true,
    isError: false,
  })),
}));

import { useAuthContext } from "@/lib/auth";

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

test("redirects unauthenticated users to sign-in", () => {
  (useAuthContext as Mock).mockReturnValue({
    isSignedIn: false,
    isLoaded: true,
  });

  renderWithProviders("/");
  expect(screen.getByText("Sign in redirect")).toBeInTheDocument();
});

test("renders dashboard for authenticated users", () => {
  (useAuthContext as Mock).mockReturnValue({
    isSignedIn: true,
    isLoaded: true,
    signOut: vi.fn(),
  });

  renderWithProviders("/");
  expect(screen.getByRole("navigation")).toBeInTheDocument();
  expect(screen.getByRole("main")).toBeInTheDocument();
});

test("renders settings for authenticated users", () => {
  (useAuthContext as Mock).mockReturnValue({
    isSignedIn: true,
    isLoaded: true,
    signOut: vi.fn(),
  });

  renderWithProviders("/settings");
  expect(screen.getByRole("heading", { name: "Settings" })).toBeInTheDocument();
});
