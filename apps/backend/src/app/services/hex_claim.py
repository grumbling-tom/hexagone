"""Hex-claim service: list raw rows + aggregate by hex cell."""

from src.app.repository import HexClaim, HexClaimByCell, In, Predicate, ScopedRepository
from src.app.settings import settings
from src.app.utils import PaginatedResult, SortOrder


def list_hex_claims(  # noqa: PLR0913
    claims: ScopedRepository[HexClaim],
    *,
    page_size: int = settings.DEFAULT_PAGE_SIZE,
    cursor: str | None = None,
    upload_uids: list[str] | None = None,
    sort_field: str = "created_at",
    sort_order: SortOrder = SortOrder.DESC,
) -> PaginatedResult[HexClaim]:
    """List raw hex claims for the authenticated user.

    Args:
        claims: HexClaim repository (the policy narrows it to the viewer's own).
        page_size: Number of items per page.
        cursor: Pagination cursor.
        upload_uids: Optional filter — only claims belonging to these uploads.
        sort_field: Column name to sort by.
        sort_order: Sort direction.

    Returns:
        Paginated list of HexClaim ORM instances.
    """
    filters: list[Predicate] = []
    if upload_uids:
        filters.append(In(field="upload_uid", values=upload_uids))

    return claims.get_filtered(
        filters=filters,
        page_size=page_size,
        cursor=cursor,
        sort_field=getattr(HexClaim, sort_field),
        sort_order=sort_order,
    )


def aggregate_hex_claims_by_cell(
    by_cell: ScopedRepository[HexClaimByCell],
    *,
    page_size: int = settings.DEFAULT_PAGE_SIZE,
    cursor: str | None = None,
) -> PaginatedResult[HexClaimByCell]:
    """Aggregate the user's hex claims by H3 cell.

    Each row is one unique cell with rolled-up metadata (claim and upload
    counts, first/last claimed timestamps). Backed by the
    ``hex_claim_by_cell`` view; cursor pagination is fixed to ``h3_cell ASC``
    because that is the only sort key in the result that is unique per row.
    """
    return by_cell.get_filtered(
        page_size=page_size,
        cursor=cursor,
        sort_field=HexClaimByCell.h3_cell,
        sort_order=SortOrder.ASC,
    )
