"""Tests for the GPX processing service.

Pure-function tests (no DB). Each happy-path test pulls factory fixtures
from ``conftest.py`` to synthesise GPX payloads inline.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime

import pytest

from src.app.services.gpx_processing import (
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


def test_detect_polygons_finds_loop(
    make_square_loop: Callable[..., list[Point]],
) -> None:
    pts = make_square_loop()
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


def test_gpx_bytes_to_polygons_one_loop_with_timestamps(
    make_square_loop: Callable[..., list[Point]],
    make_gpx_doc: Callable[[list[list[Point]]], bytes],
) -> None:
    start = datetime(2024, 1, 1, 12, 0, 0, tzinfo=UTC)
    pts = make_square_loop(start_time=start)
    data = make_gpx_doc([pts])

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


def test_gpx_bytes_to_polygons_no_timestamps_yields_completed_at_none(
    make_square_loop: Callable[..., list[Point]],
    make_gpx_doc: Callable[[list[list[Point]]], bytes],
) -> None:
    pts = make_square_loop(start_time=None)
    data = make_gpx_doc([pts])

    polygons = gpx_bytes_to_polygons(data, resolution=12, simplify=0.0)

    assert len(polygons) == 1
    assert polygons[0].completed_at is None


def test_gpx_bytes_to_polygons_open_track_returns_empty(
    make_open_track: Callable[..., list[Point]],
    make_gpx_doc: Callable[[list[list[Point]]], bytes],
) -> None:
    pts = make_open_track()
    data = make_gpx_doc([pts])

    polygons = gpx_bytes_to_polygons(data, resolution=12, simplify=0.0)

    assert polygons == []


def test_gpx_bytes_to_polygons_two_loops_indexed_sequentially(
    make_square_loop: Callable[..., list[Point]],
    make_gpx_doc: Callable[[list[list[Point]]], bytes],
) -> None:
    loop_a = make_square_loop()
    loop_b = make_square_loop(base_lat=51.51, base_lon=-0.11)
    # Two separate segments — each one self-closes.
    data = make_gpx_doc([loop_a, loop_b])

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


def test_too_many_trackpoints_rejected(
    monkeypatch: pytest.MonkeyPatch,
    make_open_track: Callable[..., list[Point]],
    make_gpx_doc: Callable[[list[list[Point]]], bytes],
) -> None:
    # Tighten the cap so we don't have to synthesise 200k points.
    monkeypatch.setattr(settings, "MAX_GPX_POINTS", 5)
    pts = make_open_track(n=10)
    data = make_gpx_doc([pts])

    with pytest.raises(GpxValidationError) as excinfo:
        gpx_bytes_to_polygons(data, resolution=12, simplify=0.0)
    assert excinfo.value.reason == "too many trackpoints"


def test_too_many_polygons_rejected(
    monkeypatch: pytest.MonkeyPatch,
    make_square_loop: Callable[..., list[Point]],
    make_gpx_doc: Callable[[list[list[Point]]], bytes],
) -> None:
    monkeypatch.setattr(settings, "MAX_GPX_POLYGONS", 1)
    loop_a = make_square_loop()
    loop_b = make_square_loop(base_lat=51.51, base_lon=-0.11)
    data = make_gpx_doc([loop_a, loop_b])

    with pytest.raises(GpxValidationError) as excinfo:
        gpx_bytes_to_polygons(data, resolution=12, simplify=0.0)
    assert excinfo.value.reason == "too many polygons"


def test_too_many_cells_rejected(
    monkeypatch: pytest.MonkeyPatch,
    make_square_loop: Callable[..., list[Point]],
    make_gpx_doc: Callable[[list[list[Point]]], bytes],
) -> None:
    monkeypatch.setattr(settings, "MAX_GPX_CELLS", 1)
    pts = make_square_loop()
    data = make_gpx_doc([pts])

    with pytest.raises(GpxValidationError) as excinfo:
        gpx_bytes_to_polygons(data, resolution=12, simplify=0.0)
    assert excinfo.value.reason == "too many cells"


def test_oversize_cap_can_be_lowered(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "MAX_GPX_BYTES", 16)
    with pytest.raises(GpxValidationError) as excinfo:
        gpx_bytes_to_polygons(b"x" * 32, resolution=12)
    assert excinfo.value.reason == "file too large"
