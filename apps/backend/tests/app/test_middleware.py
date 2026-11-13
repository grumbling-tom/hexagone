"""Tests for the ASGI middleware."""

import asyncio
from typing import Any
from unittest.mock import patch

from starlette.types import Message, Receive, Scope, Send

from src.app import middleware as middleware_module
from src.app.middleware import AccessLogMiddleware


class _FixedStatusApp:
    """Minimal ASGI app that responds with a fixed status code."""

    def __init__(self, status: int) -> None:
        self.status = status

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        await send(
            {"type": "http.response.start", "status": self.status, "headers": []}
        )
        await send({"type": "http.response.body", "body": b"ok"})


async def _receive() -> Message:
    return {"type": "http.request", "body": b"", "more_body": False}


def _drive(app: Any, scope: Scope) -> None:
    async def _send(_message: Message) -> None:
        return

    asyncio.run(app(scope, _receive, _send))


def test_health_check_is_not_access_logged():
    middleware = AccessLogMiddleware(_FixedStatusApp(200))
    scope: Scope = {"type": "http", "method": "GET", "path": "/api/health"}

    with patch.object(middleware_module, "logger") as mock_logger:
        _drive(middleware, scope)

    mock_logger.info.assert_not_called()


def test_request_is_access_logged_with_request_fields():
    middleware = AccessLogMiddleware(_FixedStatusApp(404))
    scope: Scope = {"type": "http", "method": "POST", "path": "/api/v1/users"}

    with patch.object(middleware_module, "logger") as mock_logger:
        _drive(middleware, scope)

    mock_logger.info.assert_called_once()
    _, kwargs = mock_logger.info.call_args
    assert mock_logger.info.call_args.args[0] == "http_request"
    assert kwargs["method"] == "POST"
    assert kwargs["path"] == "/api/v1/users"
    assert kwargs["status"] == 404
    assert kwargs["duration_ms"] >= 0


def test_non_http_scope_passes_through_without_logging():
    middleware = AccessLogMiddleware(_FixedStatusApp(200))
    scope: Scope = {"type": "lifespan"}

    with patch.object(middleware_module, "logger") as mock_logger:
        _drive(middleware, scope)

    mock_logger.info.assert_not_called()
