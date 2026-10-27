"""Tests for the user session service."""

import time
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
from sqlalchemy.orm import Session

from src.app.repository import (
    ScopedRepository,
    SystemPolicy,
    UnitOfWork,
    User,
    UserSession,
)
from src.app.services.password import hash_password
from src.app.services.user_session import (
    create_session,
    hash_user_agent,
    invalidate_session,
    validate_session,
)


def _make_user(db: Session, email: str = "session@example.com") -> User:
    user = User(
        email=email,
        password_hash=hash_password("password123"),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def sessions(
    system_repo: Callable[[type[Any]], ScopedRepository[Any]],
) -> ScopedRepository[UserSession]:
    return system_repo(UserSession)


def test_hash_user_agent_consistency():
    h1 = hash_user_agent("Mozilla/5.0")
    h2 = hash_user_agent("Mozilla/5.0")
    assert h1 == h2
    assert len(h1) == 64


def test_create_session(
    test_db: Session, sessions: ScopedRepository[UserSession], uow: UnitOfWork
):
    user = _make_user(test_db)
    session = create_session(sessions, uow, user.uid, "TestAgent", "127.0.0.1")
    assert session.user_uid == user.uid
    assert session.ip_address == "127.0.0.1"
    assert session.user_agent_hash == hash_user_agent("TestAgent")
    assert session.uid is not None


def test_validate_session_success(
    test_db: Session, sessions: ScopedRepository[UserSession], uow: UnitOfWork
):
    user = _make_user(test_db)
    session = create_session(sessions, uow, user.uid, "TestAgent", "127.0.0.1")
    result = validate_session(sessions, uow, session.uid, "TestAgent")
    assert result is not None
    assert result.uid == session.uid


def test_validate_session_expired(
    test_db: Session, sessions: ScopedRepository[UserSession], uow: UnitOfWork
):
    user = _make_user(test_db)
    session = create_session(sessions, uow, user.uid, "TestAgent", "127.0.0.1")

    sessions.update(
        session.uid,
        {"expires_at": datetime.now(UTC).replace(tzinfo=None) - timedelta(hours=1)},
    )
    uow.commit()

    result = validate_session(sessions, uow, session.uid, "TestAgent")
    assert result is None


def test_validate_session_ua_mismatch(
    test_db: Session, sessions: ScopedRepository[UserSession], uow: UnitOfWork
):
    user = _make_user(test_db)
    session = create_session(sessions, uow, user.uid, "TestAgent", "127.0.0.1")
    result = validate_session(sessions, uow, session.uid, "DifferentAgent")
    assert result is None


def test_validate_session_ignores_ip_change(
    test_db: Session, sessions: ScopedRepository[UserSession], uow: UnitOfWork
):
    """A changed client IP must NOT invalidate the session — mobile and VPN
    clients legitimately roam across IPs mid-session."""
    user = _make_user(test_db, email="iproam@example.com")
    session = create_session(sessions, uow, user.uid, "TestAgent", "127.0.0.1")

    # Same cookie + user agent, different IP: still valid, still alive.
    result = validate_session(sessions, uow, session.uid, "TestAgent")
    assert result is not None
    assert result.uid == session.uid

    assert sessions.find_by_uid(session.uid) is not None


def test_validate_session_archived_user(
    test_db: Session, sessions: ScopedRepository[UserSession], uow: UnitOfWork
):
    user = _make_user(test_db, email="archived_sess@example.com")
    session = create_session(sessions, uow, user.uid, "TestAgent", "127.0.0.1")

    ScopedRepository(test_db, User, SystemPolicy()).update(user.uid, {"archived": True})
    uow.commit()

    result = validate_session(sessions, uow, session.uid, "TestAgent")
    assert result is None


def test_hard_delete_on_mismatch(
    test_db: Session, sessions: ScopedRepository[UserSession], uow: UnitOfWork
):
    user = _make_user(test_db, email="harddelete@example.com")
    session = create_session(sessions, uow, user.uid, "TestAgent", "127.0.0.1")
    session_uid = session.uid

    validate_session(sessions, uow, session_uid, "DifferentAgent")

    assert sessions.find_by_uid(session_uid) is None


def test_sliding_window_refresh(
    test_db: Session, sessions: ScopedRepository[UserSession], uow: UnitOfWork
):
    user = _make_user(test_db, email="refresh@example.com")
    session = create_session(sessions, uow, user.uid, "TestAgent", "127.0.0.1")
    original_expires = session.expires_at

    time.sleep(0.01)

    validate_session(sessions, uow, session.uid, "TestAgent")
    test_db.refresh(session)
    assert session.expires_at >= original_expires


def test_invalidate_session(
    test_db: Session, sessions: ScopedRepository[UserSession], uow: UnitOfWork
):
    user = _make_user(test_db, email="invalidate@example.com")
    session = create_session(sessions, uow, user.uid, "TestAgent", "127.0.0.1")
    session_uid = session.uid

    invalidate_session(sessions, uow, session)

    assert sessions.find_by_uid(session_uid) is None
