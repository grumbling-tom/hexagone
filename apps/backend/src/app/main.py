"""FastAPI application entry point."""

from fastapi import APIRouter, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.app.routers.health import router as health_router
from src.app.routers.hex_claims import (
    aggregated_hex_claims_router,
    hex_claims_router,
)
from src.app.routers.uploads import router as uploads_router
from src.app.routers.user_sessions import router as user_sessions_router
from src.app.routers.users import router as users_router
from src.app.settings import Settings, settings
from src.app.utils import configure_logging

configure_logging()


def create_app(settings: Settings = settings) -> FastAPI:
    """Create a configured FastAPI application instance."""
    app = FastAPI(title="Backend")

    if settings.ENV == "DEV":
        app.add_middleware(
            CORSMiddleware,
            allow_origins=["http://localhost:4321"],
            allow_methods=["GET", "POST", "PUT", "DELETE"],
            allow_headers=["*"],
            allow_credentials=True,
        )

    api_v1_router = APIRouter(prefix="/api/v1")
    api_v1_router.include_router(users_router, tags=["users"])
    api_v1_router.include_router(user_sessions_router, tags=["user-sessions"])
    api_v1_router.include_router(uploads_router, tags=["uploads"])
    api_v1_router.include_router(hex_claims_router, tags=["hex-claims"])
    api_v1_router.include_router(
        aggregated_hex_claims_router, tags=["aggregated-hex-claims"]
    )

    app.include_router(health_router, prefix="/api", tags=["health"])
    app.include_router(api_v1_router)
    return app


app = create_app()
