"""Tests for the GPX processing service.

Pure-function tests (no DB). Each happy-path test synthesises a minimal
GPX XML document inline so the test is self-contained and easy to read.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from src.app.handlers.file_upload.gpx_processing import (
    DetectedPolygon,
    GpxValidationError,
    Point,
    cumulative_arc,
    detect_polygons,
    gpx_bytes_to_polygons,
    haversine_m,
    is_degenerate,
)
from src.app.settings import settings

# ---------------------------------------------------------------------------
# GPX builders
# ---------------------------------------------------------------------------

# Roughly 11 metres in latitude and longitude near London.
_LAT_STEP_11M = 0.0001
_LON_STEP_11M = 0.00015

_BASE_LAT = 51.5
_BASE_LON = -0.12


def _trkpt(lat: float, lon: float, ts: datetime | None = None) -> str:
    if ts is None:
        return f'      <trkpt lat="{lat:.7f}" lon="{lon:.7f}"/>\n'
    iso = ts.strftime("%Y-%m-%dT%H:%M:%SZ")
    return (
        f'      <trkpt lat="{lat:.7f}" lon="{lon:.7f}">\n'
        f"        <time>{iso}</time>\n"
        f"      </trkpt>\n"
    )


def _gpx_doc(segments: list[list[Point]]) -> bytes:
    """Render a GPX document containing one track with the given segments."""
    parts: list[str] = [
        '<?xml version="1.0" encoding="UTF-8"?>\n',
        '<gpx version="1.1" creator="test" '
        'xmlns="http://www.topografix.com/GPX/1/1">\n',
        "  <trk>\n",
    ]
    for points in segments:
        parts.append("    <trkseg>\n")
        for lat, lon, ts in points:
            parts.append(_trkpt(lat, lon, ts))
        parts.append("    </trkseg>\n")
    parts.append("  </trk>\n</gpx>\n")
    return "".join(parts).encode()


def _square_loop(
    *,
    base_lat: float = _BASE_LAT,
    base_lon: float = _BASE_LON,
    side_steps: int = 6,
    start_time: datetime | None = None,
    step: timedelta = timedelta(seconds=10),
) -> list[Point]:
    """A square loop centred at (base_lat, base_lon).

    side_steps controls how many trackpoints are emitted on each side of
    the square. The loop closes by returning to (and slightly past) the
    starting point so `detect_polygons` registers it.
    """
    pts: list[Point] = []
    cur_time = start_time

    def emit(lat: float, lon: float) -> None:
        nonlocal cur_time
        pts.append((lat, lon, cur_time))
        if cur_time is not None:
            cur_time = cur_time + step

    side = side_steps
    # Bottom edge: lon increases.
    for i in range(side):
        emit(base_lat, base_lon + i * _LON_STEP_11M)
    # Right edge: lat increases.
    for i in range(side):
        emit(base_lat + i * _LAT_STEP_11M, base_lon + (side - 1) * _LON_STEP_11M)
    # Top edge: lon decreases.
    for i in range(side):
        emit(
            base_lat + (side - 1) * _LAT_STEP_11M,
            base_lon + (side - 1 - i) * _LON_STEP_11M,
        )
    # Left edge: lat decreases. End back where we started.
    for i in range(side):
        emit(base_lat + (side - 1 - i) * _LAT_STEP_11M, base_lon)
    # Final closing point — overshoot slightly so the closure detector
    # finds a sub-min_distance return-to-start.
    emit(base_lat, base_lon)
    return pts


# ---------------------------------------------------------------------------
# Pure-function tests
# ---------------------------------------------------------------------------


def test_haversine_zero_distance() -> None:
    p: Point = (51.5, -0.1, None)
    assert haversine_m(p, p) == pytest.approx(0.0, abs=1e-6)  # pyright: ignore[reportUnknownMemberType]


def test_haversine_one_degree_latitude() -> None:
    """One degree of latitude is ~111 km anywhere on Earth."""
    d = haversine_m((0.0, 0.0, None), (1.0, 0.0, None))
    assert d == pytest.approx(111_194.93, rel=1e-4)  # pyright: ignore[reportUnknownMemberType]


def test_cumulative_arc_monotonic() -> None:
    pts: list[Point] = [
        (0.0, 0.0, None),
        (0.0, 0.001, None),
        (0.001, 0.001, None),
    ]
    cum = cumulative_arc(pts)
    assert cum[0] == 0.0
    assert cum[1] > cum[0]
    assert cum[2] > cum[1]


def test_detect_polygons_returns_empty_for_short_track() -> None:
    pts: list[Point] = [(0.0, 0.0, None), (0.0, 0.001, None)]
    assert detect_polygons(pts, min_distance=10.0, min_loop_length=50.0) == []


def test_detect_polygons_finds_loop() -> None:
    pts = _square_loop()
    found = detect_polygons(pts, min_distance=10.0, min_loop_length=50.0)
    assert len(found) == 1
    i, j = found[0]
    # The closure detector starts from the first point and selects the
    # closest later point; both endpoints sit on the start corner.
    assert i == 0
    assert j > i
    assert j < len(pts)


def test_is_degenerate_detects_collinear_points() -> None:
    pts: list[Point] = [
        (0.0, 0.0, None),
        (0.0, 0.001, None),
        (0.0, 0.002, None),
        (0.0, 0.003, None),
    ]
    assert is_degenerate(pts) is True


def test_is_degenerate_detects_two_unique_points() -> None:
    pts: list[Point] = [
        (0.0, 0.0, None),
        (0.0, 0.001, None),
        (0.0, 0.0, None),
    ]
    assert is_degenerate(pts) is True


def test_is_degenerate_false_for_real_triangle() -> None:
    pts: list[Point] = [
        (0.0, 0.0, None),
        (0.0, 0.001, None),
        (0.001, 0.001, None),
    ]
    assert is_degenerate(pts) is False


# ---------------------------------------------------------------------------
# gpx_bytes_to_polygons — happy paths
# ---------------------------------------------------------------------------


def test_gpx_bytes_to_polygons_one_loop_with_timestamps() -> None:
    start = datetime(2024, 1, 1, 12, 0, 0, tzinfo=UTC)
    pts = _square_loop(start_time=start)
    data = _gpx_doc([pts])

    polygons = gpx_bytes_to_polygons(data, resolution=12, simplify=0.0)

    assert len(polygons) == 1
    poly = polygons[0]
    assert isinstance(poly, DetectedPolygon)
    assert poly.polygon_index == 0
    assert len(poly.cells) > 0
    # All H3 cell IDs are 15 hex chars at res 12.
    for cell in poly.cells:
        assert len(cell) == 15

    # The polygon's completed_at should be the timestamp of whichever
    # trackpoint detect_polygons identified as the closure point. Run
    # the detector against the same point list to find that index.
    found = detect_polygons(pts, min_distance=10.0, min_loop_length=50.0)
    assert len(found) == 1
    closing_index = found[0][1]
    expected_ts = pts[closing_index][2]
    assert expected_ts is not None
    assert poly.completed_at is not None
    # gpxpy's parser uses its own tzinfo class, so compare epoch values.
    assert poly.completed_at.timestamp() == expected_ts.timestamp()


def test_gpx_bytes_to_polygons_no_timestamps_yields_completed_at_none() -> None:
    pts = _square_loop(start_time=None)
    data = _gpx_doc([pts])

    polygons = gpx_bytes_to_polygons(data, resolution=12, simplify=0.0)

    assert len(polygons) == 1
    assert polygons[0].completed_at is None


def test_gpx_bytes_to_polygons_open_track_returns_empty() -> None:
    # A straight line — never closes back on itself.
    pts: list[Point] = [
        (_BASE_LAT, _BASE_LON + i * _LON_STEP_11M, None) for i in range(20)
    ]
    data = _gpx_doc([pts])

    polygons = gpx_bytes_to_polygons(data, resolution=12, simplify=0.0)

    assert polygons == []


def test_gpx_bytes_to_polygons_two_loops_indexed_sequentially() -> None:
    loop_a = _square_loop(base_lat=_BASE_LAT, base_lon=_BASE_LON)
    loop_b = _square_loop(base_lat=_BASE_LAT + 0.01, base_lon=_BASE_LON + 0.01)
    # Two separate segments — each one self-closes.
    data = _gpx_doc([loop_a, loop_b])

    polygons = gpx_bytes_to_polygons(data, resolution=12, simplify=0.0)

    assert len(polygons) == 2
    assert [p.polygon_index for p in polygons] == [0, 1]
    # The two loops are at different locations, so their cell sets should
    # be disjoint.
    assert polygons[0].cells.isdisjoint(polygons[1].cells)


# ---------------------------------------------------------------------------
# gpx_bytes_to_polygons — security caps & malformed input
# ---------------------------------------------------------------------------


def test_oversized_payload_rejected() -> None:
    data = b"x" * (settings.MAX_GPX_BYTES + 1)
    with pytest.raises(GpxValidationError) as excinfo:
        gpx_bytes_to_polygons(data, resolution=12)
    assert excinfo.value.reason == "file too large"


def test_malformed_xml_rejected() -> None:
    with pytest.raises(GpxValidationError) as excinfo:
        gpx_bytes_to_polygons(b"not xml", resolution=12)
    assert excinfo.value.reason == "invalid GPX"


def test_xxe_external_entity_rejected() -> None:
    payload = (
        b'<?xml version="1.0"?>\n'
        b"<!DOCTYPE foo [\n"
        b'  <!ENTITY xxe SYSTEM "file:///etc/passwd">\n'
        b"]>\n"
        b'<gpx version="1.1"><trk><trkseg>\n'
        b'<trkpt lat="0.0" lon="0.0"><name>&xxe;</name></trkpt>\n'
        b"</trkseg></trk></gpx>\n"
    )
    with pytest.raises(GpxValidationError):
        gpx_bytes_to_polygons(payload, resolution=12)


def test_billion_laughs_rejected() -> None:
    lol = b"&lol;" * 10
    lol2 = b"&lol2;" * 10
    lol3 = b"&lol3;" * 10
    payload = (
        b'<?xml version="1.0"?>\n'
        b"<!DOCTYPE lolz [\n"
        b'  <!ENTITY lol "lol">\n'
        b'  <!ENTITY lol2 "' + lol + b'">\n'
        b'  <!ENTITY lol3 "' + lol2 + b'">\n'
        b'  <!ENTITY lol4 "' + lol3 + b'">\n'
        b"]>\n"
        b'<gpx version="1.1"><trk><name>&lol4;</name></trk></gpx>\n'
    )
    with pytest.raises(GpxValidationError):
        gpx_bytes_to_polygons(payload, resolution=12)


def test_too_many_trackpoints_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    # Tighten the cap so we don't have to synthesise 200k points.
    monkeypatch.setattr(settings, "MAX_GPX_POINTS", 5)
    pts: list[Point] = [
        (_BASE_LAT, _BASE_LON + i * _LON_STEP_11M, None) for i in range(10)
    ]
    data = _gpx_doc([pts])

    with pytest.raises(GpxValidationError) as excinfo:
        gpx_bytes_to_polygons(data, resolution=12, simplify=0.0)
    assert excinfo.value.reason == "too many trackpoints"


def test_too_many_polygons_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "MAX_GPX_POLYGONS", 1)
    loop_a = _square_loop(base_lat=_BASE_LAT, base_lon=_BASE_LON)
    loop_b = _square_loop(base_lat=_BASE_LAT + 0.01, base_lon=_BASE_LON + 0.01)
    data = _gpx_doc([loop_a, loop_b])

    with pytest.raises(GpxValidationError) as excinfo:
        gpx_bytes_to_polygons(data, resolution=12, simplify=0.0)
    assert excinfo.value.reason == "too many polygons"


def test_too_many_cells_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "MAX_GPX_CELLS", 1)
    pts = _square_loop()
    data = _gpx_doc([pts])

    with pytest.raises(GpxValidationError) as excinfo:
        gpx_bytes_to_polygons(data, resolution=12, simplify=0.0)
    assert excinfo.value.reason == "too many cells"


def test_oversize_cap_can_be_lowered(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "MAX_GPX_BYTES", 16)
    with pytest.raises(GpxValidationError) as excinfo:
        gpx_bytes_to_polygons(b"x" * 32, resolution=12)
    assert excinfo.value.reason == "file too large"
