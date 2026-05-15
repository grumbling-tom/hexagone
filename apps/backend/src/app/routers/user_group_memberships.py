"""User-group-membership endpoints."""

from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.orm import Session

from src.app.dependencies import authenticated_user, db_session
from src.app.repository import User
from src.app.services import user_group as user_group_service
from src.app.utils import BaseSchema

router = APIRouter()


class UpdateUserGroupMembershipRequest(BaseSchema):
    """Request body for updating a membership's share_consent flag."""

    share_consent: bool


class UserGroupMembershipResponse(BaseSchema):
    """Response body for membership endpoints."""

    uid: str
    user_uid: str
    user_group_uid: str
    share_consent: bool
    invited_by_uid: str | None
    joined_at: datetime


@router.delete(
    "/user-group-memberships/{membership_uid}",
    status_code=204,
    operation_id="deleteUserGroupMembership",
)
def delete_user_group_membership(
    membership_uid: str,
    user: Annotated[User, Depends(authenticated_user)],
    db: Annotated[Session, Depends(db_session)],
) -> Response:
    """Remove a membership. Allowed for self (leave) or group owner (kick).

    A group owner cannot leave their own group while it has other members;
    they must archive the group instead.
    """
    try:
        user_group_service.remove_membership(db, user, membership_uid)
    except user_group_service.UserGroupMembershipNotFoundError:
        raise HTTPException(status_code=404, detail="Membership not found") from None
    except user_group_service.SoleOwnerCannotLeaveError:
        raise HTTPException(
            status_code=409,
            detail=(
                "The group owner cannot leave while others remain. "
                "Delete the group instead, or transfer ownership."
            ),
        ) from None
    return Response(status_code=204)


@router.patch(
    "/user-group-memberships/{membership_uid}",
    operation_id="updateUserGroupMembership",
)
def update_user_group_membership(
    membership_uid: str,
    body: UpdateUserGroupMembershipRequest,
    user: Annotated[User, Depends(authenticated_user)],
    db: Annotated[Session, Depends(db_session)],
) -> UserGroupMembershipResponse:
    """Toggle share_consent on the caller's own membership."""
    try:
        membership = user_group_service.set_share_consent(
            db, user, membership_uid, consent=body.share_consent
        )
    except user_group_service.UserGroupMembershipNotFoundError:
        raise HTTPException(status_code=404, detail="Membership not found") from None
    except user_group_service.NotMembershipSelfError:
        raise HTTPException(
            status_code=403,
            detail="Only the member themselves can change share_consent",
        ) from None

    return UserGroupMembershipResponse(
        uid=membership.uid,
        user_uid=membership.user_uid,
        user_group_uid=membership.user_group_uid,
        share_consent=membership.share_consent,
        invited_by_uid=membership.invited_by_uid,
        joined_at=membership.created_at,
    )
