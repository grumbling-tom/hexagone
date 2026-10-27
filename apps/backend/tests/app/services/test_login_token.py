"""Tests for the magic-link login-token domain (issue / verify / peek / allowlist)."""

import hashlib
from typing import Any

import pytest
from sqlalchemy.orm import Session

from src.app.repository import LoginToken, ScopedRepository, UnitOfWork
from src.app.services.email import EmailClient, send_login_link_email
from src.app.services.login_token import (
    is_email_allowed,
    issue_login_token,
    peek_login_token,
    verify_login_token,
)
from src.app.settings import settings


@pytest.fixture(autouse=True)
def _allowlist(monkeypatch: pytest.MonkeyPatch) -> None:  # pyright: ignore[reportUnusedFunction]
    """Default allowlist + token lifetime for tests (overridable per test)."""
    monkeypatch.setattr(settings, "ALLOWED_EMAILS", ["allowed@example.com"])
    monkeypatch.setattr(settings, "LOGIN_TOKEN_EXPIRY_MINUTES", 10)


def _sha256(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


# --- issue / verify happy path -------------------------------------------------


def test_issue_then_verify_returns_email(
    test_db: Session,
    login_tokens: ScopedRepository[LoginToken],
    uow: UnitOfWork,
) -> None:
    issued = issue_login_token(login_tokens, uow, "user@example.com")

    assert (
        verify_login_token(login_tokens, uow, issued.token, issued.nonce)
        == "user@example.com"
    )


def test_only_hashes_are_persisted_not_plaintext(
    test_db: Session,
    login_tokens: ScopedRepository[LoginToken],
    uow: UnitOfWork,
) -> None:
    issued = issue_login_token(login_tokens, uow, "user@example.com")

    row = login_tokens.get_all().items[0]
    assert row.token_hash == _sha256(issued.token)
    assert row.nonce_hash == _sha256(issued.nonce)
    assert issued.token not in (row.token_hash, row.nonce_hash)
    assert issued.nonce not in (row.token_hash, row.nonce_hash)


# --- single-use ----------------------------------------------------------------


def test_token_cannot_be_reused(
    test_db: Session,
    login_tokens: ScopedRepository[LoginToken],
    uow: UnitOfWork,
) -> None:
    issued = issue_login_token(login_tokens, uow, "user@example.com")

    assert (
        verify_login_token(login_tokens, uow, issued.token, issued.nonce)
        == "user@example.com"
    )
    assert verify_login_token(login_tokens, uow, issued.token, issued.nonce) is None


# --- unknown / superseded ------------------------------------------------------


def test_unknown_token_is_rejected(
    test_db: Session,
    login_tokens: ScopedRepository[LoginToken],
    uow: UnitOfWork,
) -> None:
    issued = issue_login_token(login_tokens, uow, "user@example.com")

    assert (
        verify_login_token(login_tokens, uow, "not-a-real-token", issued.nonce) is None
    )


def test_issuing_again_revokes_the_previous_token(
    test_db: Session,
    login_tokens: ScopedRepository[LoginToken],
    uow: UnitOfWork,
) -> None:
    first = issue_login_token(login_tokens, uow, "user@example.com")
    second = issue_login_token(login_tokens, uow, "user@example.com")

    rows = login_tokens.get_all().items
    # Soft-revoke keeps the old row for audit; exactly one stays live.
    assert len(rows) == 2
    assert sum(1 for r in rows if r.revoked_at is None) == 1

    # The revoked token is rejected; the live one works.
    assert verify_login_token(login_tokens, uow, first.token, first.nonce) is None
    assert (
        verify_login_token(login_tokens, uow, second.token, second.nonce)
        == "user@example.com"
    )


# --- expiry --------------------------------------------------------------------


def test_expired_token_is_rejected(
    test_db: Session,
    monkeypatch: pytest.MonkeyPatch,
    login_tokens: ScopedRepository[LoginToken],
    uow: UnitOfWork,
) -> None:
    monkeypatch.setattr(settings, "LOGIN_TOKEN_EXPIRY_MINUTES", -1)
    issued = issue_login_token(login_tokens, uow, "user@example.com")

    assert verify_login_token(login_tokens, uow, issued.token, issued.nonce) is None


# --- browser-binding nonce -----------------------------------------------------


def test_wrong_nonce_is_rejected(
    test_db: Session,
    login_tokens: ScopedRepository[LoginToken],
    uow: UnitOfWork,
) -> None:
    issued = issue_login_token(login_tokens, uow, "user@example.com")

    assert verify_login_token(login_tokens, uow, issued.token, "wrong-nonce") is None
    # The token is untouched by a failed attempt and still spendable.
    assert (
        verify_login_token(login_tokens, uow, issued.token, issued.nonce)
        == "user@example.com"
    )


def test_each_token_gets_a_distinct_nonce(
    test_db: Session,
    login_tokens: ScopedRepository[LoginToken],
    uow: UnitOfWork,
) -> None:
    a = issue_login_token(login_tokens, uow, "a@example.com")
    b = issue_login_token(login_tokens, uow, "b@example.com")

    assert a.nonce != b.nonce
    assert a.token != b.token


# --- peek (non-consuming) ------------------------------------------------------


def test_peek_does_not_consume_the_token(
    test_db: Session,
    login_tokens: ScopedRepository[LoginToken],
    uow: UnitOfWork,
) -> None:
    issued = issue_login_token(login_tokens, uow, "user@example.com")

    assert peek_login_token(login_tokens, issued.token, issued.nonce) is True
    # Peeking left it spendable.
    assert (
        verify_login_token(login_tokens, uow, issued.token, issued.nonce)
        == "user@example.com"
    )
    # Once consumed, peek reports invalid.
    assert peek_login_token(login_tokens, issued.token, issued.nonce) is False


def test_peek_rejects_wrong_nonce(
    test_db: Session,
    login_tokens: ScopedRepository[LoginToken],
    uow: UnitOfWork,
) -> None:
    issued = issue_login_token(login_tokens, uow, "user@example.com")

    assert peek_login_token(login_tokens, issued.token, "wrong-nonce") is False


# --- allowlist -----------------------------------------------------------------


def test_allowlist_allows_listed_email() -> None:
    assert is_email_allowed("allowed@example.com") is True


def test_allowlist_denies_unlisted_email() -> None:
    assert is_email_allowed("intruder@example.com") is False


def test_empty_allowlist_denies_everyone(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "ALLOWED_EMAILS", [])
    assert is_email_allowed("allowed@example.com") is False


# --- email template ------------------------------------------------------------


class _CapturingEmailClient(EmailClient):
    """Captures the last send() call for assertions."""

    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    def send(
        self,
        *,
        to: str,
        subject: str,
        html: str,
        log_context: dict[str, Any] | None = None,
    ) -> str:
        self.calls.append({"to": to, "subject": subject, "html": html})
        return "captured"


def test_login_link_email_embeds_the_token_and_verify_url(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "APP_BASE_URL", "https://hexagone.test")
    client = _CapturingEmailClient()

    send_login_link_email(client, to_email="user@example.com", token="tok-123")

    sent = client.calls[0]
    assert sent["to"] == "user@example.com"
    assert "https://hexagone.test/auth/verify?token=tok-123" in sent["html"]
