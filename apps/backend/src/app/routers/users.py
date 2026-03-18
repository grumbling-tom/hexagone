"""User endpoints."""

from typing import TYPE_CHECKING, Annotated

from fastapi import APIRouter, Depends

from src.app.dependencies import authenticated_user
from src.app.utils import BaseSchema

if TYPE_CHECKING:
    from src.app.repository import User

router = APIRouter()


class UserResponse(BaseSchema):
    """Response body for user endpoints."""

    uid: str
    email: str
    role: str


@router.get("/users/current", operation_id="getCurrentUser")
def get_current_user(
    user: Annotated[User, Depends(authenticated_user)],
) -> UserResponse:
    """Return the currently authenticated user."""
    return UserResponse(uid=user.uid, email=user.email, role=user.role)
