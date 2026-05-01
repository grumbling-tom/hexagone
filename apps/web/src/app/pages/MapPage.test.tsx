import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { expect, test } from "vitest";
import MapPage from "./MapPage";

test("renders skeleton heading and CTA to uploads", () => {
  render(
    <MemoryRouter>
      <MapPage />
    </MemoryRouter>,
  );
  expect(
    screen.getByRole("heading", { name: "Your map will appear here" }),
  ).toBeInTheDocument();
  const cta = screen.getByRole("link", { name: "Add your first upload" });
  expect(cta).toHaveAttribute("href", "/uploads");
});
