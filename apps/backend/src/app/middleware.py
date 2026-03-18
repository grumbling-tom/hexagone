"""JWT verification middleware for authenticating requests.

Verifies Bearer tokens against a JWKS endpoint. This is standard OIDC JWT
verification — not specific to any auth provider. Swapping providers means
changing the JWKS URL, issuer, and authorized parties in settings.

The middleware only attaches verified claims to request state — it does NOT
reject requests. The `authenticated_user` dependency handles 401 responses
when claims are missing. This separation keeps middleware non-blocking for
CORS preflight requests and allows dependency overrides in tests.
"""

import jwt as pyjwt
from jwt import PyJWKClient
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from src.app.settings import settings
from src.app.utils import get_logger

logger = get_logger(__name__)

_jwks_client: PyJWKClient | None = None


def _get_jwks_client() -> PyJWKClient:
    """Return a cached JWKS client, creating it on first call."""
    global _jwks_client  # noqa: PLW0603
    if _jwks_client is None:
        _jwks_client = PyJWKClient(settings.CLERK_JWKS_URL)
    return _jwks_client


class JWTAuthMiddleware(BaseHTTPMiddleware):
    """Verify JWT Bearer tokens and attach claims to request state."""

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        """Verify JWT and attach claims to request state if valid."""
        auth_header = request.headers.get("authorization", "")

        if auth_header.startswith("Bearer ") and settings.CLERK_JWKS_URL:
            token = auth_header[len("Bearer ") :]
            try:
                jwks_client = _get_jwks_client()
                signing_key = jwks_client.get_signing_key_from_jwt(token)

                claims = pyjwt.decode(
                    token,
                    signing_key.key,
                    algorithms=["RS256"],
                    issuer=settings.CLERK_ISSUER,
                    options={"verify_aud": False},
                )

                if settings.CLERK_AUTHORIZED_PARTIES:
                    azp = claims.get("azp")
                    if azp not in settings.CLERK_AUTHORIZED_PARTIES:
                        logger.warning(
                            "jwt_invalid_azp",
                            azp=azp,
                            expected=settings.CLERK_AUTHORIZED_PARTIES,
                        )
                        return await call_next(request)

                request.state.auth_claims = claims

            except pyjwt.ExpiredSignatureError:
                logger.warning("jwt_expired")
            except pyjwt.InvalidIssuerError:
                logger.warning("jwt_invalid_issuer")
            except pyjwt.InvalidTokenError, Exception:
                logger.warning("jwt_invalid")

        return await call_next(request)
