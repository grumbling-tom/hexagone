"""Session validation middleware for cookie-based authentication."""

from contextlib import contextmanager

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response

from src.app.context import current_user, current_user_session
from src.app.repository.database import get_db
from src.app.services.user_session import validate_session
from src.app.settings import settings
from src.app.utils import get_logger

logger = get_logger(__name__)

EXEMPT_ROUTES: set[tuple[str, str]] = {
    ("POST", "/api/v1/users"),
    ("POST", "/api/v1/user-sessions"),
    ("DELETE", "/api/v1/user-sessions/current"),
}


def _get_client_ip(request: Request) -> str:
    """Extract client IP from X-Forwarded-For header or request.client."""
    forwarded_for = request.headers.get("x-forwarded-for")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    if request.client:
        return request.client.host
    return "unknown"


class SessionValidationMiddleware(BaseHTTPMiddleware):
    """Validate session cookie on every request except exempt routes."""

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        """Check session cookie and set context vars for authenticated routes."""
        method = request.method
        path = request.url.path

        if path.startswith("/api/health"):
            return await call_next(request)

        if (method, path) in EXEMPT_ROUTES:
            return await call_next(request)

        session_id = request.cookies.get(settings.SESSION_COOKIE_NAME)
        if not session_id:
            return JSONResponse(
                status_code=401,
                content={"detail": "Authentication required"},
            )

        user_agent = request.headers.get("user-agent", "")
        ip_address = _get_client_ip(request)

        with contextmanager(get_db)() as db:
            session = validate_session(db, session_id, user_agent, ip_address)
            if not session:
                return JSONResponse(
                    status_code=401,
                    content={"detail": "Invalid or expired session"},
                )

            token_session = current_user_session.set(session)
            token_user = current_user.set(session.user)

        try:
            return await call_next(request)
        finally:
            current_user_session.reset(token_session)
            current_user.reset(token_user)
