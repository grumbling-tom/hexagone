"""FastAPI dependencies for use with Depends()."""

from fastapi import HTTPException

from src.app.context import current_user
from src.app.repository.database import get_db
from src.app.repository.models import User  # noqa: TC001

__all__ = ["authenticated_user", "get_db"]


def authenticated_user() -> User:
    """Return the current user or raise 401."""
    user = current_user.get()
    if user is None:
        raise HTTPException(status_code=401, detail="Authentication required")
    return user
