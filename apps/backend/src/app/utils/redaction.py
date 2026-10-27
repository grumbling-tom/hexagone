"""Helpers for redacting sensitive values before they reach the logs or a viewer."""

from enum import Enum


def mask_email(email: str) -> str:
    """Mask the local part of an email for safe logging.

    Keeps the domain visible for debugging but obscures the handle, e.g.
    ``thomas@gmail.com`` -> ``t***@gmail.com``. Strings that aren't
    email-shaped (no ``@``) are masked entirely.

    Args:
        email: The raw email address.

    Returns:
        The masked representation safe to log.
    """
    local, sep, domain = email.partition("@")
    if not sep:  # not an email-shaped string — mask entirely
        return "***"
    head = local[0] if local else ""
    return f"{head}***@{domain}"


class Redacted(Enum):
    """A field value the viewer may not see.

    Distinct from ``None``: ``None`` means "there is no value", ``REDACTED``
    means "there is one, and it's none of your business". A one-member enum
    so the marker has its own type (``Redactable[T]`` in ``utils.schemas``)
    rather than being a string a caller could confuse for real data.
    """

    REDACTED = "redacted"


REDACTED = Redacted.REDACTED

# Key in an instance's ``InstanceState.info`` holding the names of fields the
# repository has hidden from the current viewer. See ``BaseModel.__getattribute__``.
HIDDEN_FIELDS_KEY = "hidden_fields"
