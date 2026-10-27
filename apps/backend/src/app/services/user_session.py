"""User session service for session-based authentication."""

import hashlib
from datetime import UTC, datetime, timedelta

from src.app.repository import ScopedRepository, Transaction, UserSession
from src.app.settings import settings
from src.app.utils import get_logger

logger = get_logger(__name__)


def hash_user_agent(user_agent: str) -> str:
    """Hash user agent string with SHA-256.

    Args:
        user_agent: Raw user agent string from request headers.

    Returns:
        Hexadecimal SHA-256 hash of the user agent.
    """
    return hashlib.sha256(user_agent.encode()).hexdigest()


def create_session(
    sessions: ScopedRepository[UserSession],
    tx: Transaction,
    user_uid: str,
    user_agent: str,
    ip_address: str,
) -> UserSession:
    """Create a new session bound to a user, user agent, and IP address.

    Args:
        sessions: UserSession repository (system-scoped: there's no viewer yet).
        tx: Transaction boundary.
        user_uid: UID of the user who owns this session.
        user_agent: User agent string from request.
        ip_address: Client IP address.

    Returns:
        Newly created UserSession with sliding-window expiration.
    """
    now = datetime.now(UTC)
    expires_at = now + timedelta(hours=settings.SESSION_EXPIRY_HOURS)

    session = UserSession(
        user_uid=user_uid,
        user_agent_hash=hash_user_agent(user_agent),
        ip_address=ip_address,
        expires_at=expires_at,
    )

    sessions.create(session)
    tx.commit()

    logger.info(
        "session_created",
        session_id=session.uid,
        ip_address=ip_address,
        expires_at=expires_at.isoformat(),
    )

    return session


def validate_session(
    sessions: ScopedRepository[UserSession],
    tx: Transaction,
    session_id: str,
    user_agent: str,
) -> UserSession | None:
    """Validate session ID and fingerprint.

    Args:
        sessions: UserSession repository (system-scoped).
        tx: Transaction boundary.
        session_id: Session UID from cookie.
        user_agent: Current user agent string.

    Returns:
        Valid UserSession if all checks pass, None otherwise.

    Checks performed:
        - Session exists
        - User account not archived
        - Session not expired
        - User agent matches

    Note:
        The session's origin IP is recorded at creation for audit, but is
        deliberately *not* part of the fingerprint: client IPs legitimately
        change mid-session (mobile networks roaming between Wi-Fi and
        cellular, carrier-grade NAT, VPNs), and binding to the IP forced a
        re-login on every change. Validation relies on the opaque, httpOnly
        session cookie plus the user-agent hash instead.
    """
    session = sessions.find_by_uid(session_id)

    if not session:
        logger.warning("session_not_found", session_id=session_id)
        return None

    if session.user.archived:
        logger.warning(
            "session_user_archived",
            session_id=session_id,
            user_uid=session.user_uid,
        )
        invalidate_session(sessions, tx, session)
        return None

    now = datetime.now(UTC)
    expires_at = session.expires_at
    if expires_at.tzinfo is None:
        now = now.replace(tzinfo=None)

    if now > expires_at:
        logger.warning("session_expired", session_id=session_id)
        invalidate_session(sessions, tx, session)
        return None

    if session.user_agent_hash != hash_user_agent(user_agent):
        logger.warning(
            "session_user_agent_mismatch",
            session_id=session_id,
        )
        invalidate_session(sessions, tx, session)
        return None

    return refresh_session(sessions, tx, session)


def refresh_session(
    sessions: ScopedRepository[UserSession], tx: Transaction, session: UserSession
) -> UserSession:
    """Refresh session expiration (sliding window).

    Args:
        sessions: UserSession repository (system-scoped).
        tx: Transaction boundary.
        session: Session object to refresh.

    Returns:
        The refreshed session.
    """
    now = datetime.now(UTC)
    if session.expires_at.tzinfo is None:
        now = now.replace(tzinfo=None)

    refreshed = sessions.update(
        session.uid,
        {"expires_at": now + timedelta(hours=settings.SESSION_EXPIRY_HOURS)},
    )
    tx.commit()
    return refreshed


def invalidate_session(
    sessions: ScopedRepository[UserSession], tx: Transaction, session: UserSession
) -> None:
    """Invalidate a session by permanently deleting it.

    Args:
        sessions: UserSession repository (system-scoped).
        tx: Transaction boundary.
        session: UserSession object to invalidate.
    """
    session_id = session.uid

    sessions.delete(session_id)
    tx.commit()

    logger.info("session_invalidated", session_id=session_id)
