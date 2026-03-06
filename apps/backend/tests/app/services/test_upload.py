"""Tests for upload service."""

from datetime import UTC, datetime, timedelta

from sqlalchemy.orm import Session

from src.app.repository import (
    Repository,
    Upload,
    UploadStatus,
    UploadStatusValue,
    User,
)
from src.app.services.password import hash_password
from src.app.services.storage import LocalStorageBackend
from src.app.services.upload import create_upload, list_uploads


def test_create_upload(test_db: Session, test_user: User):
    storage = LocalStorageBackend()
    response = create_upload(
        db=test_db,
        user=test_user,
        original_filename="test.gpx",
        file_size=1024,
        storage=storage,
    )

    assert response.original_filename == "test.gpx"
    assert response.file_size == 1024
    assert response.current_status == UploadStatusValue.UPLOAD_PENDING
    assert response.presigned_url is not None
    assert response.required_headers is not None
    assert response.required_headers["Content-Length"] == "1024"
    assert response.s3_key.startswith(f"uploads/{test_user.uid}/")
    assert response.s3_key.endswith(".gpx")


def test_create_upload_persists(test_db: Session, test_user: User):
    storage = LocalStorageBackend()
    response = create_upload(
        db=test_db,
        user=test_user,
        original_filename="track.gpx",
        file_size=2048,
        storage=storage,
    )

    upload = test_db.query(Upload).filter_by(uid=response.uid).one()
    assert upload.original_filename == "track.gpx"
    assert upload.file_size == 2048
    assert upload.user_uid == test_user.uid

    statuses = test_db.query(UploadStatus).filter_by(upload_uid=upload.uid).all()
    assert len(statuses) == 1
    assert statuses[0].status == UploadStatusValue.UPLOAD_PENDING


def test_list_uploads_excludes_pending(test_db: Session, test_user: User):
    storage = LocalStorageBackend()

    create_upload(
        db=test_db,
        user=test_user,
        original_filename="pending.gpx",
        file_size=100,
        storage=storage,
    )

    result = list_uploads(db=test_db, user=test_user, storage=storage)
    assert len(result.items) == 0


def test_list_uploads_includes_pending_when_requested(
    test_db: Session, test_user: User
):
    storage = LocalStorageBackend()

    create_upload(
        db=test_db,
        user=test_user,
        original_filename="pending.gpx",
        file_size=100,
        storage=storage,
    )

    result = list_uploads(
        db=test_db,
        user=test_user,
        storage=storage,
        statuses=[UploadStatusValue.UPLOAD_PENDING],
    )
    assert len(result.items) == 1
    assert result.items[0].current_status == UploadStatusValue.UPLOAD_PENDING


def test_list_uploads_filters_by_user(test_db: Session, test_user: User):
    storage = LocalStorageBackend()

    other_user = User(
        email="other@example.com",
        password_hash=hash_password("pass"),
    )
    test_db.add(other_user)
    test_db.commit()
    test_db.refresh(other_user)

    create_upload(
        db=test_db,
        user=other_user,
        original_filename="other.gpx",
        file_size=100,
        storage=storage,
    )

    result = list_uploads(
        db=test_db,
        user=test_user,
        storage=storage,
        statuses=[UploadStatusValue.UPLOAD_PENDING],
    )
    assert len(result.items) == 0


def test_list_uploads_with_received_status(test_db: Session, test_user: User):
    storage = LocalStorageBackend()

    response = create_upload(
        db=test_db,
        user=test_user,
        original_filename="received.gpx",
        file_size=500,
        storage=storage,
    )

    status_repo = Repository(test_db, UploadStatus)
    status_repo.add(
        UploadStatus(
            upload_uid=response.uid,
            status=UploadStatusValue.UPLOAD_RECEIVED,
        )
    )
    test_db.commit()

    result = list_uploads(db=test_db, user=test_user, storage=storage)
    assert len(result.items) == 1
    assert result.items[0].current_status == UploadStatusValue.UPLOAD_RECEIVED
    assert result.items[0].presigned_url is None


def test_presigned_url_none_for_old_pending_upload(test_db: Session, test_user: User):
    storage = LocalStorageBackend()

    upload_repo = Repository(test_db, Upload)
    status_repo = Repository(test_db, UploadStatus)

    upload = Upload(
        user_uid=test_user.uid,
        original_filename="old.gpx",
        file_size=100,
        s3_key="uploads/old/test.gpx",
        created_at=datetime.now(UTC) - timedelta(minutes=10),
    )
    upload_repo.add(upload)
    test_db.flush()

    status = UploadStatus(
        upload_uid=upload.uid,
        status=UploadStatusValue.UPLOAD_PENDING,
    )
    status_repo.add(status)
    test_db.commit()
    test_db.refresh(upload)

    result = list_uploads(
        db=test_db,
        user=test_user,
        storage=storage,
        statuses=[UploadStatusValue.UPLOAD_PENDING],
    )
    assert len(result.items) == 1
    assert result.items[0].presigned_url is None
