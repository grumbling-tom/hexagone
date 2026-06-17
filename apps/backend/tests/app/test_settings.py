"""Tests for application settings validation."""

import pytest
from pydantic import ValidationError

from src.app.settings import Settings


def test_allowed_emails_accepts_valid_addresses() -> None:
    settings = Settings(ENV="TEST", ALLOWED_EMAILS=["a@example.com", "b@example.com"])
    assert [str(e) for e in settings.ALLOWED_EMAILS] == [
        "a@example.com",
        "b@example.com",
    ]


def test_allowed_emails_rejects_malformed_address() -> None:
    # A bad allowlist entry must fail Settings validation at boot, so the app
    # refuses to start rather than silently admitting a junk invite entry.
    with pytest.raises(ValidationError):
        Settings(ENV="TEST", ALLOWED_EMAILS=["not-an-email"])
