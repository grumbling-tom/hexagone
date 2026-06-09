"""Tests for the hex-claims and aggregated-hex-claims routers."""

from collections.abc import Callable
from datetime import UTC, datetime

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from src.app.repository import HexClaim, Upload, User
from src.app.services.password import hash_password

# ---------------------------------------------------------------------------
# /hex-claims (raw events, paginated)
# ---------------------------------------------------------------------------


def test_list_hex_claims_unauthenticated(unauthenticated_client: TestClient):
    response = unauthenticated_client.get("/api/v1/hex-claims")
    assert response.status_code == 401


def test_list_hex_claims_empty(client: TestClient):
    response = client.get("/api/v1/hex-claims")
    assert response.status_code == 200
    assert response.json()["items"] == []


def test_list_hex_claims_returns_user_claims(
    client: TestClient,
    create_upload: Callable[..., Upload],
    create_hex_claim: Callable[..., HexClaim],
):
    upload = create_upload("hike.gpx")
    create_hex_claim(upload, h3_cell="8c1f1d2806467ff", polygon_index=0)
    create_hex_claim(upload, h3_cell="8c1f1d2806469ff", polygon_index=1)

    response = client.get("/api/v1/hex-claims")
    assert response.status_code == 200
    data = response.json()
    assert len(data["items"]) == 2
    cells = {item["h3_cell"] for item in data["items"]}
    assert cells == {"8c1f1d2806467ff", "8c1f1d2806469ff"}
    for item in data["items"]:
        assert item["upload_uid"] == upload.uid
        assert "uid" in item
        assert "created_at" in item


def test_list_hex_claims_filter_by_upload_uid(
    client: TestClient,
    create_upload: Callable[..., Upload],
    create_hex_claim: Callable[..., HexClaim],
):
    upload_a = create_upload("a.gpx")
    upload_b = create_upload("b.gpx")
    create_hex_claim(upload_a, h3_cell="8c1f1d2806467ff")
    create_hex_claim(upload_b, h3_cell="8c1f1d2806469ff")

    response = client.get(f"/api/v1/hex-claims?upload_uid={upload_a.uid}")
    assert response.status_code == 200
    data = response.json()
    assert len(data["items"]) == 1
    assert data["items"][0]["upload_uid"] == upload_a.uid


def test_list_hex_claims_excludes_other_users(
    client: TestClient,
    test_db: Session,
    create_upload: Callable[..., Upload],
    create_hex_claim: Callable[..., HexClaim],
):
    other = User(email="other@example.com", password_hash=hash_password("p"))
    test_db.add(other)
    test_db.commit()
    test_db.refresh(other)

    other_upload = create_upload("other.gpx", user=other)
    create_hex_claim(other_upload, h3_cell="8c1f1d2806467ff")

    response = client.get("/api/v1/hex-claims")
    assert response.status_code == 200
    assert response.json()["items"] == []


# ---------------------------------------------------------------------------
# /aggregated-hex-claims?by=… (rollups)
# ---------------------------------------------------------------------------


def test_list_aggregated_hex_claims_unauthenticated(
    unauthenticated_client: TestClient,
):
    response = unauthenticated_client.get("/api/v1/aggregated-hex-claims?by=hex_cell")
    assert response.status_code == 401


def test_list_aggregated_hex_claims_missing_by(client: TestClient):
    response = client.get("/api/v1/aggregated-hex-claims")
    assert response.status_code == 422


def test_list_aggregated_hex_claims_invalid_by(client: TestClient):
    response = client.get("/api/v1/aggregated-hex-claims?by=bogus")
    assert response.status_code == 422


def test_list_aggregated_hex_claims_page_size_cap(client: TestClient):
    response = client.get("/api/v1/aggregated-hex-claims?by=hex_cell&page_size=10001")
    assert response.status_code == 422


def test_list_aggregated_hex_claims_by_cell_dedupes_across_uploads(
    client: TestClient,
    create_upload: Callable[..., Upload],
    create_hex_claim: Callable[..., HexClaim],
):
    upload_a = create_upload("a.gpx")
    upload_b = create_upload("b.gpx")
    # Same cell from two different uploads: claim_count=2, upload_count=2.
    create_hex_claim(upload_a, h3_cell="8c1f1d2806467ff")
    create_hex_claim(upload_b, h3_cell="8c1f1d2806467ff")
    # Unique cell from upload_a only.
    create_hex_claim(upload_a, h3_cell="8c1f1d2806469ff")

    response = client.get("/api/v1/aggregated-hex-claims?by=hex_cell")
    assert response.status_code == 200
    items = {row["h3_cell"]: row for row in response.json()["items"]}
    assert set(items) == {"8c1f1d2806467ff", "8c1f1d2806469ff"}
    assert items["8c1f1d2806467ff"]["claim_count"] == 2
    assert items["8c1f1d2806467ff"]["upload_count"] == 2
    assert items["8c1f1d2806469ff"]["claim_count"] == 1
    assert items["8c1f1d2806469ff"]["upload_count"] == 1


def test_list_aggregated_hex_claims_by_cell_same_upload_twice(
    client: TestClient,
    create_upload: Callable[..., Upload],
    create_hex_claim: Callable[..., HexClaim],
):
    upload = create_upload("hike.gpx")
    # Same cell twice within the same upload (e.g. there-and-back trail):
    # claim_count=2, upload_count=1.
    create_hex_claim(upload, h3_cell="8c1f1d2806467ff", polygon_index=0)
    create_hex_claim(upload, h3_cell="8c1f1d2806467ff", polygon_index=1)

    response = client.get("/api/v1/aggregated-hex-claims?by=hex_cell")
    assert response.status_code == 200
    items = response.json()["items"]
    assert len(items) == 1
    assert items[0]["h3_cell"] == "8c1f1d2806467ff"
    assert items[0]["claim_count"] == 2
    assert items[0]["upload_count"] == 1


def test_list_aggregated_hex_claims_by_cell_first_last_timestamps(
    client: TestClient,
    test_db: Session,
    create_upload: Callable[..., Upload],
    create_hex_claim: Callable[..., HexClaim],
):
    upload = create_upload("hike.gpx")
    a = create_hex_claim(upload, h3_cell="8c1f1d2806467ff", polygon_index=0)
    b = create_hex_claim(upload, h3_cell="8c1f1d2806467ff", polygon_index=1)
    a.created_at = datetime(2026, 1, 1, tzinfo=UTC)
    b.created_at = datetime(2026, 6, 1, tzinfo=UTC)
    test_db.commit()

    response = client.get("/api/v1/aggregated-hex-claims?by=hex_cell")
    assert response.status_code == 200
    item = response.json()["items"][0]
    assert item["first_claimed_at"].startswith("2026-01-01")
    assert item["last_claimed_at"].startswith("2026-06-01")


def test_list_aggregated_hex_claims_by_cell_paginates(
    client: TestClient,
    create_upload: Callable[..., Upload],
    create_hex_claim: Callable[..., HexClaim],
):
    upload = create_upload("hike.gpx")
    # 5 unique cells, lexicographic order: 8c…01 < 8c…02 < … < 8c…05.
    cells = [f"8c1f1d28064670{i}" for i in range(1, 6)]
    for i, cell in enumerate(cells):
        create_hex_claim(upload, h3_cell=cell, polygon_index=i)

    seen: list[str] = []
    cursor: str | None = None
    while True:
        url = "/api/v1/aggregated-hex-claims?by=hex_cell&page_size=2"
        if cursor:
            url += f"&cursor={cursor}"
        response = client.get(url)
        assert response.status_code == 200
        page = response.json()
        seen.extend(item["h3_cell"] for item in page["items"])
        if not page["has_next"]:
            break
        cursor = page["next_cursor"]

    assert seen == sorted(cells)


def test_list_aggregated_hex_claims_excludes_other_users(
    client: TestClient,
    test_db: Session,
    create_upload: Callable[..., Upload],
    create_hex_claim: Callable[..., HexClaim],
):
    other = User(email="other@example.com", password_hash=hash_password("p"))
    test_db.add(other)
    test_db.commit()
    test_db.refresh(other)

    other_upload = create_upload("other.gpx", user=other)
    create_hex_claim(other_upload, h3_cell="8c1f1d2806467ff")

    response = client.get("/api/v1/aggregated-hex-claims?by=hex_cell")
    assert response.status_code == 200
    assert response.json()["items"] == []
