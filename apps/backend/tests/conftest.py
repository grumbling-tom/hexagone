"""Shared test fixtures."""

import uuid
from collections.abc import Callable, Generator
from datetime import datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import StaticPool, create_engine
from sqlalchemy.orm import Session, sessionmaker

from src.app.dependencies import get_db, get_storage_backend
from src.app.main import app
from src.app.repository import (
    BaseModel,
    Repository,
    Upload,
    UploadStatus,
    UploadStatusValue,
    User,
)
from src.app.services.password import hash_password
from src.app.services.storage import LocalStorageBackend
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


@pytest.fixture
def create_upload(test_db: Session, test_user: User) -> Callable[..., Upload]:
    """Return a factory that creates an Upload with status rows.

    Args passed to the returned callable:
        filename: Original filename for the upload.
        file_size: File size in bytes (default 100).
        created_at: Override the created_at timestamp.
        status_values: List of UploadStatusValue to append.
            Defaults to [UPLOAD_PENDING].
        user: Override the owning user (defaults to test_user).
    """

    def _factory(
        filename: str,
        *,
        file_size_bytes: int = 100,
        created_at: datetime | None = None,
        status_values: list[UploadStatusValue] | None = None,
        user: User | None = None,
    ) -> Upload:
        owner = user or test_user
        if status_values is None:
            status_values = [UploadStatusValue.UPLOAD_PENDING]

        upload_repo = Repository(test_db, Upload)
        status_repo = Repository(test_db, UploadStatus)

        upload = Upload(
            user_uid=owner.uid,
            original_filename=filename,
            file_size_bytes=file_size_bytes,
            s3_key=f"uploads/{owner.uid}/{uuid.uuid4()}/{filename}",
        )
        if created_at is not None:
            upload.created_at = created_at
        upload_repo.add(upload)
        test_db.flush()

        for value in status_values:
            status_repo.add(UploadStatus(upload_uid=upload.uid, status=value))
            test_db.flush()

        test_db.commit()
        test_db.refresh(upload)
        return upload

    return _factory


def _make_get_db(db: Session) -> Generator[Session]:
    """Create a get_db override that yields the given session."""
    yield db


@pytest.fixture
def client(test_db: Session, test_user: User) -> Generator[TestClient]:
    """Yield an authenticated FastAPI test client."""

    def override_get_db() -> Generator[Session]:
        yield from _make_get_db(test_db)

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_storage_backend] = LocalStorageBackend

    session = create_session(test_db, test_user.uid, "testclient", "testclient")

    with TestClient(app) as c:
        c.cookies.set("sessionid", session.uid)
        yield c

    app.dependency_overrides.clear()


@pytest.fixture
def unauthenticated_client(test_db: Session) -> Generator[TestClient]:
    """Yield an unauthenticated FastAPI test client."""

    def override_get_db() -> Generator[Session]:
        yield from _make_get_db(test_db)

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_storage_backend] = LocalStorageBackend

    with TestClient(app) as c:
        yield c

    app.dependency_overrides.clear()
