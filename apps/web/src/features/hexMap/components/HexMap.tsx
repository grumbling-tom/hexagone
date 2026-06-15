"use client";

import type { MapViewState } from "@deck.gl/core";
import { H3HexagonLayer } from "@deck.gl/geo-layers";
import { DeckGL } from "@deck.gl/react";
import { Map as MapLibre } from "react-map-gl/maplibre";
import type { AggregatedHexClaimByCell } from "@/__generated__/backend-client/backend.schemas";

// TODO: Compute me based on return values from the backend.
const INITIAL_VIEW_STATE: MapViewState = {
  longitude: -0.19,
  latitude: 51.47,
  zoom: 13,
};

// Claims are fetched server-side by the route and passed in; this component is
// client-only because deck.gl/MapLibre need browser APIs.
export default function HexMap({
  claims,
}: {
  claims: AggregatedHexClaimByCell[];
}) {
  if (claims.length === 0) {
    return <div>No hex claims found</div>;
  }

  const layers = [
    new H3HexagonLayer<AggregatedHexClaimByCell>({
      id: "hex-claims",
      data: claims,
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
