"""Hex-claim service: list raw rows + aggregate by hex cell."""

from datetime import datetime
from typing import NamedTuple

from sqlalchemy import asc, func, select
from sqlalchemy.orm import Session as DBSession

from src.app.repository import HexClaim, InFilter, Repository
from src.app.repository.models import User
from src.app.services.permissions import permission_filters
from src.app.settings import settings
from src.app.utils import Cursor, PaginatedResult, SortOrder


def list_hex_claims(  # noqa: PLR0913
    db: DBSession,
    user: User,
    *,
    page_size: int = settings.DEFAULT_PAGE_SIZE,
    cursor: str | None = None,
    upload_uids: list[str] | None = None,
    sort_field: str = "created_at",
    sort_order: SortOrder = SortOrder.DESC,
) -> PaginatedResult[HexClaim]:
    """List raw hex claims for the authenticated user.

    Args:
        db: Database session.
        user: The authenticated user.
        page_size: Number of items per page.
        cursor: Pagination cursor.
        upload_uids: Optional filter — only claims belonging to these uploads.
        sort_field: Column name to sort by.
        sort_order: Sort direction.

    Returns:
        Paginated list of HexClaim ORM instances.
    """
    filters = permission_filters(user, HexClaim)
    if upload_uids:
        filters.append(InFilter(field="upload_uid", values=upload_uids))

    repo = Repository(db, HexClaim)
    return repo.get_filtered(
        filters=filters,
        page_size=page_size,
        cursor=cursor,
        sort_field=getattr(HexClaim, sort_field),
        sort_order=sort_order,
    )


class AggregatedHexClaimByCellRow(NamedTuple):
    """One row of the by-cell aggregation.

    Internal data carrier — mapped to a Pydantic response schema in the
    router layer. Not a ``BaseSchema`` so the
    ``test_services_do_not_return_pydantic_schemas`` architecture test
    stays green.
    """

    h3_cell: str
    claim_count: int
    upload_count: int
    first_claimed_at: datetime
    last_claimed_at: datetime


# h3_cell is the only sort key for the aggregated query — it's the GROUP BY
# column and is unique in the result set, so it doubles as the cursor's tie-
# breaker uid. Sort order is fixed (ASC) for cursor stability.
_AGGREGATE_SORT_FIELD = "h3_cell"
_AGGREGATE_SORT_ORDER = SortOrder.ASC


def aggregate_hex_claims_by_cell(
    db: DBSession,
    user: User,
    *,
    page_size: int = settings.DEFAULT_PAGE_SIZE,
    cursor: str | None = None,
) -> PaginatedResult[AggregatedHexClaimByCellRow]:
    """Aggregate the user's hex claims by H3 cell.

    Each row in the result is one unique cell with rolled-up metadata
    (claim and upload counts, first/last claimed timestamps).

    Pagination cursors are managed manually here rather than via
    ``Repository.get_filtered`` because the aggregate query does not
    select ORM instances — it selects a projection over a ``GROUP BY``.
    The cursor format and base64 envelope match the project-wide
    ``Cursor`` so clients can treat it as opaque.
    """
    stmt = select(
        HexClaim.h3_cell,
        func.count().label("claim_count"),
        func.count(func.distinct(HexClaim.upload_uid)).label("upload_count"),
        func.min(HexClaim.created_at).label("first_claimed_at"),
        func.max(HexClaim.created_at).label("last_claimed_at"),
    ).group_by(HexClaim.h3_cell)

    for permission_filter in permission_filters(user, HexClaim):
        stmt = permission_filter.apply(stmt, HexClaim)

    if cursor is not None:
        decoded = Cursor.decode(cursor)
        if (
            decoded.sort_field != _AGGREGATE_SORT_FIELD
            or decoded.sort_order != _AGGREGATE_SORT_ORDER
        ):
            msg = (
                f"Cursor sort parameters "
                f"(field='{decoded.sort_field}', "
                f"order='{decoded.sort_order.value}') do not match "
                f"requested parameters (field='{_AGGREGATE_SORT_FIELD}', "
                f"order='{_AGGREGATE_SORT_ORDER.value}')"
            )
            raise ValueError(msg)
        stmt = stmt.where(HexClaim.h3_cell > decoded.sort_value)

    stmt = stmt.order_by(asc(HexClaim.h3_cell)).limit(page_size + 1)

    rows = [
        AggregatedHexClaimByCellRow(
            h3_cell=row.h3_cell,
            claim_count=row.claim_count,
            upload_count=row.upload_count,
            first_claimed_at=row.first_claimed_at,
            last_claimed_at=row.last_claimed_at,
        )
        for row in db.execute(stmt).all()
    ]

    has_next = len(rows) > page_size
    items = rows[:page_size]
    has_previous = cursor is not None and len(items) > 0

    def _cursor(value: str) -> str:
        return Cursor(
            sort_value=value,
            uid=value,
            sort_field=_AGGREGATE_SORT_FIELD,
            sort_order=_AGGREGATE_SORT_ORDER,
        ).encode()

    previous_cursor = _cursor(items[0].h3_cell) if has_previous else None
    next_cursor = _cursor(items[-1].h3_cell) if has_next and items else None

    return PaginatedResult(
        items=items,
        previous_cursor=previous_cursor,
        next_cursor=next_cursor,
        has_previous=has_previous,
        has_next=has_next,
    )
