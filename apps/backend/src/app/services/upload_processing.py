"""Transport-agnostic GPX upload processing.

Extracted from the former AWS Lambda S3-event handler. :func:`process_upload`
is called with an object key once the file has landed in storage — today from
the Tigris object-notification webhook via a background worker, previously from
an S3 ObjectCreated event. It knows nothing about how it was triggered.
"""

from sqlalchemy.orm import Session

from src.app.repository import (
    EqualsFilter,
    HexClaim,
    Repository,
    Upload,
    UploadStatusValue,
)
from src.app.services.gpx_processing import GpxValidationError, gpx_bytes_to_polygons
from src.app.services.storage import StorageBackend
from src.app.services.upload import set_upload_status
from src.app.settings import settings
from src.app.utils import get_logger

logger = get_logger(__name__)


def find_upload_by_s3_key(db: Session, key: str) -> Upload | None:
    """Find an Upload record by its associated object key."""
    result = Repository(db, Upload).get_filtered(
        filters=[EqualsFilter(field="s3_key", value=key)],
        page_size=1,
    )
    return result.items[0] if result.items else None


def process_upload(db: Session, key: str, storage: StorageBackend) -> None:
    """Process an uploaded GPX object: parse it and record hex claims.

    Idempotent on upload status: only an upload still in ``UPLOAD_PENDING`` is
    processed, so at-least-once delivery (a duplicate notification, a retried
    job) is a safe no-op. Invalid GPX is a *terminal* outcome
    (``UPLOAD_INVALID``), not an error — only unexpected infrastructure
    failures propagate, so the caller's queue can retry those.

    The caller owns the session lifecycle (e.g. the worker opens one via
    ``get_db()``); this function manages its own commits within it.
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
