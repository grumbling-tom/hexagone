"""Render branded transactional emails from Jinja templates.

Templates live in ``email_templates/`` and inline the brand design tokens from
``email_theme.EMAIL_THEME`` (mirrored from the web app's ``theme.css`` — see
``scripts/gen_email_theme.py``). Autoescaping is on, so interpolated values like
the recipient address can't inject markup.
"""

from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

from src.app.services.email_theme import EMAIL_THEME
from src.app.settings import settings

_TEMPLATES_DIR = Path(__file__).parent / "email_templates"

# Module-level environment: templates are loaded from disk once and cached.
_env = Environment(
    loader=FileSystemLoader(_TEMPLATES_DIR),
    autoescape=select_autoescape(["html"]),
    trim_blocks=True,
    lstrip_blocks=True,
)


def _render(template: str, *, title: str, preheader: str, **context: str) -> str:
    """Render ``template`` within the branded shell.

    Every template receives ``theme`` (the brand tokens) and ``app_base_url``.
    """
    return _env.get_template(template).render(
        theme=EMAIL_THEME,
        title=title,
        preheader=preheader,
        app_base_url=settings.APP_BASE_URL,
        **context,
    )


def render_welcome(*, user_email: str) -> str:
    """Render the post-signup welcome email body."""
    return _render(
        "welcome.html",
        title="Welcome to Hexagone",
        preheader="Your account is ready — open the map and start claiming hexes.",
        user_email=user_email,
        map_url=f"{settings.APP_BASE_URL}/map",
    )


def render_login_link(*, verify_url: str, minutes: int) -> str:
    """Render the magic-link sign-in email body."""
    return _render(
        "login_link.html",
        title="Your Hexagone sign-in link",
        preheader="Your single-use sign-in link for Hexagone.",
        verify_url=verify_url,
        minutes=str(minutes),
    )
