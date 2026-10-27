"""Tests for the user sessions router."""

from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from src.app.repository import LoginToken, ScopedRepository, Transaction, User
from src.app.services.login_token import issue_login_token
from src.app.services.user import create_user
from src.app.settings import settings


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
    assert response.status_code == 401


# --- magic-link (token) sign-in ------------------------------------------------


def _post_token(client: TestClient, token: str, nonce: str | None) -> Any:
    if nonce is not None:
        client.cookies.set(settings.LOGIN_NONCE_COOKIE_NAME, nonce)
    return client.post("/api/v1/user-sessions", json={"token": token})


def test_verify_token_creates_new_user_and_session(
    unauthenticated_client: TestClient,
    test_db: Session,
    sent_emails: list[dict[str, Any]],
    monkeypatch: pytest.MonkeyPatch,
    login_tokens: ScopedRepository[LoginToken],
    tx: Transaction,
):
    monkeypatch.setattr(settings, "ALLOWED_EMAILS", ["newbie@example.com"])
    issued = issue_login_token(login_tokens, tx, "newbie@example.com")

    response = _post_token(unauthenticated_client, issued.token, issued.nonce)

    assert response.status_code == 200
    assert response.json()["email"] == "newbie@example.com"
    assert "sessionid" in response.cookies
    # First-time creation sends the welcome email.
    assert [e["to"] for e in sent_emails] == ["newbie@example.com"]


def test_verify_token_for_existing_user_makes_no_second_account(
    unauthenticated_client: TestClient,
    test_db: Session,
    monkeypatch: pytest.MonkeyPatch,
    login_tokens: ScopedRepository[LoginToken],
    tx: Transaction,
    system_users: ScopedRepository[User],
):
    monkeypatch.setattr(settings, "ALLOWED_EMAILS", ["existing@example.com"])
    create_user(system_users, tx, "existing@example.com", "placeholder-pw-123")
    issued = issue_login_token(login_tokens, tx, "existing@example.com")

    response = _post_token(unauthenticated_client, issued.token, issued.nonce)

    assert response.status_code == 200
    assert len(system_users.get_all().items) == 1


def test_verify_invalid_token_is_rejected(
    unauthenticated_client: TestClient,
    test_db: Session,
    monkeypatch: pytest.MonkeyPatch,
    login_tokens: ScopedRepository[LoginToken],
    tx: Transaction,
):
    monkeypatch.setattr(settings, "ALLOWED_EMAILS", ["x@example.com"])
    issued = issue_login_token(login_tokens, tx, "x@example.com")

    response = _post_token(unauthenticated_client, "not-a-real-token", issued.nonce)
    assert response.status_code == 401


def test_verify_rejects_wrong_or_missing_nonce(
    unauthenticated_client: TestClient,
    test_db: Session,
    monkeypatch: pytest.MonkeyPatch,
    login_tokens: ScopedRepository[LoginToken],
    tx: Transaction,
):
    monkeypatch.setattr(settings, "ALLOWED_EMAILS", ["x@example.com"])
    issued = issue_login_token(login_tokens, tx, "x@example.com")

    wrong = _post_token(unauthenticated_client, issued.token, "wrong-nonce")
    assert wrong.status_code == 401

    unauthenticated_client.cookies.clear()
    missing = _post_token(unauthenticated_client, issued.token, None)
    assert missing.status_code == 401


def test_verify_token_is_single_use(
    unauthenticated_client: TestClient,
    test_db: Session,
    monkeypatch: pytest.MonkeyPatch,
    login_tokens: ScopedRepository[LoginToken],
    tx: Transaction,
):
    monkeypatch.setattr(settings, "ALLOWED_EMAILS", ["x@example.com"])
    issued = issue_login_token(login_tokens, tx, "x@example.com")

    first = _post_token(unauthenticated_client, issued.token, issued.nonce)
    assert first.status_code == 200
    second = _post_token(unauthenticated_client, issued.token, issued.nonce)
    assert second.status_code == 401


def test_verify_rejected_when_email_removed_from_allowlist(
    unauthenticated_client: TestClient,
    test_db: Session,
    monkeypatch: pytest.MonkeyPatch,
    login_tokens: ScopedRepository[LoginToken],
    tx: Transaction,
):
    monkeypatch.setattr(settings, "ALLOWED_EMAILS", ["x@example.com"])
    issued = issue_login_token(login_tokens, tx, "x@example.com")
    monkeypatch.setattr(settings, "ALLOWED_EMAILS", [])  # de-invited before verify

    response = _post_token(unauthenticated_client, issued.token, issued.nonce)
    assert response.status_code == 401


def test_create_session_requires_exactly_one_credential_mode(
    unauthenticated_client: TestClient,
):
    neither = unauthenticated_client.post("/api/v1/user-sessions", json={})
    assert neither.status_code == 422

    both = unauthenticated_client.post(
        "/api/v1/user-sessions",
        json={"email": "a@example.com", "password": "p", "token": "t"},
    )
    assert both.status_code == 422
