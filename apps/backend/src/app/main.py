"""FastAPI application entry point."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.app.routers.health import router as health_router
from src.app.settings import Settings, settings
from src.app.utils import configure_logging

configure_logging()


def create_app(settings: Settings = settings) -> FastAPI:
    """Create a configured FastAPI application instance."""
    app = FastAPI()

    if settings.ENV == "DEV":
        app.add_middleware(
            CORSMiddleware,
            allow_origins=["http://localhost:4321"],
            allow_methods=["GET"],
            allow_headers=["*"],
        )

    app.include_router(health_router)
    return app


app = create_app()
