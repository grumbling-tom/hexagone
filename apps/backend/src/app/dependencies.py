"""FastAPI dependencies for dependency injection."""

import time
from typing import TYPE_CHECKING, Annotated

from fastapi import Depends, HTTPException, Request
from sqlalchemy.orm import Session

from src.app.repository.database import db_session
from src.app.services.storage import S3StorageBackend, StorageBackend
from src.app.services.user import get_or_create_user

if TYPE_CHECKING:
    from src.app.repository.models import User

__all__ = ["authenticated_user", "db_session", "file_storage"]

# In-memory cache: external_auth_id -> (User, expiry_timestamp)
_user_cache: dict[str, tuple[User, float]] = {}
_CACHE_TTL_SECONDS = 60


def file_storage() -> StorageBackend:
    """Return the configured file storage backend."""
    return S3StorageBackend()


def _get_cached_user(external_auth_id: str) -> User | None:
    """Return a cached user if the entry exists and hasn't expired."""
    entry = _user_cache.get(external_auth_id)
    if entry is None:
        return None
    user, expiry = entry
    if time.monotonic() > expiry:
        del _user_cache[external_auth_id]
        return None
    return user


def _cache_user(external_auth_id: str, user: User) -> None:
    """Cache a user with a TTL."""
    _user_cache[external_auth_id] = (user, time.monotonic() + _CACHE_TTL_SECONDS)


def authenticated_user(
    request: Request,
    db: Annotated[Session, Depends(db_session)],
) -> User:
    """Extract the authenticated user from JWT claims set by middleware."""
    claims: dict[str, str] | None = getattr(request.state, "auth_claims", None)
    if not claims:
        raise HTTPException(status_code=401, detail="Authentication required")

    external_auth_id: str = claims["sub"]
    email: str = claims.get("email", "")

    cached = _get_cached_user(external_auth_id)
    if cached is not None:
        if cached.archived:
            raise HTTPException(status_code=401, detail="Account is archived")
        return cached

    user = get_or_create_user(db, external_auth_id, email)

    if user.archived:
        raise HTTPException(status_code=401, detail="Account is archived")

    _cache_user(external_auth_id, user)
    return user
