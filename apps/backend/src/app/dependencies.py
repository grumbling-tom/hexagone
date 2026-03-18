"""FastAPI dependencies for dependency injection."""

from typing import TYPE_CHECKING, Annotated

from fastapi import Depends, HTTPException
from sqlalchemy.orm import Session

from src.app.context import auth_claims_context
from src.app.repository.database import db_session
from src.app.services.storage import S3StorageBackend, StorageBackend
from src.app.services.user import get_or_create_user

if TYPE_CHECKING:
    from src.app.repository.models import User

__all__ = ["authenticated_user", "db_session", "file_storage"]


def file_storage() -> StorageBackend:
    """Return the configured file storage backend."""
    return S3StorageBackend()


def authenticated_user(
    db: Annotated[Session, Depends(db_session)],
) -> User:
    """Extract the authenticated user from JWT claims set by middleware."""
    claims = auth_claims_context.get()

    if claims is None:
        raise HTTPException(status_code=401, detail="Authentication required")

    # TODO: Cache me.
    # We wan't to retain our own internal user_id value, so that our foreign keys do not
    # reference external auth IDs. That means a lookup by external_auth_id.
    # Ideally, we'll have this provided as part of the JWT claims.
    user = get_or_create_user(db, claims.sub, claims.email)

    if user.archived:
        raise HTTPException(status_code=401, detail="Account is archived")

    return user
