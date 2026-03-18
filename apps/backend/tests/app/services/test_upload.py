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
from src.app.services.storage import S3StorageBackend
from src.app.services.upload import create_upload, list_uploads, maybe_presigned_url


def test_create_upload(test_db: Session, test_user: User):
    upload = create_upload(
        db=test_db,
        user=test_user,
        original_filename="test.gpx",
        file_size_bytes=1024,
    )

    assert upload.original_filename == "test.gpx"
    assert upload.file_size_bytes == 1024
    assert upload.current_status == UploadStatusValue.UPLOAD_PENDING
    assert upload.s3_key.startswith("v1/uploads/")


def test_create_upload_persists(test_db: Session, test_user: User):
    upload = create_upload(
        db=test_db,
        user=test_user,
        original_filename="track.gpx",
        file_size_bytes=2048,
    )

    persisted = test_db.query(Upload).filter_by(uid=upload.uid).one()
    assert persisted.original_filename == "track.gpx"
    assert persisted.file_size_bytes == 2048
    assert persisted.user_uid == test_user.uid

    statuses = test_db.query(UploadStatus).filter_by(upload_uid=upload.uid).all()
    assert len(statuses) == 1
    assert statuses[0].status == UploadStatusValue.UPLOAD_PENDING


def test_list_uploads_excludes_pending(test_db: Session, test_user: User):
    create_upload(
        db=test_db,
        user=test_user,
        original_filename="pending.gpx",
        file_size_bytes=100,
    )

    result = list_uploads(db=test_db, user=test_user)
    assert len(result.items) == 0


def test_list_uploads_includes_pending_when_requested(
    test_db: Session, test_user: User
):
    create_upload(
        db=test_db,
        user=test_user,
        original_filename="pending.gpx",
        file_size_bytes=100,
    )

    result = list_uploads(
        db=test_db,
        user=test_user,
        statuses=[UploadStatusValue.UPLOAD_PENDING],
    )
    assert len(result.items) == 1
    assert result.items[0].current_status == UploadStatusValue.UPLOAD_PENDING


def test_list_uploads_filters_by_user(test_db: Session, test_user: User):
    other_user = User(
        email="other@example.com",
        external_auth_id="other_clerk_id",
    )
    test_db.add(other_user)
    test_db.commit()
    test_db.refresh(other_user)

    create_upload(
        db=test_db,
        user=other_user,
        original_filename="other.gpx",
        file_size_bytes=100,
    )

    result = list_uploads(
        db=test_db,
        user=test_user,
        statuses=[UploadStatusValue.UPLOAD_PENDING],
    )
    assert len(result.items) == 0


def test_list_uploads_with_received_status(test_db: Session, test_user: User):
    upload = create_upload(
        db=test_db,
        user=test_user,
        original_filename="received.gpx",
        file_size_bytes=500,
    )

    status_repo = Repository(test_db, UploadStatus)
    status_repo.add(
        UploadStatus(
            upload_uid=upload.uid,
            status=UploadStatusValue.UPLOAD_RECEIVED,
        )
    )
    test_db.commit()

    result = list_uploads(db=test_db, user=test_user)
    assert len(result.items) == 1
    assert result.items[0].current_status == UploadStatusValue.UPLOAD_RECEIVED


def test_list_uploads_pagination_with_status_filter(test_db: Session, test_user: User):
    status_repo = Repository(test_db, UploadStatus)

    # Create 5 RECEIVED uploads
    for i in range(5):
        upload = create_upload(
            db=test_db,
            user=test_user,
            original_filename=f"received_{i}.gpx",
            file_size_bytes=100,
        )
        status_repo.add(
            UploadStatus(
                upload_uid=upload.uid,
                status=UploadStatusValue.UPLOAD_RECEIVED,
            )
        )
        test_db.commit()

    # Create 5 PENDING uploads (excluded by default filter)
    for i in range(5):
        create_upload(
            db=test_db,
            user=test_user,
            original_filename=f"pending_{i}.gpx",
            file_size_bytes=100,
        )

    # First page: exactly 3 items
    page1 = list_uploads(db=test_db, user=test_user, page_size=3)
    assert len(page1.items) == 3
    assert page1.has_next is True

    # Second page: exactly 2 items
    page2 = list_uploads(
        db=test_db,
        user=test_user,
        page_size=3,
        cursor=page1.next_cursor,
    )
    assert len(page2.items) == 2
    assert page2.has_next is False


def _create_upload_with_status(
    test_db: Session,
    test_user: User,
    status: str,
    filename: str = "test.gpx",
) -> Upload:
    """Helper to create an upload and advance it to the given status."""
    upload_repo = Repository(test_db, Upload)
    status_repo = Repository(test_db, UploadStatus)

    upload = Upload(
        user_uid=test_user.uid,
        original_filename=filename,
        file_size_bytes=100,
        s3_bucket_name="test-bucket",
        s3_key=f"uploads/test/{filename}",
    )
    upload_repo.add(upload)
    test_db.flush()
    status_repo.add(
        UploadStatus(
            upload_uid=upload.uid,
            status=UploadStatusValue.UPLOAD_PENDING,
        )
    )
    if status != UploadStatusValue.UPLOAD_PENDING:
        status_repo.add(
            UploadStatus(
                upload_uid=upload.uid,
                status=status,
            )
        )
    test_db.commit()
    test_db.refresh(upload)
    return upload


def test_maybe_presigned_url_non_pending(test_db: Session, test_user: User):
    """Non-pending uploads should get a presigned GET URL."""
    upload = _create_upload_with_status(
        test_db, test_user, UploadStatusValue.UPLOAD_RECEIVED, "received.gpx"
    )

    storage = S3StorageBackend()
    url, headers = maybe_presigned_url(upload, storage)
    assert url is not None
    assert "X-Amz-Signature" in url
    assert headers is None


def test_maybe_presigned_url_get_url_for_received(test_db: Session, test_user: User):
    """UPLOAD_RECEIVED uploads should get a GET URL with no required_headers."""
    upload = _create_upload_with_status(
        test_db, test_user, UploadStatusValue.UPLOAD_RECEIVED, "received.gpx"
    )

    storage = S3StorageBackend()
    url, headers = maybe_presigned_url(upload, storage)
    assert url is not None
    assert "X-Amz-Signature" in url
    assert headers is None


def test_maybe_presigned_url_get_url_for_success(test_db: Session, test_user: User):
    """UPLOAD_SUCCESS uploads should get a GET URL with no required_headers."""
    upload = _create_upload_with_status(
        test_db, test_user, UploadStatusValue.UPLOAD_SUCCESS, "success.gpx"
    )

    storage = S3StorageBackend()
    url, headers = maybe_presigned_url(upload, storage)
    assert url is not None
    assert "X-Amz-Signature" in url
    assert headers is None


def test_maybe_presigned_url_old_pending(test_db: Session, test_user: User):
    """Pending uploads older than the window should not get a presigned URL."""
    upload_repo = Repository(test_db, Upload)
    status_repo = Repository(test_db, UploadStatus)

    upload = Upload(
        user_uid=test_user.uid,
        original_filename="old.gpx",
        file_size_bytes=100,
        s3_bucket_name="test-bucket",
        s3_key="uploads/test/old.gpx",
        created_at=datetime.now(UTC) - timedelta(minutes=10),
    )
    upload_repo.add(upload)
    test_db.flush()
    status_repo.add(
        UploadStatus(
            upload_uid=upload.uid,
            status=UploadStatusValue.UPLOAD_PENDING,
        )
    )
    test_db.commit()
    test_db.refresh(upload)

    storage = S3StorageBackend()
    url, headers = maybe_presigned_url(upload, storage)
    assert url is None
    assert headers is None


def test_maybe_presigned_url_recent_pending(test_db: Session, test_user: User):
    """Recent pending uploads should get a presigned URL and headers."""
    upload = create_upload(
        db=test_db,
        user=test_user,
        original_filename="new.gpx",
        file_size_bytes=1024,
    )

    storage = S3StorageBackend()
    url, headers = maybe_presigned_url(upload, storage)
    assert url is not None
    assert headers is not None
    assert headers["Content-Length"] == "1024"
