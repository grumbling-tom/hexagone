#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "gpxpy>=1.6",
#     "h3>=4.1",
# ]
# ///
"""Convert a GPX track into H3 hex IDs enclosed by polygons the path forms.

A GPX track is a line, not a polygon. This script walks the track and, wherever
the line returns within ``--min-distance`` metres of an earlier position, closes
that span into a polygon. The union of H3 cells inside all detected polygons is
written one-per-line to stdout; summary details are written to stderr.

Invoke with ``uv run scripts/gpx_to_h3.py <gpx> <resolution> [options]``.
"""

from __future__ import annotations

import argparse
import math
import sys
from pathlib import Path

import gpxpy
import h3

EARTH_RADIUS_M = 6_371_000.0

Point = tuple[float, float]


def haversine_m(p1: Point, p2: Point) -> float:
    lat1, lng1 = p1
    lat2, lng2 = p2
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlam = math.radians(lng2 - lng1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlam / 2) ** 2
    return 2 * EARTH_RADIUS_M * math.asin(math.sqrt(a))


def cumulative_arc(points: list[Point]) -> list[float]:
    cum = [0.0]
    for i in range(1, len(points)):
        cum.append(cum[-1] + haversine_m(points[i - 1], points[i]))
    return cum


def detect_polygons(
    points: list[Point], min_distance: float, min_loop_length: float
) -> list[tuple[int, int]]:
    """Greedy closure detection.

    At each position ``j``, scan backwards over earlier points ``i`` that are at
    least ``min_loop_length`` metres of arc behind ``j``. Pick the ``i`` with the
    smallest great-circle distance to ``p_j``; if that distance is below
    ``min_distance``, emit the slice ``(i, j)`` as a polygon and resume scanning
    from ``j + 1``. Picking the closest ``i`` (rather than the first one that
    fits) avoids letting a brief doubled-back micro-loop consume a larger
    enclosing loop.
    """
    n = len(points)
    if n < 3:
        return []
    cum = cumulative_arc(points)
    polygons: list[tuple[int, int]] = []
    start = 0
    j = start + 1
    while j < n:
        best_i: int | None = None
        best_d = float("inf")
        for i in range(start, j):
            if cum[j] - cum[i] < min_loop_length:
                break
            d = haversine_m(points[i], points[j])
            if d < best_d:
                best_d = d
                best_i = i
        if best_i is not None and best_d < min_distance:
            polygons.append((best_i, j))
            start = j + 1
            j = start + 1
        else:
            j += 1
    return polygons


def is_degenerate(polygon: list[Point]) -> bool:
    unique = {(round(p[0], 7), round(p[1], 7)) for p in polygon}
    if len(unique) < 3:
        return True
    area = 0.0
    n = len(polygon)
    for k in range(n):
        lat1, lng1 = polygon[k]
        lat2, lng2 = polygon[(k + 1) % n]
        area += (lng2 - lng1) * (lat2 + lat1)
    return abs(area) < 1e-12


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=__doc__.splitlines()[0],
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("gpx_file", type=Path, help="Path to the input GPX file.")
    parser.add_argument("resolution", type=int, help="H3 resolution (0-15).")
    parser.add_argument(
        "--min-distance",
        type=float,
        default=10.0,
        help="Closure threshold in metres.",
    )
    parser.add_argument(
        "--min-loop-length",
        type=float,
        default=50.0,
        help="Minimum arc length between candidate endpoints in metres.",
    )
    parser.add_argument(
        "--simplify",
        type=float,
        default=2.0,
        help="Douglas-Peucker tolerance in metres (0 disables).",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)

    if not (0 <= args.resolution <= 15):
        print(f"error: resolution must be 0-15, got {args.resolution}", file=sys.stderr)
        return 2

    with open(args.gpx_file) as f:
        gpx = gpxpy.parse(f)

    total_points = sum(len(s.points) for t in gpx.tracks for s in t.segments)
    if total_points == 0:
        print(f"warning: {args.gpx_file} contains no track points", file=sys.stderr)
        return 0

    if args.simplify > 0:
        for track in gpx.tracks:
            for segment in track.segments:
                segment.simplify(max_distance=args.simplify)

    all_cells: set[str] = set()
    polygon_count = 0
    skipped = 0
    for ti, track in enumerate(gpx.tracks):
        for si, segment in enumerate(track.segments):
            pts: list[Point] = [(p.latitude, p.longitude) for p in segment.points]
            if len(pts) < 3:
                continue
            for i, j in detect_polygons(pts, args.min_distance, args.min_loop_length):
                polygon = pts[i : j + 1]
                if is_degenerate(polygon):
                    skipped += 1
                    print(
                        f"  track {ti} seg {si}: skipping degenerate polygon {i}..{j} ({len(polygon)} pts)",
                        file=sys.stderr,
                    )
                    continue
                cells = h3.h3shape_to_cells(h3.LatLngPoly(polygon), args.resolution)
                polygon_count += 1
                all_cells.update(cells)
                print(
                    f"  track {ti} seg {si}: polygon {i}..{j} ({len(polygon)} pts) -> {len(cells)} cells",
                    file=sys.stderr,
                )

    print(
        f"detected {polygon_count} polygon(s){f', skipped {skipped} degenerate' if skipped else ''}; "
        f"{len(all_cells)} unique cells at res {args.resolution}",
        file=sys.stderr,
    )
    for cell in sorted(all_cells):
        print(cell)

    return 0


if __name__ == "__main__":
    sys.exit(main())
