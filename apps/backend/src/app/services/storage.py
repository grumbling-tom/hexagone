"""Storage abstraction for file uploads."""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import TYPE_CHECKING, Literal

import boto3

from src.app.settings import settings
from src.app.utils import get_logger

if TYPE_CHECKING:
    from mypy_boto3_s3 import S3Client


logger = get_logger(__name__)


class StorageBackend(ABC):
    """Abstract storage backend for file operations."""

    @abstractmethod
    def generate_presigned_url(  # noqa: PLR0913
        self,
        filename: str,
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
        kwargs: dict[str, str | None] = {
            "region_name": settings.HEXAGONE_AWS_REGION,
        }

        if settings.HEXAGONE_S3_ENDPOINT_URL:
            # Use explicit credentials and endpoint for LocalStack (dev).
            kwargs["endpoint_url"] = settings.HEXAGONE_S3_ENDPOINT_URL
            kwargs["aws_access_key_id"] = settings.AWS_ACCESS_KEY_ID
            kwargs["aws_secret_access_key"] = settings.AWS_SECRET_ACCESS_KEY
        else:
            # Use the region-specific endpoint so pre-signed URLs contain the
            # correct hostname and don't trigger S3 TemporaryRedirect responses.
            kwargs["endpoint_url"] = (
                f"https://s3.{settings.HEXAGONE_AWS_REGION}.amazonaws.com"
            )

        self._client: S3Client = boto3.client(  # pyright: ignore[reportUnknownMemberType]
            "s3",
            **{k: v for k, v in kwargs.items() if v},  # type: ignore
        )

    def generate_presigned_url(  # noqa: PLR0913
        self,
        filename: str,
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
                    "Bucket": settings.HEXAGONE_S3_BUCKET,
                    "Key": str(key),
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

        params: dict[str, str | int | dict[str, str]] = {
            "Bucket": settings.HEXAGONE_S3_BUCKET,
            "Key": str(key),
            "ContentType": content_type,
            "ContentLength": content_length,
            "ContentDisposition": f"attachment; filename={filename}",
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
            Bucket=settings.HEXAGONE_S3_BUCKET,
            Key=key,
        )
        data: bytes = response["Body"].read()
        return data
