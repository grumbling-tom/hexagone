"""Storage abstraction for file uploads."""

import uuid
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

import boto3

from src.app.settings import settings

if TYPE_CHECKING:
    from mypy_boto3_s3 import S3Client


class StorageBackend(ABC):
    """Abstract storage backend for file operations."""

    @abstractmethod
    def generate_presigned_put_url(
        self,
        key: str,
        content_type: str,
        content_length: int,
        expires_in: int,
    ) -> str:
        """Generate a presigned PUT URL for uploading a file.

        Args:
            key: Object key in the bucket.
            content_type: MIME type of the file.
            content_length: Expected file size in bytes.
            expires_in: URL expiry time in seconds.

        Returns:
            Presigned PUT URL string.
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

    def generate_presigned_put_url(
        self,
        key: str,
        content_type: str,
        content_length: int,
        expires_in: int,
    ) -> str:
        """Generate a presigned S3 PUT URL with content-length condition."""
        url: str = self._client.generate_presigned_url(
            "put_object",
            Params={
                "Bucket": settings.GPX_UPLOAD_BUCKET,
                "Key": key,
                "ContentType": content_type,
                "ContentLength": content_length,
            },
            ExpiresIn=expires_in,
        )
        return url

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

    def generate_presigned_put_url(
        self,
        key: str,
        content_type: str,  # noqa: ARG002
        content_length: int,  # noqa: ARG002
        expires_in: int,  # noqa: ARG002
    ) -> str:
        """Generate a fake presigned URL for local development."""
        return f"http://localhost:9000/fake-presigned/{key}?token={uuid.uuid4()}"

    def get_object(self, key: str) -> bytes:
        """Read from local filesystem (not implemented for dev)."""
        msg = "LocalStorageBackend.get_object is not implemented"
        raise NotImplementedError(msg)
