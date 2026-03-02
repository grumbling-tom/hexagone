"""Context variables for request-scoped state.

Standalone module to avoid circular imports between middleware and routes.
"""

from __future__ import annotations

from contextvars import ContextVar
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.app.repository.models import User, UserSession

current_user_session: ContextVar[UserSession | None] = ContextVar(
    "current_user_session", default=None
)
current_user: ContextVar[User | None] = ContextVar("current_user", default=None)
