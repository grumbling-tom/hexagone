// MapLibre style URL. Sourced from PUBLIC_MAP_STYLE_URL so we can swap
// providers (OpenFreeMap → Protomaps → self-hosted PMTiles) without a
// code change.
export const MAP_STYLE_URL =
  import.meta.env.PUBLIC_MAP_STYLE_URL ??
  "https://tiles.openfreemap.org/styles/liberty";

// deck.gl wants RGBA (0–255) tuples — it can't read CSS custom properties.
// Mirrors --color-link in apps/web/src/styles/theme.css. The 4th value is
// alpha; 180/255 ≈ 0.7 opacity so the basemap labels stay legible
// underneath.
export const MAP_HEX_FILL: [number, number, number, number] = [
  0x25, 0x63, 0xeb, 180,
];

export const MAP_HEX_STROKE: [number, number, number, number] = [
  0x25, 0x63, 0xeb, 255,
];
