"""Web-process Procrastinate app (defer-only).

The FastAPI process only *enqueues* jobs, so it uses the
:class:`~procrastinate.contrib.sqlalchemy.SQLAlchemyPsycopg2Connector`, which
reuses the app's existing SQLAlchemy engine/pool (no separate connection pool,
no async psycopg3). It defers the job *by name*: the task body lives in the
worker process, so this app doesn't register it — ``configure_task`` is
Procrastinate's cross-process defer path (``allow_unknown`` defaults to True).

Opened once at FastAPI startup (see ``main.create_app``'s lifespan) and closed
on shutdown.
"""

from procrastinate import App
from procrastinate.contrib.sqlalchemy import SQLAlchemyPsycopg2Connector

from src.app.repository.database import engine
from src.worker.tasks import PROCESS_UPLOAD

defer_app = App(connector=SQLAlchemyPsycopg2Connector())


def open_defer_app() -> None:
    """Bind the defer app to the app's SQLAlchemy engine."""
    defer_app.open(engine)


def close_defer_app() -> None:
    """Release the defer app's connector resources."""
    defer_app.close()


def defer_process_upload(key: str) -> None:
    """Enqueue a ``process_upload`` job for the object at ``key``."""
    defer_app.configure_task(name=PROCESS_UPLOAD).defer(key=key)
