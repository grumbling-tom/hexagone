"""Tests for the worker's task body and registration.

The processing logic itself (``process_upload``) is covered in
``tests/app/services/test_upload.py``; here we only check the thin task wrapper
delegates to it and that the worker app registers it under the expected name.
"""

from typing import Any

import pytest

from src.worker import tasks
from src.worker.app import app as worker_app


def test_process_upload_task_is_registered() -> None:
    assert tasks.PROCESS_UPLOAD in worker_app.tasks  # pyright: ignore[reportUnknownMemberType]


def test_process_upload_task_delegates_to_process_upload(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, Any] = {}

    class FakeSession:
        def __enter__(self) -> str:
            return "db-session"

        def __exit__(self, *_: object) -> bool:
            return False

    def fake_process_upload(db: object, key: str, storage: object) -> None:
        captured.update(db=db, key=key, storage=storage)

    monkeypatch.setattr(tasks, "get_db", FakeSession)
    monkeypatch.setattr(tasks, "S3StorageBackend", lambda: "storage-backend")
    monkeypatch.setattr(tasks, "process_upload", fake_process_upload)

    tasks.process_upload_task(key="v1/uploads/abc")

    assert captured == {
        "db": "db-session",
        "key": "v1/uploads/abc",
        "storage": "storage-backend",
    }
