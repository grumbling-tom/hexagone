"""Helpers for redacting sensitive values before they reach the logs."""


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
