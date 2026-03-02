"""Shared test fixtures."""

from collections.abc import Generator
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import StaticPool, create_engine
from sqlalchemy.orm import Session, sessionmaker

from src.app.main import app
from src.app.repository import BaseModel, User
from src.app.repository.database import get_db
from src.app.services.password import hash_password
from src.app.services.user_session import create_session


@pytest.fixture
def test_db() -> Generator[Session]:
    """Yield an in-memory SQLite database session for testing."""
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    BaseModel.metadata.create_all(engine)
    testing_session_local = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = testing_session_local()
    try:
        yield db
    finally:
        db.close()
        BaseModel.metadata.drop_all(engine)


@pytest.fixture
def test_user(test_db: Session) -> User:
    """Create and return a test user."""
    user = User(
        email="test@example.com",
        password_hash=hash_password("testpassword123"),
    )
    test_db.add(user)
    test_db.commit()
    test_db.refresh(user)
    return user


def _make_get_db(db: Session) -> Generator[Session]:
    """Create a get_db override that yields the given session."""
    yield db


@pytest.fixture
def client(test_db: Session, test_user: User) -> Generator[TestClient]:
    """Yield an authenticated FastAPI test client."""

    def override_get_db() -> Generator[Session]:
        yield from _make_get_db(test_db)

    app.dependency_overrides[get_db] = override_get_db

    session = create_session(test_db, test_user.uid, "testclient", "testclient")

    with (
        patch("src.app.middleware.get_db", override_get_db),
        patch("src.app.routers.users.get_db", override_get_db),
        patch("src.app.routers.user_sessions.get_db", override_get_db),
        TestClient(app) as c,
    ):
        c.cookies.set("sessionid", session.uid)
        yield c

    app.dependency_overrides.clear()


@pytest.fixture
def unauthenticated_client(test_db: Session) -> Generator[TestClient]:
    """Yield an unauthenticated FastAPI test client."""

    def override_get_db() -> Generator[Session]:
        yield from _make_get_db(test_db)

    app.dependency_overrides[get_db] = override_get_db

    with (
        patch("src.app.middleware.get_db", override_get_db),
        patch("src.app.routers.users.get_db", override_get_db),
        patch("src.app.routers.user_sessions.get_db", override_get_db),
        TestClient(app) as c,
    ):
        yield c

    app.dependency_overrides.clear()
