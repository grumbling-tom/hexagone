"""Tigris object-notification webhook.

Tigris POSTs here when an object lands in the GPX bucket; we enqueue a
``process_upload`` job and return promptly. Delivery is at-least-once and may be
out of order — ``process_upload`` guards on ``UPLOAD_PENDING``, so duplicate or
late notifications are safe no-ops.

Payload shape and the ``OBJECT_CREATED_PUT`` event name follow the Tigris docs:
https://www.tigrisdata.com/docs/buckets/object-notifications/
"""

import secrets
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import Field

from src.app.settings import settings
from src.app.utils import BaseSchema
from src.worker.defer import defer_process_upload

router = APIRouter()

_bearer = HTTPBearer(auto_error=False)


def verify_notification_secret(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
) -> None:
    """Reject requests without a valid Bearer shared secret."""
    expected = settings.UPLOAD_NOTIFICATION_SECRET
    if (
        credentials is None
        or not expected
        or not secrets.compare_digest(credentials.credentials, expected)
    ):
        raise HTTPException(status_code=401, detail="Invalid notification secret")


class NotificationObject(BaseSchema):
    """The ``object`` block of a Tigris notification event."""

    key: str


class NotificationEvent(BaseSchema):
    """A single Tigris object-notification event."""

    event_name: str = Field(alias="eventName")
    obj: NotificationObject = Field(alias="object")


class UploadNotification(BaseSchema):
    """Request body for the Tigris object-notification webhook."""

    events: list[NotificationEvent]


@router.post(
    "/upload-notifications",
    status_code=202,
    operation_id="createUploadNotification",
    dependencies=[Depends(verify_notification_secret)],
)
def create_upload_notification(body: UploadNotification) -> None:
    """Enqueue a processing job for each newly-created object."""
    for event in body.events:
        # OBJECT_CREATED_PUT: object created/updated via PUT (see module docstring).
        if event.event_name == "OBJECT_CREATED_PUT":
            defer_process_upload(event.obj.key)
