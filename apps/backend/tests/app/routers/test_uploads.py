"""Tests for the uploads router."""

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from src.app.repository import UploadStatus, UploadStatusValue, User


def test_create_upload_success(client: TestClient):
    response = client.post(
        "/api/v1/uploads",
        json={"original_filename": "test.gpx", "file_size_bytes": 1024},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["original_filename"] == "test.gpx"
    assert data["file_size_bytes"] == 1024
    assert data["current_status"] == "UPLOAD_PENDING"
    assert data["presigned_url"] is not None
    assert data["required_headers"]["Content-Length"] == 1024
    assert data["required_headers"]["Content-Type"] == "application/gpx+xml"
    assert "uid" in data


def test_create_upload_unauthenticated(unauthenticated_client: TestClient):
    response = unauthenticated_client.post(
        "/api/v1/uploads",
        json={"original_filename": "test.gpx", "file_size_bytes": 1024},
    )
    assert response.status_code == 401


def test_list_uploads_empty(client: TestClient):
    response = client.get("/api/v1/uploads")
    assert response.status_code == 200
    data = response.json()
    assert data["items"] == []


def test_list_uploads_excludes_pending_by_default(client: TestClient):
    client.post(
        "/api/v1/uploads",
        json={"original_filename": "test.gpx", "file_size_bytes": 1024},
    )
    response = client.get("/api/v1/uploads")
    assert response.status_code == 200
    assert len(response.json()["items"]) == 0


def test_list_uploads_includes_pending_when_requested(client: TestClient):
    client.post(
        "/api/v1/uploads",
        json={"original_filename": "test.gpx", "file_size_bytes": 1024},
    )
    response = client.get("/api/v1/uploads?statuses=UPLOAD_PENDING")
    assert response.status_code == 200
    data = response.json()
    assert len(data["items"]) == 1
    assert data["items"][0]["current_status"] == "UPLOAD_PENDING"


def test_list_uploads_with_received_status(
    client: TestClient, test_db: Session, test_user: User
):
    create_resp = client.post(
        "/api/v1/uploads",
        json={"original_filename": "test.gpx", "file_size_bytes": 512},
    )
    upload_uid = create_resp.json()["uid"]

    # Simulate file received
    status = UploadStatus(
        upload_uid=upload_uid,
        status=UploadStatusValue.UPLOAD_RECEIVED,
    )
    test_db.add(status)
    test_db.commit()

    response = client.get("/api/v1/uploads")
    assert response.status_code == 200
    data = response.json()
    assert len(data["items"]) == 1
    assert data["items"][0]["current_status"] == "UPLOAD_RECEIVED"
    assert data["items"][0]["presigned_url"] is not None


def test_list_uploads_unauthenticated(unauthenticated_client: TestClient):
    response = unauthenticated_client.get("/api/v1/uploads")
    assert response.status_code == 401


def test_list_uploads_invalid_status(client: TestClient):
    response = client.get("/api/v1/uploads?statuses=INVALID")
    assert response.status_code == 422
