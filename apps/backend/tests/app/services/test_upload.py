"""Tests for upload service."""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime, timedelta

import boto3
import pytest
from mypy_boto3_s3 import S3Client
from sqlalchemy.orm import Session

from src.app.repository import (
    HexClaim,
    ScopedRepository,
    SystemPolicy,
    Transaction,
    Upload,
    UploadStatus,
    UploadStatusValue,
    User,
)
from src.app.services.gpx import Point
from src.app.services.password import hash_password
from src.app.services.permissions import ViewerPolicy
from src.app.services.storage import S3StorageBackend
from src.app.services.upload import (
    create_upload,
    list_uploads,
    maybe_presigned_url,
    process_upload,
)
from src.app.settings import settings


@pytest.fixture(autouse=True)
def _fine_h3_resolution(monkeypatch: pytest.MonkeyPatch) -> None:  # pyright: ignore[reportUnusedFunction]
    """Pin H3 resolution to 12 for the processing tests.

    The factory loops are only ~50 m across; at the default resolution (10,
    ~65 m hexagon edge) a polygon that small can enclose no cell centre and
    rasterise to zero cells. Res 12 (~9 m edge) guarantees claims, so the
    tests don't depend on the ambient ``H3_RESOLUTION`` setting.
    """
    monkeypatch.setattr(settings, "H3_RESOLUTION", 12)


@pytest.fixture
def s3_client() -> S3Client:
    """Return a boto3 S3 client wired to the moto bucket from conftest."""
    return boto3.client("s3", region_name="eu-west-2")  # pyright: ignore[reportUnknownMemberType]


@pytest.fixture
def uploads(test_db: Session, test_user: User) -> ScopedRepository[Upload]:
    """Upload repository scoped to ``test_user``."""
    return ScopedRepository(test_db, Upload, ViewerPolicy(test_user))


@pytest.fixture
def process(test_db: Session) -> Callable[[str], None]:
    """Run the worker on an object key, as the worker does: system-scoped."""

    def _run(key: str) -> None:
        process_upload(
            ScopedRepository(test_db, Upload, SystemPolicy()),
            ScopedRepository(test_db, UploadStatus, SystemPolicy()),
            ScopedRepository(test_db, HexClaim, SystemPolicy()),
            Transaction(test_db),
            key,
            S3StorageBackend(),
        )

    return _run


def _latest_status(db: Session, upload: Upload) -> UploadStatus:
    db.refresh(upload)
    return upload.statuses[-1]


def _hex_claims_for(db: Session, upload: Upload) -> list[HexClaim]:
    return list(
        db.query(HexClaim)
        .filter(HexClaim.upload_uid == upload.uid)
        .order_by(HexClaim.polygon_index, HexClaim.h3_cell)
        .all()
    )


def test_create_upload(
    test_db: Session,
    test_user: User,
    uploads: ScopedRepository[Upload],
    tx: Transaction,
):
    upload = create_upload(
        uploads,
        tx,
        user=test_user,
        original_filename="test.gpx",
        file_size_bytes=1024,
    )

    assert upload.original_filename == "test.gpx"
    assert upload.file_size_bytes == 1024
    assert upload.current_status == UploadStatusValue.UPLOAD_PENDING
    assert upload.s3_key.startswith("v1/uploads/")


def test_create_upload_persists(
    test_db: Session,
    test_user: User,
    uploads: ScopedRepository[Upload],
    tx: Transaction,
):
    upload = create_upload(
        uploads,
        tx,
        user=test_user,
        original_filename="track.gpx",
        file_size_bytes=2048,
    )

    persisted = test_db.query(Upload).filter_by(uid=upload.uid).one()
    assert persisted.original_filename == "track.gpx"
    assert persisted.file_size_bytes == 2048
    assert persisted.user_uid == test_user.uid

    statuses = test_db.query(UploadStatus).filter_by(upload_uid=upload.uid).all()
    assert len(statuses) == 1
    assert statuses[0].status == UploadStatusValue.UPLOAD_PENDING


def test_list_uploads_excludes_pending(
    test_db: Session,
    test_user: User,
    uploads: ScopedRepository[Upload],
    tx: Transaction,
):
    create_upload(
        uploads,
        tx,
        user=test_user,
        original_filename="pending.gpx",
        file_size_bytes=100,
    )

    result = list_uploads(uploads)
    assert len(result.items) == 0


def test_list_uploads_includes_pending_when_requested(
    test_db: Session,
    test_user: User,
    uploads: ScopedRepository[Upload],
    tx: Transaction,
):
    create_upload(
        uploads,
        tx,
        user=test_user,
        original_filename="pending.gpx",
        file_size_bytes=100,
    )

    result = list_uploads(
        uploads,
        statuses=[UploadStatusValue.UPLOAD_PENDING],
    )
    assert len(result.items) == 1
    assert result.items[0].current_status == UploadStatusValue.UPLOAD_PENDING


def test_list_uploads_filters_by_user(
    test_db: Session,
    test_user: User,
    uploads: ScopedRepository[Upload],
    tx: Transaction,
):
    other_user = User(
        email="other@example.com",
        password_hash=hash_password("pass"),
    )
    test_db.add(other_user)
    test_db.commit()
    test_db.refresh(other_user)

    create_upload(
        ScopedRepository(test_db, Upload, ViewerPolicy(other_user)),
        tx,
        user=other_user,
        original_filename="other.gpx",
        file_size_bytes=100,
    )

    result = list_uploads(
        uploads,
        statuses=[UploadStatusValue.UPLOAD_PENDING],
    )
    assert len(result.items) == 0


def test_list_uploads_with_received_status(
    test_db: Session,
    test_user: User,
    uploads: ScopedRepository[Upload],
    tx: Transaction,
):
    upload = create_upload(
        uploads,
        tx,
        user=test_user,
        original_filename="received.gpx",
        file_size_bytes=500,
    )

    test_db.add(
        UploadStatus(
            upload_uid=upload.uid,
            status=UploadStatusValue.UPLOAD_RECEIVED,
        )
    )
    test_db.commit()

    result = list_uploads(uploads)
    assert len(result.items) == 1
    assert result.items[0].current_status == UploadStatusValue.UPLOAD_RECEIVED


def test_list_uploads_pagination_with_status_filter(
    test_db: Session,
    test_user: User,
    uploads: ScopedRepository[Upload],
    tx: Transaction,
):
    # Create 5 RECEIVED uploads
    for i in range(5):
        upload = create_upload(
            uploads,
            tx,
            user=test_user,
            original_filename=f"received_{i}.gpx",
            file_size_bytes=100,
        )
        test_db.add(
            UploadStatus(
                upload_uid=upload.uid,
                status=UploadStatusValue.UPLOAD_RECEIVED,
            )
        )
        test_db.commit()

    # Create 5 PENDING uploads (excluded by default filter)
    for i in range(5):
        create_upload(
            uploads,
            tx,
            user=test_user,
            original_filename=f"pending_{i}.gpx",
            file_size_bytes=100,
        )

    # First page: exactly 3 items
    page1 = list_uploads(uploads, page_size=3)
    assert len(page1.items) == 3
    assert page1.has_next is True

    # Second page: exactly 2 items
    page2 = list_uploads(
        uploads,
        page_size=3,
        cursor=page1.next_cursor,
    )
    assert len(page2.items) == 2
    assert page2.has_next is False


def _create_upload_with_status(
    test_db: Session,
    test_user: User,
    status: str,
    filename: str = "test.gpx",
) -> Upload:
    """Helper to create an upload and advance it to the given status."""
    upload = Upload(
        user_uid=test_user.uid,
        original_filename=filename,
        file_size_bytes=100,
        s3_bucket_name="test-bucket",
        s3_key=f"uploads/test/{filename}",
    )
    test_db.add(upload)
    test_db.flush()
    test_db.add(
        UploadStatus(
            upload_uid=upload.uid,
            status=UploadStatusValue.UPLOAD_PENDING,
        )
    )
    if status != UploadStatusValue.UPLOAD_PENDING:
        test_db.add(
            UploadStatus(
                upload_uid=upload.uid,
                status=status,
            )
        )
    test_db.commit()
    test_db.refresh(upload)
    return upload


def test_maybe_presigned_url_non_pending(
    test_db: Session,
    test_user: User,
):
    """Non-pending uploads should get a presigned GET URL."""
    upload = _create_upload_with_status(
        test_db, test_user, UploadStatusValue.UPLOAD_RECEIVED, "received.gpx"
    )

    storage = S3StorageBackend()
    url, headers = maybe_presigned_url(upload, storage)
    assert url is not None
    assert "X-Amz-Signature" in url
    assert headers is None


def test_maybe_presigned_url_get_url_for_received(
    test_db: Session,
    test_user: User,
):
    """UPLOAD_RECEIVED uploads should get a GET URL with no required_headers."""
    upload = _create_upload_with_status(
        test_db, test_user, UploadStatusValue.UPLOAD_RECEIVED, "received.gpx"
    )

    storage = S3StorageBackend()
    url, headers = maybe_presigned_url(upload, storage)
    assert url is not None
    assert "X-Amz-Signature" in url
    assert headers is None


def test_maybe_presigned_url_get_url_for_success(
    test_db: Session,
    test_user: User,
):
    """UPLOAD_SUCCESS uploads should get a GET URL with no required_headers."""
    upload = _create_upload_with_status(
        test_db, test_user, UploadStatusValue.UPLOAD_SUCCESS, "success.gpx"
    )

    storage = S3StorageBackend()
    url, headers = maybe_presigned_url(upload, storage)
    assert url is not None
    assert "X-Amz-Signature" in url
    assert headers is None


def test_maybe_presigned_url_old_pending(
    test_db: Session,
    test_user: User,
):
    """Pending uploads older than the window should not get a presigned URL."""
    upload = Upload(
        user_uid=test_user.uid,
        original_filename="old.gpx",
        file_size_bytes=100,
        s3_bucket_name="test-bucket",
        s3_key="uploads/test/old.gpx",
        created_at=datetime.now(UTC) - timedelta(minutes=10),
    )
    test_db.add(upload)
    test_db.flush()
    test_db.add(
        UploadStatus(
            upload_uid=upload.uid,
            status=UploadStatusValue.UPLOAD_PENDING,
        )
    )
    test_db.commit()
    test_db.refresh(upload)

    storage = S3StorageBackend()
    url, headers = maybe_presigned_url(upload, storage)
    assert url is None
    assert headers is None


def test_maybe_presigned_url_recent_pending(
    test_db: Session,
    test_user: User,
    uploads: ScopedRepository[Upload],
    tx: Transaction,
):
    """Recent pending uploads should get a presigned URL and headers."""
    upload = create_upload(
        uploads,
        tx,
        user=test_user,
        original_filename="new.gpx",
        file_size_bytes=1024,
    )

    storage = S3StorageBackend()
    url, headers = maybe_presigned_url(upload, storage)
    assert url is not None
    assert headers is not None
    assert headers["Content-Length"] == "1024"


# ---------------------------------------------------------------------------
# process_upload
#
# GPX-payload factories (make_square_loop / make_open_track / make_gpx_doc)
# live in the sibling conftest.py so they're shared with test_gpx.py.
# ---------------------------------------------------------------------------


def test_happy_path_inserts_hex_claims_and_marks_success(
    test_db: Session,
    s3_client: S3Client,
    create_upload: Callable[..., Upload],
    make_square_loop: Callable[..., list[Point]],
    make_gpx_doc: Callable[[list[list[Point]]], bytes],
    process: Callable[[str], None],
):
    start = datetime(2024, 1, 1, 12, 0, 0, tzinfo=UTC)
    pts = make_square_loop(start_time=start)
    data = make_gpx_doc([pts])

    upload = create_upload("happy.gpx", file_size_bytes=len(data))
    s3_client.put_object(
        Bucket=settings.HEXAGONE_S3_BUCKET, Key=upload.s3_key, Body=data
    )

    process(upload.s3_key)

    rows = _hex_claims_for(test_db, upload)
    assert len(rows) > 0
    assert {row.polygon_index for row in rows} == {0}
    assert all(row.h3_resolution == settings.H3_RESOLUTION for row in rows)
    assert all(row.git_sha == settings.GIT_SHA for row in rows)
    assert all(row.user_uid == upload.user_uid for row in rows)
    # All H3 cell IDs are 15 hex chars regardless of resolution.
    assert all(len(row.h3_cell) == 15 for row in rows)

    # completed_at must match the closing trackpoint timestamp for the
    # one detected polygon.
    completed_at_values = {row.completed_at for row in rows}
    assert len(completed_at_values) == 1
    closing_ts = next(iter(completed_at_values))
    assert closing_ts is not None
    assert closing_ts.timestamp() >= start.timestamp()

    latest = _latest_status(test_db, upload)
    assert latest.status == UploadStatusValue.UPLOAD_SUCCESS
    assert latest.detail is None
    assert latest.git_sha == settings.GIT_SHA

    # And the UPLOAD_RECEIVED status must have been written too.
    statuses = [s.status for s in upload.statuses]
    assert statuses == [
        UploadStatusValue.UPLOAD_PENDING,
        UploadStatusValue.UPLOAD_RECEIVED,
        UploadStatusValue.UPLOAD_SUCCESS,
    ]


def test_two_overlapping_loops_produce_distinct_polygon_indices(
    test_db: Session,
    s3_client: S3Client,
    create_upload: Callable[..., Upload],
    make_square_loop: Callable[..., list[Point]],
    make_gpx_doc: Callable[[list[list[Point]]], bytes],
    process: Callable[[str], None],
):
    # Two identical square loops in two segments → cells fully overlap,
    # but each loop is a distinct polygon with its own polygon_index and
    # closing timestamp.
    start_a = datetime(2024, 1, 1, 12, 0, 0, tzinfo=UTC)
    start_b = datetime(2024, 1, 1, 13, 0, 0, tzinfo=UTC)
    loop_a = make_square_loop(start_time=start_a)
    loop_b = make_square_loop(start_time=start_b)
    data = make_gpx_doc([loop_a, loop_b])

    upload = create_upload("overlap.gpx", file_size_bytes=len(data))
    s3_client.put_object(
        Bucket=settings.HEXAGONE_S3_BUCKET, Key=upload.s3_key, Body=data
    )

    process(upload.s3_key)

    rows = _hex_claims_for(test_db, upload)
    poly_indices = {row.polygon_index for row in rows}
    assert poly_indices == {0, 1}

    cells_by_index: dict[int, set[str]] = {0: set(), 1: set()}
    completed_by_index: dict[int, set[datetime | None]] = {0: set(), 1: set()}
    for row in rows:
        cells_by_index[row.polygon_index].add(row.h3_cell)
        completed_by_index[row.polygon_index].add(row.completed_at)

    # Identical loops → cells overlap.
    overlap = cells_by_index[0] & cells_by_index[1]
    assert overlap, "expected overlapping cells across the two loops"

    # Each polygon has exactly one closing timestamp, and they differ.
    [ts0] = completed_by_index[0]
    [ts1] = completed_by_index[1]
    assert ts0 is not None
    assert ts1 is not None
    assert ts0.timestamp() < ts1.timestamp()


def test_no_timestamps_yields_completed_at_null(
    test_db: Session,
    s3_client: S3Client,
    create_upload: Callable[..., Upload],
    make_square_loop: Callable[..., list[Point]],
    make_gpx_doc: Callable[[list[list[Point]]], bytes],
    process: Callable[[str], None],
):
    pts = make_square_loop(start_time=None)
    data = make_gpx_doc([pts])

    upload = create_upload("no-time.gpx", file_size_bytes=len(data))
    s3_client.put_object(
        Bucket=settings.HEXAGONE_S3_BUCKET, Key=upload.s3_key, Body=data
    )

    process(upload.s3_key)

    rows = _hex_claims_for(test_db, upload)
    assert len(rows) > 0
    assert all(row.completed_at is None for row in rows)

    latest = _latest_status(test_db, upload)
    assert latest.status == UploadStatusValue.UPLOAD_SUCCESS


def test_oversized_payload_marks_invalid(
    test_db: Session,
    s3_client: S3Client,
    create_upload: Callable[..., Upload],
    monkeypatch: pytest.MonkeyPatch,
    process: Callable[[str], None],
):
    # Tighten the cap so we don't have to push an actual 10 MiB blob.
    monkeypatch.setattr(settings, "MAX_GPX_BYTES", 16)
    data = b"x" * 32

    upload = create_upload("oversize.gpx", file_size_bytes=len(data))
    s3_client.put_object(
        Bucket=settings.HEXAGONE_S3_BUCKET, Key=upload.s3_key, Body=data
    )

    process(upload.s3_key)

    assert _hex_claims_for(test_db, upload) == []
    latest = _latest_status(test_db, upload)
    assert latest.status == UploadStatusValue.UPLOAD_INVALID
    assert latest.detail == "file too large"


def test_malformed_xml_marks_invalid(
    test_db: Session,
    s3_client: S3Client,
    create_upload: Callable[..., Upload],
    process: Callable[[str], None],
):
    data = b"not xml at all"
    upload = create_upload("bad.gpx", file_size_bytes=len(data))
    s3_client.put_object(
        Bucket=settings.HEXAGONE_S3_BUCKET, Key=upload.s3_key, Body=data
    )

    process(upload.s3_key)

    assert _hex_claims_for(test_db, upload) == []
    latest = _latest_status(test_db, upload)
    assert latest.status == UploadStatusValue.UPLOAD_INVALID
    assert latest.detail == "invalid GPX"


def test_xxe_attempt_marks_invalid(
    test_db: Session,
    s3_client: S3Client,
    create_upload: Callable[..., Upload],
    process: Callable[[str], None],
):
    data = (
        b'<?xml version="1.0"?>\n'
        b"<!DOCTYPE foo [\n"
        b'  <!ENTITY xxe SYSTEM "file:///etc/passwd">\n'
        b"]>\n"
        b'<gpx version="1.1"><trk><trkseg>\n'
        b'<trkpt lat="0.0" lon="0.0"><name>&xxe;</name></trkpt>\n'
        b"</trkseg></trk></gpx>\n"
    )
    upload = create_upload("xxe.gpx", file_size_bytes=len(data))
    s3_client.put_object(
        Bucket=settings.HEXAGONE_S3_BUCKET, Key=upload.s3_key, Body=data
    )

    process(upload.s3_key)

    assert _hex_claims_for(test_db, upload) == []
    latest = _latest_status(test_db, upload)
    assert latest.status == UploadStatusValue.UPLOAD_INVALID


def test_billion_laughs_marks_invalid(
    test_db: Session,
    s3_client: S3Client,
    create_upload: Callable[..., Upload],
    process: Callable[[str], None],
):
    lol = b"&lol;" * 10
    lol2 = b"&lol2;" * 10
    lol3 = b"&lol3;" * 10
    data = (
        b'<?xml version="1.0"?>\n'
        b"<!DOCTYPE lolz [\n"
        b'  <!ENTITY lol "lol">\n'
        b'  <!ENTITY lol2 "' + lol + b'">\n'
        b'  <!ENTITY lol3 "' + lol2 + b'">\n'
        b'  <!ENTITY lol4 "' + lol3 + b'">\n'
        b"]>\n"
        b'<gpx version="1.1"><trk><name>&lol4;</name></trk></gpx>\n'
    )
    upload = create_upload("lol.gpx", file_size_bytes=len(data))
    s3_client.put_object(
        Bucket=settings.HEXAGONE_S3_BUCKET, Key=upload.s3_key, Body=data
    )

    process(upload.s3_key)

    assert _hex_claims_for(test_db, upload) == []
    latest = _latest_status(test_db, upload)
    assert latest.status == UploadStatusValue.UPLOAD_INVALID


def test_no_closed_loops_succeeds_with_zero_rows(
    test_db: Session,
    s3_client: S3Client,
    create_upload: Callable[..., Upload],
    make_open_track: Callable[..., list[Point]],
    make_gpx_doc: Callable[[list[list[Point]]], bytes],
    process: Callable[[str], None],
):
    pts = make_open_track()
    data = make_gpx_doc([pts])

    upload = create_upload("open.gpx", file_size_bytes=len(data))
    s3_client.put_object(
        Bucket=settings.HEXAGONE_S3_BUCKET, Key=upload.s3_key, Body=data
    )

    process(upload.s3_key)

    assert _hex_claims_for(test_db, upload) == []

    latest = _latest_status(test_db, upload)
    assert latest.status == UploadStatusValue.UPLOAD_SUCCESS


def test_replay_of_already_received_upload_is_a_noop(
    test_db: Session,
    s3_client: S3Client,
    create_upload: Callable[..., Upload],
    make_square_loop: Callable[..., list[Point]],
    make_gpx_doc: Callable[[list[list[Point]]], bytes],
    process: Callable[[str], None],
):
    # At-least-once delivery: a second notification for an upload already
    # past PENDING must not reprocess or append status rows.
    pts = make_square_loop()
    data = make_gpx_doc([pts])

    upload = create_upload(
        "replay.gpx",
        file_size_bytes=len(data),
        status_values=[
            UploadStatusValue.UPLOAD_PENDING,
            UploadStatusValue.UPLOAD_RECEIVED,
        ],
    )
    s3_client.put_object(
        Bucket=settings.HEXAGONE_S3_BUCKET, Key=upload.s3_key, Body=data
    )

    process(upload.s3_key)

    # No claims inserted, no extra status rows appended.
    assert _hex_claims_for(test_db, upload) == []
    test_db.refresh(upload)
    assert [s.status for s in upload.statuses] == [
        UploadStatusValue.UPLOAD_PENDING,
        UploadStatusValue.UPLOAD_RECEIVED,
    ]


def test_unknown_key_is_a_noop(
    test_db: Session,
    process: Callable[[str], None],
):
    # A notification for an object with no matching Upload row must not raise.
    process("v1/uploads/does-not-exist")
