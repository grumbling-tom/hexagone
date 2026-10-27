"""User endpoints."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from pydantic import EmailStr, Field

from src.app.dependencies import (
    GroupRepo,
    SessionRepo,
    SystemUserRepo,
    TxDep,
    UserRepo,
    authenticated_user,
    email_client,
)
from src.app.repository import User
from src.app.services import user as user_service
from src.app.services import user_group as user_group_service
from src.app.services.email import EmailClient, send_welcome_email
from src.app.services.user import DuplicateEmailError
from src.app.services.user import create_user as create_user_service
from src.app.services.user_session import create_session
from src.app.settings import settings
from src.app.utils import (
    BaseSchema,
    PaginatedResult,
    Redactable,
    get_client_ip,
    get_logger,
)

logger = get_logger(__name__)

router = APIRouter()


class CreateUserRequest(BaseSchema):
    """Request body for user registration."""

    email: EmailStr
    password: str


class ListUsersParams(BaseSchema):
    """Query parameters for listing users.

    ``group_uid`` is required for now — listing all users across the
    system has no current use case and would leak data. Additional
    filters (e.g. by email substring) can be added alongside later.
    """

    group_uid: str = Field(..., min_length=36, max_length=36)
    page_size: int = Field(default=settings.DEFAULT_PAGE_SIZE, gt=0, le=100)
    cursor: str | None = Field(default=None)


class UserResponse(BaseSchema):
    """Response body for user endpoints.

    ``email`` is ``{"redacted": true}`` when the viewer may not see it (they
    are not that user and share no group with them).
    """

    uid: str
    email: Redactable[str]


@router.post("/users", status_code=201, operation_id="createUser")
def create_user(  # noqa: PLR0913 — FastAPI-injected deps
    body: CreateUserRequest,
    request: Request,
    response: Response,
    users: SystemUserRepo,
    sessions: SessionRepo,
    tx: TxDep,
    email: Annotated[EmailClient, Depends(email_client)],
) -> UserResponse:
    """Create a new user account and start a session."""
    try:
        user = create_user_service(users, tx, body.email, body.password)
    except DuplicateEmailError:
        raise HTTPException(status_code=409, detail="Email already taken") from None

    user_agent = request.headers.get("user-agent", "")
    ip_address = get_client_ip(request)
    session = create_session(sessions, tx, user.uid, user_agent, ip_address)

    response.set_cookie(
        key=settings.SESSION_COOKIE_NAME,
        value=session.uid,
        max_age=settings.session_expiry_seconds,
        httponly=True,
        secure=True,
        samesite="strict",
    )

    # Best-effort: a welcome-email failure must not fail signup.
    try:
        send_welcome_email(email, user=user)
    except Exception:
        logger.exception("welcome_email_failed", user_uid=user.uid)

    return UserResponse(uid=user.uid, email=user.email)


@router.get("/users", operation_id="listUsers")
def list_users(
    users: UserRepo,
    groups: GroupRepo,
    params: Annotated[ListUsersParams, Query()],
) -> PaginatedResult[UserResponse]:
    """List users filtered by group membership.

    Caller must be able to see the group (owner OR member); 404 otherwise.
    """
    try:
        result = user_service.list_users(
            users,
            groups,
            group_uid=params.group_uid,
            page_size=params.page_size,
            cursor=params.cursor,
        )
    except user_group_service.UserGroupNotFoundError:
        raise HTTPException(status_code=404, detail="Group not found") from None

    return PaginatedResult(
        items=[UserResponse.model_validate(u) for u in result.items],
        previous_cursor=result.previous_cursor,
        next_cursor=result.next_cursor,
        has_previous=result.has_previous,
        has_next=result.has_next,
    )


@router.get("/users/current", operation_id="getCurrentUser")
def get_current_user(
    user: Annotated[User, Depends(authenticated_user)],
) -> UserResponse:
    """Return the currently authenticated user."""
    return UserResponse(uid=user.uid, email=user.email)
