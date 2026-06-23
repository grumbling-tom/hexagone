import asyncio
import time
from collections.abc import Callable
from typing import Any

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from src.app.utils import get_logger

logger = get_logger(__name__)

# The k8s readiness probe hits this every periodSeconds (10s — see
# infra/k8s/base/app/backend.yaml); skip it so its steady drip doesn't bury the
# request lines that actually matter.
_ACCESS_LOG_SKIP_PATHS = frozenset({"/api/health"})


class RequestThrottlerMiddleware(BaseHTTPMiddleware):
    delay_seconds: float

    def __init__(self, app: ASGIApp, delay_seconds: float) -> None:
        super().__init__(app)
        self.delay_seconds = delay_seconds

    async def dispatch(self, request: Request, call_next: Callable[..., Any]) -> Any:  # noqa: ANN401
        if self.delay_seconds > 0:
            await asyncio.sleep(self.delay_seconds)
        return await call_next(request)


class AccessLogMiddleware:
    """Emit one structured access-log line per HTTP request, through structlog.

    Replaces uvicorn's stdlib access log (disabled with ``--no-access-log``) so
    every request line flows through the same structlog pipeline as the rest of
    the app and therefore carries the active span's ``trace_id``/``span_id``
    (stamped by ``add_otel_trace_context``) — keeping a request one correlated
    trace across the frontend and backend. A pure-ASGI middleware (not
    ``BaseHTTPMiddleware``) so it runs in the request task and the OpenTelemetry
    context/contextvars are intact; it is added before ``setup_tracing`` so the
    OTel middleware wraps it and a span is current when it logs.
    """

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http" or scope["path"] in _ACCESS_LOG_SKIP_PATHS:
            await self.app(scope, receive, send)
            return

        status_code = 0

        async def send_wrapper(message: Message) -> None:
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = message["status"]
            await send(message)

        start = time.perf_counter()
        try:
            await self.app(scope, receive, send_wrapper)
        finally:
            logger.info(
                "http_request",
                method=scope["method"],
                path=scope["path"],
                status=status_code,
                duration_ms=round((time.perf_counter() - start) * 1000, 1),
            )
