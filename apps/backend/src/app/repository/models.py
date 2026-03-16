"""Domain models for the application."""

import enum
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    String,
    desc,
    select,
)
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import BaseModel

if TYPE_CHECKING:
    from sqlalchemy import ScalarSelect


class UploadStatusValue(enum.StrEnum):
    """Allowed status values for upload processing."""

    UPLOAD_PENDING = "UPLOAD_PENDING"
    UPLOAD_RECEIVED = "UPLOAD_RECEIVED"
    UPLOAD_SUCCESS = "UPLOAD_SUCCESS"
    UPLOAD_INVALID = "UPLOAD_INVALID"


class User(BaseModel):
    """Represents a user in the system.

    Attributes:
        email: The user's email address.
        password_hash: Bcrypt hash of the user's password.
        archived: Whether the user account is archived (soft deleted).
    """

    __tablename__ = "user"

    email: Mapped[str] = mapped_column(String, unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(String, nullable=False)
    archived: Mapped[bool] = mapped_column(Boolean, default=False, index=True)


class Upload(BaseModel):
    """Represents a GPX file upload.

    Attributes:
        user_uid: The UID of the user who uploaded the file.
        original_filename: Client-provided filename.
        file_size_bytes: Expected file size in bytes, declared by client.
        s3_bucket_name: The S3 bucket where the file is stored.
        s3_key: Object key in the GPX bucket.
        statuses: All status events, ordered by created_at ascending.
    """

    __tablename__ = "upload"

    user_uid: Mapped[str] = mapped_column(
        String(36), ForeignKey("user.uid"), nullable=False, index=True
    )
    original_filename: Mapped[str] = mapped_column(String, nullable=False)
    file_size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    s3_bucket_name: Mapped[str] = mapped_column(String, nullable=False)
    s3_key: Mapped[str] = mapped_column(String, unique=True, nullable=False)

    statuses: Mapped[list[UploadStatus]] = relationship(
        back_populates="upload",
        order_by="UploadStatus.created_at.asc()",
        lazy="selectin",
    )

    @hybrid_property
    def current_status(self) -> str:
        """Return the most recent status value, or None if no statuses exist."""
        if not self.statuses:
            msg = f"Upload {self.uid} has no statuses!"
            raise ValueError(msg)

        return self.statuses[-1].status  # TODO: Return an UploadStatusValue enum

    @current_status.inplace.expression
    @classmethod
    def _current_status_expression(cls) -> ScalarSelect[str]:
        """SQL-side: correlated subquery for the latest status value."""
        return (
            select(UploadStatus.status)
            .where(UploadStatus.upload_uid == cls.uid)
            .order_by(desc(UploadStatus.created_at), desc(UploadStatus.uid))
            .limit(1)
            .correlate(cls)
            .scalar_subquery()
        )


class UploadStatus(BaseModel):
    """Append-only event log for upload processing status.

    Attributes:
        upload_uid: The UID of the parent upload.
        upload: The parent upload.
        status: Current status value.
        git_sha: Code version that processed the file.
        detail: Optional error detail for UPLOAD_INVALID.
    """

    __tablename__ = "upload_status"

    upload_uid: Mapped[str] = mapped_column(
        String(36), ForeignKey("upload.uid"), nullable=False, index=True
    )
    status: Mapped[str] = mapped_column(
        String,
        CheckConstraint(
            "status IN ('UPLOAD_PENDING', 'UPLOAD_RECEIVED',"
            " 'UPLOAD_SUCCESS', 'UPLOAD_INVALID')",
            name="ck_upload_status_value",
        ),
        nullable=False,
    )
    git_sha: Mapped[str | None] = mapped_column(String(40), nullable=True)
    detail: Mapped[str | None] = mapped_column(String, nullable=True)

    upload: Mapped[Upload] = relationship(back_populates="statuses")


class UserSession(BaseModel):
    """User session for authentication and session management.

    Sessions are bound to a user, user agent, and IP address for security.
    Sessions expire after a configurable period of inactivity (sliding window).

    Attributes:
        user_uid: The UID of the user who owns this session.
        user: The user who owns this session.
        user_agent_hash: SHA-256 hash of user agent string for fingerprinting.
        ip_address: Client IP address bound to this session.
        expires_at: Session expiration timestamp.
    """

    __tablename__ = "user_session"

    user_uid: Mapped[str] = mapped_column(
        String(36), ForeignKey("user.uid"), nullable=False, index=True
    )
    user: Mapped[User] = relationship("User")

    user_agent_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    ip_address: Mapped[str] = mapped_column(String(45), nullable=False)

    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
