"""FastAPI application entry point."""

from fastapi import FastAPI

from src.app.routers.health import router as health_router
from src.app.utils import configure_logging

configure_logging()

app = FastAPI()
app.include_router(health_router)
