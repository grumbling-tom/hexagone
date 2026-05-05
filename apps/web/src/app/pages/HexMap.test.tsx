import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, expect, type Mock, test, vi } from "vitest";

vi.mock("@/__generated__/backend-client/aggregated-hex-claims", () => ({
  useListAggregatedHexClaims: vi.fn(),
}));

vi.mock("@/features/map/MapView", () => ({
  default: ({ claims }: { claims: ReadonlyArray<{ h3_cell: string }> }) => (
    <div data-testid="map-view-stub">{`live map (${claims.length} cells)`}</div>
  ),
}));

import { useListAggregatedHexClaims } from "@/__generated__/backend-client/aggregated-hex-claims";
import HexMap from "./HexMap";

function renderHexMap() {
  return render(
    <MemoryRouter>
      <HexMap />
    </MemoryRouter>,
  );
}

beforeEach(() => {
  vi.clearAllMocks();
});

test("renders skeleton while loading", () => {
  (useListAggregatedHexClaims as Mock).mockReturnValue({
    data: undefined,
    isLoading: true,
    isError: false,
  });

  renderHexMap();
  expect(
    screen.getByRole("heading", { name: "Your map will appear here" }),
  ).toBeInTheDocument();
});

test("renders error message on fetch failure", () => {
  (useListAggregatedHexClaims as Mock).mockReturnValue({
    data: undefined,
    isLoading: false,
    isError: true,
  });

  renderHexMap();
  expect(screen.getByText(/couldn't load your hexes/i)).toBeInTheDocument();
});

test("renders skeleton + CTA when the user has no hexes", () => {
  (useListAggregatedHexClaims as Mock).mockReturnValue({
    data: { items: [], has_next: false, has_previous: false },
    isLoading: false,
    isError: false,
  });

  renderHexMap();
  expect(
    screen.getByRole("heading", { name: "Your map will appear here" }),
  ).toBeInTheDocument();
  const cta = screen.getByRole("link", { name: "Add your first upload" });
  expect(cta).toHaveAttribute("href", "/uploads");
});

test("renders the live MapView when the user has hexes", () => {
  (useListAggregatedHexClaims as Mock).mockReturnValue({
    data: {
      items: [
        {
          h3_cell: "8c1f1d2806467ff",
          claim_count: 1,
          upload_count: 1,
          first_claimed_at: "2026-05-01T00:00:00Z",
          last_claimed_at: "2026-05-01T00:00:00Z",
        },
      ],
      has_next: false,
      has_previous: false,
    },
    isLoading: false,
    isError: false,
  });

  renderHexMap();
  expect(screen.getByTestId("map-view-stub")).toHaveTextContent(
    "live map (1 cells)",
  );
});
