"""Tests for the users router."""

from fastapi.testclient import TestClient


def test_signup_success(unauthenticated_client: TestClient):
    response = unauthenticated_client.post(
        "/api/v1/users",
        json={"email": "signup@example.com", "password": "newpassword123"},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "signup@example.com"
    assert "uid" in data
    assert "sessionid" in response.cookies


def test_signup_duplicate_email(unauthenticated_client: TestClient):
    unauthenticated_client.post(
        "/api/v1/users",
        json={"email": "dupe@example.com", "password": "password123"},
    )
    response = unauthenticated_client.post(
        "/api/v1/users",
        json={"email": "dupe@example.com", "password": "password456"},
    )
    assert response.status_code == 409
    assert response.json()["detail"] == "Email already taken"


def test_get_current_user_authenticated(client: TestClient):
    response = client.get("/api/v1/users/me")
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "test@example.com"
    assert "uid" in data


def test_get_current_user_unauthenticated(unauthenticated_client: TestClient):
    response = unauthenticated_client.get("/api/v1/users/me")
    assert response.status_code == 401
