"""Database operations: migrate and reset.

Previously an AWS Lambda handler invoked with an action payload; now a plain
module run by a k8s Job (or locally):

    python -m src.app.db_ops migrate   # apply pending migrations
    python -m src.app.db_ops reset     # drop all tables, then re-migrate (destructive)
"""

import subprocess
import sys

from sqlalchemy import text

from src.app.repository import BaseModel, SessionLocal, engine
from src.app.utils import get_logger

logger = get_logger(__name__)


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


def main(argv: list[str] | None = None) -> None:
    """Run a database operation from the command line.

    Supported actions:
    - "migrate": Apply pending database migrations only.
    - "reset": Drop all tables and reapply all migrations (destructive).
    """
    args = sys.argv[1:] if argv is None else argv
    action = args[0] if args else ""

    match action:
        case "migrate":
            run_migrations()
            logger.info("db_ops_completed", action="migrate")
        case "reset":
            reset_database()
            run_migrations()
            logger.info("db_ops_completed", action="reset")
        case _:
            msg = f"usage: python -m src.app.db_ops [migrate|reset] (got {action!r})"
            raise SystemExit(msg)


if __name__ == "__main__":
    main()
