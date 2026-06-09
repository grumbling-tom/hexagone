import asyncio
from collections.abc import Callable
from typing import Any

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp


class RequestThrottlerMiddleware(BaseHTTPMiddleware):
    delay_seconds: float

    def __init__(self, app: ASGIApp, delay_seconds: float) -> None:
        super().__init__(app)
        self.delay_seconds = delay_seconds

    async def dispatch(self, request: Request, call_next: Callable[..., Any]) -> Any:  # noqa: ANN401
        if self.delay_seconds > 0:
            await asyncio.sleep(self.delay_seconds)
        return await call_next(request)
