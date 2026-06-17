"""Magic-link (passwordless) login tokens.

Issue and verify the single-use, time-limited tokens behind email magic-link
login, plus the email allowlist gate. We persist only the SHA-256 hash of each
secret (the token and its browser-binding nonce) — never the plaintext — so a
database leak cannot be replayed to log in. Tokens expire after
``settings.LOGIN_TOKEN_EXPIRY_MINUTES`` and are single-use.

See ``repository.models.LoginToken`` for the data model and the rationale
behind always-on browser binding (the PKCE-for-magic-links pattern: the token
travels in the email, the nonce in a cookie, and redemption requires both).
"""

import hashlib
import hmac
import secrets
from datetime import UTC, datetime, timedelta

from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session as DBSession

from src.app.repository import EqualsFilter, LoginToken, Repository
from src.app.settings import settings
from src.app.utils import get_logger, mask_email

logger = get_logger(__name__)

# Entropy (in bytes) for the token and nonce. token_urlsafe(32) yields a
# ~43-char, 256-bit secret — brute force is infeasible, so the hash lookup is
# not a practical timing target; we still compare in constant time defensively.
_SECRET_BYTES = 32


class IssuedLoginToken(BaseModel):
    """A freshly issued login token and its browser-binding nonce.

    An internal value object — a plain Pydantic model, deliberately NOT a
    ``BaseSchema`` response schema (services must not return those; see
    ``tests/app/test_service_returns.py``). Frozen because it is a one-shot
    carrier of two plaintext secrets: the caller emails the ``token`` as a link
    and sets the ``nonce`` as an httpOnly cookie. Neither is ever logged.
    """

    model_config = ConfigDict(frozen=True)

    token: str
    nonce: str


def _hash_secret(value: str) -> str:
    """Return the hex SHA-256 digest of a secret (token or nonce)."""
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def is_email_allowed(email: str) -> bool:
    """Return whether *email* may sign in / sign up.

    ``settings.ALLOWED_EMAILS`` is the invite gate. Both the allowlist and the
    incoming address are normalised by ``EmailStr`` at their boundaries (the
    request schema and Settings) — surrounding whitespace stripped, domain
    lower-cased — so this is an exact membership check. An empty allowlist
    denies everyone, the secure default for an invite-only app.

    Note: ``EmailStr`` preserves the case of the local part (before the ``@``),
    so matching is case-sensitive there — consistent with how the rest of the
    app treats ``User.email``.
    """
    return email in settings.ALLOWED_EMAILS


def issue_login_token(db: DBSession, email: str) -> IssuedLoginToken:
    """Issue a single-use magic-link token (and browser nonce) for *email*.

    Supersedes any outstanding token for the same email, so at most one token is
    live per email at a time. Only the SHA-256 hashes are persisted; the
    plaintext secrets are returned to the caller and never stored or logged.

    Args:
        db: Database session.
        email: Target email address, already ``EmailStr``-normalised by the
            request boundary — this service does not re-normalise.

    Returns:
        The plaintext token and nonce, to deliver over the two channels.
    """
    repo = Repository(db, LoginToken)

    # Supersede outstanding tokens for this email — one live token per email.
    existing = repo.get_filtered(
        filters=[EqualsFilter(field="email", value=email)],
        page_size=100,
    )
    for token in existing.items:
        repo.permanent_delete(token)

    plaintext_token = secrets.token_urlsafe(_SECRET_BYTES)
    plaintext_nonce = secrets.token_urlsafe(_SECRET_BYTES)
    expires_at = datetime.now(UTC) + timedelta(
        minutes=settings.LOGIN_TOKEN_EXPIRY_MINUTES
    )

    repo.add(
        LoginToken(
            email=email,
            token_hash=_hash_secret(plaintext_token),
            nonce_hash=_hash_secret(plaintext_nonce),
            expires_at=expires_at,
        )
    )
    db.commit()

    logger.info(
        "login_token_issued",
        email=mask_email(email),
        expires_at=expires_at.isoformat(),
    )
    return IssuedLoginToken(token=plaintext_token, nonce=plaintext_nonce)


def _find_spendable_token(db: DBSession, token: str, nonce: str) -> LoginToken | None:
    """Return the live, unspent ``LoginToken`` for *token* + *nonce*, else None.

    Non-consuming: runs every validity check (token hash match, browser-binding
    nonce, single-use, expiry) but does not stamp ``used_at``. Shared by
    ``verify_login_token`` (which consumes) and ``peek_login_token`` (which
    doesn't).
    """
    token_hash = _hash_secret(token)
    matches = Repository(db, LoginToken).get_filtered(
        filters=[EqualsFilter(field="token_hash", value=token_hash)],
        page_size=1,
    )
    if not matches.items:
        logger.warning("login_token_not_found")
        return None

    login_token = matches.items[0]

    # The DB already matched the token hash; re-compare in constant time (and
    # check the browser-binding nonce the same way). A token scraped from an
    # intercepted email is useless without the nonce from the requester's
    # cookie.
    if not hmac.compare_digest(login_token.token_hash, token_hash):
        return None
    if not hmac.compare_digest(login_token.nonce_hash, _hash_secret(nonce)):
        logger.warning(
            "login_token_nonce_mismatch", email=mask_email(login_token.email)
        )
        return None

    if login_token.used_at is not None:
        logger.warning("login_token_already_used", email=mask_email(login_token.email))
        return None

    now = datetime.now(UTC)
    expires_at = login_token.expires_at
    if expires_at.tzinfo is None:
        now = now.replace(tzinfo=None)
    if now > expires_at:
        logger.warning("login_token_expired", email=mask_email(login_token.email))
        return None

    return login_token


def verify_login_token(db: DBSession, token: str, nonce: str) -> str | None:
    """Consume a magic-link token and return the email it was issued for.

    **POST-only / single-use.** This is the spend step: on success it stamps
    ``used_at`` so the token cannot be replayed (e.g. by an email prefetcher
    that GETs the link). Only invoke it from an explicit POST — use
    ``peek_login_token`` for read-only validity checks.

    Args:
        db: Database session.
        token: Plaintext token from the magic link.
        nonce: Plaintext browser-binding nonce from the requester's cookie.

    Returns:
        The email address (lowercased) if token + nonce are valid, else None.
    """
    login_token = _find_spendable_token(db, token, nonce)
    if login_token is None:
        return None

    login_token.used_at = datetime.now(UTC)
    db.commit()

    logger.info("login_token_verified", email=mask_email(login_token.email))
    return login_token.email


def peek_login_token(db: DBSession, token: str, nonce: str) -> bool:
    """Return whether *token* + *nonce* is currently valid, without consuming it.

    Lets an idempotent GET landing page show "expired/invalid" without spending
    the token, so automated prefetchers (Outlook SafeLinks, security gateways)
    that GET the link can't burn it. The token is only spent by
    ``verify_login_token`` on an explicit POST.
    """
    return _find_spendable_token(db, token, nonce) is not None
