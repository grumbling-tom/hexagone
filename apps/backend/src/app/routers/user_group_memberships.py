"""User-group-membership endpoints."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.orm import Session

from src.app.dependencies import authenticated_user, db_session
from src.app.repository import User
from src.app.services import user_group as user_group_service

router = APIRouter()


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
