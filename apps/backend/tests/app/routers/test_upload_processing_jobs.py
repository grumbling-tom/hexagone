"""Tests for the upload-processing-job ingress (Tigris notification webhook)."""

from fastapi.testclient import TestClient
from procrastinate.testing import InMemoryConnector

from src.worker.tasks import NAMESPACE
from tests.conftest import UPLOAD_NOTIFICATION_SECRET


def _payload(key: str, event_name: str = "OBJECT_CREATED_PUT") -> dict[str, object]:
    return {
        "events": [
            {
                "eventName": event_name,
                "bucket": "hexagone-gpx-uploads",
                "object": {"key": key, "size": 1024},
            }
        ]
    }


def _auth(secret: str = UPLOAD_NOTIFICATION_SECRET) -> dict[str, str]:
    return {"Authorization": f"Bearer {secret}"}


def test_missing_bearer_is_rejected(unauthenticated_client: TestClient) -> None:
    response = unauthenticated_client.post(
        "/api/v1/upload-processing-jobs", json=_payload("v1/uploads/a")
    )
    assert response.status_code == 401


def test_wrong_bearer_is_rejected(unauthenticated_client: TestClient) -> None:
    response = unauthenticated_client.post(
        "/api/v1/upload-processing-jobs",
        json=_payload("v1/uploads/a"),
        headers=_auth("nope"),
    )
    assert response.status_code == 401


def test_created_event_enqueues_a_job(
    unauthenticated_client: TestClient,
    procrastinate_connector: InMemoryConnector,
) -> None:
    response = unauthenticated_client.post(
        "/api/v1/upload-processing-jobs",
        json=_payload("v1/uploads/abc"),
        headers=_auth(),
    )

    assert response.status_code == 202
    jobs = list(procrastinate_connector.jobs.values())
    assert len(jobs) == 1
    assert jobs[0]["task_name"] == f"{NAMESPACE}:process_upload"
    assert jobs[0]["args"] == {"key": "v1/uploads/abc"}


def test_non_created_event_is_ignored(
    unauthenticated_client: TestClient,
    procrastinate_connector: InMemoryConnector,
) -> None:
    response = unauthenticated_client.post(
        "/api/v1/upload-processing-jobs",
        json=_payload("v1/uploads/abc", event_name="OBJECT_DELETED"),
        headers=_auth(),
    )

    assert response.status_code == 202
    assert procrastinate_connector.jobs == {}
