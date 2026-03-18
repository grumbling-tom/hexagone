from jwt import (
    ExpiredSignatureError,
    InvalidIssuerError,
    InvalidTokenError,
    PyJWKClient,
    decode,
)
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from src.app.context import AuthClaims, auth_claims_context
from src.app.settings import settings
from src.app.utils import get_logger

logger = get_logger(__name__)

JWK_CLIENT = PyJWKClient(settings.CLERK_JWKS_URL)


class JWTAuthMiddleware(BaseHTTPMiddleware):
    """Verify JWT Bearer tokens and attach claims to request state."""

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        """Verify JWT and attach claims to request state if valid."""
        auth_header = request.headers.get("authorization", "")

        if not auth_header.startswith("Bearer ") or not settings.CLERK_JWKS_URL:
            return await call_next(request)

        token = auth_header[len("Bearer ") :]
        signing_key = JWK_CLIENT.get_signing_key_from_jwt(token)

        try:
            claims = decode(
                token,
                signing_key.key,
                algorithms=["RS256"],
                issuer=settings.CLERK_ISSUER,
                options={
                    "verify_aud": False,  # Not populated - 'azp' is used instead.
                    "require": ["azp", "email"],
                },
            )
        except (
            ExpiredSignatureError,
            InvalidIssuerError,
            InvalidTokenError,
        ) as e:
            logger.warning("jwt_validation_failed", error=str(e))
            return await call_next(request)

        if (azp := claims.get("azp")) not in settings.CLERK_AUTHORIZED_PARTIES:
            logger.warning(
                "jwt_invalid_azp",
                azp=azp,
                expected=settings.CLERK_AUTHORIZED_PARTIES,
            )
            return await call_next(request)

        auth_claims_context.set(AuthClaims(sub=claims["sub"], email=claims["email"]))

        return await call_next(request)
