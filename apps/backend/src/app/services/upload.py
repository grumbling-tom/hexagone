"""Upload service for GPX file uploads."""

import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path

from sqlalchemy.orm import Session as DBSession

from src.app.repository import (
    Equals,
    HexClaim,
    In,
    Repository,
    Upload,
    UploadStatus,
    UploadStatusValue,
)
from src.app.repository.models import User
from src.app.services.gpx import GpxValidationError, gpx_bytes_to_polygons
from src.app.services.permissions import permissions_predicates
from src.app.services.storage import StorageBackend
from src.app.settings import settings
from src.app.utils import PaginatedResult, SortOrder, get_logger

logger = get_logger(__name__)


def maybe_presigned_url(
    upload: Upload,
    storage: StorageBackend,
) -> tuple[str | None, dict[str, str] | None]:
    """Conditionally generate a presigned URL for an upload.

    Returns (presigned_url, required_headers) or (None, None).
    - UPLOAD_PENDING + recent: PUT URL with required headers
    - UPLOAD_PENDING + old: (None, None)
    - Any other status: GET URL with no required headers
    """
    if upload.current_status != UploadStatusValue.UPLOAD_PENDING:
        # TODO: FE client should cache presigned GET URLs with a TTL
        url, _ = storage.generate_presigned_url(
            filename=upload.original_filename,
            key=Path(upload.s3_key),
            method="get_object",
            expires_in=settings.PRESIGNED_GET_URL_EXPIRY_SECONDS,
        )
        return url, None

    cutoff = datetime.now(UTC) - timedelta(
        seconds=settings.PRESIGNED_PUT_URL_EXPIRY_SECONDS
    )
    created_at = upload.created_at
    if created_at.tzinfo is None:
        created_at = created_at.replace(tzinfo=UTC)
    if created_at < cutoff:
        return None, None

    url, headers = storage.generate_presigned_url(
        filename=upload.original_filename,
        key=Path(upload.s3_key),
        method="put_object",
        expires_in=settings.PRESIGNED_PUT_URL_EXPIRY_SECONDS,
        content_length=upload.file_size_bytes,
        # Only GPX file uploads are permitted at the moment.
        content_type="application/gpx+xml",
    )
    return url, headers


def create_upload(
    db: DBSession,
    user: User,
    original_filename: str,
    file_size_bytes: int,
) -> Upload:
    """Create a new upload record with initial UPLOAD_PENDING status.

    Args:
        db: Database session.
        user: The authenticated user.
        original_filename: Client-provided filename.
        file_size_bytes: Expected file size in bytes.

    Returns:
        Upload ORM instance.
    """
    s3_key = f"v1/uploads/{uuid.uuid4()}"

    upload_repo = Repository(db, Upload)
    status_repo = Repository(db, UploadStatus)

    upload = Upload(
        user_uid=user.uid,
        original_filename=original_filename,
        file_size_bytes=file_size_bytes,
        s3_bucket_name=settings.HEXAGONE_S3_BUCKET,
        s3_key=s3_key,
    )
    upload_repo.add(upload)
    db.flush()

    status = UploadStatus(
        upload_uid=upload.uid,
        status=UploadStatusValue.UPLOAD_PENDING,
    )
    status_repo.add(status)
    db.commit()
    db.refresh(upload)

    logger.info(
        "upload_created",
        upload_uid=upload.uid,
        filename=original_filename,
    )

    return upload


def set_upload_status(
    db: DBSession,
    upload: Upload,
    status: UploadStatusValue,
    *,
    detail: str | None = None,
    commit: bool = True,
) -> None:
    """Append a new UploadStatus row.

    By default this commits the surrounding transaction; pass
    ``commit=False`` to defer the commit so the caller can batch the
    status flip with other writes (e.g. bulk hex_claim inserts) into a
    single transaction.
    """
    db.add(
        UploadStatus(
            upload_uid=upload.uid,
            status=status,
            git_sha=settings.GIT_SHA,
            detail=detail,
        )
    )
    if commit:
        db.commit()


def list_uploads(  # noqa: PLR0913
    db: DBSession,
    user: User,
    page_size: int = settings.DEFAULT_PAGE_SIZE,
    cursor: str | None = None,
    statuses: list[UploadStatusValue] | None = None,
    sort_field: str = "created_at",
    sort_order: SortOrder = SortOrder.DESC,
    upload_uid: str | None = None,
) -> PaginatedResult[Upload]:
    """List uploads for the authenticated user, filtered by status.

    Args:
        db: Database session.
        user: The authenticated user.
        page_size: Number of items per page.
        cursor: Pagination cursor.
        statuses: Filter by most recent status values.
        sort_field: Column name to sort by.
        sort_order: Sort direction.
        upload_uid: Optional filter to a single upload.

    Returns:
        Paginated list of Upload ORM instances.
    """
    if statuses is None:
        statuses = [
            UploadStatusValue.UPLOAD_RECEIVED,
            UploadStatusValue.UPLOAD_SUCCESS,
            UploadStatusValue.UPLOAD_INVALID,
        ]

    filters = permissions_predicates(user, Upload)
    filters.append(In(field="current_status", values=statuses))
    if upload_uid is not None:
        filters.append(Equals(field="uid", value=upload_uid))

    upload_repo = Repository(db, Upload)
    return upload_repo.get_filtered(
        filters=filters,
        page_size=page_size,
        cursor=cursor,
        sort_field=getattr(Upload, sort_field),
        sort_order=sort_order,
    )


def get_upload(db: DBSession, user: User, upload_uid: str) -> Upload | None:
    """Return one of the user's uploads, whatever its status, or None."""
    try:
        return list_uploads(
            db, user, statuses=list(UploadStatusValue), upload_uid=upload_uid
        ).items[0]
    except IndexError:
        return None


class UploadNotInStorageError(Exception):
    """Raised when processing is requested before the file has landed in storage."""

    def __init__(self, upload_uid: str) -> None:
        super().__init__(f"Upload {upload_uid} has no file in storage yet")
        self.upload_uid = upload_uid


def process_user_upload(
    db: DBSession, user: User, upload_uid: str, storage: StorageBackend
) -> Upload | None:
    """Process one of the user's uploads now, once its file is in storage.

    Called by the browser straight after it finishes PUTting the file to the
    presigned URL. Processing runs in the request, synchronously: simple to
    run and debug, at the cost of the caller waiting for large files. The
    work itself is ``process_upload``, so moving this to a background worker
    later only changes how it is triggered.

    Returns None when the upload doesn't exist or isn't the user's. Raises
    ``UploadNotInStorageError`` if the upload is still pending but its file
    hasn't landed, leaving it pending so the caller can try again. An upload
    that has already been processed is returned unchanged.
    """
    upload = get_upload(db, user, upload_uid)
    if upload is None:
        return None

    if upload.current_status == UploadStatusValue.UPLOAD_PENDING:
        if not storage.object_exists(upload.s3_key):
            raise UploadNotInStorageError(upload_uid)
        process_upload(db, upload.s3_key, storage)
        db.refresh(upload)

    return upload


def find_upload_by_s3_key(db: DBSession, key: str) -> Upload | None:
    """Find an Upload record by its associated object key."""
    result = Repository(db, Upload).get_filtered(
        filters=[Equals(field="s3_key", value=key)],
        page_size=1,
    )
    return result.items[0] if result.items else None


def process_upload(db: DBSession, key: str, storage: StorageBackend) -> None:
    """Process an uploaded GPX object: parse it and record hex claims.

    Extracted from the former AWS Lambda S3-event handler — called with an
    object key once the file has landed in storage (today from
    ``process_user_upload``, when the browser reports the upload finished), and
    knows nothing about how it was triggered.

    Idempotent on upload status: only an upload still in ``UPLOAD_PENDING`` is
    processed, so at-least-once delivery (a duplicate notification, a retried
    job) is a safe no-op. Invalid GPX is a *terminal* outcome
    (``UPLOAD_INVALID``), not an error — only unexpected infrastructure
    failures propagate, so the caller's queue can retry those.

    The caller owns the session lifecycle (e.g. the request's session); this
    function manages its own commits within it.
    """
    upload = find_upload_by_s3_key(db, key)

    if not upload:
        logger.warning("upload_not_found", key=key)
        return

    if upload.current_status != UploadStatusValue.UPLOAD_PENDING:
        logger.info("upload_not_pending", key=key, status=upload.current_status)
        return

    set_upload_status(db, upload, UploadStatusValue.UPLOAD_RECEIVED)
    logger.info("upload_status_updated", key=key, status="UPLOAD_RECEIVED")

    data = storage.get_object(key)

    try:
        polygons = gpx_bytes_to_polygons(data, resolution=settings.H3_RESOLUTION)
    except GpxValidationError as e:
        logger.warning("gpx_invalid", key=key, reason=e.reason)
        set_upload_status(db, upload, UploadStatusValue.UPLOAD_INVALID, detail=e.reason)
        return

    claims = [
        HexClaim(
            upload_uid=upload.uid,
            user_uid=upload.user_uid,
            h3_cell=cell,
            h3_resolution=settings.H3_RESOLUTION,
            polygon_index=polygon.polygon_index,
            completed_at=polygon.completed_at,
            git_sha=settings.GIT_SHA,
        )
        for polygon in polygons
        for cell in polygon.cells
    ]

    # Bulk insert + UPLOAD_SUCCESS share a single transaction so a failed
    # insert does not leave a misleading success status.
    db.add_all(claims)
    set_upload_status(db, upload, UploadStatusValue.UPLOAD_SUCCESS, commit=False)
    db.commit()

    # TODO: Consider an UPLOAD_FAILED status for bulk insert failures.
    logger.info(
        "upload_processed",
        key=key,
        polygon_count=len(polygons),
        cells_inserted=len(claims),
    )
