// Pointy-top hex grid + route projection for the landing trace animation.
// Ported from the landing-page prototype (apps/web/landing-examples). This is
// pure geometry: it returns the data the server-rendered SVG draws, and for
// each hex the running route passes, when it should "pop" (expressed as a
// delay in seconds, spread along the route). No styling or colour lives here —
// that's all in main.css.

export const TRACE_WIDTH = 512;
export const TRACE_HEIGHT = 512;

// Seconds the route line takes to draw; on-route hex delays are spread across
// this window so they pop roughly as the line's tip reaches them.
export const TRACE_DRAW_SECONDS = 3.4;

// Hex geometry — pointy-top, matching the app's EmptyMap.
const R = 15;
const DX = Math.sqrt(3) * R; // horizontal centre spacing
const DY = 1.5 * R; // vertical centre spacing

// A hex counts as "on the route" when its centre is within this of the line.
const ON_ROUTE = R * 1.05;

// The running route, hand-traced over the Stanley Park seawall / Park Drive on
// public/map.png. Coordinates are in the 512×512 tile pixel space (y points
// down); nudge these to re-trace the line.
const ROUTE: ReadonlyArray<readonly [number, number]> = [
  [108, 38],
  [70, 92],
  [42, 165],
  [30, 240],
  [38, 305],
  [66, 348],
  [128, 360],
  [192, 350],
  [250, 330],
  [305, 320],
  [350, 318],
  [378, 292],
  [398, 248],
  [422, 230],
  [440, 244],
];

// The six corners of a pointy-top hexagon, as an SVG points string.
function hexPoints(cx: number, cy: number, r: number): string {
  return Array.from({ length: 6 }, (_, i) => {
    const a = ((60 * i - 90) * Math.PI) / 180;
    return `${(cx + r * Math.cos(a)).toFixed(1)},${(cy + r * Math.sin(a)).toFixed(1)}`;
  }).join(" ");
}

// Every hex centre covering the viewBox, with a little bleed past the edges.
function buildGrid(w: number, h: number): Array<{ cx: number; cy: number }> {
  const cells: Array<{ cx: number; cy: number }> = [];
  const cols = Math.ceil(w / DX) + 2;
  const rows = Math.ceil(h / DY) + 2;
  for (let row = 0; row < rows; row++) {
    for (let col = 0; col < cols; col++) {
      cells.push({
        cx: col * DX + (row % 2 ? DX / 2 : 0),
        cy: row * DY,
      });
    }
  }
  return cells;
}

// Closest distance from a point to a polyline, plus the arc-length position of
// that closest point (used to order hexes along the route) and the polyline's
// total length.
function projectOntoPolyline(
  px: number,
  py: number,
  pts: ReadonlyArray<readonly [number, number]>,
): { dist: number; arc: number; total: number } {
  let best = Number.POSITIVE_INFINITY;
  let bestArc = 0;
  let arc = 0;
  for (let i = 0; i < pts.length - 1; i++) {
    const [x1, y1] = pts[i];
    const [x2, y2] = pts[i + 1];
    const dx = x2 - x1;
    const dy = y2 - y1;
    const segLen2 = dx * dx + dy * dy || 1;
    const t = Math.max(
      0,
      Math.min(1, ((px - x1) * dx + (py - y1) * dy) / segLen2),
    );
    const qx = x1 + t * dx;
    const qy = y1 + t * dy;
    const d = Math.hypot(px - qx, py - qy);
    const segLen = Math.sqrt(segLen2);
    if (d < best) {
      best = d;
      bestArc = arc + t * segLen;
    }
    arc += segLen;
  }
  return { dist: best, arc: bestArc, total: arc };
}

export interface TraceCell {
  points: string;
  // Animation delay in seconds — when this hex pops relative to the line draw.
  delay: number;
}

export interface TraceModel {
  width: number;
  height: number;
  // SVG points string for the route polyline.
  routePoints: string;
  // Total polyline length (for the stroke-dasharray draw trick).
  routeLength: number;
  // Faint background hexes covering the whole map.
  gridHexes: string[];
  // The hexes the route passes, with their pop delays.
  routeHexes: TraceCell[];
  drawSeconds: number;
}

// Build everything the trace SVG needs. Deterministic, so it runs once at
// server-render time.
export function buildTraceModel(): TraceModel {
  const gridHexes: string[] = [];
  const routeHexes: TraceCell[] = [];

  for (const { cx, cy } of buildGrid(TRACE_WIDTH, TRACE_HEIGHT)) {
    gridHexes.push(hexPoints(cx, cy, R));
    const { dist, arc, total } = projectOntoPolyline(cx, cy, ROUTE);
    if (dist < ON_ROUTE) {
      routeHexes.push({
        points: hexPoints(cx, cy, R * 0.92),
        delay: (arc / total) * TRACE_DRAW_SECONDS,
      });
    }
  }

  let routeLength = 0;
  for (let i = 0; i < ROUTE.length - 1; i++) {
    routeLength += Math.hypot(
      ROUTE[i + 1][0] - ROUTE[i][0],
      ROUTE[i + 1][1] - ROUTE[i][1],
    );
  }

  return {
    width: TRACE_WIDTH,
    height: TRACE_HEIGHT,
    routePoints: ROUTE.map((p) => p.join(",")).join(" "),
    routeLength,
    gridHexes,
    routeHexes,
    drawSeconds: TRACE_DRAW_SECONDS,
  };
}
