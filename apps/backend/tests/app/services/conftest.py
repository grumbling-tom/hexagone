"""Shared fixtures for the upload-processing service tests.

Provides factory fixtures for synthesising GPX payloads inline. These
were previously private helper functions duplicated across
``test_gpx_processing.py`` and ``test_upload.py``; per
``apps/backend/CLAUDE.md`` ("Fixtures over Helper Functions"), test-data
construction belongs in a fixture so it can be shared and discovered
through pytest's dependency injection.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, timedelta

import pytest

from src.app.services.gpx_processing import Point

# Roughly 11 metres in latitude / longitude near London. Baked into the
# loop / track factories so individual tests don't have to reason about
# them.
_LAT_STEP_11M = 0.0001
_LON_STEP_11M = 0.00015
_BASE_LAT = 51.5
_BASE_LON = -0.12


@pytest.fixture
def make_trkpt() -> Callable[..., str]:
    """Render a single ``<trkpt>`` XML fragment, optionally with a ``<time>``."""

    def _factory(lat: float, lon: float, ts: datetime | None = None) -> str:
        if ts is None:
            return f'      <trkpt lat="{lat:.7f}" lon="{lon:.7f}"/>\n'
        iso = ts.strftime("%Y-%m-%dT%H:%M:%SZ")
        return (
            f'      <trkpt lat="{lat:.7f}" lon="{lon:.7f}">\n'
            f"        <time>{iso}</time>\n"
            f"      </trkpt>\n"
        )

    return _factory


@pytest.fixture
def make_gpx_doc(
    make_trkpt: Callable[..., str],
) -> Callable[[list[list[Point]]], bytes]:
    """Render a GPX document containing one track with the given segments."""

    def _factory(segments: list[list[Point]]) -> bytes:
        parts: list[str] = [
            '<?xml version="1.0" encoding="UTF-8"?>\n',
            '<gpx version="1.1" creator="test" '
            'xmlns="http://www.topografix.com/GPX/1/1">\n',
            "  <trk>\n",
        ]
        for points in segments:
            parts.append("    <trkseg>\n")
            for lat, lon, ts in points:
                parts.append(make_trkpt(lat, lon, ts))
            parts.append("    </trkseg>\n")
        parts.append("  </trk>\n</gpx>\n")
        return "".join(parts).encode()

    return _factory


@pytest.fixture
def make_square_loop() -> Callable[..., list[Point]]:
    """Build a closed square loop centred at (base_lat, base_lon).

    ``side_steps`` controls how many trackpoints are emitted on each side
    of the square. The loop closes by returning to (and slightly past) the
    starting point so ``detect_polygons`` registers it.
    """

    def _factory(
        *,
        base_lat: float = _BASE_LAT,
        base_lon: float = _BASE_LON,
        side_steps: int = 6,
        start_time: datetime | None = None,
        step: timedelta = timedelta(seconds=10),
    ) -> list[Point]:
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

    return _factory


@pytest.fixture
def make_open_track() -> Callable[..., list[Point]]:
    """Build a straight east-west track that never closes on itself."""

    def _factory(*, n: int = 20) -> list[Point]:
        return [(_BASE_LAT, _BASE_LON + i * _LON_STEP_11M, None) for i in range(n)]

    return _factory
