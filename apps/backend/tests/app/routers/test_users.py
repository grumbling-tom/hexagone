"""Tests for the users router."""

from fastapi.testclient import TestClient


def test_get_current_user_authenticated(client: TestClient):
    response = client.get("/api/v1/users/current")
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "test@example.com"
    assert data["role"] == "user"
    assert "uid" in data


def test_get_current_user_unauthenticated(unauthenticated_client: TestClient):
    response = unauthenticated_client.get("/api/v1/users/current")
    assert response.status_code == 401
