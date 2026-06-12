"""GPX processing service.

Converts an uploaded GPX file (as raw bytes) into a list of detected
polygons covered by H3 cells. The algorithm mirrors
``scripts/gpx_to_h3.py``: walk each track segment, detect closed loops via
greedy closure detection, and rasterise each loop into H3 cells at the
requested resolution.

Trackpoint timestamps are carried through the pipeline so that the
``completed_at`` field on each :class:`DetectedPolygon` can be populated
from the timestamp of the trackpoint that closed the polygon.

Security
--------
The module hardens the stdlib XML parsers against XXE / billion-laughs
attacks at import time via :func:`defusedxml.defuse_stdlib`. Resource
exhaustion is bounded by the ``MAX_GPX_*`` settings; each cap raises a
typed :class:`GpxValidationError` so the lambda handler can mark the
upload ``UPLOAD_INVALID`` with a useful reason.
"""

from __future__ import annotations

import math
import xml.etree.ElementTree as ET
from datetime import datetime

import defusedxml
import gpxpy
import gpxpy.gpx
import h3  # pyright: ignore[reportMissingTypeStubs]
from defusedxml.common import DefusedXmlException
from pydantic import BaseModel

from src.app.settings import settings
from src.app.utils import get_logger

# Harden stdlib XML parsers (etree, sax, minidom, expat, ...) once on
# import so any code path that ends up using them — including gpxpy's
# internal ElementTree-based parser — refuses DTDs, external entities,
# and entity expansion.
defusedxml.defuse_stdlib()  # pyright: ignore[reportUnknownMemberType, reportAttributeAccessIssue]

logger = get_logger(__name__)

EARTH_RADIUS_M = 6_371_000.0

# Minimum number of points required to form a polygon.
MIN_POLYGON_POINTS = 3

# Below this absolute area value (in degree² shoelace units) the polygon
# is treated as degenerate (collinear / zero-area).
DEGENERATE_AREA_EPSILON = 1e-12

# A point carries lat, lng, and an optional timestamp from the GPX
# trackpoint. The timestamp rides through ``simplify`` and
# ``detect_polygons`` so the closing point of a polygon retains the
# wall-clock time it was traversed.
Point = tuple[float, float, datetime | None]

# Reason strings for ``GpxValidationError``. These are surfaced verbatim
# on the upload status row, so keep them short, user-safe, and stable.
_REASON_FILE_TOO_LARGE = "file too large"
_REASON_INVALID_GPX = "invalid GPX"
_REASON_TOO_MANY_POINTS = "too many trackpoints"
_REASON_TOO_MANY_POLYGONS = "too many polygons"
_REASON_TOO_MANY_CELLS = "too many cells"


class GpxValidationError(Exception):
    """Raised when an uploaded GPX cannot be processed.

    ``reason`` is a short, user-safe string suitable for surfacing on the
    upload status row.
    """

    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


class DetectedPolygon(BaseModel):
    """A closed loop detected in a GPX track, expanded to H3 cells."""

    model_config = {"frozen": True}

    polygon_index: int
    cells: frozenset[str]
    completed_at: datetime | None


def haversine_m(p1: Point, p2: Point) -> float:
    """Great-circle distance in metres between two points."""
    lat1, lng1, _ = p1
    lat2, lng2, _ = p2
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlam = math.radians(lng2 - lng1)
    a = (
        math.sin(dphi / 2) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(dlam / 2) ** 2
    )
    return 2 * EARTH_RADIUS_M * math.asin(math.sqrt(a))


def cumulative_arc(points: list[Point]) -> list[float]:
    """Return cumulative arc length (metres) from ``points[0]`` to each point."""
    cum = [0.0]
    for i in range(1, len(points)):
        cum.append(cum[-1] + haversine_m(points[i - 1], points[i]))
    return cum


def detect_polygons(
    points: list[Point], min_distance: float, min_loop_length: float
) -> list[tuple[int, int]]:
    """Greedy closure detection.

    At each position ``j``, scan backwards over earlier points ``i`` that
    are at least ``min_loop_length`` metres of arc behind ``j``. Pick the
    ``i`` with the smallest great-circle distance to ``p_j``; if that
    distance is below ``min_distance``, emit the slice ``(i, j)`` as a
    polygon and resume scanning from ``j + 1``. Picking the closest ``i``
    (rather than the first one that fits) avoids letting a brief
    doubled-back micro-loop consume a larger enclosing loop.
    """
    n = len(points)
    if n < MIN_POLYGON_POINTS:
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
    """True if the polygon has fewer than 3 distinct points or zero area."""
    unique = {(round(p[0], 7), round(p[1], 7)) for p in polygon}
    if len(unique) < MIN_POLYGON_POINTS:
        return True
    area = 0.0
    n = len(polygon)
    for k in range(n):
        lat1, lng1, _ = polygon[k]
        lat2, lng2, _ = polygon[(k + 1) % n]
        area += (lng2 - lng1) * (lat2 + lat1)
    return abs(area) < DEGENERATE_AREA_EPSILON


def gpx_bytes_to_polygons(
    data: bytes,
    *,
    resolution: int,
    min_distance: float = 10.0,
    min_loop_length: float = 50.0,
    simplify: float = 2.0,
) -> list[DetectedPolygon]:
    """Convert a GPX file (bytes) into a list of :class:`DetectedPolygon`.

    Args:
        data: Raw GPX file contents.
        resolution: Target H3 resolution (0-15).
        min_distance: Closure threshold in metres.
        min_loop_length: Minimum arc length between candidate endpoints
            in metres.
        simplify: Douglas-Peucker tolerance in metres applied to each
            segment before closure detection (0 disables).

    Returns:
        One :class:`DetectedPolygon` per non-degenerate closed loop, in
        the order they appeared in the file. Degenerate polygons (fewer
        than 3 unique points or zero area) are silently skipped, mirroring
        the script behaviour.

    Raises:
        GpxValidationError: If any of the security caps trip, the file is
            larger than ``MAX_GPX_BYTES``, or the XML is malformed /
            contains forbidden constructs (DTDs, external entities, entity
            expansion).
    """
    if len(data) > settings.MAX_GPX_BYTES:
        raise GpxValidationError(_REASON_FILE_TOO_LARGE)

    try:
        gpx = gpxpy.parse(data)
    except (
        gpxpy.gpx.GPXException,
        DefusedXmlException,
        ET.ParseError,
        ValueError,
    ) as e:
        logger.info("gpx_parse_failed", error=str(e), error_type=type(e).__name__)
        raise GpxValidationError(_REASON_INVALID_GPX) from e

    total_points = sum(len(s.points) for t in gpx.tracks for s in t.segments)
    if total_points > settings.MAX_GPX_POINTS:
        raise GpxValidationError(_REASON_TOO_MANY_POINTS)

    if simplify > 0:
        for track in gpx.tracks:
            for segment in track.segments:
                segment.simplify(max_distance=simplify)

    return _segments_to_polygons(
        gpx,
        resolution=resolution,
        min_distance=min_distance,
        min_loop_length=min_loop_length,
    )


def _segments_to_polygons(
    gpx: gpxpy.gpx.GPX,
    *,
    resolution: int,
    min_distance: float,
    min_loop_length: float,
) -> list[DetectedPolygon]:
    """Walk the parsed GPX, run closure detection, and rasterise to H3."""
    detected: list[DetectedPolygon] = []
    polygon_count = 0
    cell_count = 0

    for track in gpx.tracks:
        for segment in track.segments:
            pts: list[Point] = [
                (p.latitude, p.longitude, p.time) for p in segment.points
            ]
            if len(pts) < MIN_POLYGON_POINTS:
                continue
            for i, j in detect_polygons(pts, min_distance, min_loop_length):
                polygon_pts = pts[i : j + 1]
                if is_degenerate(polygon_pts):
                    continue
                if polygon_count >= settings.MAX_GPX_POLYGONS:
                    raise GpxValidationError(_REASON_TOO_MANY_POLYGONS)
                cells: list[str] = h3.h3shape_to_cells(  # pyright: ignore[reportUnknownMemberType]
                    h3.LatLngPoly([(lat, lng) for lat, lng, _ in polygon_pts]),
                    resolution,
                )
                cell_count += len(cells)
                if cell_count > settings.MAX_GPX_CELLS:
                    raise GpxValidationError(_REASON_TOO_MANY_CELLS)
                detected.append(
                    DetectedPolygon(
                        polygon_index=polygon_count,
                        cells=frozenset(cells),
                        completed_at=pts[j][2],
                    )
                )
                polygon_count += 1

    return detected
