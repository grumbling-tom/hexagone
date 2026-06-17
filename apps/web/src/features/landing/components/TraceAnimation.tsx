import type { CSSProperties } from "react";
import { buildTraceModel } from "@/features/landing/geometry";

// The landing hero's trace visual: the Stanley Park basemap, a faint hex grid,
// the running route drawn over the seawall, and the hexes the route passes
// shown claimed. Pure server-rendered SVG — the animation is layered on in CSS
// (the .hex-anim block in main.css), so there's no client component.
//
// The map tile is CARTO Positron (the same basemap the app's HexMap uses);
// "© OpenStreetMap contributors © CARTO" is shown as required by the tile
// usage policy.
export default function TraceAnimation() {
  const model = buildTraceModel();

  return (
    <svg
      className="hex-anim__svg"
      viewBox={`0 0 ${model.width} ${model.height}`}
      preserveAspectRatio="xMidYMid slice"
      role="img"
      aria-label="A running route traced over Stanley Park, with the hexes it passes claimed"
    >
      <image
        className="hex-anim__map"
        href="/map.png"
        x={0}
        y={0}
        width={model.width}
        height={model.height}
      />

      {model.gridHexes.map((points) => (
        <polygon key={points} className="hex-anim__hex" points={points} />
      ))}

      {model.routeHexes.map((cell) => (
        // --d carries this hex's geometry-derived pop delay (its position along
        // the route) into the CSS cascade. The style attribute is the only
        // inline style here, and it's deliberate: it carries a data value, not
        // visual rules — all real styling (the hex-pop keyframes and what --d
        // drives) lives in main.css. Setting it imperatively from TraceLoop
        // instead would mean querying every cell from the client, which is
        // strictly worse than letting the server emit it.
        <polygon
          key={cell.points}
          className="hex-anim__cell"
          points={cell.points}
          style={{ "--d": `${cell.delay.toFixed(2)}s` } as CSSProperties}
        />
      ))}

      {/* strokeDasharray (an SVG attribute, not inline style) sets the dash;
          --len carries the line length so the route-draw keyframe can animate
          the offset from len → 0. The base (drawn) state lives in main.css. */}
      <polyline
        className="hex-anim__route"
        points={model.routePoints}
        strokeDasharray={model.routeLength}
        style={{ "--len": model.routeLength } as CSSProperties}
      />

      <text
        className="hex-anim__attrib"
        x={model.width - 6}
        y={model.height - 6}
        textAnchor="end"
      >
        © OpenStreetMap contributors © CARTO
      </text>
    </svg>
  );
}
