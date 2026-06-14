"""Email client abstraction for transactional email."""

from abc import ABC, abstractmethod
from typing import Any

import resend

from src.app.repository.models import User
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
        logger.info("resend_email_sending", to=mask_email(to), subject=subject, **ctx)
        email = resend.Emails.send(params)
        message_id = email["id"]
        logger.info(
            "resend_email_sent",
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
        html: str,  # noqa: ARG002 — body intentionally not logged (embeds PII)
        log_context: dict[str, Any] | None = None,
    ) -> str:
        """Log the email instead of sending it; returns a sentinel id."""
        ctx = log_context or {}
        # Dev/test sink: masks the recipient and omits the html body (which
        # embeds the address) to keep the same no-plaintext-PII guarantee.
        logger.info("email_console", to=mask_email(to), subject=subject, **ctx)
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
    html = (
        f"<h1>Welcome!</h1>"
        f"<p>Your account ({user.email}) is ready. "
        f'<a href="{settings.APP_BASE_URL}/map">Open the map</a>.</p>'
    )
    return email.send(
        to=user.email,
        subject=subject,
        html=html,
        log_context={"user_uid": str(user.uid)},
    )
