"""Tests for the JWT authentication middleware."""

from collections.abc import Callable, Generator
from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock, patch

import jwt as pyjwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives.serialization import (
    Encoding,
    NoEncryption,
    PrivateFormat,
)
from fastapi.testclient import TestClient
from sqlalchemy import StaticPool, create_engine
from sqlalchemy.orm import Session, sessionmaker

from src.app.dependencies import db_session, file_storage
from src.app.main import create_app
from src.app.repository import BaseModel
from src.app.services.storage import S3StorageBackend
from src.app.settings import Settings

# Generate a test RSA key pair
_private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
_public_key = _private_key.public_key()
_private_key_pem = _private_key.private_bytes(
    Encoding.PEM, PrivateFormat.PKCS8, NoEncryption()
)

TEST_ISSUER = "https://test.clerk.accounts.dev"
TEST_AZP = "http://localhost:4321"

_test_settings = Settings(
    ENV="TEST",
    CLERK_JWKS_URL="https://test.clerk.accounts.dev/.well-known/jwks.json",
    CLERK_ISSUER=TEST_ISSUER,
    CLERK_AUTHORIZED_PARTIES=[TEST_AZP],
)


@pytest.fixture
def make_token() -> Callable[..., str]:
    """Return a factory that creates signed JWT tokens for testing."""

    def _factory(
        *,
        sub: str = "user_test123",
        email: str = "test@example.com",
        issuer: str = TEST_ISSUER,
        azp: str = TEST_AZP,
        expired: bool = False,
    ) -> str:
        now = datetime.now(UTC)
        exp = now - timedelta(hours=1) if expired else now + timedelta(hours=1)
        payload: dict[str, str | datetime] = {
            "sub": sub,
            "email": email,
            "iss": issuer,
            "azp": azp,
            "exp": exp,
            "iat": now,
        }
        return pyjwt.encode(payload, _private_key_pem, algorithm="RS256")

    return _factory


@pytest.fixture
def client() -> Generator[TestClient]:
    """Create a test client with a mocked JWK client."""
    mock_signing_key = MagicMock()
    mock_signing_key.key = _public_key
    mock_jwk_client = MagicMock()
    mock_jwk_client.return_value.get_signing_key_from_jwt.return_value = (
        mock_signing_key
    )

    test_engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    BaseModel.metadata.create_all(test_engine)
    test_session_local = sessionmaker(
        autocommit=False, autoflush=False, bind=test_engine
    )

    def override_get_db() -> Generator[Session]:
        db = test_session_local()
        try:
            yield db
        finally:
            db.close()

    # Patch PyJWKClient for the lifetime of each test so the middleware
    # never makes real HTTP calls to the JWKS endpoint.
    with patch("src.app.middleware.PyJWKClient", mock_jwk_client):
        app = create_app(settings=_test_settings)
        app.dependency_overrides[db_session] = override_get_db
        app.dependency_overrides[file_storage] = S3StorageBackend
        yield TestClient(app)


def test_valid_token_attaches_claims(
    client: TestClient, make_token: Callable[..., str]
):
    token = make_token()
    response = client.get(
        "/api/v1/users/current",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "test@example.com"


def test_expired_token_does_not_attach_claims(
    client: TestClient, make_token: Callable[..., str]
):
    token = make_token(expired=True)
    response = client.get(
        "/api/v1/users/current",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 401


def test_wrong_issuer_does_not_attach_claims(
    client: TestClient, make_token: Callable[..., str]
):
    token = make_token(issuer="https://evil.example.com")
    response = client.get(
        "/api/v1/users/current",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 401


def test_wrong_azp_does_not_attach_claims(
    client: TestClient, make_token: Callable[..., str]
):
    token = make_token(azp="https://evil.example.com")
    response = client.get(
        "/api/v1/users/current",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 401


def test_missing_token_returns_401(client: TestClient):
    response = client.get("/api/v1/users/current")
    assert response.status_code == 401


def test_public_path_skips_auth(client: TestClient):
    response = client.get("/api/health")
    assert response.status_code == 200
