import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import { expect, test, vi } from "vitest";
import Dashboard from "./Dashboard";

vi.mock("@/__generated__/backend-client/uploads", () => ({
  useListUploads: vi.fn(() => ({
    data: undefined,
    isLoading: true,
    isError: false,
  })),
  useCreateUpload: vi.fn(() => ({
    mutate: vi.fn(),
    isPending: false,
  })),
}));

test("renders upload list section", () => {
  const queryClient = new QueryClient();
  render(
    <QueryClientProvider client={queryClient}>
      <Dashboard />
    </QueryClientProvider>,
  );
  expect(screen.getByRole("main")).toBeInTheDocument();
});
