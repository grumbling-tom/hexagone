"""Tests for the upload processing router."""

from collections.abc import Callable
from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient
from mypy_boto3_s3 import S3Client
from sqlalchemy.orm import Session

from src.app.repository import HexClaim, Upload, UploadStatusValue, User
from src.app.services.gpx import Point
from src.app.settings import settings

URL = "/api/v1/upload-processing-jobs"


@pytest.fixture(autouse=True)
def _fine_h3_resolution(monkeypatch: pytest.MonkeyPatch) -> None:  # pyright: ignore[reportUnusedFunction]
    """Pin H3 resolution to 12 so the small fixture loops always claim cells."""
    monkeypatch.setattr(settings, "H3_RESOLUTION", 12)


@pytest.fixture
def uploaded_loop(
    s3_client: S3Client,
    create_upload: Callable[..., Upload],
    make_square_loop: Callable[..., list[Point]],
    make_gpx_doc: Callable[[list[list[Point]]], bytes],
) -> Upload:
    """A pending upload whose valid, one-loop GPX file is already in storage."""
    data = make_gpx_doc([make_square_loop(start_time=datetime(2024, 1, 1, tzinfo=UTC))])
    upload = create_upload("loop.gpx", file_size_bytes=len(data))
    s3_client.put_object(
        Bucket=settings.HEXAGONE_S3_BUCKET, Key=upload.s3_key, Body=data
    )
    return upload


def _claim_count(db: Session, upload: Upload) -> int:
    return db.query(HexClaim).filter(HexClaim.upload_uid == upload.uid).count()


def test_processes_a_landed_upload(
    client: TestClient, test_db: Session, uploaded_loop: Upload
):
    response = client.post(URL, json={"upload_uid": uploaded_loop.uid})

    assert response.status_code == 200
    data = response.json()
    assert data["uid"] == uploaded_loop.uid
    assert data["current_status"] == UploadStatusValue.UPLOAD_SUCCESS
    assert data["current_status_detail"] is None
    assert _claim_count(test_db, uploaded_loop) > 0


def test_invalid_file_returns_reason(
    client: TestClient,
    test_db: Session,
    s3_client: S3Client,
    create_upload: Callable[..., Upload],
):
    upload = create_upload("broken.gpx")
    s3_client.put_object(
        Bucket=settings.HEXAGONE_S3_BUCKET, Key=upload.s3_key, Body=b"not a gpx file"
    )

    response = client.post(URL, json={"upload_uid": upload.uid})

    assert response.status_code == 200
    data = response.json()
    assert data["current_status"] == UploadStatusValue.UPLOAD_INVALID
    assert data["current_status_detail"] == "invalid GPX"
    assert _claim_count(test_db, upload) == 0


def test_file_not_in_storage_yet_leaves_upload_pending(
    client: TestClient, test_db: Session, create_upload: Callable[..., Upload]
):
    upload = create_upload("not-yet.gpx")

    response = client.post(URL, json={"upload_uid": upload.uid})

    assert response.status_code == 409
    test_db.refresh(upload)
    assert upload.current_status == UploadStatusValue.UPLOAD_PENDING


def test_calling_twice_does_not_duplicate_claims(
    client: TestClient, test_db: Session, uploaded_loop: Upload
):
    client.post(URL, json={"upload_uid": uploaded_loop.uid})
    first = _claim_count(test_db, uploaded_loop)

    response = client.post(URL, json={"upload_uid": uploaded_loop.uid})

    assert response.status_code == 200
    assert response.json()["current_status"] == UploadStatusValue.UPLOAD_SUCCESS
    assert _claim_count(test_db, uploaded_loop) == first


def test_someone_elses_upload_is_not_found(
    client: TestClient,
    s3_client: S3Client,
    create_user: Callable[..., User],
    create_upload: Callable[..., Upload],
):
    other = create_user()
    upload = create_upload("theirs.gpx", user=other)
    s3_client.put_object(
        Bucket=settings.HEXAGONE_S3_BUCKET, Key=upload.s3_key, Body=b"<gpx/>"
    )

    response = client.post(URL, json={"upload_uid": upload.uid})

    assert response.status_code == 404
    assert upload.current_status == UploadStatusValue.UPLOAD_PENDING


def test_unknown_upload_is_not_found(client: TestClient):
    response = client.post(URL, json={"upload_uid": "does-not-exist"})
    assert response.status_code == 404


def test_requires_sign_in(unauthenticated_client: TestClient, uploaded_loop: Upload):
    response = unauthenticated_client.post(URL, json={"upload_uid": uploaded_loop.uid})
    assert response.status_code == 401
