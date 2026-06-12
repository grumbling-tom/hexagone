from logging.config import fileConfig

from sqlalchemy import create_engine, pool

from alembic import context
from src.app.repository import BaseModel
from src.app.settings import settings

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = BaseModel.metadata


def include_object(
    obj: object,  # noqa: ARG001
    name: str | None,
    type_: str,
    reflected: bool,  # noqa: ARG001
    compare_to: object,  # noqa: ARG001
) -> bool:
    """Keep Procrastinate's tables out of autogenerate.

    Procrastinate owns its ``procrastinate_*`` tables (created by the
    ``0007_add_procrastinate_schema`` migration), so they aren't in
    ``BaseModel.metadata``. Without this guard, ``--autogenerate`` would see
    them as stray DB objects and emit ``DROP TABLE`` for each. (Autogenerate
    doesn't track stored functions/triggers, so filtering tables is enough.)
    """
    return not (
        type_ == "table" and name is not None and name.startswith("procrastinate_")
    )


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.
    """
    # render_as_batch enables copy-and-move for SQLite (which lacks ALTER TABLE
    # for constraints) and is a no-op on PostgreSQL
    context.configure(
        url=settings.DATABASE_URL,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        render_as_batch=True,
        include_object=include_object,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.
    """
    connectable = create_engine(
        settings.DATABASE_URL,
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        # render_as_batch enables copy-and-move for SQLite (which lacks ALTER TABLE
        # for constraints) and is a no-op on PostgreSQL
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            render_as_batch=True,
            include_object=include_object,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
