"""User-group endpoints."""

from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import Field
from sqlalchemy.orm import Session

from src.app.dependencies import authenticated_user, db_session
from src.app.repository import User, UserGroup, UserGroupMembership
from src.app.services import user_group as user_group_service
from src.app.utils import BaseSchema

router = APIRouter()


class CreateUserGroupRequest(BaseSchema):
    """Request body for creating a new user group."""

    name: str = Field(min_length=1, max_length=80)


class UpdateUserGroupRequest(BaseSchema):
    """Request body for renaming a user group."""

    name: str = Field(min_length=1, max_length=80)


class UserGroupResponse(BaseSchema):
    """Response body for user group endpoints."""

    uid: str
    name: str
    owner_uid: str
    created_at: datetime
    member_count: int


class UserGroupMemberResponse(BaseSchema):
    """Response body describing a single member of a group."""

    uid: str  # membership uid
    user_uid: str
    email: str
    joined_at: datetime  # alias of membership.created_at


def _to_group_response(group: UserGroup, member_count: int) -> UserGroupResponse:
    return UserGroupResponse(
        uid=group.uid,
        name=group.name,
        owner_uid=group.owner_uid,
        created_at=group.created_at,
        member_count=member_count,
    )


def _to_member_response(
    membership: UserGroupMembership,
) -> UserGroupMemberResponse:
    return UserGroupMemberResponse(
        uid=membership.uid,
        user_uid=membership.user_uid,
        email=membership.user.email,
        joined_at=membership.created_at,
    )


@router.post("/user-groups", status_code=201, operation_id="createUserGroup")
def create_user_group(
    body: CreateUserGroupRequest,
    user: Annotated[User, Depends(authenticated_user)],
    db: Annotated[Session, Depends(db_session)],
) -> UserGroupResponse:
    """Create a new group with the caller as owner and sole initial member."""
    group = user_group_service.create_group(db, user, name=body.name)
    # Caller is the only member at creation time.
    return _to_group_response(group, member_count=1)


@router.get("/user-groups", operation_id="listUserGroups")
def list_user_groups(
    user: Annotated[User, Depends(authenticated_user)],
    db: Annotated[Session, Depends(db_session)],
) -> list[UserGroupResponse]:
    """List the caller's non-archived groups, newest first."""
    groups = user_group_service.list_groups(db, user)
    return [
        _to_group_response(g, user_group_service.count_members(db, g)) for g in groups
    ]


@router.get("/user-groups/{group_uid}", operation_id="getUserGroup")
def get_user_group(
    group_uid: str,
    user: Annotated[User, Depends(authenticated_user)],
    db: Annotated[Session, Depends(db_session)],
) -> UserGroupResponse:
    """Return one group the caller belongs to. 404 if not a member."""
    try:
        group = user_group_service.get_group(db, user, group_uid)
    except user_group_service.UserGroupNotFoundError:
        raise HTTPException(status_code=404, detail="Group not found") from None
    return _to_group_response(group, user_group_service.count_members(db, group))


@router.patch("/user-groups/{group_uid}", operation_id="updateUserGroup")
def update_user_group(
    group_uid: str,
    body: UpdateUserGroupRequest,
    user: Annotated[User, Depends(authenticated_user)],
    db: Annotated[Session, Depends(db_session)],
) -> UserGroupResponse:
    """Rename a group. Owner only."""
    try:
        group = user_group_service.update_group(db, user, group_uid, name=body.name)
    except user_group_service.UserGroupNotFoundError:
        raise HTTPException(status_code=404, detail="Group not found") from None
    return _to_group_response(group, user_group_service.count_members(db, group))


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
    try:
        user_group_service.archive_group(db, user, group_uid)
    except user_group_service.UserGroupNotFoundError:
        raise HTTPException(status_code=404, detail="Group not found") from None

    return Response(status_code=204)


@router.get(
    "/user-groups/{group_uid}/members",
    operation_id="listUserGroupMembers",
)
def list_user_group_members(
    group_uid: str,
    user: Annotated[User, Depends(authenticated_user)],
    db: Annotated[Session, Depends(db_session)],
) -> list[UserGroupMemberResponse]:
    """List members of a group the caller belongs to."""
    try:
        memberships = user_group_service.list_members(db, user, group_uid)
    except user_group_service.UserGroupNotFoundError:
        raise HTTPException(status_code=404, detail="Group not found") from None
    return [_to_member_response(m) for m in memberships]
