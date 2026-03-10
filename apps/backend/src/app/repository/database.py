import uuid
from collections.abc import Generator
from contextlib import contextmanager
from datetime import UTC, datetime

from sqlalchemy import DateTime, String, create_engine, text
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, sessionmaker

from ..settings import settings
from ..utils import get_logger

logger = get_logger(__name__)

engine = create_engine(settings.DATABASE_URL, pool_pre_ping=True)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class BaseModel(DeclarativeBase):
    """Abstract base class for all SQLAlchemy models.

    Provides common fields that all models should have, including
    a UUID v7 primary key and creation timestamp.

    UUIDs use version 7 for time-ordered, monotonically increasing IDs
    that provide better database indexing performance and sortability.
    """

    __abstract__ = True

    uid: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid7()), index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
    )


@contextmanager
def get_db() -> Generator[Session]:
    """Context manager that provides a database session.

    This is a context manager that can be used with the 'with' statement
    to ensure proper cleanup of the database session. It is to be used
    in non-FastAPI contexts where Depends() cannot be used, e.g.
    in background tasks or workers.

    Yields:
        Database session that is automatically closed after use.

    Examples:
        with get_db() as db:
            ...
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def db_session() -> Generator[Session]:
    """Dependency function that provides a database session.

    This is a plain generator function designed for use with FastAPI's
    Depends() dependency injection system.

    Yields:
        Database session that is automatically closed after use.

    Examples as FastAPI dependency:
        def route(db: Session = Depends(db_session)):
            ...
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def check_database_health() -> bool:
    """Check if the database is accessible and responsive.

    Returns:
        True if the database is healthy, False otherwise.
    """
    try:
        with get_db() as db:
            db.execute(text("SELECT 1"))
    except OperationalError:
        logger.exception("database_health_check_failed")
        return False
    else:
        logger.debug("database_health_check_passed")
        return True
