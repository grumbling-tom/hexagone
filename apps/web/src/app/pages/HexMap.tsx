import { Link } from "react-router-dom";

const HEX_RADIUS = 20;
const VIEW_W = 400;
const VIEW_H = 280;
const DX = Math.sqrt(3) * HEX_RADIUS;
const DY = 1.5 * HEX_RADIUS;

const CLAIMED_CELLS = new Set([
  "5,4",
  "6,4",
  "5,5",
  "6,5",
  "7,5",
  "6,6",
  "7,6",
  "8,6",
  "7,7",
  "8,7",
]);

function hexPoints(cx: number, cy: number): string {
  return Array.from({ length: 6 }, (_, i) => {
    const angle = ((60 * i - 90) * Math.PI) / 180;
    return `${(cx + HEX_RADIUS * Math.cos(angle)).toFixed(1)},${(
      cy + HEX_RADIUS * Math.sin(angle)
    ).toFixed(1)}`;
  }).join(" ");
}

function buildGrid() {
  const cells: Array<{
    key: string;
    cx: number;
    cy: number;
    claimed: boolean;
  }> = [];
  const cols = Math.ceil(VIEW_W / DX) + 1;
  const rows = Math.ceil(VIEW_H / DY) + 1;
  for (let row = 0; row < rows; row++) {
    for (let col = 0; col < cols; col++) {
      const cx = col * DX + (row % 2 === 1 ? DX / 2 : 0);
      const cy = row * DY;
      cells.push({
        key: `${col},${row}`,
        cx,
        cy,
        claimed: CLAIMED_CELLS.has(`${col},${row}`),
      });
    }
  }
  return cells;
}

export default function HexMap() {
  const cells = buildGrid();

  return (
    <main className="page map-page">
      <section className="map-skeleton" aria-label="Map preview">
        <svg
          className="map-skeleton__grid"
          viewBox={`0 0 ${VIEW_W} ${VIEW_H}`}
          preserveAspectRatio="xMidYMid slice"
          aria-hidden="true"
        >
          {cells.map(({ key, cx, cy, claimed }) => (
            <polygon
              key={key}
              points={hexPoints(cx, cy)}
              className={
                claimed
                  ? "map-skeleton__hex map-skeleton__hex--claimed"
                  : "map-skeleton__hex"
              }
            />
          ))}
        </svg>
        <div className="map-skeleton__overlay">
          <h1 className="map-skeleton__heading">Your map will appear here</h1>
          <p className="map-skeleton__copy">
            Upload a GPX file and Hexagone will colour in the hexagons you've
            covered.
          </p>
          <Link to="/uploads" className="button button--primary">
            Add your first upload
          </Link>
        </div>
      </section>
    </main>
  );
}
