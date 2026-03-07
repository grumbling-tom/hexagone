"""Storage abstraction for file uploads."""

import uuid
from abc import ABC, abstractmethod
from pathlib import Path
from typing import TYPE_CHECKING, Literal

import boto3

from src.app.settings import settings

if TYPE_CHECKING:
    from mypy_boto3_s3 import S3Client


class StorageBackend(ABC):
    """Abstract storage backend for file operations."""

    @abstractmethod
    def generate_presigned_url(
        self,
        key: Path,
        method: Literal["get_object", "put_object"],
        expires_in: int,
        content_type: str | None = None,
        content_length: int | None = None,
        **file_metadata: str,
    ) -> tuple[str, dict[str, str] | None]:
        """Generate a presigned URL for uploading or downloading a file.

        Args:
            key: Object key in the bucket.
            method: S3 operation ("get_object" or "put_object").
            expires_in: URL expiry time in seconds.
            content_type: MIME type of the file (required for put_object).
            content_length: Expected file size in bytes (required for put_object).

        Returns:
            Presigned URL string.
        """

    @abstractmethod
    def get_object(self, key: str) -> bytes:
        """Retrieve an object's contents.

        Args:
            key: Object key in the bucket.

        Returns:
            File contents as bytes.
        """


class S3StorageBackend(StorageBackend):
    """S3-backed storage using boto3."""

    def __init__(self) -> None:
        self._client: S3Client = boto3.client(  # pyright: ignore[reportUnknownMemberType]
            "s3", region_name=settings.GPX_UPLOAD_REGION
        )

    def generate_presigned_url(
        self,
        key: Path,
        method: Literal["get_object", "put_object"],
        expires_in: int,
        content_type: str | None = None,
        content_length: int | None = None,
        **file_metadata: str,
    ) -> tuple[str, dict[str, str] | None]:
        """Generate a presigned S3 URL for GET or PUT."""
        if method == "get_object":
            url = self._client.generate_presigned_url(
                "get_object",
                Params={
                    "Bucket": settings.GPX_UPLOAD_BUCKET,
                    "Key": key,
                },
                ExpiresIn=expires_in,
            )
            return url, None

        if content_type is None:
            msg = "content_type is required for put_object presigned URLs"
            raise ValueError(msg)

        if content_length is None:
            msg = "content_length is required for put_object presigned URLs"
            raise ValueError(msg)

        params: dict[str, str | dict[str, str]] = {
            "Bucket": settings.GPX_UPLOAD_BUCKET,
            "Key": str(key),
            "ContentType": content_type,
            "ContentLength": str(content_length),
            "ContentDisposition": f'attachment; filename="{key.name}"',
            "Metadata": file_metadata,
        }
        url: str = self._client.generate_presigned_url(
            method,
            Params=params,
            ExpiresIn=expires_in,
        )
        headers: dict[str, str] = {
            "Content-Length": params["ContentLength"],
            "Content-Type": params["ContentType"],
            "Content-Disposition": params["ContentDisposition"],
            # Ensure metadata keys are  are lowercase and prefixed with 'x-amz-meta-'
            # TODO: Fix '"dict[str, str]" is not assignable to "str'
            **{f"x-amz-meta-{k.lower()}": v for k, v in (file_metadata or {}).items()},  #  type: ignore
        }
        return url, headers

    def get_object(self, key: str) -> bytes:
        """Retrieve an object from S3."""
        response = self._client.get_object(
            Bucket=settings.GPX_UPLOAD_BUCKET,
            Key=key,
        )
        data: bytes = response["Body"].read()
        return data


class LocalStorageBackend(StorageBackend):
    """Local filesystem storage for development."""

    def generate_presigned_url(
        self,
        key: Path,
        method: Literal["get_object", "put_object"],
        expires_in: int,  # noqa: ARG002
        content_type: str | None = None,
        content_length: int | None = None,
        **file_metadata: str,  # noqa: ARG002
    ) -> tuple[str, dict[str, str] | None]:
        """Generate a fake presigned URL for local development."""
        url = (
            f"http://localhost:9000/fake-presigned/{method}/{key}?token={uuid.uuid4()}"
        )
        headers = {
            "Content-Length": str(content_length)
            if content_length is not None
            else "0",
            "Content-Type": content_type or "application/octet-stream",
        }
        return url, headers

    def get_object(self, key: str) -> bytes:
        """Read from local filesystem (not implemented for dev)."""
        msg = "LocalStorageBackend.get_object is not implemented"
        raise NotImplementedError(msg)
