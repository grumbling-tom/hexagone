"""File upload processing handler."""

from typing import Any
from urllib.parse import unquote_plus

from sqlalchemy.orm import Session

from src.app.repository import (
    EqualsFilter,
    Repository,
    Upload,
    UploadStatus,
    UploadStatusValue,
    get_db,
)
from src.app.settings import settings
from src.app.utils import get_logger
from src.app.utils.lambda_types import LambdaContext, LambdaResponse
from src.app.utils.s3_events import S3Event

logger = get_logger(__name__)


def find_upload_by_s3_key(db: Session, key: str) -> Upload | None:
    """Find an Upload record by its associated S3 key."""
    result = Repository(db, Upload).get_filtered(
        filters=[EqualsFilter(field="s3_key", value=key)],
        page_size=1,
    )
    return result.items[0] if result.items else None


def set_upload_status(db: Session, upload: Upload, status: UploadStatusValue) -> None:
    """Given an upload, create a new UploadStatus record with the given status."""
    db.add(
        UploadStatus(
            upload_uid=upload.uid,
            status=status,
            git_sha=settings.GIT_SHA,
        )
    )
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

    return {"statusCode": 200, "body": "OK"}
