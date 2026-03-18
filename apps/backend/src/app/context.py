from contextvars import ContextVar

from src.app.utils.schemas import BaseSchema


class AuthClaims(BaseSchema):
    """Typed container for JWT claims extracted by middleware."""

    sub: str
    email: str


auth_claims_context: ContextVar[AuthClaims | None] = ContextVar(
    "auth_claims_context", default=None
)
