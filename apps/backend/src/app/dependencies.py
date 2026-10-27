"""FastAPI dependencies: the session, the viewer, and the repositories built on them.

Routers inject repositories, never a ``Session``. A repository comes from one
of two factories:

  * ``scoped(X)``        — scoped to the signed-in viewer (``ViewerPolicy``).
  * ``system_scoped(X)`` — unrestricted (``SystemPolicy``), for the routes that
    run before there is a viewer (sign-up, sign-in, session checks).

Build each ``Annotated`` alias once at module level: FastAPI caches a
dependency per request by function identity, so a request that asks for
``UserRepo`` twice gets one repository.
"""

from collections.abc import Callable
from typing import Annotated

from fastapi import Cookie, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from src.app.repository import (
    HexClaim,
    HexClaimByCell,
    LoginToken,
    Policy,
    ScopedRepository,
    SystemPolicy,
    Transaction,
    Upload,
    User,
    UserGroup,
    UserGroupMembership,
    UserSession,
)
from src.app.repository.database import BaseModel, db_session
from src.app.services.email import (
    ConsoleEmailClient,
    EmailClient,
    ResendEmailClient,
)
from src.app.services.permissions import ViewerPolicy
from src.app.services.storage import S3StorageBackend, StorageBackend
from src.app.services.user_session import validate_session
from src.app.settings import settings

__all__ = [
    "GroupRepo",
    "HexClaimByCellRepo",
    "HexClaimRepo",
    "LoginTokenRepo",
    "MembershipRepo",
    "PolicyDep",
    "SessionRepo",
    "SystemUserRepo",
    "TxDep",
    "UploadRepo",
    "UserRepo",
    "authenticated_user",
    "db_session",
    "email_client",
    "file_storage",
    "scoped",
    "system_scoped",
]

DbDep = Annotated[Session, Depends(db_session)]


def file_storage() -> StorageBackend:
    return S3StorageBackend()


def email_client() -> EmailClient:
    if settings.ENV in ("DEV", "TEST"):
        return ConsoleEmailClient()
    return ResendEmailClient()


def transaction(db: DbDep) -> Transaction:
    return Transaction(db)


TxDep = Annotated[Transaction, Depends(transaction)]


def system_scoped[T: BaseModel](
    entity: type[T],
) -> Callable[[Session], ScopedRepository[T]]:
    """Dependency factory: an unrestricted repository for ``entity``."""

    def dep(db: DbDep) -> ScopedRepository[T]:
        return ScopedRepository(db, entity, SystemPolicy())

    return dep


SessionRepo = Annotated[
    ScopedRepository[UserSession], Depends(system_scoped(UserSession))
]
LoginTokenRepo = Annotated[
    ScopedRepository[LoginToken], Depends(system_scoped(LoginToken))
]
SystemUserRepo = Annotated[ScopedRepository[User], Depends(system_scoped(User))]


def authenticated_user(
    request: Request,
    sessions: SessionRepo,
    tx: TxDep,
    session_id: Annotated[
        str | None, Cookie(alias=settings.SESSION_COOKIE_NAME)
    ] = None,
) -> User:
    """Validate the session cookie and return the authenticated user.

    The viewer is the policy's input, not data being shown to anyone, so it
    is loaded unmasked through the system-scoped session repository.
    """
    if not session_id:
        raise HTTPException(status_code=401, detail="Authentication required")

    user_agent = request.headers.get("user-agent", "")

    session = validate_session(sessions, tx, session_id, user_agent)
    if not session:
        raise HTTPException(status_code=401, detail="Invalid or expired session")

    return session.user


def viewer_policy(user: Annotated[User, Depends(authenticated_user)]) -> Policy:
    return ViewerPolicy(user)


PolicyDep = Annotated[Policy, Depends(viewer_policy)]


def scoped[T: BaseModel](
    entity: type[T],
) -> Callable[[Session, Policy], ScopedRepository[T]]:
    """Dependency factory: a repository for ``entity`` scoped to the viewer.

    Depending on it implies authentication (via ``viewer_policy``).
    """

    def dep(db: DbDep, policy: PolicyDep) -> ScopedRepository[T]:
        return ScopedRepository(db, entity, policy)

    return dep


UserRepo = Annotated[ScopedRepository[User], Depends(scoped(User))]
GroupRepo = Annotated[ScopedRepository[UserGroup], Depends(scoped(UserGroup))]
MembershipRepo = Annotated[
    ScopedRepository[UserGroupMembership], Depends(scoped(UserGroupMembership))
]
UploadRepo = Annotated[ScopedRepository[Upload], Depends(scoped(Upload))]
HexClaimRepo = Annotated[ScopedRepository[HexClaim], Depends(scoped(HexClaim))]
HexClaimByCellRepo = Annotated[
    ScopedRepository[HexClaimByCell], Depends(scoped(HexClaimByCell))
]
