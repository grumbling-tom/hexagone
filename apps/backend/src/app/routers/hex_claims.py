"""Hex-claim endpoints: raw events + aggregated rollups.

This module exports two routers (one per resource) so each gets its own
OpenAPI tag and therefore its own Orval-generated TypeScript module on the
frontend (`hex-claims.ts`, `aggregated-hex-claims.ts`).
"""

from datetime import datetime
from enum import StrEnum
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from pydantic import Field
from sqlalchemy.orm import Session

from src.app.dependencies import authenticated_user, db_session
from src.app.repository.models import User
from src.app.services.hex_claim import (
    aggregate_hex_claims_by_cell,
    list_hex_claims,
)
from src.app.settings import settings
from src.app.utils import BaseSchema, PaginatedResult, SortOrder

# ---------------------------------------------------------------------------
# /hex-claims — raw events, paginated, follows the project-wide convention.
# ---------------------------------------------------------------------------

hex_claims_router = APIRouter()


class HexClaimResponse(BaseSchema):
    """One hex-claim row exactly as stored."""

    uid: str
    h3_cell: str
    h3_resolution: int
    upload_uid: str
    polygon_index: int
    completed_at: datetime | None
    created_at: datetime


class HexClaimSortField(StrEnum):
    """Allowed sort fields for raw hex-claim listing."""

    created_at = "created_at"
    completed_at = "completed_at"


class ListHexClaimsParams(BaseSchema):
    """Query parameters for listing raw hex claims."""

    page_size: int = Field(default=settings.DEFAULT_PAGE_SIZE, gt=0, le=100)
    cursor: str | None = Field(default=None)
    upload_uid: list[str] | None = Field(
        default=None,
        description="Restrict results to claims belonging to these uploads.",
    )
    sort_field: HexClaimSortField = Field(default=HexClaimSortField.created_at)
    sort_order: SortOrder = Field(default=SortOrder.DESC)


@hex_claims_router.get("/hex-claims", operation_id="listHexClaims")
def list_hex_claims_endpoint(
    user: Annotated[User, Depends(authenticated_user)],
    db: Annotated[Session, Depends(db_session)],
    params: Annotated[ListHexClaimsParams, Query()],
) -> PaginatedResult[HexClaimResponse]:
    """List the authenticated user's raw hex claims."""
    result = list_hex_claims(
        db=db,
        user=user,
        page_size=params.page_size,
        cursor=params.cursor,
        upload_uids=params.upload_uid,
        sort_field=params.sort_field.value,
        sort_order=params.sort_order,
    )
    return PaginatedResult(
        items=[HexClaimResponse.model_validate(c) for c in result.items],
        previous_cursor=result.previous_cursor,
        next_cursor=result.next_cursor,
        has_previous=result.has_previous,
        has_next=result.has_next,
    )


# ---------------------------------------------------------------------------
# /aggregated-hex-claims?by=… — rollups. Today only `by=hex_cell` is
# supported; the URL is shaped so further `by` values (e.g. `upload`,
# `week`) can be added without a new endpoint.
#
# The page_size cap is intentionally raised to 10_000 (vs the project-wide
# 100) so the map view can fetch a heavy user's full territory in a few
# round-trips rather than several hundred. Cardinality is bounded by the
# user's territory size (currently <100k cells); revisit if a future `by`
# value introduces unbounded cardinality.
# ---------------------------------------------------------------------------

aggregated_hex_claims_router = APIRouter()


class AggregateHexClaimBy(StrEnum):
    """Dimensions the aggregated-hex-claims endpoint can roll up over."""

    hex_cell = "hex_cell"


class AggregatedHexClaimByCell(BaseSchema):
    """One aggregated row when ``by=hex_cell``."""

    h3_cell: str
    claim_count: int
    upload_count: int
    first_claimed_at: datetime
    last_claimed_at: datetime


class ListAggregatedHexClaimsParams(BaseSchema):
    """Query parameters for the aggregated hex-claims endpoint."""

    by: AggregateHexClaimBy = Field(
        ...,
        description=(
            "Dimension to aggregate by. Required — the URL is meaningless without it."
        ),
    )
    page_size: int = Field(
        default=settings.DEFAULT_PAGE_SIZE,
        gt=0,
        le=10_000,
        description=(
            "Cap raised to 10k so the map can fetch a full user territory "
            "in a handful of round-trips."
        ),
    )
    cursor: str | None = Field(default=None)


@aggregated_hex_claims_router.get(
    "/aggregated-hex-claims", operation_id="listAggregatedHexClaims"
)
def list_aggregated_hex_claims_endpoint(
    user: Annotated[User, Depends(authenticated_user)],
    db: Annotated[Session, Depends(db_session)],
    params: Annotated[ListAggregatedHexClaimsParams, Query()],
) -> PaginatedResult[AggregatedHexClaimByCell]:
    """Aggregate the user's hex claims along the requested dimension."""
    # Today only one `by` value exists; this branches once a second is added.
    if params.by is AggregateHexClaimBy.hex_cell:
        result = aggregate_hex_claims_by_cell(
            db=db,
            user=user,
            page_size=params.page_size,
            cursor=params.cursor,
        )
        return PaginatedResult(
            items=[
                AggregatedHexClaimByCell(
                    h3_cell=row.h3_cell,
                    claim_count=row.claim_count,
                    upload_count=row.upload_count,
                    first_claimed_at=row.first_claimed_at,
                    last_claimed_at=row.last_claimed_at,
                )
                for row in result.items
            ],
            previous_cursor=result.previous_cursor,
            next_cursor=result.next_cursor,
            has_previous=result.has_previous,
            has_next=result.has_next,
        )

    # The enum is exhaustively handled above; this is unreachable today and
    # exists so a future contributor adding a `by` value gets a fast failure
    # instead of a silent None return.
    msg = f"Unhandled aggregation dimension: {params.by!r}"
    raise NotImplementedError(msg)
