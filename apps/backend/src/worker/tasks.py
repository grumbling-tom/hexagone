"""Procrastinate task bodies.

The bodies live here as plain functions; the worker app binds them with
``app.task(...)`` in ``app.py``. Keeping them un-decorated (rather than a
module-level ``@app.task`` or a shared ``Blueprint``) means the web defer path
(``defer.py``) can share the task-name constant without importing the worker's
async connector, and the bodies stay trivially unit-testable.

Bodies are sync ``def`` — Procrastinate runs them in worker threads, which suits
the CPU-bound GPX parsing. Scale throughput by adding worker replicas.
"""

from src.app.repository.database import get_db
from src.app.services.storage import S3StorageBackend
from src.app.services.upload import process_upload

#: Name the process_upload task is registered (worker) and deferred (web) under.
PROCESS_UPLOAD = "process_upload"


def process_upload_task(key: str) -> None:
    """Parse an uploaded GPX object and record its hex claims.

    Idempotent on at-least-once delivery: ``process_upload`` no-ops unless the
    upload is still ``UPLOAD_PENDING``. Only unexpected infrastructure failures
    propagate, so Procrastinate retries those and terminal outcomes (invalid
    GPX) don't.
    """
    with get_db() as db:
        process_upload(db, key, S3StorageBackend())
