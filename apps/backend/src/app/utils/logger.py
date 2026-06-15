"""Structured logging configuration using structlog."""

import logging

import structlog
from opentelemetry import trace
from structlog.typing import EventDict, WrappedLogger

from src.app.settings import settings


def add_otel_trace_context(
    _logger: WrappedLogger, _method_name: str, event_dict: EventDict
) -> EventDict:
    """Stamp the active span's trace/span ids onto each log line.

    The ``trace_id`` is rendered exactly as the W3C ``traceparent`` trace-id
    field (32 lowercase hex), so the same id can be grepped across the frontend
    span output, the backend span output, and these logs — proving a single
    request is one correlated trace. When no span is active (or tracing is off)
    the span context is invalid and the fields are simply omitted.
    """
    span_context = trace.get_current_span().get_span_context()
    if span_context.is_valid:
        event_dict["trace_id"] = format(span_context.trace_id, "032x")
        event_dict["span_id"] = format(span_context.span_id, "016x")
    return event_dict


def configure_logging() -> None:
    """Configure structlog for the application.

    Uses pretty-printed colored output for DEV environments,
    and JSON formatting for TEST, STAGING, and PROD environments.
    """
    shared_processors = [
        structlog.contextvars.merge_contextvars,
        add_otel_trace_context,
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
