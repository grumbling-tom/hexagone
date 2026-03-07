import { render, screen } from "@testing-library/react";
import { expect, test, vi } from "vitest";
import Dashboard from "./Dashboard";

vi.mock("@/__generated__/backend-client/health", () => ({
  useGetHealth: vi.fn(() => ({
    data: undefined,
    isLoading: true,
    isError: false,
  })),
}));

test("renders welcome message", () => {
  render(<Dashboard />);
  expect(screen.getByText("Welcome to Hexagone...")).toBeInTheDocument();
});
