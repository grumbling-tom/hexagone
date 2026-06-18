"""Login-token (magic-link) endpoints."""

import secrets
from typing import Annotated

from fastapi import APIRouter, Depends, Response
from pydantic import EmailStr
from sqlalchemy.orm import Session

from src.app.dependencies import db_session, email_client
from src.app.services.email import EmailClient, send_login_link_email
from src.app.services.login_token import is_email_allowed, issue_login_token
from src.app.settings import settings
from src.app.utils import BaseSchema, get_logger

logger = get_logger(__name__)

router = APIRouter()


class CreateLoginTokenRequest(BaseSchema):
    """Request body for requesting a magic-link sign-in email."""

    email: EmailStr


@router.post("/login-tokens", status_code=202, operation_id="createLoginToken")
def create_login_token(
    body: CreateLoginTokenRequest,
    db: Annotated[Session, Depends(db_session)],
    mailer: Annotated[EmailClient, Depends(email_client)],
) -> Response:
    """Request a magic-link sign-in email (enumeration-safe).

    Always returns 202 with an empty body and always sets a browser-binding
    nonce cookie, so neither the status, the body, nor the headers reveal
    whether the address is on the invite allowlist. A link is only issued and
    emailed for allow-listed addresses; the nonce is a harmless throwaway
    otherwise. How (or whether) to message the user is left to the frontend.
    """
    nonce = secrets.token_urlsafe(settings.LOGIN_TOKEN_SECRET_BYTES)

    if is_email_allowed(body.email):
        issued = issue_login_token(db, body.email)
        nonce = issued.nonce
        # Best-effort: a provider failure must not change the response (that
        # would leak allow-status), so swallow and log.
        try:
            send_login_link_email(mailer, to_email=body.email, token=issued.token)
        except Exception:
            logger.exception("login_link_email_failed")

    response = Response(status_code=202)
    response.set_cookie(
        key=settings.LOGIN_NONCE_COOKIE_NAME,
        value=nonce,
        max_age=settings.LOGIN_TOKEN_EXPIRY_MINUTES * 60,
        httponly=True,
        secure=True,
        samesite="lax",
    )
    return response
