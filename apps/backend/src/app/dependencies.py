from typing import TYPE_CHECKING, Annotated

from fastapi import Cookie, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from src.app.repository.database import db_session
from src.app.services.storage import S3StorageBackend, StorageBackend
from src.app.services.user_session import validate_session
from src.app.settings import settings
from src.app.utils import get_client_ip

if TYPE_CHECKING:
    from src.app.repository.models import User

__all__ = ["authenticated_user", "db_session", "file_storage"]


def file_storage() -> StorageBackend:
    return S3StorageBackend()


def authenticated_user(
    request: Request,
    db: Annotated[Session, Depends(db_session)],
    session_id: Annotated[
        str | None, Cookie(alias=settings.SESSION_COOKIE_NAME)
    ] = None,
) -> User:
    """Validate the session cookie and return the authenticated user."""
    if not session_id:
        raise HTTPException(status_code=401, detail="Authentication required")

    user_agent = request.headers.get("user-agent", "")
    ip_address = get_client_ip(request)

    session = validate_session(db, session_id, user_agent, ip_address)
    if not session:
        raise HTTPException(status_code=401, detail="Invalid or expired session")

    return session.user
