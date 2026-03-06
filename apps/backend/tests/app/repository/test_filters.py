"""Tests for hybrid_property filtering on Upload.current_status."""

from sqlalchemy.orm import Session

from src.app.repository import (
    EqualsFilter,
    InFilter,
    Repository,
    Upload,
    UploadStatus,
    UploadStatusValue,
    User,
)
from src.app.services.password import hash_password


def _create_upload_with_statuses(
    db: Session,
    user: User,
    filename: str,
    status_values: list[UploadStatusValue],
) -> Upload:
    """Helper to create an upload and append status events."""
    upload_repo = Repository(db, Upload)
    status_repo = Repository(db, UploadStatus)

    upload = Upload(
        user_uid=user.uid,
        original_filename=filename,
        file_size=100,
        s3_key=f"uploads/{user.uid}/{filename}",
    )
    upload_repo.add(upload)
    db.flush()

    for value in status_values:
        status_repo.add(UploadStatus(upload_uid=upload.uid, status=value))
        db.flush()

    db.commit()
    db.refresh(upload)
    return upload


def test_in_filter_on_current_status_matches(test_db: Session, test_user: User):
    _create_upload_with_statuses(
        test_db,
        test_user,
        "a.gpx",
        [UploadStatusValue.UPLOAD_PENDING, UploadStatusValue.UPLOAD_RECEIVED],
    )

    repo = Repository(test_db, Upload)
    result = repo.get_filtered(
        filters=[
            InFilter(field="current_status", values=[UploadStatusValue.UPLOAD_RECEIVED])
        ],
    )
    assert len(result.items) == 1
    assert result.items[0].current_status == UploadStatusValue.UPLOAD_RECEIVED


def test_in_filter_on_current_status_uses_latest(test_db: Session, test_user: User):
    _create_upload_with_statuses(
        test_db,
        test_user,
        "b.gpx",
        [
            UploadStatusValue.UPLOAD_PENDING,
            UploadStatusValue.UPLOAD_RECEIVED,
            UploadStatusValue.UPLOAD_INVALID,
        ],
    )

    repo = Repository(test_db, Upload)
    result = repo.get_filtered(
        filters=[
            InFilter(field="current_status", values=[UploadStatusValue.UPLOAD_RECEIVED])
        ],
    )
    assert len(result.items) == 0


def test_in_filter_on_current_status_excludes_non_matching(
    test_db: Session, test_user: User
):
    _create_upload_with_statuses(
        test_db,
        test_user,
        "c.gpx",
        [UploadStatusValue.UPLOAD_PENDING],
    )

    repo = Repository(test_db, Upload)
    result = repo.get_filtered(
        filters=[
            InFilter(field="current_status", values=[UploadStatusValue.UPLOAD_SUCCESS])
        ],
    )
    assert len(result.items) == 0


def test_in_filter_on_current_status_no_statuses(test_db: Session, test_user: User):
    upload_repo = Repository(test_db, Upload)
    upload = Upload(
        user_uid=test_user.uid,
        original_filename="d.gpx",
        file_size=100,
        s3_key=f"uploads/{test_user.uid}/d.gpx",
    )
    upload_repo.add(upload)
    test_db.commit()

    result = upload_repo.get_filtered(
        filters=[
            InFilter(field="current_status", values=[UploadStatusValue.UPLOAD_RECEIVED])
        ],
    )
    assert len(result.items) == 0


def test_in_filter_on_current_status_multiple_values(test_db: Session, test_user: User):
    _create_upload_with_statuses(
        test_db,
        test_user,
        "e.gpx",
        [UploadStatusValue.UPLOAD_PENDING, UploadStatusValue.UPLOAD_RECEIVED],
    )
    _create_upload_with_statuses(
        test_db,
        test_user,
        "f.gpx",
        [UploadStatusValue.UPLOAD_PENDING, UploadStatusValue.UPLOAD_SUCCESS],
    )

    repo = Repository(test_db, Upload)
    result = repo.get_filtered(
        filters=[
            InFilter(
                field="current_status",
                values=[
                    UploadStatusValue.UPLOAD_RECEIVED,
                    UploadStatusValue.UPLOAD_SUCCESS,
                ],
            )
        ],
    )
    assert len(result.items) == 2


def test_in_filter_on_current_status_composes_with_equals(
    test_db: Session, test_user: User
):
    other_user = User(
        email="other@example.com",
        password_hash=hash_password("pass"),
    )
    test_db.add(other_user)
    test_db.commit()
    test_db.refresh(other_user)

    _create_upload_with_statuses(
        test_db,
        test_user,
        "g.gpx",
        [UploadStatusValue.UPLOAD_PENDING, UploadStatusValue.UPLOAD_RECEIVED],
    )
    _create_upload_with_statuses(
        test_db,
        other_user,
        "h.gpx",
        [UploadStatusValue.UPLOAD_PENDING, UploadStatusValue.UPLOAD_RECEIVED],
    )

    repo = Repository(test_db, Upload)
    result = repo.get_filtered(
        filters=[
            InFilter(
                field="current_status", values=[UploadStatusValue.UPLOAD_RECEIVED]
            ),
            EqualsFilter(field="user_uid", value=test_user.uid),
        ],
    )
    assert len(result.items) == 1
    assert result.items[0].user_uid == test_user.uid
