"""Tests for the user service."""

from sqlalchemy.orm import Session

from src.app.repository import User
from src.app.services.user import get_or_create_user


def test_get_or_create_user_creates_new(test_db: Session):
    user = get_or_create_user(test_db, "clerk_id_1", "new@example.com")
    assert user.email == "new@example.com"
    assert user.external_auth_id == "clerk_id_1"
    assert user.role == "user"
    assert user.uid is not None


def test_get_or_create_user_returns_existing(test_db: Session):
    existing = User(
        email="existing@example.com",
        external_auth_id="clerk_id_2",
    )
    test_db.add(existing)
    test_db.commit()
    test_db.refresh(existing)

    user = get_or_create_user(test_db, "clerk_id_2", "existing@example.com")
    assert user.uid == existing.uid
    assert user.email == "existing@example.com"


def test_get_or_create_user_different_ids_create_different_users(test_db: Session):
    user1 = get_or_create_user(test_db, "clerk_id_a", "a@example.com")
    user2 = get_or_create_user(test_db, "clerk_id_b", "b@example.com")
    assert user1.uid != user2.uid
