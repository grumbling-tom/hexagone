"""Generate the email theme-token module from the web app's ``theme.css``.

The brand's design tokens (colours, fonts, spacing) are authored *once*, in
``apps/web/src/styles/theme.css`` as CSS custom properties on ``:root``. The web
app consumes them via ``var(--token)``; email cannot (mail clients strip CSS
custom properties and external stylesheets), so we mirror the *resolved literal
values* into a committed Python module that the email templates read.

This keeps ``theme.css`` the single source of truth — no hex codes are
duplicated. Run this whenever ``theme.css`` changes; the pre-commit
``gen-email-theme`` hook does so automatically and re-stages the output (see
``lefthook.yml``). The generated file is committed, so the backend image — which
never contains the web source — has the tokens at runtime.

Usage:
    uv run python src/scripts/gen_email_theme.py
"""

import re
from pathlib import Path

# This script lives at apps/backend/src/scripts/gen_email_theme.py.
#   parents[0] = scripts, [1] = src, [2] = backend, [3] = apps
_APPS_DIR = Path(__file__).resolve().parents[3]
THEME_CSS = _APPS_DIR / "web" / "src" / "styles" / "theme.css"
OUTPUT = _APPS_DIR / "backend" / "src" / "app" / "services" / "email_theme.py"

# `--name: value;` declarations. The value is everything up to the first `;`.
_DECL = re.compile(r"--([\w-]+)\s*:\s*([^;]+);")
# `var(--name)` references (no fallbacks are used in theme.css today).
_VAR = re.compile(r"var\(\s*--([\w-]+)\s*\)")

_MAX_RESOLVE_DEPTH = 20


def parse_declarations(css: str) -> dict[str, str]:
    """Return every ``--name: value`` declaration, last write winning."""
    return {name: value.strip() for name, value in _DECL.findall(css)}


def resolve(raw: dict[str, str]) -> dict[str, str]:
    """Resolve ``var(--x)`` references down to literal values.

    Tokens reference other tokens (e.g. ``--color-link: var(--color-primary-600)``
    and ``--sketch-border: 2px solid var(--color-border)``). We substitute
    repeatedly until no ``var()`` remains; an unknown reference is left verbatim
    so it shows up rather than silently vanishing.
    """
    resolved: dict[str, str] = {}
    for name, raw_value in raw.items():
        value = raw_value
        for _ in range(_MAX_RESOLVE_DEPTH):
            if "var(" not in value:
                break
            value = _VAR.sub(lambda m: raw.get(m.group(1), m.group(0)), value)
        else:
            msg = f"Unresolved var() in token --{name}: {value!r}"
            raise ValueError(msg)
        resolved[name] = value
    return resolved


def pyquote(s: str) -> str:
    """Quote a string the way ``ruff format`` would: double quotes by default,
    single quotes when that avoids escaping a contained double quote (e.g. the
    ``font-heading`` value, which embeds ``"Architects Daughter"``). Keeps the
    generated file stable under the pre-commit formatter.
    """
    if '"' in s and "'" not in s:
        return f"'{s}'"
    return '"' + s.replace('"', '\\"') + '"'


def render_module(tokens: dict[str, str]) -> str:
    """Render the generated Python module source."""
    lines = [
        '"""Brand design tokens for email, mirrored from the web app.',
        "",
        "GENERATED FILE — do not edit by hand. Regenerate with:",
        "    uv run python src/scripts/gen_email_theme.py",
        "",
        "Source of truth: apps/web/src/styles/theme.css. Values are resolved to",
        "literals (no CSS var()) so they can be inlined into email HTML, which",
        "cannot use CSS custom properties.",
        '"""',
        "",
        "EMAIL_THEME: dict[str, str] = {",
    ]
    for name, value in tokens.items():
        lines.append(f"    {pyquote(name)}: {pyquote(value)},")
    lines.append("}")
    lines.append("")
    return "\n".join(lines)


def main() -> None:
    """Parse theme.css and (re)write the generated token module."""
    css = THEME_CSS.read_text(encoding="utf-8")
    tokens = resolve(parse_declarations(css))
    OUTPUT.write_text(render_module(tokens), encoding="utf-8")
    print(f"Wrote {len(tokens)} tokens to {OUTPUT.relative_to(_APPS_DIR.parent)}")


if __name__ == "__main__":
    main()
