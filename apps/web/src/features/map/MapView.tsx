import "maplibre-gl/dist/maplibre-gl.css";

import { H3HexagonLayer } from "@deck.gl/geo-layers";
import { MapboxOverlay } from "@deck.gl/mapbox";
import { cellToLatLng } from "h3-js";
import maplibregl from "maplibre-gl";
import { useEffect, useRef } from "react";

import type { AggregatedHexClaimByCell } from "@/__generated__/backend-client/backend.schemas";
import { MAP_HEX_FILL, MAP_HEX_STROKE, MAP_STYLE_URL } from "@/lib/map-config";

type MapViewProps = {
  claims: AggregatedHexClaimByCell[];
};

function fitBoundsTo(
  map: maplibregl.Map,
  claims: AggregatedHexClaimByCell[],
): void {
  if (claims.length === 0) return;

  const bounds = new maplibregl.LngLatBounds();
  for (const claim of claims) {
    const [lat, lng] = cellToLatLng(claim.h3_cell);
    bounds.extend([lng, lat]);
  }
  map.fitBounds(bounds, { padding: 64, animate: false, maxZoom: 13 });
}

export default function MapView({ claims }: MapViewProps) {
  const containerRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    if (!containerRef.current) return;

    const map = new maplibregl.Map({
      container: containerRef.current,
      style: MAP_STYLE_URL,
      center: [0, 0],
      zoom: 1,
    });

    map.addControl(new maplibregl.NavigationControl(), "top-right");

    // The overlay must be added inside ``load`` because ``interleaved: true``
    // inserts deck.gl layers into MapLibre's style spec — that requires the
    // style to already be loaded. ``interleaved: true`` also avoids the
    // separate-canvas height bug we hit with ``interleaved: false`` where
    // deck.gl's overlay container ends up at ``height: 0``.
    map.on("load", () => {
      const overlay = new MapboxOverlay({
        interleaved: true,
        layers: [
          new H3HexagonLayer<AggregatedHexClaimByCell>({
            id: "hex-claims",
            data: claims,
            getHexagon: (c) => c.h3_cell,
            getFillColor: MAP_HEX_FILL,
            getLineColor: MAP_HEX_STROKE,
            lineWidthMinPixels: 1,
            stroked: true,
            filled: true,
            extruded: false,
            pickable: true,
            // Force per-hex boundary computation. The default optimisation
            // picks a "center hexagon" and reuses its shape (translated)
            // for every other hex, which trips ``code: 3`` from h3-js for
            // sparse / single-cell / wide-extent data. Perf cost is
            // negligible at our scale (≤1 000 cells).
            highPrecision: true,
          }),
        ],
      });
      map.addControl(overlay as unknown as maplibregl.IControl);
      fitBoundsTo(map, claims);
    });

    // MapLibre measures the container once at construction time. If the
    // container's dimensions resolve after the React effect runs (common
    // with Astro hydration / late layout), the canvas stays at whatever
    // size was visible at init. Watch the container and call ``resize()``
    // whenever it changes so the canvas tracks the layout.
    const resizeObserver = new ResizeObserver(() => {
      map.resize();
    });
    resizeObserver.observe(containerRef.current);

    return () => {
      resizeObserver.disconnect();
      map.remove();
    };
  }, [claims]);

  return (
    <section className="map-view" aria-label="Your hex map">
      <div ref={containerRef} className="map-view__canvas" />
    </section>
  );
}
