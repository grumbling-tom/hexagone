"""Tests for the Repository pattern and filtering functionality."""

import base64
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING

import pytest

from src.app.repository import (
    EqualsFilter,
    GreaterThanFilter,
    GreaterThanOrEqualFilter,
    InFilter,
    IsNullFilter,
    LessThanFilter,
    LessThanOrEqualFilter,
    LikeFilter,
    NotEqualsFilter,
    NotInFilter,
    RangeFilter,
    Repository,
    Upload,
    UploadStatus,
    UploadStatusValue,
    User,
)
from src.app.services.password import hash_password
from src.app.settings import settings
from src.app.utils import SortOrder

if TYPE_CHECKING:
    from sqlalchemy.orm import Session


# Basic Repository Operations Tests


def test_get_all_returns_all_uploads(
    test_db: Session, create_upload: Callable[..., Upload]
):
    create_upload("a.gpx")
    create_upload("b.gpx")
    repo = Repository(test_db, Upload)

    result = repo.get_all()
    assert len(result.items) == 2
    filenames = {u.original_filename for u in result.items}
    assert filenames == {"a.gpx", "b.gpx"}
    assert result.has_previous is False
    assert result.previous_cursor is None
    assert result.has_next is False
    assert result.next_cursor is None


def test_pagination_basic(test_db: Session, create_upload: Callable[..., Upload]):
    for i in range(5):
        create_upload(f"file_{i}.gpx")
    repo = Repository(test_db, Upload)

    page1 = repo.get_all(page_size=2)
    assert len(page1.items) == 2
    assert page1.has_previous is False
    assert page1.has_next is True

    page2 = repo.get_all(page_size=2, cursor=page1.next_cursor)
    assert len(page2.items) == 2
    assert page2.has_previous is True
    assert page2.has_next is True

    page3 = repo.get_all(page_size=2, cursor=page2.next_cursor)
    assert len(page3.items) == 1
    assert page3.has_previous is True
    assert page3.has_next is False

    all_uids = [u.uid for u in page1.items + page2.items + page3.items]
    assert len(all_uids) == len(set(all_uids))


def test_repository_uses_default_page_size(
    test_db: Session, create_upload: Callable[..., Upload]
):
    for i in range(settings.DEFAULT_PAGE_SIZE + 5):
        create_upload(f"file_{i}.gpx")
    repo = Repository(test_db, Upload)

    result = repo.get_all()
    assert len(result.items) == settings.DEFAULT_PAGE_SIZE
    assert result.has_next is True


def test_repository_page_size_can_override_default(
    test_db: Session, create_upload: Callable[..., Upload]
):
    for i in range(15):
        create_upload(f"file_{i}.gpx")
    repo = Repository(test_db, Upload)

    custom_page_size = 5
    assert custom_page_size != settings.DEFAULT_PAGE_SIZE

    result = repo.get_all(page_size=custom_page_size)
    assert len(result.items) == custom_page_size
    assert result.has_next is True


def test_custom_sorting_by_original_filename(
    test_db: Session, create_upload: Callable[..., Upload]
):
    create_upload("zebra.gpx")
    create_upload("alpha.gpx")
    create_upload("gamma.gpx")
    repo = Repository(test_db, Upload)

    result_asc = repo.get_all(
        sort_field=Upload.original_filename, sort_order=SortOrder.ASC
    )
    names_asc = [u.original_filename for u in result_asc.items]
    assert names_asc == ["alpha.gpx", "gamma.gpx", "zebra.gpx"]

    result_desc = repo.get_all(
        sort_field=Upload.original_filename, sort_order=SortOrder.DESC
    )
    names_desc = [u.original_filename for u in result_desc.items]
    assert names_desc == ["zebra.gpx", "gamma.gpx", "alpha.gpx"]


def test_pagination_with_custom_sorting(
    test_db: Session, create_upload: Callable[..., Upload]
):
    names = ["delta.gpx", "alpha.gpx", "echo.gpx", "bravo.gpx", "charlie.gpx"]
    for name in names:
        create_upload(name)
    repo = Repository(test_db, Upload)

    page1 = repo.get_all(
        page_size=2, sort_field=Upload.original_filename, sort_order=SortOrder.ASC
    )
    assert [u.original_filename for u in page1.items] == ["alpha.gpx", "bravo.gpx"]
    assert page1.has_next is True

    page2 = repo.get_all(
        page_size=2,
        cursor=page1.next_cursor,
        sort_field=Upload.original_filename,
        sort_order=SortOrder.ASC,
    )
    assert [u.original_filename for u in page2.items] == ["charlie.gpx", "delta.gpx"]
    assert page2.has_next is True

    page3 = repo.get_all(
        page_size=2,
        cursor=page2.next_cursor,
        sort_field=Upload.original_filename,
        sort_order=SortOrder.ASC,
    )
    assert [u.original_filename for u in page3.items] == ["echo.gpx"]
    assert page3.has_next is False

    all_names = [u.original_filename for u in page1.items + page2.items + page3.items]
    assert len(all_names) == len(set(all_names))
    assert set(all_names) == set(names)


# Cursor Validation Tests


def test_cursor_validation_mismatched_sort_field(
    test_db: Session, create_upload: Callable[..., Upload]
):
    for i in range(3):
        create_upload(f"file_{i}.gpx")
    repo = Repository(test_db, Upload)

    page1 = repo.get_all(page_size=2, sort_field=Upload.uid, sort_order=SortOrder.ASC)
    assert page1.next_cursor is not None

    with pytest.raises(ValueError, match=r"Cursor sort parameters.*do not match"):
        repo.get_all(
            page_size=2,
            cursor=page1.next_cursor,
            sort_field=Upload.original_filename,
            sort_order=SortOrder.ASC,
        )


def test_cursor_validation_mismatched_sort_order(
    test_db: Session, create_upload: Callable[..., Upload]
):
    for i in range(3):
        create_upload(f"file_{i}.gpx")
    repo = Repository(test_db, Upload)

    page1 = repo.get_all(page_size=2, sort_field=Upload.uid, sort_order=SortOrder.ASC)
    assert page1.next_cursor is not None

    with pytest.raises(ValueError, match=r"Cursor sort parameters.*do not match"):
        repo.get_all(
            page_size=2,
            cursor=page1.next_cursor,
            sort_field=Upload.uid,
            sort_order=SortOrder.DESC,
        )


def test_invalid_cursor_format(test_db: Session, create_upload: Callable[..., Upload]):
    create_upload("test.gpx")
    repo = Repository(test_db, Upload)

    with pytest.raises(ValueError, match="Invalid cursor format"):
        repo.get_all(cursor="not-valid-base64!")

    invalid_json = base64.b64encode(b"not json").decode()
    with pytest.raises(ValueError, match="Invalid cursor format"):
        repo.get_all(cursor=invalid_json)

    incomplete_cursor = base64.b64encode(b'{"uid": "test"}').decode()
    with pytest.raises(ValueError, match="Invalid cursor format"):
        repo.get_all(cursor=incomplete_cursor)


# Filter Tests


def test_equals_filter(test_db: Session, create_upload: Callable[..., Upload]):
    create_upload("alpha.gpx")
    create_upload("beta.gpx")
    create_upload("alpha.gpx", file_size_bytes=200)
    repo = Repository(test_db, Upload)

    result = repo.get_filtered(
        filters=[EqualsFilter(field="original_filename", value="alpha.gpx")]
    )
    assert len(result.items) == 2
    assert all(u.original_filename == "alpha.gpx" for u in result.items)


def test_not_equals_filter(test_db: Session, create_upload: Callable[..., Upload]):
    create_upload("alpha.gpx")
    create_upload("beta.gpx")
    create_upload("gamma.gpx")
    repo = Repository(test_db, Upload)

    result = repo.get_filtered(
        filters=[NotEqualsFilter(field="original_filename", value="alpha.gpx")]
    )
    assert len(result.items) == 2
    assert {u.original_filename for u in result.items} == {"beta.gpx", "gamma.gpx"}


def test_greater_than_filter(test_db: Session, create_upload: Callable[..., Upload]):
    now = datetime.now(UTC)
    create_upload("early.gpx", created_at=now - timedelta(hours=2))
    create_upload("middle.gpx", created_at=now - timedelta(hours=1))
    create_upload("late.gpx", created_at=now)
    repo = Repository(test_db, Upload)

    result = repo.get_filtered(
        filters=[GreaterThanFilter(field="created_at", value=now - timedelta(hours=1))]
    )
    assert len(result.items) == 1
    assert result.items[0].original_filename == "late.gpx"


def test_greater_than_or_equal_filter(
    test_db: Session, create_upload: Callable[..., Upload]
):
    now = datetime.now(UTC)
    create_upload("early.gpx", created_at=now - timedelta(hours=2))
    create_upload("middle.gpx", created_at=now - timedelta(hours=1))
    create_upload("late.gpx", created_at=now)
    repo = Repository(test_db, Upload)

    result = repo.get_filtered(
        filters=[
            GreaterThanOrEqualFilter(field="created_at", value=now - timedelta(hours=1))
        ]
    )
    assert len(result.items) == 2
    assert {u.original_filename for u in result.items} == {"middle.gpx", "late.gpx"}


def test_less_than_filter(test_db: Session, create_upload: Callable[..., Upload]):
    now = datetime.now(UTC)
    create_upload("early.gpx", created_at=now - timedelta(hours=2))
    create_upload("middle.gpx", created_at=now - timedelta(hours=1))
    create_upload("late.gpx", created_at=now)
    repo = Repository(test_db, Upload)

    result = repo.get_filtered(
        filters=[LessThanFilter(field="created_at", value=now - timedelta(hours=1))]
    )
    assert len(result.items) == 1
    assert result.items[0].original_filename == "early.gpx"


def test_less_than_or_equal_filter(
    test_db: Session, create_upload: Callable[..., Upload]
):
    now = datetime.now(UTC)
    create_upload("early.gpx", created_at=now - timedelta(hours=2))
    create_upload("middle.gpx", created_at=now - timedelta(hours=1))
    create_upload("late.gpx", created_at=now)
    repo = Repository(test_db, Upload)

    result = repo.get_filtered(
        filters=[
            LessThanOrEqualFilter(field="created_at", value=now - timedelta(hours=1))
        ]
    )
    assert len(result.items) == 2
    assert {u.original_filename for u in result.items} == {"early.gpx", "middle.gpx"}


def test_like_filter_case_insensitive(
    test_db: Session, create_upload: Callable[..., Upload]
):
    create_upload("Test Track.gpx")
    create_upload("TESTING Route.gpx")
    create_upload("production.gpx")
    create_upload("test hike.gpx")
    repo = Repository(test_db, Upload)

    result = repo.get_filtered(
        filters=[
            LikeFilter(
                field="original_filename", pattern="%test%", case_sensitive=False
            )
        ]
    )
    assert len(result.items) == 3
    assert {u.original_filename for u in result.items} == {
        "Test Track.gpx",
        "TESTING Route.gpx",
        "test hike.gpx",
    }


def test_in_filter(test_db: Session, create_upload: Callable[..., Upload]):
    create_upload("alpha.gpx")
    create_upload("beta.gpx")
    create_upload("gamma.gpx")
    create_upload("delta.gpx")
    repo = Repository(test_db, Upload)

    result = repo.get_filtered(
        filters=[InFilter(field="original_filename", values=["alpha.gpx", "gamma.gpx"])]
    )
    assert len(result.items) == 2
    assert {u.original_filename for u in result.items} == {"alpha.gpx", "gamma.gpx"}


def test_not_in_filter(test_db: Session, create_upload: Callable[..., Upload]):
    create_upload("alpha.gpx")
    create_upload("beta.gpx")
    create_upload("gamma.gpx")
    create_upload("delta.gpx")
    repo = Repository(test_db, Upload)

    result = repo.get_filtered(
        filters=[
            NotInFilter(field="original_filename", values=["alpha.gpx", "gamma.gpx"])
        ]
    )
    assert len(result.items) == 2
    assert {u.original_filename for u in result.items} == {"beta.gpx", "delta.gpx"}


def test_range_filter_both_bounds(
    test_db: Session, create_upload: Callable[..., Upload]
):
    create_upload("a.gpx", file_size_bytes=10)
    create_upload("b.gpx", file_size_bytes=50)
    create_upload("c.gpx", file_size_bytes=100)
    create_upload("d.gpx", file_size_bytes=200)
    repo = Repository(test_db, Upload)

    result = repo.get_filtered(
        filters=[RangeFilter(field="file_size_bytes", min_value=50, max_value=100)]
    )
    assert len(result.items) == 2
    assert {u.original_filename for u in result.items} == {"b.gpx", "c.gpx"}


def test_range_filter_min_only(test_db: Session, create_upload: Callable[..., Upload]):
    create_upload("small.gpx", file_size_bytes=10)
    create_upload("medium.gpx", file_size_bytes=50)
    create_upload("large.gpx", file_size_bytes=100)
    repo = Repository(test_db, Upload)

    result = repo.get_filtered(
        filters=[RangeFilter(field="file_size_bytes", min_value=50, max_value=None)]
    )
    assert len(result.items) == 2
    assert {u.original_filename for u in result.items} == {"medium.gpx", "large.gpx"}


def test_range_filter_max_only(test_db: Session, create_upload: Callable[..., Upload]):
    create_upload("small.gpx", file_size_bytes=10)
    create_upload("medium.gpx", file_size_bytes=50)
    create_upload("large.gpx", file_size_bytes=100)
    repo = Repository(test_db, Upload)

    result = repo.get_filtered(
        filters=[RangeFilter(field="file_size_bytes", min_value=None, max_value=50)]
    )
    assert len(result.items) == 2
    assert {u.original_filename for u in result.items} == {"small.gpx", "medium.gpx"}


def test_is_null_filter(test_db: Session, create_upload: Callable[..., Upload]):
    """Test IsNullFilter using UploadStatus.detail which is nullable."""
    upload = create_upload("test.gpx", status_values=[])

    status_repo = Repository(test_db, UploadStatus)
    status_repo.add(
        UploadStatus(
            upload_uid=upload.uid,
            status=UploadStatusValue.UPLOAD_PENDING,
            detail=None,
        )
    )
    status_repo.add(
        UploadStatus(
            upload_uid=upload.uid,
            status=UploadStatusValue.UPLOAD_INVALID,
            detail="Missing coordinates",
        )
    )
    test_db.commit()

    null_result = status_repo.get_filtered(
        filters=[IsNullFilter(field="detail", is_null=True)]
    )
    assert len(null_result.items) == 1
    assert null_result.items[0].status == UploadStatusValue.UPLOAD_PENDING

    not_null_result = status_repo.get_filtered(
        filters=[IsNullFilter(field="detail", is_null=False)]
    )
    assert len(not_null_result.items) == 1
    assert not_null_result.items[0].detail == "Missing coordinates"


def test_multiple_filters_combined(
    test_db: Session, create_upload: Callable[..., Upload]
):
    create_upload("test_small.gpx", file_size_bytes=10)
    create_upload("prod_small.gpx", file_size_bytes=10)
    create_upload("test_large.gpx", file_size_bytes=200)
    create_upload("prod_large.gpx", file_size_bytes=200)
    repo = Repository(test_db, Upload)

    result = repo.get_filtered(
        filters=[
            LikeFilter(
                field="original_filename", pattern="%test%", case_sensitive=False
            ),
            GreaterThanOrEqualFilter(field="file_size_bytes", value=100),
        ]
    )
    assert len(result.items) == 1
    assert result.items[0].original_filename == "test_large.gpx"


def test_filter_with_pagination(test_db: Session, create_upload: Callable[..., Upload]):
    for i in range(5):
        create_upload(f"test_{i}.gpx")
        create_upload(f"prod_{i}.gpx")
    repo = Repository(test_db, Upload)

    filters = [
        LikeFilter(field="original_filename", pattern="%test%", case_sensitive=False)
    ]

    page1 = repo.get_filtered(filters=filters, page_size=2)
    assert len(page1.items) == 2
    assert all("test" in u.original_filename for u in page1.items)
    assert page1.has_next is True

    page2 = repo.get_filtered(filters=filters, page_size=2, cursor=page1.next_cursor)
    assert len(page2.items) == 2
    assert all("test" in u.original_filename for u in page2.items)
    assert page2.has_next is True

    page3 = repo.get_filtered(filters=filters, page_size=2, cursor=page2.next_cursor)
    assert len(page3.items) == 1
    assert all("test" in u.original_filename for u in page3.items)
    assert page3.has_next is False

    all_uids = [u.uid for u in page1.items + page2.items + page3.items]
    assert len(all_uids) == len(set(all_uids))


def test_invalid_field_name_raises_error(
    test_db: Session, create_upload: Callable[..., Upload]
):
    create_upload("test.gpx")
    repo = Repository(test_db, Upload)

    with pytest.raises(AttributeError):
        repo.get_filtered(
            filters=[EqualsFilter(field="nonexistent_field", value="test")]
        )


def test_get_filtered_with_no_filters(
    test_db: Session, create_upload: Callable[..., Upload]
):
    create_upload("alpha.gpx")
    create_upload("beta.gpx")
    create_upload("gamma.gpx")
    repo = Repository(test_db, Upload)

    result = repo.get_filtered(filters=None)
    assert len(result.items) == 3
    assert {u.original_filename for u in result.items} == {
        "alpha.gpx",
        "beta.gpx",
        "gamma.gpx",
    }


def test_get_filtered_with_empty_filters_list(
    test_db: Session, create_upload: Callable[..., Upload]
):
    create_upload("alpha.gpx")
    create_upload("beta.gpx")
    repo = Repository(test_db, Upload)

    result = repo.get_filtered(filters=[])
    assert len(result.items) == 2
    assert {u.original_filename for u in result.items} == {"alpha.gpx", "beta.gpx"}


# Hybrid Property Filter Tests (current_status)


def test_in_filter_on_current_status_matches(
    test_db: Session, create_upload: Callable[..., Upload]
):
    create_upload(
        "a.gpx",
        status_values=[
            UploadStatusValue.UPLOAD_PENDING,
            UploadStatusValue.UPLOAD_RECEIVED,
        ],
    )

    repo = Repository(test_db, Upload)
    result = repo.get_filtered(
        filters=[
            InFilter(field="current_status", values=[UploadStatusValue.UPLOAD_RECEIVED])
        ],
    )
    assert len(result.items) == 1
    assert result.items[0].current_status == UploadStatusValue.UPLOAD_RECEIVED


def test_in_filter_on_current_status_uses_latest(
    test_db: Session, create_upload: Callable[..., Upload]
):
    create_upload(
        "b.gpx",
        status_values=[
            UploadStatusValue.UPLOAD_PENDING,
            UploadStatusValue.UPLOAD_RECEIVED,
            UploadStatusValue.UPLOAD_INVALID,
        ],
    )

    repo = Repository(test_db, Upload)
    result = repo.get_filtered(
        filters=[
            InFilter(field="current_status", values=[UploadStatusValue.UPLOAD_RECEIVED])
        ],
    )
    assert len(result.items) == 0


def test_in_filter_on_current_status_excludes_non_matching(
    test_db: Session, create_upload: Callable[..., Upload]
):
    create_upload("c.gpx", status_values=[UploadStatusValue.UPLOAD_PENDING])

    repo = Repository(test_db, Upload)
    result = repo.get_filtered(
        filters=[
            InFilter(field="current_status", values=[UploadStatusValue.UPLOAD_SUCCESS])
        ],
    )
    assert len(result.items) == 0


def test_in_filter_on_current_status_no_statuses(
    test_db: Session, create_upload: Callable[..., Upload]
):
    create_upload("d.gpx", status_values=[])

    repo = Repository(test_db, Upload)
    result = repo.get_filtered(
        filters=[
            InFilter(field="current_status", values=[UploadStatusValue.UPLOAD_RECEIVED])
        ],
    )
    assert len(result.items) == 0


def test_in_filter_on_current_status_multiple_values(
    test_db: Session, create_upload: Callable[..., Upload]
):
    create_upload(
        "e.gpx",
        status_values=[
            UploadStatusValue.UPLOAD_PENDING,
            UploadStatusValue.UPLOAD_RECEIVED,
        ],
    )
    create_upload(
        "f.gpx",
        status_values=[
            UploadStatusValue.UPLOAD_PENDING,
            UploadStatusValue.UPLOAD_SUCCESS,
        ],
    )

    repo = Repository(test_db, Upload)
    result = repo.get_filtered(
        filters=[
            InFilter(
                field="current_status",
                values=[
                    UploadStatusValue.UPLOAD_RECEIVED,
                    UploadStatusValue.UPLOAD_SUCCESS,
                ],
            )
        ],
    )
    assert len(result.items) == 2


def test_in_filter_on_current_status_composes_with_equals(
    test_db: Session, test_user: User, create_upload: Callable[..., Upload]
):
    other_user = User(
        email="other@example.com",
        password_hash=hash_password("pass"),
    )
    test_db.add(other_user)
    test_db.commit()
    test_db.refresh(other_user)

    create_upload(
        "g.gpx",
        status_values=[
            UploadStatusValue.UPLOAD_PENDING,
            UploadStatusValue.UPLOAD_RECEIVED,
        ],
    )
    create_upload(
        "h.gpx",
        user=other_user,
        status_values=[
            UploadStatusValue.UPLOAD_PENDING,
            UploadStatusValue.UPLOAD_RECEIVED,
        ],
    )

    repo = Repository(test_db, Upload)
    result = repo.get_filtered(
        filters=[
            InFilter(
                field="current_status", values=[UploadStatusValue.UPLOAD_RECEIVED]
            ),
            EqualsFilter(field="user_uid", value=test_user.uid),
        ],
    )
    assert len(result.items) == 1
    assert result.items[0].user_uid == test_user.uid
