import { render, screen } from "@testing-library/react";
import { expect, test } from "vitest";
import Dashboard from "./Dashboard";

test("renders welcome message", () => {
  render(<Dashboard />);
  expect(screen.getByText("Welcome to Hexagone...")).toBeInTheDocument();
});
