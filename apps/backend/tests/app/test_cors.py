"""Tests for CORS middleware configuration."""

from fastapi.testclient import TestClient

from src.app.main import create_app
from src.app.settings import Settings


def test_cors_allows_dev_origin():
    app = create_app(Settings(ENV="DEV"))
    client = TestClient(app)
    response = client.get("/api/health", headers={"origin": "http://localhost:4321"})
    assert response.headers["access-control-allow-origin"] == "http://localhost:4321"


def test_cors_blocks_disallowed_origin():
    app = create_app(Settings(ENV="DEV"))
    client = TestClient(app)
    response = client.get("/api/health", headers={"origin": "http://evil.com"})
    assert "access-control-allow-origin" not in response.headers


def test_cors_not_applied_in_prod():
    app = create_app(Settings(ENV="PROD", DATABASE_URL="postgresql://u:p@host:5432/db"))
    client = TestClient(app)
    response = client.get("/api/health", headers={"origin": "http://localhost:4321"})
    assert "access-control-allow-origin" not in response.headers
