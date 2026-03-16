"""User endpoints."""

from typing import TYPE_CHECKING, Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import EmailStr
from sqlalchemy.orm import Session

from src.app.dependencies import authenticated_user, db_session
from src.app.services.user import DuplicateEmailError
from src.app.services.user import create_user as create_user_service
from src.app.services.user_session import create_session
from src.app.settings import settings
from src.app.utils import BaseSchema, get_client_ip

if TYPE_CHECKING:
    from src.app.repository import User

router = APIRouter()


class CreateUserRequest(BaseSchema):
    """Request body for user registration."""

    email: EmailStr
    password: str


class UserResponse(BaseSchema):
    """Response body for user endpoints."""

    uid: str
    email: str


@router.post("/users", status_code=201, operation_id="createUser")
def create_user(
    body: CreateUserRequest,
    request: Request,
    response: Response,
    db: Annotated[Session, Depends(db_session)],
) -> UserResponse:
    """Create a new user account and start a session."""
    try:
        user = create_user_service(db, body.email, body.password)
    except DuplicateEmailError:
        raise HTTPException(status_code=409, detail="Email already taken") from None

    user_agent = request.headers.get("user-agent", "")
    ip_address = get_client_ip(request)
    session = create_session(db, user.uid, user_agent, ip_address)

    response.set_cookie(
        key=settings.SESSION_COOKIE_NAME,
        value=session.uid,
        max_age=settings.session_expiry_seconds,
        httponly=True,
        secure=True,
        samesite="strict",
    )

    return UserResponse(uid=user.uid, email=user.email)


@router.get("/users/current", operation_id="getCurrentUser")
def get_current_user(
    user: Annotated[User, Depends(authenticated_user)],
) -> UserResponse:
    """Return the currently authenticated user."""
    return UserResponse(uid=user.uid, email=user.email)
