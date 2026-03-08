"""File upload processing handler."""

from contextlib import contextmanager
from typing import Any
from urllib.parse import unquote_plus

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


def handler(
    event: dict[str, Any],
    context: LambdaContext,  # noqa: ARG001
) -> LambdaResponse:
    parsed = S3Event.model_validate(event)

    for record in parsed.Records:
        bucket = record.s3.bucket.name
        key = unquote_plus(record.s3.object.key)

        logger.info("processing_s3_event", bucket=bucket, key=key)

        with contextmanager(get_db)() as db:
            result = Repository(db, Upload).get_filtered(
                filters=[EqualsFilter(field="s3_key", value=key)],
                page_size=1,
            )

            if not result.items:
                logger.warning("upload_not_found", key=key)
                continue

            upload = result.items[0]

            if upload.current_status != UploadStatusValue.UPLOAD_PENDING:
                logger.info(
                    "upload_not_pending",
                    key=key,
                    status=upload.current_status,
                )
                continue

            db.add(
                UploadStatus(
                    upload_uid=upload.uid,
                    status=UploadStatusValue.UPLOAD_RECEIVED,
                    git_sha=settings.GIT_SHA,
                )
            )
            db.commit()

            logger.info("upload_status_updated", key=key, status="UPLOAD_RECEIVED")

    return {"statusCode": 200, "body": "OK"}
