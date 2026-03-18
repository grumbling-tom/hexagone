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
from starlette.types import ASGIApp

from src.app.context import AuthClaims, auth_claims_context
from src.app.utils import get_logger

logger = get_logger(__name__)


class JWTAuthMiddleware(BaseHTTPMiddleware):
    """Verify JWT Bearer tokens and attach claims to request state."""

    def __init__(
        self,
        app: ASGIApp,
        jwks_url: str,
        jwt_issuer: str,
        jwt_authorized_parties: list[str],
    ) -> None:
        super().__init__(app)

        self.jwks_url = jwks_url
        self.issuer = jwt_issuer
        self.authorized_parties = jwt_authorized_parties
        self.jwk_client = PyJWKClient(jwks_url)

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        """Verify JWT and attach claims to the auth context if valid."""
        auth_header = request.headers.get("authorization", "")

        if not auth_header.startswith("Bearer ") or not self.jwks_url:
            return await call_next(request)

        token = auth_header[len("Bearer ") :]
        signing_key = self.jwk_client.get_signing_key_from_jwt(token)

        try:
            claims = decode(
                token,
                signing_key.key,
                algorithms=["RS256"],
                issuer=self.issuer,
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

        if (azp := claims.get("azp")) not in self.authorized_parties:
            logger.warning(
                "jwt_invalid_azp",
                azp=azp,
                expected=self.authorized_parties,
            )
            return await call_next(request)

        auth_claims_context.set(AuthClaims(sub=claims["sub"], email=claims["email"]))

        return await call_next(request)
