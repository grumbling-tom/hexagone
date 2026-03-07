"""Upload endpoints."""

from collections.abc import Callable
from datetime import datetime
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query
from pydantic import Field, ValidationInfo, model_validator
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

    @model_validator(mode="wrap")
    @classmethod
    def _resolve_presigned_url(
        cls,
        data: object,
        handler: Callable[..., UploadResponse],
        info: ValidationInfo,
    ) -> UploadResponse:
        instance = handler(data)
        context: dict[str, Any] = info.context or {}
        storage: StorageBackend | None = context.get("storage")
        if storage is not None and isinstance(data, Upload):
            url, headers = maybe_presigned_url(data, storage)
            instance.presigned_url = url
            instance.required_headers = headers
        return instance


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
    upload = create_upload_service(
        db=db,
        user=user,
        original_filename=body.original_filename,
        file_size=body.file_size,
    )
    return UploadResponse.model_validate(upload, context={"storage": storage})


@router.get("/uploads", operation_id="listUploads")
def list_uploads(
    user: Annotated[User, Depends(authenticated_user)],
    db: Annotated[Session, Depends(get_db)],
    storage: Annotated[StorageBackend, Depends(get_storage_backend)],
    params: Annotated[ListUploadsParams, Query()],
) -> PaginatedResult[UploadResponse]:
    """List the authenticated user's uploads, filtered by status."""
    result = list_uploads_service(
        db=db,
        user=user,
        page_size=params.page_size,
        cursor=params.cursor,
        statuses=params.statuses,
    )

    return PaginatedResult(
        items=[
            UploadResponse.model_validate(u, context={"storage": storage})
            for u in result.items
        ],
        previous_cursor=result.previous_cursor,
        next_cursor=result.next_cursor,
        has_previous=result.has_previous,
        has_next=result.has_next,
    )
