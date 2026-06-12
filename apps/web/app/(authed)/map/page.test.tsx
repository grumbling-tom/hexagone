import { render, screen } from "@testing-library/react";
import type { ReactNode } from "react";
import { expect, test, vi } from "vitest";
import MapPage from "./page";

vi.mock("next/link", () => ({
  default: ({
    href,
    children,
    ...props
  }: {
    href: string;
    children: ReactNode;
    className?: string;
  }) => (
    <a href={href} {...props}>
      {children}
    </a>
  ),
}));

vi.mock("@/__generated__/backend-client/uploads", () => ({
  listUploads: vi.fn(() => Promise.resolve({ items: [] })),
}));

vi.mock("@/__generated__/backend-client/aggregated-hex-claims", () => ({
  listAggregatedHexClaims: vi.fn(),
}));

test("renders skeleton heading and CTA to uploads when there are no uploads", async () => {
  render(await MapPage());
  expect(
    screen.getByRole("heading", { name: "Your map will appear here" }),
  ).toBeInTheDocument();
  const cta = screen.getByRole("link", { name: "Add your first upload" });
  expect(cta).toHaveAttribute("href", "/uploads");
});
