"""User endpoints."""

from typing import TYPE_CHECKING, Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import EmailStr
from sqlalchemy.orm import Session

from src.app.dependencies import authenticated_user, get_db
from src.app.services.user import DuplicateEmailError, create_user
from src.app.services.user_session import create_session
from src.app.settings import settings
from src.app.utils import BaseSchema

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


def _get_client_ip(request: Request) -> str:
    forwarded_for = request.headers.get("x-forwarded-for")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    if request.client:
        return request.client.host
    return "unknown"


@router.post("/users", status_code=201)
def signup(
    body: CreateUserRequest,
    request: Request,
    response: Response,
    db: Annotated[Session, Depends(get_db)],
) -> UserResponse:
    """Create a new user account and start a session."""
    try:
        user = create_user(db, body.email, body.password)
    except DuplicateEmailError:
        raise HTTPException(status_code=409, detail="Email already taken") from None

    user_agent = request.headers.get("user-agent", "")
    ip_address = _get_client_ip(request)
    session = create_session(db, user.uid, user_agent, ip_address)

    response.set_cookie(
        key=settings.SESSION_COOKIE_NAME,
        value=session.uid,
        max_age=settings.session_expiry_seconds,
        httponly=True,
        secure=True,
        samesite="lax",
    )

    return UserResponse(uid=user.uid, email=user.email)


@router.get("/users/current")
def get_current_user(
    user: Annotated[User, Depends(authenticated_user)],
) -> UserResponse:
    """Return the currently authenticated user."""
    return UserResponse(uid=user.uid, email=user.email)
