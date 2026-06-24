"""Tests for the worker's task body and registration.

The processing logic itself (``process_upload``) is covered in
``tests/app/services/test_upload.py``; here we only check the thin task wrapper
delegates to it and that the defer app registers it under the expected name.

The defer app is built inside the lifespan, so we enter the ``TestClient`` to
run startup and read it back off ``app.state``.
"""

from typing import Any

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.worker import tasks


def test_process_upload_task_is_registered(app: FastAPI) -> None:
    registered_name = f"{tasks.NAMESPACE}:process_upload"

    with TestClient(app):  # startup runs the lifespan, which registers the task
        procrastinate_app = app.state.procrastinate_app
        assert registered_name in procrastinate_app.tasks  # pyright: ignore[reportUnknownMemberType]


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

    tasks.defer_process_upload(key="v1/uploads/abc")

    assert captured == {
        "db": "db-session",
        "key": "v1/uploads/abc",
        "storage": "storage-backend",
    }
