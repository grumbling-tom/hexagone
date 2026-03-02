"""Tests for the user sessions router."""

from fastapi.testclient import TestClient


def test_login_success(unauthenticated_client: TestClient):
    # First create a user
    unauthenticated_client.post(
        "/api/v1/users",
        json={"email": "login@example.com", "password": "password123"},
    )
    # Clear cookies from signup
    unauthenticated_client.cookies.clear()

    response = unauthenticated_client.post(
        "/api/v1/user-sessions",
        json={"email": "login@example.com", "password": "password123"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "login@example.com"
    assert "uid" in data
    assert "sessionid" in response.cookies


def test_login_failure(unauthenticated_client: TestClient):
    response = unauthenticated_client.post(
        "/api/v1/user-sessions",
        json={"email": "nobody@example.com", "password": "wrongpassword"},
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid credentials"


def test_logout_with_session(client: TestClient):
    response = client.delete("/api/v1/user-sessions/current")
    assert response.status_code == 204

    # Verify cookie is cleared via set-cookie header
    cookie_header = response.headers.get("set-cookie", "")
    assert "sessionid=" in cookie_header
    assert "max-age=0" in cookie_header.lower()


def test_logout_without_session(unauthenticated_client: TestClient):
    response = unauthenticated_client.delete("/api/v1/user-sessions/current")
    assert response.status_code == 204
