"""File upload processing handler."""

from typing import Any
from urllib.parse import unquote_plus

from sqlalchemy import insert
from sqlalchemy.orm import Session

from src.app.handlers.file_upload.gpx_processing import (
    GpxValidationError,
    gpx_bytes_to_polygons,
)
from src.app.repository import (
    EqualsFilter,
    HexClaim,
    Repository,
    Upload,
    UploadStatus,
    UploadStatusValue,
    get_db,
)
from src.app.services.storage import S3StorageBackend, StorageBackend
from src.app.settings import settings
from src.app.utils import get_logger
from src.app.utils.lambda_types import LambdaContext, LambdaResponse
from src.app.utils.s3_events import S3Event

logger = get_logger(__name__)


def _default_storage_backend() -> StorageBackend:
    """Return the storage backend used by the handler.

    Module-level indirection so tests can monkeypatch this to inject a
    fake; in production this just constructs an :class:`S3StorageBackend`.
    """
    return S3StorageBackend()


def find_upload_by_s3_key(db: Session, key: str) -> Upload | None:
    """Find an Upload record by its associated S3 key."""
    result = Repository(db, Upload).get_filtered(
        filters=[EqualsFilter(field="s3_key", value=key)],
        page_size=1,
    )
    return result.items[0] if result.items else None


def set_upload_status(
    db: Session,
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


def handler(
    event: dict[str, Any],
    context: LambdaContext,  # noqa: ARG001
) -> LambdaResponse:
    parsed = S3Event.model_validate(event)
    # We only expect exactly one record per S3 Object created event.
    record = parsed.Records[0]

    bucket = record.s3.bucket.name
    key = unquote_plus(record.s3.object.key)

    logger.info("processing_s3_event", bucket=bucket, key=key)

    with get_db() as db:
        upload = find_upload_by_s3_key(db, key)

        if not upload:
            logger.warning("upload_not_found", key=key)
            return {"statusCode": 404, "body": "Upload not found"}

        if upload.current_status != UploadStatusValue.UPLOAD_PENDING:
            logger.info(
                "upload_not_pending",
                key=key,
                status=upload.current_status,
            )
            return {
                "statusCode": 400,
                "body": (
                    f"Upload '{key}' is in status '{upload.current_status}' and "
                    "cannot be processed."
                ),
            }

        set_upload_status(db, upload, UploadStatusValue.UPLOAD_RECEIVED)
        logger.info("upload_status_updated", key=key, status="UPLOAD_RECEIVED")

        storage = _default_storage_backend()
        data = storage.get_object(key)

        try:
            polygons = gpx_bytes_to_polygons(data, resolution=settings.H3_RESOLUTION)
        except GpxValidationError as e:
            logger.warning("gpx_invalid", key=key, reason=e.reason)
            set_upload_status(
                db, upload, UploadStatusValue.UPLOAD_INVALID, detail=e.reason
            )
            return {"statusCode": 400, "body": e.reason}

        rows = [
            {
                "upload_uid": upload.uid,
                "user_uid": upload.user_uid,
                "h3_cell": cell,
                "h3_resolution": settings.H3_RESOLUTION,
                "polygon_index": polygon.polygon_index,
                "completed_at": polygon.completed_at,
                "git_sha": settings.GIT_SHA,
            }
            for polygon in polygons
            for cell in polygon.cells
        ]

        # Bulk insert + UPLOAD_SUCCESS share a single transaction so a
        # failed insert does not leave a misleading success status.
        if rows:
            db.execute(insert(HexClaim), rows)
        set_upload_status(db, upload, UploadStatusValue.UPLOAD_SUCCESS, commit=False)
        db.commit()

        logger.info(
            "upload_processed",
            key=key,
            polygon_count=len(polygons),
            cells_inserted=len(rows),
        )

    return {"statusCode": 200, "body": "OK"}
