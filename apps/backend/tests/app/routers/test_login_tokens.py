"""Tests for the login-tokens (magic-link request) router."""

from typing import Any

import pytest
from fastapi.testclient import TestClient

from src.app.settings import settings


def test_request_link_allowed_sends_email_and_sets_nonce(
    unauthenticated_client: TestClient,
    sent_emails: list[dict[str, Any]],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "ALLOWED_EMAILS", ["allowed@example.com"])

    response = unauthenticated_client.post(
        "/api/v1/login-tokens", json={"email": "allowed@example.com"}
    )

    # 202 with an empty body — no human-facing message (the frontend decides).
    assert response.status_code == 202
    assert response.content == b""
    assert "login_nonce=" in response.headers.get("set-cookie", "")
    assert [e["to"] for e in sent_emails] == ["allowed@example.com"]
    assert "/auth/verify?token=" in sent_emails[0]["html"]


def test_request_link_disallowed_is_enumeration_safe(
    unauthenticated_client: TestClient,
    sent_emails: list[dict[str, Any]],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "ALLOWED_EMAILS", ["allowed@example.com"])

    response = unauthenticated_client.post(
        "/api/v1/login-tokens", json={"email": "intruder@example.com"}
    )

    # Identical 202 + nonce cookie, but no email — indistinguishable from the
    # allowed case.
    assert response.status_code == 202
    assert response.content == b""
    assert "login_nonce=" in response.headers.get("set-cookie", "")
    assert sent_emails == []


def test_request_link_rejects_malformed_email(
    unauthenticated_client: TestClient,
) -> None:
    response = unauthenticated_client.post(
        "/api/v1/login-tokens", json={"email": "not-an-email"}
    )
    assert response.status_code == 422
