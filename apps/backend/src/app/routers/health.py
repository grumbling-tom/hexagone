"""Health check endpoint."""

from fastapi import APIRouter, HTTPException

from src.app.repository import check_database_health

router = APIRouter()


@router.get("/health")
async def health() -> dict[str, str]:
    """Return the health status of the application."""
    if not check_database_health():
        msg = "check_database_health failed"
        raise HTTPException(status_code=503, detail=msg)

    return {"status": "ok"}
