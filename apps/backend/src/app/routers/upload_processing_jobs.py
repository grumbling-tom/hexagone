"""Upload processing endpoints.

The browser calls this once it has finished PUTting a GPX file to its
presigned URL. Processing runs synchronously in the request today; the
resource name leaves room to make it a queued background job later
without changing the URL.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from src.app.dependencies import authenticated_user, db_session, file_storage
from src.app.repository.models import User
from src.app.routers.uploads import UploadResponse
from src.app.services.storage import StorageBackend
from src.app.services.upload import UploadNotInStorageError, process_user_upload
from src.app.utils import BaseSchema

router = APIRouter()


class CreateUploadProcessingJobRequest(BaseSchema):
    """Request body for processing an upload."""

    upload_uid: str


@router.post(
    "/upload-processing-jobs",
    operation_id="createUploadProcessingJob",
    responses={
        404: {"description": "Upload not found"},
        409: {"description": "The file has not landed in storage yet"},
    },
)
def create_upload_processing_job(
    body: CreateUploadProcessingJobRequest,
    user: Annotated[User, Depends(authenticated_user)],
    db: Annotated[Session, Depends(db_session)],
    storage: Annotated[StorageBackend, Depends(file_storage)],
) -> UploadResponse:
    """Process an uploaded GPX file and return the upload with its final status.

    `current_status` comes back as `UPLOAD_SUCCESS`, or `UPLOAD_INVALID` with
    the reason in `current_status_detail`. Calling it again for an upload
    that has already been processed is a no-op that returns it unchanged.
    """
    try:
        upload = process_user_upload(db, user, body.upload_uid, storage)
    except UploadNotInStorageError:
        raise HTTPException(
            status_code=409, detail="The file has not finished uploading yet"
        ) from None
    if upload is None:
        raise HTTPException(status_code=404, detail="Upload not found")
    return UploadResponse.model_validate(upload)
