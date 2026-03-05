"""User session service for session-based authentication."""

import hashlib
from datetime import UTC, datetime, timedelta

from sqlalchemy.orm import Session as DBSession

from src.app.repository import Repository, UserSession
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
    db: DBSession, user_uid: str, user_agent: str, ip_address: str
) -> UserSession:
    """Create a new session bound to a user, user agent, and IP address.

    Args:
        db: Database session.
        user_uid: UID of the user who owns this session.
        user_agent: User agent string from request.
        ip_address: Client IP address.

    Returns:
        Newly created UserSession with sliding-window expiration.
    """
    session_repo = Repository(db, UserSession)

    now = datetime.now(UTC)
    expires_at = now + timedelta(hours=settings.SESSION_EXPIRY_HOURS)

    session = UserSession(
        user_uid=user_uid,
        user_agent_hash=hash_user_agent(user_agent),
        ip_address=ip_address,
        expires_at=expires_at,
    )

    session_repo.add(session)
    db.commit()
    db.refresh(session)

    logger.info(
        "session_created",
        session_id=session.uid,
        ip_address=ip_address,
        expires_at=expires_at.isoformat(),
    )

    return session


def validate_session(
    db: DBSession,
    session_id: str,
    user_agent: str,
    ip_address: str,
) -> UserSession | None:
    """Validate session ID and fingerprint.

    Args:
        db: Database session.
        session_id: Session UID from cookie.
        user_agent: Current user agent string.
        ip_address: Current client IP address.

    Returns:
        Valid UserSession if all checks pass, None otherwise.

    Checks performed:
        - Session exists
        - User account not archived
        - Session not expired
        - User agent matches
        - IP address matches
    """
    session_repo = Repository(db, UserSession)
    session = session_repo.find_by_uid(session_id)

    if not session:
        logger.warning("session_not_found", session_id=session_id)
        return None

    if session.user.archived:
        logger.warning(
            "session_user_archived",
            session_id=session_id,
            user_uid=session.user_uid,
        )
        invalidate_session(db, session)
        return None

    now = datetime.now(UTC)
    expires_at = session.expires_at
    if expires_at.tzinfo is None:
        now = now.replace(tzinfo=None)

    if now > expires_at:
        logger.warning("session_expired", session_id=session_id)
        invalidate_session(db, session)
        return None

    if session.user_agent_hash != hash_user_agent(user_agent):
        logger.warning(
            "session_user_agent_mismatch",
            session_id=session_id,
            ip_address=ip_address,
        )
        invalidate_session(db, session)
        return None

    if session.ip_address != ip_address:
        logger.warning(
            "session_ip_mismatch",
            session_id=session_id,
            expected_ip=session.ip_address,
            actual_ip=ip_address,
        )
        invalidate_session(db, session)
        return None

    refresh_session(db, session)
    return session


def refresh_session(db: DBSession, session: UserSession) -> None:
    """Refresh session expiration (sliding window).

    Args:
        db: Database session.
        session: Session object to refresh.
    """
    now = datetime.now(UTC)
    if session.expires_at.tzinfo is None:
        now = now.replace(tzinfo=None)

    session.expires_at = now + timedelta(hours=settings.SESSION_EXPIRY_HOURS)
    db.commit()


def invalidate_session(db: DBSession, session: UserSession) -> None:
    """Invalidate a session by permanently deleting it.

    Args:
        db: Database session.
        session: UserSession object to invalidate.
    """
    session_repo = Repository(db, UserSession)
    session_id = session.uid

    session_repo.permanent_delete(session)
    db.commit()

    logger.info("session_invalidated", session_id=session_id)
