#!/usr/bin/env node
/*
 * Render a square CARTO Positron basemap image centred on a lat/lon, for the
 * landing page's static map underlay (public/map.png).
 *
 * Flow:
 *   1. Find the tile the point falls in, and fetch the 3×3 block around it (9
 *      tiles), so there's a full tile of margin on every side.
 *   2. Stitch those into one image whose lat/lon bounds we know.
 *   3. Draw a box of the requested size centred on the point and clip to it.
 *   4. Write the clipped image (the point is dead-centre of it).
 *
 * Positron is the same basemap the app's HexMap uses, and the tiles are
 * keyless. Showing the tile requires the attribution "© OpenStreetMap
 * contributors © CARTO".
 *
 * Usage:
 *   pnpm map:tile <lat> <lon> [zoom=14] [size=512] [outfile=map-preview.png] [--mark] [--write-stitched]
 *
 *   --mark            overlay a crosshair dot on the point (centre of the clip,
 *                     true position in the stitched image)
 *   --write-stitched  also write the full 3×3 stitched image alongside the clip
 *                     (as <outfile>-stitched.png), honouring --mark
 *
 * Examples:
 *   pnpm map:tile 49.3017 -123.1417                     # 512×512 @ z14
 *   pnpm map:tile 49.3017 -123.1250 15                  # one level closer
 *   pnpm map:tile 49.3017 -123.1250 --mark              # dot on the point
 *   pnpm map:tile 49.3017 -123.1250 14 512 public/map.png   # write it in
 *
 * Inspect the output (`open map-preview.png`); when it looks right, re-run with
 * public/map.png as the outfile (or copy it there). Drop --mark for the final
 * asset so the marker isn't baked in.
 */
import { writeFile } from "node:fs/promises";
import { resolve } from "node:path";
import sharp from "sharp";

const rawArgs = process.argv.slice(2);
const flags = new Set(rawArgs.filter((a) => a.startsWith("--")));
const [latArg, lonArg, zoomArg, arg4, arg5] = rawArgs.filter(
  (a) => !a.startsWith("--"),
);
const mark = flags.has("--mark");
const writeStitched = flags.has("--write-stitched");

if (latArg === undefined || lonArg === undefined) {
  console.error(
    "Usage: pnpm map:tile <lat> <lon> [zoom=14] [size=512] [outfile=map-preview.png] [--mark] [--write-stitched]",
  );
  process.exit(1);
}

const lat = Number(latArg);
const lon = Number(lonArg);
const zoom = zoomArg === undefined ? 14 : Number(zoomArg);

// The trailing [size] and [outfile] are both optional and order-tolerant: a
// purely-numeric trailing arg is the size, anything else is the outfile. So
// `<lat> <lon> <zoom> out.png` works without having to spell out the size.
const looksNumeric = (s) => s !== undefined && /^\d+$/.test(s);
let sizeArg;
let outArg;
for (const a of [arg4, arg5]) {
  if (a === undefined) continue;
  if (looksNumeric(a)) sizeArg = a;
  else outArg = a;
}
const size = sizeArg === undefined ? 512 : Number(sizeArg);
const outfile = outArg ?? "map-preview.png";

// @2x tiles are 512px square; the 3×3 stitch is 1536px, so the clip box can be
// up to 2 tiles (a full margin tile each side of the centre tile) and still fit
// wherever the point lands.
const TILE = 512;
const MAX_SIZE = 2 * TILE;

if (!Number.isFinite(lat) || lat < -85.0511 || lat > 85.0511) {
  console.error(`Invalid latitude: ${latArg} (expected -85.0511..85.0511)`);
  process.exit(1);
}
if (!Number.isFinite(lon) || lon < -180 || lon > 180) {
  console.error(`Invalid longitude: ${lonArg} (expected -180..180)`);
  process.exit(1);
}
if (!Number.isInteger(zoom) || zoom < 0 || zoom > 20) {
  console.error(`Invalid zoom: ${zoomArg} (expected integer 0..20)`);
  process.exit(1);
}
if (!Number.isInteger(size) || size < 1 || size > MAX_SIZE) {
  console.error(`Invalid size: ${sizeArg} (expected integer 1..${MAX_SIZE})`);
  process.exit(1);
}

const n = 2 ** zoom;

// Web Mercator forward (lat/lon -> fractional tile coords) and inverse (tile
// coords -> lat/lon), slippy-map convention.
// https://wiki.openstreetmap.org/wiki/Slippy_map_tilenames#Lon..2Flat._to_tile_numbers
const latRad = (lat * Math.PI) / 180;
const xTile = ((lon + 180) / 360) * n;
const yTile = ((1 - Math.asinh(Math.tan(latRad)) / Math.PI) / 2) * n;
const tileToLon = (x) => (x / n) * 360 - 180;
const tileToLat = (y) =>
  (Math.atan(Math.sinh(Math.PI * (1 - (2 * y) / n))) * 180) / Math.PI;

// The 3×3 block of tiles around the one the point falls in.
const firstCol = Math.floor(xTile) - 1;
const firstRow = Math.floor(yTile) - 1;
const lastCol = firstCol + 2;
const lastRow = firstRow + 2;
const canvasW = 3 * TILE;
const canvasH = 3 * TILE;

// The point's pixel position within the stitched image (not its centre).
const pointX = (xTile - firstCol) * TILE;
const pointY = (yTile - firstRow) * TILE;

// The clip box, centred on the point. Guaranteed to fit: the point sits in the
// centre tile, so there's ≥ TILE of margin each side and size ≤ 2·TILE.
const clipLeft = Math.round(pointX - size / 2);
const clipTop = Math.round(pointY - size / 2);

console.log(
  `Point tile-fraction (${xTile.toFixed(3)}, ${yTile.toFixed(3)}) @ z${zoom}`,
);
console.log(
  `Stitched bounds: N ${tileToLat(firstRow).toFixed(5)}, S ${tileToLat(
    lastRow + 1,
  ).toFixed(5)}, W ${tileToLon(firstCol).toFixed(5)}, E ${tileToLon(
    lastCol + 1,
  ).toFixed(5)}`,
);
console.log(`Stitching 9 tile(s), clipping ${size}×${size}`);

const clampTile = (v) => ((v % n) + n) % n; // wrap x, also guards y

async function fetchTile(col, row) {
  const tx = clampTile(col);
  const ty = clampTile(row);
  const url = `https://basemaps.cartocdn.com/light_all/${zoom}/${tx}/${ty}@2x.png`;
  const res = await fetch(url, { headers: { "User-Agent": "hexagone-dev" } });
  if (!res.ok) {
    throw new Error(`Tile ${zoom}/${tx}/${ty}: ${res.status} ${res.statusText}`);
  }
  return Buffer.from(await res.arrayBuffer());
}

const jobs = [];
for (let row = firstRow; row <= lastRow; row++) {
  for (let col = firstCol; col <= lastCol; col++) {
    jobs.push({ col, row });
  }
}
const tiles = await Promise.all(
  jobs.map(async ({ col, row }) => ({
    buf: await fetchTile(col, row),
    x: (col - firstCol) * TILE,
    y: (row - firstRow) * TILE,
  })),
);

// A crosshair + dot, as an SVG overlay sized to the target image, centred on
// (cx, cy). Red with a white halo so it reads on the light basemap.
function markerSvg(w, h, cx, cy) {
  const a = 14; // crosshair arm length
  return Buffer.from(
    `<svg xmlns="http://www.w3.org/2000/svg" width="${w}" height="${h}">` +
      `<line x1="${cx}" y1="${cy - a}" x2="${cx}" y2="${cy + a}" stroke="#fff" stroke-width="4"/>` +
      `<line x1="${cx - a}" y1="${cy}" x2="${cx + a}" y2="${cy}" stroke="#fff" stroke-width="4"/>` +
      `<line x1="${cx}" y1="${cy - a}" x2="${cx}" y2="${cy + a}" stroke="#e11d48" stroke-width="2"/>` +
      `<line x1="${cx - a}" y1="${cy}" x2="${cx + a}" y2="${cy}" stroke="#e11d48" stroke-width="2"/>` +
      `<circle cx="${cx}" cy="${cy}" r="5" fill="#e11d48" stroke="#fff" stroke-width="2"/>` +
      `</svg>`,
  );
}

// Stitch the 9 tiles into one image.
const stitched = await sharp({
  create: {
    width: canvasW,
    height: canvasH,
    channels: 4,
    background: { r: 0, g: 0, b: 0, alpha: 0 },
  },
})
  .composite(tiles.map((t) => ({ input: t.buf, left: t.x, top: t.y })))
  .png()
  .toBuffer();

// Clip the centred box out of the stitch; the point is at the clip's centre.
let clipped = await sharp(stitched)
  .extract({ left: clipLeft, top: clipTop, width: size, height: size })
  .png()
  .toBuffer();
if (mark) {
  clipped = await sharp(clipped)
    .composite([{ input: markerSvg(size, size, size / 2, size / 2) }])
    .png()
    .toBuffer();
}

const dest = resolve(process.cwd(), outfile);
await writeFile(dest, clipped);
console.log(`Wrote ${size}×${size} clip to ${dest}`);

if (writeStitched) {
  let out = stitched;
  if (mark) {
    out = await sharp(stitched)
      .composite([{ input: markerSvg(canvasW, canvasH, pointX, pointY) }])
      .png()
      .toBuffer();
  }
  // <outfile> -> <outfile>-stitched.png
  const dot = outfile.lastIndexOf(".");
  const slash = Math.max(outfile.lastIndexOf("/"), outfile.lastIndexOf("\\"));
  const stitchedOut =
    dot > slash
      ? `${outfile.slice(0, dot)}-stitched${outfile.slice(dot)}`
      : `${outfile}-stitched`;
  const stitchedDest = resolve(process.cwd(), stitchedOut);
  await writeFile(stitchedDest, out);
  console.log(`Wrote ${canvasW}×${canvasH} stitched image to ${stitchedDest}`);
}

console.log("Inspect it, then re-run with public/map.png as the outfile if good.");
