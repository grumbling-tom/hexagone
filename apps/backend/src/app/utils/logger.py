"""Structured logging configuration using structlog."""

import logging

import structlog

from src.app.settings import settings


def configure_logging() -> None:
    """Configure structlog for the application.

    Uses pretty-printed colored output for DEV environments,
    and JSON formatting for TEST, STAGING, and PROD environments.
    """
    shared_processors = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
    ]

    if settings.ENV == "DEV":
        processors = [*shared_processors, structlog.dev.ConsoleRenderer(colors=True)]
    else:
        processors = [
            *shared_processors,
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer(),
        ]

    structlog.configure(
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str | None = None) -> structlog.stdlib.BoundLogger:
    """Get a configured logger instance.

    Args:
        name: Optional name for the logger, typically __name__ from the calling module.

    Returns:
        A configured structlog logger instance.
    """
    return structlog.get_logger(name)
