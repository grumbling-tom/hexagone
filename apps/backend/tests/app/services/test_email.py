"""Tests for the email service and client selection."""

from typing import Any

import pytest

from src.app.dependencies import email_client
from src.app.repository import User
from src.app.services.email import (
    ConsoleEmailClient,
    EmailClient,
    ResendEmailClient,
    send_login_link_email,
    send_welcome_email,
)
from src.app.services.email_render import render_login_link, render_welcome
from src.app.services.email_theme import EMAIL_THEME
from src.app.services.password import hash_password
from src.app.settings import settings
from src.scripts.gen_email_theme import (
    THEME_CSS,
    parse_declarations,
    resolve,
)


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


def test_send_login_link_email_composes_message():
    client = _RecordingClient()

    send_login_link_email(client, to_email="rider@example.com", token="tok-123")

    call = client.calls[0]
    assert call["to"] == "rider@example.com"
    assert call["subject"] == "Your Hexagone sign-in link"
    assert "tok-123" in call["html"]


# --- rendering ---------------------------------------------------------------


def test_rendered_emails_use_inlined_brand_tokens():
    # Templates must inline literal token values (mail clients drop CSS custom
    # properties), so the brand blue appears verbatim and no var() leaks out.
    for html in (
        render_welcome(user_email="rider@example.com"),
        render_login_link(verify_url="https://x/auth/verify?token=abc", minutes=15),
    ):
        assert EMAIL_THEME["color-primary-600"] in html  # #2563eb
        assert "var(" not in html
        # The branded shell: the Hexa/gone wordmark split.
        assert ">Hexa</span>" in html
        assert ">gone</span>" in html


def test_welcome_email_links_to_the_map_and_names_the_user():
    html = render_welcome(user_email="rider@example.com")
    assert f"{settings.APP_BASE_URL}/map" in html
    assert "rider@example.com" in html


def test_login_link_email_includes_link_and_expiry():
    html = render_login_link(verify_url="https://x/auth/verify?token=abc", minutes=15)
    assert "https://x/auth/verify?token=abc" in html
    assert "15 minutes" in html


def test_rendering_escapes_interpolated_values():
    # Autoescaping must neutralise markup in the recipient address.
    html = render_welcome(user_email="<script>alert(1)</script>@x.com")
    assert "<script>" not in html
    assert "&lt;script&gt;" in html


def test_email_theme_in_sync_with_theme_css():
    # Drift guard: the committed token module must equal a fresh resolve of
    # theme.css. Regenerate with `uv run python src/scripts/gen_email_theme.py`.
    if not THEME_CSS.exists():
        pytest.skip("theme.css not present (web source not checked out)")
    expected = resolve(parse_declarations(THEME_CSS.read_text(encoding="utf-8")))
    assert expected == EMAIL_THEME


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
