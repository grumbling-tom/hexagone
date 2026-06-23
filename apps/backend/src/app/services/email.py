"""Email client abstraction for transactional email."""

from abc import ABC, abstractmethod
from typing import Any
from urllib.parse import quote_plus

import resend

from src.app.repository.models import User
from src.app.services.email_render import render_login_link, render_welcome
from src.app.settings import settings
from src.app.utils import get_logger, mask_email

logger = get_logger(__name__)


class EmailClient(ABC):
    """Abstract transactional-email client."""

    @abstractmethod
    def send(
        self,
        *,
        to: str,
        subject: str,
        html: str,
        log_context: dict[str, Any] | None = None,
    ) -> str:
        """Send an email and return the provider message id.

        Args:
            to: Recipient email address.
            subject: Email subject line.
            html: HTML body of the email.
            log_context: Non-PII identifiers (e.g. ``user_uid``) attached to the
                surrounding log lines. The recipient is always masked in logs.

        Returns:
            The provider message id.
        """


class ResendEmailClient(EmailClient):
    """Resend-backed email client using the official SDK."""

    def __init__(self) -> None:
        resend.api_key = settings.RESEND_API_KEY

    def send(
        self,
        *,
        to: str,
        subject: str,
        html: str,
        log_context: dict[str, Any] | None = None,
    ) -> str:
        """Send an email via Resend and return the provider message id."""
        params: resend.Emails.SendParams = {
            "from": settings.RESEND_FROM_EMAIL,
            "to": [to],
            "subject": subject,
            "html": html,
        }
        ctx = log_context or {}
        # Log around the external Resend call (see "Logging Around External
        # Service Calls" in apps/backend/CLAUDE.md). Recipient is masked; never
        # log the raw email or the html body (it embeds the address).
        logger.info("send_email_pending", to=mask_email(to), subject=subject, **ctx)
        email = resend.Emails.send(params)
        message_id = email["id"]
        logger.info(
            "send_email_success",
            to=mask_email(to),
            subject=subject,
            message_id=message_id,
            **ctx,
        )
        return message_id


class ConsoleEmailClient(EmailClient):
    """Logs emails instead of sending — used in DEV/TEST."""

    def send(
        self,
        *,
        to: str,
        subject: str,
        html: str,
        log_context: dict[str, Any] | None = None,
    ) -> str:
        """Log the email instead of sending it; returns a sentinel id."""
        ctx = log_context or {}
        # Dev/test sink: masks the recipient and omits the html body (which
        # embeds the address) to keep the same no-plaintext-PII guarantee.
        logger.info("send_email_console", to=mask_email(to), subject=subject, **ctx)
        logger.info("send_email_console_body", body=html, **ctx)
        return "console"


def send_welcome_email(email: EmailClient, *, user: User) -> str:
    """Send the post-signup welcome email.

    Args:
        email: The injected email client.
        user: The newly created user.

    Returns:
        The provider message id.
    """
    subject = "Welcome to Hexagone"
    html = render_welcome(user_email=user.email)
    return email.send(
        to=user.email,
        subject=subject,
        html=html,
        log_context={"user_uid": str(user.uid)},
    )


def send_login_link_email(email: EmailClient, *, to_email: str, token: str) -> str:
    """Send the magic-link sign-in email.

    Builds the sign-in link to ``${APP_BASE_URL}/auth/verify?token=...``. The
    recipient is masked by ``EmailClient.send`` and the html body (which embeds
    both the address and the token) is never logged — so the plaintext token
    stays out of the logs.

    Args:
        email: The injected email client.
        to_email: Recipient address — the link's destination.
        token: Plaintext login token to embed in the link.

    Returns:
        The provider message id.
    """
    verify_url = f"{settings.APP_BASE_URL}/auth/verify?token={quote_plus(token)}"
    minutes = settings.LOGIN_TOKEN_EXPIRY_MINUTES
    subject = "Your Hexagone sign-in link"
    html = render_login_link(verify_url=verify_url, minutes=minutes)
    return email.send(to=to_email, subject=subject, html=html)
