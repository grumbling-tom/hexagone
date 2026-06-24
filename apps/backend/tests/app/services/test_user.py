"""Tests for the user service."""

import pytest
from sqlalchemy.orm import Session

from src.app.repository import User
from src.app.services.password import hash_password
from src.app.services.user import (
    DuplicateEmailError,
    authenticate_user,
    create_user,
)


def test_authenticate_user_success(test_db: Session):
    user = User(
        email="auth@example.com",
        password_hash=hash_password("password123"),
    )
    test_db.add(user)
    test_db.commit()

    result = authenticate_user(test_db, "auth@example.com", "password123")
    assert result is not None
    assert result.email == "auth@example.com"


def test_authenticate_user_wrong_password(test_db: Session):
    user = User(
        email="auth2@example.com",
        password_hash=hash_password("password123"),
    )
    test_db.add(user)
    test_db.commit()

    result = authenticate_user(test_db, "auth2@example.com", "wrongpassword")
    assert result is None


def test_authenticate_user_archived(test_db: Session):
    user = User(
        email="archived@example.com",
        password_hash=hash_password("password123"),
        archived=True,
    )
    test_db.add(user)
    test_db.commit()

    result = authenticate_user(test_db, "archived@example.com", "password123")
    assert result is None


def test_authenticate_user_nonexistent(test_db: Session):
    result = authenticate_user(test_db, "nobody@example.com", "password123")
    assert result is None


def test_create_user_success(test_db: Session):
    user = create_user(test_db, "new@example.com", "password123")
    assert user.email == "new@example.com"
    assert user.uid is not None
    assert user.password_hash != "password123"


def test_create_user_duplicate_email(test_db: Session):
    create_user(test_db, "dupe@example.com", "password123")
    with pytest.raises(DuplicateEmailError):
        create_user(test_db, "dupe@example.com", "password456")


def test_first_user_bootstraps_to_admin(test_db: Session):
    """The first user to sign up becomes admin; everyone after is not."""
    first = create_user(test_db, "first@example.com", "password123")
    second = create_user(test_db, "second@example.com", "password123")

    assert first.is_admin is True
    assert second.is_admin is False
