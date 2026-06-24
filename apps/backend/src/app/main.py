"""FastAPI application entry point."""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager, nullcontext
from functools import partial

from fastapi import APIRouter, FastAPI, Request
from fastapi.responses import JSONResponse
from procrastinate import App
from procrastinate.connector import BaseConnector
from procrastinate.contrib.sqlalchemy import SQLAlchemyPsycopg2Connector

from src.app.middleware import RequestThrottlerMiddleware
from src.app.repository import NotAuthorisedError
from src.app.repository.database import engine
from src.app.routers.health import router as health_router
from src.app.routers.hex_claims import (
    aggregated_hex_claims_router,
    hex_claims_router,
)
from src.app.routers.login_tokens import router as login_tokens_router
from src.app.routers.upload_processing_jobs import (
    router as upload_processing_jobs_router,
)
from src.app.routers.uploads import router as uploads_router
from src.app.routers.user_groups import router as user_groups_router
from src.app.routers.user_sessions import router as user_sessions_router
from src.app.routers.users import router as users_router
from src.app.settings import Settings, settings
from src.app.telemetry import setup_tracing
from src.app.utils import configure_logging
from src.worker.tasks import NAMESPACE, blueprint

configure_logging()

def _handle_not_authorised(request: Request, exc: Exception) -> JSONResponse:  # noqa: ARG001 — request/exc are required by Starlette's exception-handler signature
    """Map a repository write-guard rejection to 403 Forbidden.

    Services let `NotAuthorisedError` propagate rather than translating it,
    so authorization failures are rendered consistently in one place.
    """
    return JSONResponse(status_code=403, content={"detail": "Not authorised"})


@asynccontextmanager
async def lifespan(
    app: FastAPI,
    *,
    procrastinate_connector: BaseConnector | None,
) -> AsyncGenerator[None]:
    """Open the defer-only Procrastinate app for the server's lifetime.

    ``procrastinate_connector`` (an ``InMemoryConnector`` in tests) replaces the
    production SQLAlchemy connector for the app's lifetime; otherwise the defer
    app opens against the shared SQLAlchemy ``engine``.
    """
    if not procrastinate_connector:
        procrastinate_connector = SQLAlchemyPsycopg2Connector()

    procrastinate_app = App(connector=procrastinate_connector)
    procrastinate_app.open(engine)
    procrastinate_app.add_tasks_from(blueprint, namespace=NAMESPACE)

    # Expose the running defer app so tests can assert on its registered tasks.
    app.state.procrastinate_app = procrastinate_app

    try:
        yield
    finally:
        procrastinate_app.close()



def create_app(
    settings: Settings = settings,
    procrastinate_connector: BaseConnector | None = None,
) -> FastAPI:
    """Create a configured FastAPI application instance.

    ``procrastinate_connector`` overrides the connector the defer-only
    Procrastinate app runs on for this app's lifetime. Tests inject an
    ``InMemoryConnector`` so enqueued jobs are inspectable and no real database
    is touched; production leaves it ``None`` and uses the SQLAlchemy connector
    bound to ``engine``.
    """
    app = FastAPI(
        title="Backend",
        lifespan=partial(lifespan, procrastinate_connector=procrastinate_connector),
    )

    # No CORS: the browser never calls the backend directly (Next.js reaches it
    # server-side via RSC / Server Actions), so cross-origin requests don't occur.

    if settings.THROTTLE_DELAY_SECONDS is not None:
        app.add_middleware(
            RequestThrottlerMiddleware, delay_seconds=settings.THROTTLE_DELAY_SECONDS
        )

    api_v1_router = APIRouter(prefix="/api/v1")
    api_v1_router.include_router(users_router, tags=["users"])
    api_v1_router.include_router(user_sessions_router, tags=["user-sessions"])
    api_v1_router.include_router(login_tokens_router, tags=["login-tokens"])
    api_v1_router.include_router(uploads_router, tags=["uploads"])
    api_v1_router.include_router(
        upload_processing_jobs_router, tags=["upload-processing-jobs"]
    )
    api_v1_router.include_router(hex_claims_router, tags=["hex-claims"])
    api_v1_router.include_router(
        aggregated_hex_claims_router, tags=["aggregated-hex-claims"]
    )
    api_v1_router.include_router(user_groups_router, tags=["user-groups"])

    app.include_router(health_router, prefix="/api", tags=["health"])
    app.include_router(api_v1_router)

    app.add_exception_handler(NotAuthorisedError, _handle_not_authorised)

    # Instrument last, once every route and middleware is in place.
    setup_tracing(app, settings)
    return app


app = create_app()
