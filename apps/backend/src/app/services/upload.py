"""Upload service for GPX file uploads."""

import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy.orm import Session as DBSession

from src.app.repository import (
    InFilter,
    Repository,
    Upload,
    UploadStatus,
    UploadStatusValue,
)
from src.app.repository.models import User
from src.app.services.permissions import permission_filters
from src.app.services.storage import StorageBackend
from src.app.settings import settings
from src.app.utils import PaginatedResult, SortOrder, get_logger

logger = get_logger(__name__)

GPX_CONTENT_TYPE = "application/gpx+xml"
PRESIGNED_URL_WINDOW_MINUTES = 5


def maybe_presigned_url(
    upload: Upload,
    storage: StorageBackend,
) -> tuple[str | None, dict[str, str] | None]:
    """Conditionally generate a presigned URL for an upload.

    Returns (presigned_url, required_headers) or (None, None).
    """
    if upload.current_status != UploadStatusValue.UPLOAD_PENDING:
        return None, None

    cutoff = datetime.now(UTC) - timedelta(minutes=PRESIGNED_URL_WINDOW_MINUTES)
    created_at = upload.created_at
    if created_at.tzinfo is None:
        created_at = created_at.replace(tzinfo=UTC)
    if created_at < cutoff:
        return None, None

    url = storage.generate_presigned_put_url(
        key=upload.s3_key,
        content_type=GPX_CONTENT_TYPE,
        content_length=upload.file_size,
        expires_in=settings.PRESIGNED_URL_EXPIRY_SECONDS,
    )
    headers = {
        "Content-Length": str(upload.file_size),
        "Content-Type": GPX_CONTENT_TYPE,
    }
    return url, headers


def create_upload(
    db: DBSession,
    user: User,
    original_filename: str,
    file_size: int,
) -> Upload:
    """Create a new upload record with initial UPLOAD_PENDING status.

    Args:
        db: Database session.
        user: The authenticated user.
        original_filename: Client-provided filename.
        file_size: Expected file size in bytes.

    Returns:
        Upload ORM instance.
    """
    s3_key = f"uploads/{user.uid}/{uuid.uuid4()}.gpx"

    upload_repo = Repository(db, Upload)
    status_repo = Repository(db, UploadStatus)

    upload = Upload(
        user_uid=user.uid,
        original_filename=original_filename,
        file_size=file_size,
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


def list_uploads(
    db: DBSession,
    user: User,
    page_size: int = settings.DEFAULT_PAGE_SIZE,
    cursor: str | None = None,
    statuses: list[str] | None = None,
) -> PaginatedResult[Upload]:
    """List uploads for the authenticated user, filtered by status.

    Args:
        db: Database session.
        user: The authenticated user.
        page_size: Number of items per page.
        cursor: Pagination cursor.
        statuses: Filter by most recent status values.

    Returns:
        Paginated list of Upload ORM instances.
    """
    if statuses is None:
        statuses = [
            UploadStatusValue.UPLOAD_RECEIVED,
            UploadStatusValue.UPLOAD_SUCCESS,
            UploadStatusValue.UPLOAD_INVALID,
        ]

    filters = permission_filters(user, Upload)
    filters.append(InFilter(field="current_status", values=statuses))

    upload_repo = Repository(db, Upload)
    return upload_repo.get_filtered(
        filters=filters,
        page_size=page_size,
        cursor=cursor,
        sort_field=Upload.created_at,
        sort_order=SortOrder.DESC,
    )
