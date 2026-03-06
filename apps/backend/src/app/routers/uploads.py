"""Upload endpoints."""

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from pydantic import Field
from sqlalchemy.orm import Session

from src.app.dependencies import (
    authenticated_user,
    get_db,
    get_storage_backend,
)
from src.app.repository.models import UploadStatusValue, User
from src.app.services.storage import StorageBackend
from src.app.services.upload import UploadResponse
from src.app.services.upload import create_upload as create_upload_service
from src.app.services.upload import list_uploads as list_uploads_service
from src.app.settings import settings
from src.app.utils import BaseSchema, PaginatedResult

router = APIRouter()


class CreateUploadRequest(BaseSchema):
    """Request body for creating a new upload."""

    original_filename: str
    file_size: int


class ListUploadsParams(BaseSchema):
    """Query parameters for listing uploads."""

    page_size: int = Field(
        default=settings.DEFAULT_PAGE_SIZE,
        gt=0,
        le=100,
    )
    cursor: str | None = Field(default=None)
    statuses: list[UploadStatusValue] | None = Field(default=None)


@router.post("/uploads", status_code=201, operation_id="createUpload")
def create_upload(
    body: CreateUploadRequest,
    user: Annotated[User, Depends(authenticated_user)],
    db: Annotated[Session, Depends(get_db)],
    storage: Annotated[StorageBackend, Depends(get_storage_backend)],
) -> UploadResponse:
    """Create a new GPX file upload and return a presigned URL."""
    return create_upload_service(
        db=db,
        user=user,
        original_filename=body.original_filename,
        file_size=body.file_size,
        storage=storage,
    )


@router.get("/uploads", operation_id="listUploads")
def list_uploads(
    user: Annotated[User, Depends(authenticated_user)],
    db: Annotated[Session, Depends(get_db)],
    storage: Annotated[StorageBackend, Depends(get_storage_backend)],
    params: Annotated[ListUploadsParams, Query()],
) -> PaginatedResult[UploadResponse]:
    """List the authenticated user's uploads, filtered by status."""
    statuses: list[str] | None = None
    if params.statuses is not None:
        statuses = [s.value for s in params.statuses]

    return list_uploads_service(
        db=db,
        user=user,
        storage=storage,
        page_size=params.page_size,
        cursor=params.cursor,
        statuses=statuses,
    )
