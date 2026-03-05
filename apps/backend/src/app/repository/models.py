"""Domain models for the application."""

from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import BaseModel


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
