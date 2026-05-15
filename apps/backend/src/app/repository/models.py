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
    UniqueConstraint,
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
    hex_claims: Mapped[list[HexClaim]] = relationship(
        back_populates="upload",
        lazy="raise",
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


class HexClaim(BaseModel):
    """Represents a single H3 hex cell claimed by a user via an upload.

    One row per `(upload, polygon_index, h3_cell)` triple. Powers the
    leaderboard query "who has claimed this hex?".

    Attributes:
        upload_uid: The UID of the upload that produced this claim.
        upload: The parent upload.
        user_uid: The UID of the claiming user. Denormalised from
            `upload.user_uid` so the leaderboard query doesn't need a join.
        h3_cell: The H3 cell ID covered by the claim.
        h3_resolution: The H3 resolution of `h3_cell`.
        polygon_index: 0-based index of the closed polygon (within this
            upload) that produced this claim.
        completed_at: Timestamp of the GPX trackpoint that closed the
            polygon. Nullable — some GPX files have no `<time>` tags.
        git_sha: Code version that produced this row.
    """

    __tablename__ = "hex_claim"

    upload_uid: Mapped[str] = mapped_column(
        String(36), ForeignKey("upload.uid"), nullable=False, index=True
    )
    user_uid: Mapped[str] = mapped_column(
        String(36), ForeignKey("user.uid"), nullable=False, index=True
    )
    h3_cell: Mapped[str] = mapped_column(String(15), nullable=False, index=True)
    h3_resolution: Mapped[int] = mapped_column(Integer, nullable=False)
    polygon_index: Mapped[int] = mapped_column(Integer, nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    git_sha: Mapped[str | None] = mapped_column(String(40), nullable=True)

    upload: Mapped[Upload] = relationship(back_populates="hex_claims")


class UserGroup(BaseModel):
    """A named group that users can be members of.

    Attributes:
        name: Display name. Not unique — identity is the uid.
        owner_uid: The single owner; only this user can rename or
            archive the group, and they cannot leave it while it has
            other members (they must archive instead).
        archived: Soft-delete flag.
        members: Read-only many-to-many traversal to User through
            ``user_group_membership``. Exposed so that filters can
            ask "is this user a member of this group?" via the
            standard Filter pattern (e.g. ``RelationFilter(
            field="members", inner=EqualsFilter(field="uid", value=X)
            )``). Writes go through ``UserGroupMembership`` directly
            so ``share_consent`` and ``invited_by_uid`` stay
            first-class.
    """

    __tablename__ = "user_group"

    name: Mapped[str] = mapped_column(String(80), nullable=False)
    owner_uid: Mapped[str] = mapped_column(
        String(36), ForeignKey("user.uid"), nullable=False, index=True
    )
    archived: Mapped[bool] = mapped_column(Boolean, default=False, index=True)

    # Explicit primaryjoin/secondaryjoin: UserGroupMembership has two FKs to
    # user.uid (user_uid + invited_by_uid), so SQLAlchemy can't disambiguate
    # without help. viewonly=True so this side never tries to manage writes.
    # lazy="raise" so loaded UserGroup instances never silently trigger
    # N+1s; the relationship is a query-shape primitive.
    members: Mapped[list[User]] = relationship(
        "User",
        secondary="user_group_membership",
        primaryjoin="UserGroup.uid == foreign(UserGroupMembership.user_group_uid)",
        secondaryjoin="User.uid == foreign(UserGroupMembership.user_uid)",
        viewonly=True,
        lazy="raise",
    )


class UserGroupMembership(BaseModel):
    """Many-to-many link between users and groups, with a sharing flag.

    Attributes:
        user_uid: The member.
        user_group_uid: The group.
        share_consent: Whether this member's hex claims and profile are
            visible to other group members. Defaults to True (joining is
            an act of consent); a member can flip this off at any time.
        invited_by_uid: The user who invited this member. NULL for
            the group's founding owner. Stored on the membership row so
            the relationship graph survives invitation cleanup.
    """

    __tablename__ = "user_group_membership"
    __table_args__ = (
        UniqueConstraint(
            "user_uid",
            "user_group_uid",
            name="uq_user_group_membership_user_group",
        ),
    )

    user_uid: Mapped[str] = mapped_column(
        String(36), ForeignKey("user.uid"), nullable=False, index=True
    )
    user_group_uid: Mapped[str] = mapped_column(
        String(36), ForeignKey("user_group.uid"), nullable=False, index=True
    )
    share_consent: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    invited_by_uid: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("user.uid"), nullable=True
    )

    # Two FKs to user, so foreign_keys= is required to disambiguate.
    user: Mapped[User] = relationship(
        "User",
        foreign_keys="UserGroupMembership.user_uid",
        lazy="selectin",
    )


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
