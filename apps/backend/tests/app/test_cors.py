"""Tests for CORS middleware configuration."""

import importlib
from unittest.mock import patch

from fastapi.testclient import TestClient

import src.app.main


def _make_app():
    """Create a fresh app instance with current settings."""
    importlib.reload(src.app.main)
    return src.app.main.app


def test_cors_allows_dev_origin():
    with patch("src.app.settings.settings.ENV", "DEV"):
        app = _make_app()
    client = TestClient(app)
    response = client.get("/health", headers={"origin": "http://localhost:4321"})
    assert response.headers["access-control-allow-origin"] == "http://localhost:4321"


def test_cors_blocks_disallowed_origin():
    with patch("src.app.settings.settings.ENV", "DEV"):
        app = _make_app()
    client = TestClient(app)
    response = client.get("/health", headers={"origin": "http://evil.com"})
    assert "access-control-allow-origin" not in response.headers


def test_cors_not_applied_in_prod():
    with patch("src.app.settings.settings.ENV", "PROD"):
        app = _make_app()
    client = TestClient(app)
    response = client.get("/health", headers={"origin": "http://localhost:4321"})
    assert "access-control-allow-origin" not in response.headers
