"""Shared test fixtures."""

import uuid
from collections.abc import Callable, Generator
from datetime import datetime

import boto3
import pytest
from fastapi.testclient import TestClient
from moto import mock_aws
from mypy_boto3_s3 import S3Client
from sqlalchemy import StaticPool, create_engine
from sqlalchemy.orm import Session, sessionmaker

from src.app.dependencies import db_session, file_storage
from src.app.main import app
from src.app.repository import (
    BaseModel,
    HexClaim,
    Repository,
    Upload,
    UploadStatus,
    UploadStatusValue,
    User,
    UserGroup,
    UserGroupMembership,
)
from src.app.services.password import hash_password
from src.app.services.storage import S3StorageBackend
from src.app.services.user_session import create_session


@pytest.fixture(autouse=True)
def _mock_s3() -> Generator[None]:  # pyright: ignore[reportUnusedFunction]
    """Mock AWS S3 for all tests."""
    with mock_aws():
        client: S3Client = boto3.client("s3", region_name="eu-west-2")  # pyright: ignore[reportUnknownMemberType]
        client.create_bucket(
            Bucket="hexagone-gpx-uploads",
            CreateBucketConfiguration={"LocationConstraint": "eu-west-2"},
        )
        yield


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
            s3_bucket_name="test-bucket",
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


@pytest.fixture
def create_hex_claim(test_db: Session) -> Callable[..., HexClaim]:
    """Return a factory that creates a HexClaim row.

    The claim is attributed to ``upload.user_uid`` and uses the default
    H3 resolution (12). Tests that need to override resolution, git_sha,
    or user can mutate the returned ORM instance before re-committing.

    Args passed to the returned callable:
        upload: Parent Upload to attach the claim to.
        h3_cell: H3 cell ID (default a fixed valid res-12 cell).
        polygon_index: 0-based polygon index (default 0).
        completed_at: Closing timestamp; None by default.
    """

    def _factory(
        upload: Upload,
        *,
        h3_cell: str = "8c1f1d2806467ff",
        polygon_index: int = 0,
        completed_at: datetime | None = None,
    ) -> HexClaim:
        claim = HexClaim(
            upload_uid=upload.uid,
            user_uid=upload.user_uid,
            h3_cell=h3_cell,
            h3_resolution=12,
            polygon_index=polygon_index,
            completed_at=completed_at,
        )
        test_db.add(claim)
        test_db.commit()
        test_db.refresh(claim)
        return claim

    return _factory


@pytest.fixture
def create_user(test_db: Session) -> Callable[..., User]:
    """Return a factory that creates additional users beyond ``test_user``."""

    def _factory(
        *,
        email: str | None = None,
        password: str = "testpassword123",
    ) -> User:
        unique_email = email or f"user-{uuid.uuid4()}@example.com"
        user = User(
            email=unique_email,
            password_hash=hash_password(password),
        )
        test_db.add(user)
        test_db.commit()
        test_db.refresh(user)
        return user

    return _factory


@pytest.fixture
def create_group(
    test_db: Session, test_user: User
) -> Callable[..., UserGroup]:
    """Return a factory that creates a UserGroup with the owner's membership.

    Args passed to the returned callable:
        name: Group name (default "Test Group").
        owner: User who owns the group (defaults to ``test_user``).
    """

    def _factory(
        *,
        name: str = "Test Group",
        owner: User | None = None,
    ) -> UserGroup:
        actual_owner = owner or test_user
        group = UserGroup(
            name=name, owner_uid=actual_owner.uid, archived=False
        )
        test_db.add(group)
        test_db.flush()
        test_db.add(
            UserGroupMembership(
                user_uid=actual_owner.uid,
                user_group_uid=group.uid,
                share_consent=True,
                invited_by_uid=None,
            )
        )
        test_db.commit()
        test_db.refresh(group)
        return group

    return _factory


@pytest.fixture
def create_membership(
    test_db: Session,
) -> Callable[..., UserGroupMembership]:
    """Return a factory that adds an existing user to a group.

    Args:
        group: The group to join.
        user: The user being added.
        share_consent: Defaults to True (consistent with the service default).
        invited_by: Optional inviter (defaults to None — founder-style).
    """

    def _factory(
        *,
        group: UserGroup,
        user: User,
        share_consent: bool = True,
        invited_by: User | None = None,
    ) -> UserGroupMembership:
        membership = UserGroupMembership(
            user_uid=user.uid,
            user_group_uid=group.uid,
            share_consent=share_consent,
            invited_by_uid=invited_by.uid if invited_by else None,
        )
        test_db.add(membership)
        test_db.commit()
        test_db.refresh(membership)
        return membership

    return _factory


def _make_get_db(db: Session) -> Generator[Session]:
    """Create a get_db override that yields the given session."""
    yield db


@pytest.fixture
def client(test_db: Session, test_user: User) -> Generator[TestClient]:
    """Yield an authenticated FastAPI test client."""

    def override_get_db() -> Generator[Session]:
        yield from _make_get_db(test_db)

    app.dependency_overrides[db_session] = override_get_db
    app.dependency_overrides[file_storage] = S3StorageBackend

    session = create_session(test_db, test_user.uid, "testclient", "testclient")

    with TestClient(app) as c:
        c.cookies.set("sessionid", session.uid)
        yield c

    app.dependency_overrides.clear()


@pytest.fixture
def authenticate_as(
    test_db: Session, client: TestClient
) -> Callable[[User], TestClient]:
    """Return a helper that re-authenticates the existing test client as a user.

    Swaps the ``sessionid`` cookie on the shared client so subsequent
    requests act as ``user``. Returns the same client for chaining.
    """

    def _switch(user: User) -> TestClient:
        session = create_session(test_db, user.uid, "testclient", "testclient")
        client.cookies.set("sessionid", session.uid)
        return client

    return _switch


@pytest.fixture
def unauthenticated_client(test_db: Session) -> Generator[TestClient]:
    """Yield an unauthenticated FastAPI test client."""

    def override_get_db() -> Generator[Session]:
        yield from _make_get_db(test_db)

    app.dependency_overrides[db_session] = override_get_db
    app.dependency_overrides[file_storage] = S3StorageBackend

    with TestClient(app) as c:
        yield c

    app.dependency_overrides.clear()
