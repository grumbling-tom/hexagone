"""User-group endpoints."""

from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from pydantic import Field
from sqlalchemy.orm import Session

from src.app.authz import Resource, with_capabilities
from src.app.dependencies import authenticated_user, db_session
from src.app.repository import User
from src.app.services import user_group as user_group_service
from src.app.settings import settings
from src.app.utils import BaseSchema, PaginatedResult

router = APIRouter()


class CreateUserGroupRequest(BaseSchema):
    """Request body for creating a new user group."""

    name: str = Field(min_length=1, max_length=80)


class UpdateUserGroupRequest(BaseSchema):
    """Request body for renaming a user group."""

    name: str = Field(min_length=1, max_length=80)


class ListUserGroupsParams(BaseSchema):
    """Query parameters for listing user groups."""

    page_size: int = Field(default=settings.DEFAULT_PAGE_SIZE, gt=0, le=100)
    cursor: str | None = Field(default=None)


class UserGroupResponse(Resource):
    """Response body for user group endpoints."""

    name: str
    owner_uid: str
    created_at: datetime
    member_count: int


@router.post("/user-groups", status_code=201, operation_id="createUserGroup")
def create_user_group(
    body: CreateUserGroupRequest,
    user: Annotated[User, Depends(authenticated_user)],
    db: Annotated[Session, Depends(db_session)],
) -> UserGroupResponse:
    """Create a new group with the caller as owner and sole initial member."""
    group = user_group_service.create_group(db, user, name=body.name)
    return with_capabilities(UserGroupResponse, group, user=user, db=db)


@router.get("/user-groups", operation_id="listUserGroups")
def list_user_groups(
    user: Annotated[User, Depends(authenticated_user)],
    db: Annotated[Session, Depends(db_session)],
    params: Annotated[ListUserGroupsParams, Query()],
) -> PaginatedResult[UserGroupResponse]:
    """List the caller's non-archived groups, newest first."""
    result = user_group_service.list_groups(
        db,
        user,
        page_size=params.page_size,
        cursor=params.cursor,
    )
    return PaginatedResult(
        items=[
            with_capabilities(UserGroupResponse, g, user=user, db=db)
            for g in result.items
        ],
        previous_cursor=result.previous_cursor,
        next_cursor=result.next_cursor,
        has_previous=result.has_previous,
        has_next=result.has_next,
    )


@router.get("/user-groups/{group_uid}", operation_id="getUserGroup")
def get_user_group(
    group_uid: str,
    user: Annotated[User, Depends(authenticated_user)],
    db: Annotated[Session, Depends(db_session)],
) -> UserGroupResponse:
    """Return one group the caller belongs to. 404 if not a member."""
    group = user_group_service.get_group(db, user, group_uid)
    if group is None:
        raise HTTPException(status_code=404, detail="Group not found")
    return with_capabilities(UserGroupResponse, group, user=user, db=db)


@router.patch("/user-groups/{group_uid}", operation_id="updateUserGroup")
def update_user_group(
    group_uid: str,
    body: UpdateUserGroupRequest,
    user: Annotated[User, Depends(authenticated_user)],
    db: Annotated[Session, Depends(db_session)],
) -> UserGroupResponse:
    """Rename a group. Owner only."""
    group = user_group_service.update_group(db, user, group_uid, name=body.name)
    return with_capabilities(UserGroupResponse, group, user=user, db=db)


@router.delete(
    "/user-groups/{group_uid}",
    status_code=204,
    operation_id="deleteUserGroup",
)
def delete_user_group(
    group_uid: str,
    user: Annotated[User, Depends(authenticated_user)],
    db: Annotated[Session, Depends(db_session)],
) -> Response:
    """Soft-delete (archive) a group. Owner only."""
    user_group_service.archive_group(db, user, group_uid)
    return Response(status_code=204)
