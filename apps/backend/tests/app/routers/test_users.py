"""Tests for the users router."""

from collections.abc import Callable
from typing import Any

import pytest
from fastapi.testclient import TestClient

from src.app.repository import User, UserGroup


def test_signup_success(
    unauthenticated_client: TestClient, sent_emails: list[dict[str, Any]]
):
    response = unauthenticated_client.post(
        "/api/v1/users",
        json={"email": "signup@example.com", "password": "newpassword123"},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "signup@example.com"
    assert "uid" in data
    assert "sessionid" in response.cookies

    # A welcome email was sent to the new account.
    assert [e["to"] for e in sent_emails] == ["signup@example.com"]


def test_signup_succeeds_when_email_send_fails(
    unauthenticated_client: TestClient, monkeypatch: pytest.MonkeyPatch
):
    def _boom(*_args: Any, **_kwargs: Any) -> str:
        msg = "email provider down"
        raise RuntimeError(msg)

    # Patch the send helper used by the router so the best-effort guard fires.
    monkeypatch.setattr("src.app.routers.users.send_welcome_email", _boom)

    response = unauthenticated_client.post(
        "/api/v1/users",
        json={"email": "resilient@example.com", "password": "newpassword123"},
    )
    assert response.status_code == 201
    assert response.json()["email"] == "resilient@example.com"


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
    response = client.get("/api/v1/users/current")
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "test@example.com"
    assert "uid" in data


def test_get_current_user_unauthenticated(unauthenticated_client: TestClient):
    response = unauthenticated_client.get("/api/v1/users/current")
    assert response.status_code == 401


def test_list_users_by_group_returns_members(
    client: TestClient,
    test_user: User,
    create_user: Callable[..., User],
    create_group: Callable[..., UserGroup],
    create_membership: Callable[..., None],
):
    other = create_user(email="other@example.com")
    group = create_group(name="Two-up")
    create_membership(group=group, user=other)

    response = client.get(f"/api/v1/users?group_uid={group.uid}")
    assert response.status_code == 200

    items = response.json()["items"]
    assert {u["email"] for u in items} == {
        "test@example.com",
        "other@example.com",
    }
    # Plain UserResponse shape — no membership fields leak in.
    assert set(items[0].keys()) == {"uid", "email"}


def test_list_users_by_group_unauthenticated_returns_401(
    unauthenticated_client: TestClient,
):
    response = unauthenticated_client.get(
        "/api/v1/users?group_uid=00000000-0000-0000-0000-000000000000"
    )
    assert response.status_code == 401


def test_list_users_by_group_missing_group_uid_returns_422(client: TestClient):
    assert client.get("/api/v1/users").status_code == 422


def test_list_users_by_group_for_non_member_returns_404(
    client: TestClient,
    create_user: Callable[..., User],
    create_group: Callable[..., UserGroup],
):
    other = create_user()
    group = create_group(name="Theirs", owner=other)

    response = client.get(f"/api/v1/users?group_uid={group.uid}")
    assert response.status_code == 404
