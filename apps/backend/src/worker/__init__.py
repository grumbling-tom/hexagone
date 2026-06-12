"""Background processing for Hexagone.

This package is the **background processor** half of the backend, kept separate
from ``src/app`` (the request-serving FastAPI app) so it's clear what serves HTTP
and what drains the queue. Shared domain logic (e.g. ``process_upload``) lives in
``src/app/services`` and is imported here; nothing under ``src/app`` imports the
async worker connector.
"""
