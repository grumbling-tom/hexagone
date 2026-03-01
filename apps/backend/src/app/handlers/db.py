"""Lambda handler for database operations.

This module provides a unified AWS Lambda handler for database operations:
- migrate: Apply pending database migrations using Alembic
- reset: Drop all tables and reapply migrations (destructive)

The handler is invoked by GitHub Actions workflows and Terraform provisioners
with different action payloads to perform the appropriate operation.
"""

import subprocess
from typing import Annotated, Any, Literal

from pydantic import Field, TypeAdapter, ValidationError
from sqlalchemy import text

from src.app.repository import BaseModel, SessionLocal, engine
from src.app.utils import BaseSchema, LambdaContext, LambdaResponse, get_logger

logger = get_logger(__name__)


class MigrateEvent(BaseSchema):
    """Event schema for the migrate action."""

    action: Literal["migrate"]


class ResetEvent(BaseSchema):
    """Event schema for the reset action."""

    action: Literal["reset"]


DbOpsEvent = Annotated[
    MigrateEvent | ResetEvent,
    Field(discriminator="action"),
]

db_ops_event_adapter: TypeAdapter[DbOpsEvent] = TypeAdapter(DbOpsEvent)


def run_migrations() -> None:
    """Run Alembic database migrations.

    Executes 'alembic upgrade head' to apply all pending migrations.

    Raises:
        RuntimeError: If migrations fail.
    """
    logger.info("running_migrations")
    subprocess.run(
        ["python", "-m", "alembic", "upgrade", "head"],
        capture_output=True,
        text=True,
        check=True,
    )
    logger.info("migrations_completed")


def reset_database() -> None:
    """Drop all tables from the database.

    This function connects to the database, verifies connectivity,
    and then drops all tables using SQLAlchemy metadata.

    Raises:
        Exception: If database connection fails or table drop fails.
    """
    logger.info("resetting_database")

    logger.info("dropping_all_tables")
    BaseModel.metadata.drop_all(bind=engine)
    logger.info("all_tables_dropped")

    db = SessionLocal()
    try:
        logger.info("Dropping alembic_version table")
        db.execute(text("DROP TABLE alembic_version"))
        db.commit()
        logger.info("alembic_version_table_dropped")
    except Exception:
        logger.exception("failed_to_drop_alembic_version_table")
        raise
    finally:
        db.close()

    logger.info("database_reset_completed")


def handler(event: dict[str, Any], context: LambdaContext) -> LambdaResponse:
    """Execute database operations based on event payload.

    Supported actions:
    - "migrate": Apply pending database migrations only
    - "reset": Drop all tables and reapply all migrations (destructive)

    Args:
        event: Lambda event containing action and action-specific parameters.
        context: AWS Lambda context object.

    Returns:
        Dict with statusCode (200) and body containing operation output.

    Raises:
        RuntimeError: If the operation fails or event validation fails.
    """
    try:
        db_event = db_ops_event_adapter.validate_python(event)
    except ValidationError as e:
        error_message = f"Invalid event payload: {e!s}"
        logger.exception("event_validation_failed")
        raise RuntimeError(error_message) from e

    logger.info(
        "db_ops_handler_invoked",
        action=db_event.action,
        request_id=context.aws_request_id,
    )

    match db_event.action:
        case "migrate":
            run_migrations()
            return {
                "statusCode": 200,
                "body": "Migrations applied successfully.",
            }

        case "reset":
            reset_database()
            run_migrations()
            return {
                "statusCode": 200,
                "body": "Database reset and migrations applied successfully.",
            }
