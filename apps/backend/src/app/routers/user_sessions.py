"""User session endpoints."""

from typing import TYPE_CHECKING, Annotated, Self

from fastapi import APIRouter, Cookie, Depends, HTTPException, Request, Response
from pydantic import EmailStr, model_validator
from sqlalchemy.orm import Session

from src.app.dependencies import authenticated_user, db_session, email_client
from src.app.services.email import EmailClient, send_welcome_email
from src.app.services.login_token import is_email_allowed, verify_login_token
from src.app.services.user import authenticate_user, get_or_create_user_by_email
from src.app.services.user_session import (
    create_session,
    invalidate_session,
    validate_session,
)
from src.app.settings import settings
from src.app.utils import BaseSchema, get_client_ip, get_logger

if TYPE_CHECKING:
    from src.app.repository import User

logger = get_logger(__name__)

router = APIRouter()


class CreateUserSessionRequest(BaseSchema):
    """Credentials for creating a session — password mode OR magic-link mode.

    Exactly one mode must be supplied: ``email`` + ``password`` (legacy password
    login) or ``token`` (magic link; the browser-binding nonce is read from the
    cookie, not the body). The password mode is removed in TASK-0021, after
    which this collapses to just ``token``.
    """

    email: EmailStr | None = None
    password: str | None = None
    token: str | None = None

    @model_validator(mode="after")
    def _exactly_one_mode(self) -> Self:
        password_mode = self.email is not None and self.password is not None
        token_mode = self.token is not None
        if password_mode == token_mode:
            msg = "Provide either {email, password} or {token}, not both."
            raise ValueError(msg)
        return self


class UserSessionResponse(BaseSchema):
    """Response body after successful login."""

    uid: str
    email: str


def _user_from_login_token(
    db: Session, token: str, nonce: str | None, mailer: EmailClient
) -> User | None:
    """Resolve the user for a magic-link token, or None if it isn't valid.

    Consumes the token (single-use), re-checks the allowlist (it may have
    changed since the link was issued), and auto-creates a first-time
    allow-listed user — sending the welcome email on creation.
    """
    email = verify_login_token(db, token, nonce or "")
    if email is None:
        return None
    if not is_email_allowed(email):
        return None

    user, created = get_or_create_user_by_email(db, email)
    if user.archived:
        return None
    if created:
        # Best-effort: a welcome-email failure must not fail sign-in.
        try:
            send_welcome_email(mailer, user=user)
        except Exception:
            logger.exception("welcome_email_failed", user_uid=user.uid)
    return user


@router.post("/user-sessions", operation_id="createUserSession")
def create_user_session(  # noqa: PLR0913 — FastAPI-injected deps, not a design smell
    body: CreateUserSessionRequest,
    request: Request,
    response: Response,
    db: Annotated[Session, Depends(db_session)],
    mailer: Annotated[EmailClient, Depends(email_client)],
    nonce: Annotated[str | None, Cookie(alias=settings.LOGIN_NONCE_COOKIE_NAME)] = None,
) -> UserSessionResponse:
    """Create a session via a magic-link token or email + password."""
    if body.token is not None:
        user = _user_from_login_token(db, body.token, nonce, mailer)
    elif body.email is not None and body.password is not None:
        user = authenticate_user(db, body.email, body.password)
    else:  # pragma: no cover - the validator guarantees exactly one mode
        user = None

    if user is None:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    user_agent = request.headers.get("user-agent", "")
    ip_address = get_client_ip(request)
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


@router.delete(
    "/user-sessions/current", status_code=204, operation_id="deleteCurrentSession"
)
def delete_current_session(
    request: Request,
    response: Response,
    db: Annotated[Session, Depends(db_session)],
    _: Annotated[User, Depends(authenticated_user)],
) -> None:
    """Log out by invalidating the current session."""
    session_id = request.cookies.get(settings.SESSION_COOKIE_NAME)

    if session_id:
        user_agent = request.headers.get("user-agent", "")

        session = validate_session(db, session_id, user_agent)
        if session:
            invalidate_session(db, session)

    response.delete_cookie(
        key=settings.SESSION_COOKIE_NAME,
        httponly=True,
        secure=True,
        samesite="lax",
    )
