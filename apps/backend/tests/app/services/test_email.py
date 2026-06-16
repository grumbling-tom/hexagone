"""Tests for the email service and client selection."""

from typing import Any

import pytest

from src.app.dependencies import email_client
from src.app.repository import User
from src.app.services.email import (
    ConsoleEmailClient,
    EmailClient,
    ResendEmailClient,
    send_welcome_email,
)
from src.app.services.password import hash_password
from src.app.settings import settings


class _RecordingClient(EmailClient):
    """Email client that captures the last send call."""

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
        self.calls.append(
            {
                "to": to,
                "subject": subject,
                "html": html,
                "log_context": log_context,
            }
        )
        return "recorded"


def test_send_welcome_email_composes_message():
    client = _RecordingClient()
    user = User(email="welcome@example.com", password_hash=hash_password("pw"))

    message_id = send_welcome_email(client, user=user)

    assert message_id == "recorded"
    assert len(client.calls) == 1
    call = client.calls[0]
    assert call["to"] == "welcome@example.com"
    assert call["subject"] == "Welcome to Hexagone"
    assert settings.APP_BASE_URL in call["html"]
    assert call["log_context"] == {"user_uid": str(user.uid)}


@pytest.mark.parametrize("env", ["DEV", "TEST"])
def test_email_client_uses_console_in_dev_and_test(
    env: str, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setattr(settings, "ENV", env)
    assert isinstance(email_client(), ConsoleEmailClient)


@pytest.mark.parametrize("env", ["PROD", "STAGING"])
def test_email_client_uses_resend_in_prod_and_staging(
    env: str, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setattr(settings, "ENV", env)
    monkeypatch.setattr(settings, "RESEND_API_KEY", "test-key")
    assert isinstance(email_client(), ResendEmailClient)
