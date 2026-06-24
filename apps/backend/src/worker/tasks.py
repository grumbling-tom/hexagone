from procrastinate import Blueprint

from src.app.repository.database import get_db
from src.app.services.storage import S3StorageBackend
from src.app.services.upload import process_upload

NAMESPACE = "hexagone"

blueprint = Blueprint()


@blueprint.task(name="process_upload")
def defer_process_upload(key: str) -> None:
    """Parse an uploaded GPX object and record its hex claims.

    Idempotent on at-least-once delivery: ``process_upload`` no-ops unless the
    upload is still ``UPLOAD_PENDING``. Only unexpected infrastructure failures
    propagate, so Procrastinate retries those and terminal outcomes (invalid
    GPX) don't.
    """
    with get_db() as db:
        process_upload(db, key, S3StorageBackend())
