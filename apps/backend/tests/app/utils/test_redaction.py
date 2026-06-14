"""Tests for the redaction helpers."""

from src.app.utils import mask_email


def test_mask_email_keeps_first_char_and_domain():
    assert mask_email("user@gmail.com") == "u***@gmail.com"


def test_mask_email_empty_local_part():
    assert mask_email("@gmail.com") == "***@gmail.com"


def test_mask_email_non_email_masked_entirely():
    assert mask_email("not-an-email") == "***"
