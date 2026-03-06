"""Upload endpoints."""

from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from pydantic import Field
from sqlalchemy.orm import Session

from src.app.dependencies import (
    authenticated_user,
    get_db,
    get_storage_backend,
)
from src.app.repository.models import Upload, UploadStatusValue, User
from src.app.services.storage import StorageBackend
from src.app.services.upload import create_upload as create_upload_service
from src.app.services.upload import list_uploads as list_uploads_service
from src.app.services.upload import maybe_presigned_url
from src.app.settings import settings
from src.app.utils import BaseSchema, PaginatedResult

router = APIRouter()


class UploadResponse(BaseSchema):
    """Response body for upload endpoints."""

    uid: str
    original_filename: str
    file_size: int
    s3_key: str
    created_at: datetime
    current_status: str
    presigned_url: str | None = None
    required_headers: dict[str, str] | None = None


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


def _build_upload_response(
    upload: Upload,
    storage: StorageBackend,
) -> UploadResponse:
    """Map an Upload ORM instance to an UploadResponse schema."""
    presigned_url, required_headers = maybe_presigned_url(upload, storage)
    return UploadResponse(
        uid=upload.uid,
        original_filename=upload.original_filename,
        file_size=upload.file_size,
        s3_key=upload.s3_key,
        created_at=upload.created_at,
        current_status=upload.current_status or "",
        presigned_url=presigned_url,
        required_headers=required_headers,
    )


@router.post("/uploads", status_code=201, operation_id="createUpload")
def create_upload(
    body: CreateUploadRequest,
    user: Annotated[User, Depends(authenticated_user)],
    db: Annotated[Session, Depends(get_db)],
    storage: Annotated[StorageBackend, Depends(get_storage_backend)],
) -> UploadResponse:
    """Create a new GPX file upload and return a presigned URL."""
    upload = create_upload_service(
        db=db,
        user=user,
        original_filename=body.original_filename,
        file_size=body.file_size,
    )
    return _build_upload_response(upload, storage)


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

    result = list_uploads_service(
        db=db,
        user=user,
        page_size=params.page_size,
        cursor=params.cursor,
        statuses=statuses,
    )

    return PaginatedResult(
        items=[_build_upload_response(u, storage) for u in result.items],
        previous_cursor=result.previous_cursor,
        next_cursor=result.next_cursor,
        has_previous=result.has_previous,
        has_next=result.has_next,
    )
