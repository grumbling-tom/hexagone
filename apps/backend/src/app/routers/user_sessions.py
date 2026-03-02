"""User session endpoints."""

from typing import TYPE_CHECKING, Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import EmailStr
from sqlalchemy.orm import Session

from src.app.dependencies import authenticated_user, get_db
from src.app.services.user import authenticate_user
from src.app.services.user_session import (
    create_session,
    invalidate_session,
    validate_session,
)
from src.app.settings import settings
from src.app.utils import BaseSchema

if TYPE_CHECKING:
    from src.app.repository import User

router = APIRouter()


class CreateUserSessionRequest(BaseSchema):
    """Request body for login."""

    email: EmailStr
    password: str


class UserSessionResponse(BaseSchema):
    """Response body after successful login."""

    uid: str
    email: str


def _get_client_ip(request: Request) -> str:
    forwarded_for = request.headers.get("x-forwarded-for")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    if request.client:
        return request.client.host
    return "unknown"


@router.post("/user-sessions")
def login(
    body: CreateUserSessionRequest,
    request: Request,
    response: Response,
    db: Annotated[Session, Depends(get_db)],
) -> UserSessionResponse:
    """Authenticate and create a new session."""
    user = authenticate_user(db, body.email, body.password)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")

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

    return UserSessionResponse(uid=user.uid, email=user.email)


@router.delete("/user-sessions/current", status_code=204)
def logout(
    request: Request,
    response: Response,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(authenticated_user)],
) -> None:
    """Log out by invalidating the current session."""
    session_id = request.cookies.get(settings.SESSION_COOKIE_NAME)

    if session_id:
        user_agent = request.headers.get("user-agent", "")
        ip_address = _get_client_ip(request)

        session = validate_session(db, session_id, user_agent, ip_address)
        if session:
            invalidate_session(db, session)

    response.delete_cookie(
        key=settings.SESSION_COOKIE_NAME,
        httponly=True,
        secure=True,
        samesite="lax",
    )
