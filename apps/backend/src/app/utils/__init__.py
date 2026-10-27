"""Utility functions for the application."""

from src.app.utils.cursor import Cursor, SortOrder
from src.app.utils.logger import configure_logging, get_logger
from src.app.utils.pagination import PaginatedResult
from src.app.utils.redaction import (
    HIDDEN_FIELDS_KEY,
    REDACTED,
    Redacted,
    mask_email,
)
from src.app.utils.request import get_client_ip
from src.app.utils.schemas import BaseSchema, Redactable, RedactedMarker

__all__ = [
    "HIDDEN_FIELDS_KEY",
    "REDACTED",
    "BaseSchema",
    "BaseSchema",
    "Cursor",
    "PaginatedResult",
    "Redactable",
    "Redacted",
    "RedactedMarker",
    "SortOrder",
    "configure_logging",
    "get_client_ip",
    "get_logger",
    "mask_email",
]
