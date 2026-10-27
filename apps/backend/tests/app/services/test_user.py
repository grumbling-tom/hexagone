"""Tests for the user service."""

from unittest.mock import MagicMock

import pytest
from sqlalchemy.orm import Session

from src.app.repository import ScopedRepository, Transaction, User
from src.app.services.password import hash_password
from src.app.services.user import (
    DuplicateEmailError,
    authenticate_user,
    create_user,
    get_user_by_email,
)


def test_authenticate_user_success(
    test_db: Session,
    system_users: ScopedRepository[User],
):
    user = User(
        email="auth@example.com",
        password_hash=hash_password("password123"),
    )
    test_db.add(user)
    test_db.commit()

    result = authenticate_user(system_users, "auth@example.com", "password123")
    assert result is not None
    assert result.email == "auth@example.com"


def test_authenticate_user_wrong_password(
    test_db: Session,
    system_users: ScopedRepository[User],
):
    user = User(
        email="auth2@example.com",
        password_hash=hash_password("password123"),
    )
    test_db.add(user)
    test_db.commit()

    result = authenticate_user(system_users, "auth2@example.com", "wrongpassword")
    assert result is None


def test_authenticate_user_archived(
    test_db: Session,
    system_users: ScopedRepository[User],
):
    user = User(
        email="archived@example.com",
        password_hash=hash_password("password123"),
        archived=True,
    )
    test_db.add(user)
    test_db.commit()

    result = authenticate_user(system_users, "archived@example.com", "password123")
    assert result is None


def test_authenticate_user_nonexistent(
    test_db: Session,
    system_users: ScopedRepository[User],
):
    result = authenticate_user(system_users, "nobody@example.com", "password123")
    assert result is None


def test_create_user_success(
    test_db: Session,
    system_users: ScopedRepository[User],
    tx: Transaction,
):
    user = create_user(system_users, tx, "new@example.com", "password123")
    assert user.email == "new@example.com"
    assert user.uid is not None
    assert user.password_hash != "password123"


def test_create_user_duplicate_email(
    test_db: Session,
    system_users: ScopedRepository[User],
    tx: Transaction,
):
    create_user(system_users, tx, "dupe@example.com", "password123")
    with pytest.raises(DuplicateEmailError):
        create_user(system_users, tx, "dupe@example.com", "password456")


def test_get_user_by_email_with_a_mock_repository():
    """Business logic needs no database: the permission rules are the
    repository's job (and are tested against a real one in
    ``test_user_directory``), so a service test can mock it outright."""
    users = MagicMock(spec=ScopedRepository[User])
    users.get_filtered.return_value.items = [User(email="alice@acme.com")]

    user = get_user_by_email(users, "alice@acme.com")

    assert user is not None
    assert user.email == "alice@acme.com"
