"use client";

import type { MapViewState } from "@deck.gl/core";
import { H3HexagonLayer } from "@deck.gl/geo-layers";
import { DeckGL } from "@deck.gl/react";
import { Map as MapLibre } from "react-map-gl/maplibre";
import { useListAggregatedHexClaims } from "@/__generated__/backend-client/aggregated-hex-claims";
import {
  type AggregatedHexClaimByCell,
  AggregateHexClaimBy,
} from "@/__generated__/backend-client/backend.schemas";

// TODO: Compute me based on return values from the backend.
const INITIAL_VIEW_STATE: MapViewState = {
  longitude: -0.19,
  latitude: 51.47,
  zoom: 13,
};

export default function HexMap() {
  const { data, isPending, isError } = useListAggregatedHexClaims({
    page_size: 1000,
    by: AggregateHexClaimBy.hex_cell,
  });

  if (isPending) {
    return <div className="auth-loading">Loading</div>;
  }

  if (isError || !data) {
    // TODO: Consider adding error boundaries to the app.
    throw new Error("Failed to load hex claims");
  }

  if (data.items.length === 0) {
    return <div>No hex claims found</div>;
  }

  const layers = [
    new H3HexagonLayer<AggregatedHexClaimByCell>({
      id: "hex-claims",
      data: data.items,
      getHexagon: (d) => d.h3_cell,
      extruded: false,
    }),
  ];

  return (
    <div className="hex-map">
      <DeckGL initialViewState={INITIAL_VIEW_STATE} controller layers={layers}>
        <MapLibre mapStyle="https://basemaps.cartocdn.com/gl/positron-gl-style/style.json" />
      </DeckGL>
    </div>
  );
}
