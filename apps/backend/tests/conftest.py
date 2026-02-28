"""Shared test fixtures."""

from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient

from src.app.main import app


@pytest.fixture
def client() -> Generator[TestClient]:
    """Yield a FastAPI test client."""
    with TestClient(app) as c:
        yield c
