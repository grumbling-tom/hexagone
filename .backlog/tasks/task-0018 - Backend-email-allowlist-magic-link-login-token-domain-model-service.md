---
id: TASK-0018
title: 'Backend: email allowlist + magic-link login-token domain (model & service)'
status: In Progress
assignee:
  - grumbling-tom
created_date: '2026-06-17 10:11'
updated_date: '2026-06-17 10:55'
labels:
  - auth
  - backend
milestone: m-0
dependencies: []
references:
  - .backlog/milestones/m-0 - passwordless-login.md
  - >-
    PR #16 — alternative Clerk/SSO approach; NOT the direction for this
    milestone
modified_files:
  - apps/backend/src/app/repository/models.py
  - apps/backend/src/app/repository/__init__.py
  - apps/backend/src/app/services/login_token.py
  - apps/backend/src/app/services/email.py
  - apps/backend/src/app/settings.py
  - apps/backend/.env.example
  - apps/backend/src/alembic/versions/0006_add_login_token_table.py
  - apps/backend/tests/app/services/test_login_token.py
priority: medium
ordinal: 1000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
## Why

First step toward replacing password auth with email-based passwordless login (magic links). This PR adds the backend *domain capability* to issue and verify single-use, time-limited magic-link tokens for allow-listed emails, plus the sign-in email template. It is **purely additive** — no endpoints, nothing removed; the existing password login keeps working. Endpoints come in the next task.

## Decision (already made)

Magic link, built in-house on stdlib — no third-party auth vendor. Token = `secrets.token_urlsafe(32)`; we store **only its sha256 hash**, never the plaintext. Default lifetime 10 minutes, single-use. This reuses the existing session layer rather than introducing a new one.

## Current system context (for an implementer new to the repo)

- Auth today is a hand-rolled session system. `User` (in `apps/backend/src/app/repository/models.py`) has `email` (unique, indexed), `password_hash` (bcrypt), `archived`. Sessions live in the `UserSession` table; `create_session(db, user_uid, user_agent, ip_address)` in `apps/backend/src/app/services/user_session.py` is what mints a session + the opaque httpOnly `sessionid` cookie. **Do not change the session layer in this task** — later tasks reuse `create_session` as-is.
- Email is already wired (Resend). `apps/backend/src/app/services/email.py` has an `EmailClient` ABC with `ResendEmailClient` (prod) and `ConsoleEmailClient` (dev/test), injected via the `email_client` dependency. `send_welcome_email(...)` is the existing template to mirror. `settings.APP_BASE_URL` is used for links. **Logging rule: mask the recipient (`mask_email`) and never log the raw address or the html body.**
- Settings is a pydantic `Settings` singleton; services read the global `settings`. Only `create_app` takes a `Settings`. Use an autouse monkeypatch fixture for per-test overrides (project convention — no `settings` arg threaded through service functions).

## Notes / non-goals

- Allowlist storage: start as a pydantic `Settings` list (e.g. `ALLOWED_EMAILS`). Do **not** build a DB table / admin UI for it now — promote to a table later only if runtime editing is actually needed.
- Rate-limiting and the HTTP endpoints are the **next** task; this task only needs the domain primitives (issuing should supersede any prior outstanding token for that email, which bounds accumulation).
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 A `login_token` model + Alembic migration store: target email, sha256 hash of the token (never the plaintext), created_at, expires_at, used_at (nullable). Migration follows the project's lazy-import convention.
- [x] #2 An issue-token service generates `secrets.token_urlsafe(32)`, persists only its sha256 hash with a configurable expiry (default 10 min), supersedes/invalidates any prior outstanding token for the same email, and returns the plaintext token to the caller for embedding in the email link.
- [x] #3 A verify-token service hashes the presented token, looks it up using a constant-time compare (`hmac.compare_digest`), and rejects when missing, expired, or already used; on success it marks `used_at` and returns the resolved email.
- [x] #4 An allowlist gate function answers 'is this email permitted to sign in/sign up?' sourced from a pydantic Settings list (e.g. `ALLOWED_EMAILS`); behaviour for empty/unset list is documented.
- [x] #5 A magic-link email template (alongside `send_welcome_email`) builds the sign-in email linking to `${APP_BASE_URL}/auth/verify?token=...`; recipient is masked in logs and the html body is never logged.
- [x] #6 Unit tests cover: issue→verify happy path, expired token rejected, reused token rejected, unknown token rejected, superseded prior-token rejected, allowlist allow + deny, and that comparison is constant-time / hashes (not plaintext) are stored.
- [x] #7 Module docstrings explain the magic-link decision, token lifetime, and the store-hash-only invariant; `.env.example` updated for any new settings introduced here (e.g. token expiry, `ALLOWED_EMAILS`).
- [x] #8 `verify_login_token` is the single-use CONSUME step (stamps `used_at`) and is documented POST-only; a non-consuming `peek_login_token` validates a token without spending it, so an idempotent GET landing page can show expired/invalid without burning the link.
- [x] #9 The plaintext token and nonce are never logged (only masked email / non-PII identifiers); tests assert no plaintext secret is persisted or returned in log context.
- [x] #10 Browser-binding (nonce) is ALWAYS ON (not configurable): issuing mints a high-entropy nonce and returns it alongside the token; `nonce_hash` is stored NOT NULL and verify always requires a matching nonce. Deliberate consequence (documented in the model): sign-in must complete in the same browser that requested the link — no request-on-desktop/open-on-phone.
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
## Approach (magic link, in-house, stdlib only)

**1. Model** — add `LoginToken` to `repository/models.py` (export in `repository/__init__.py`):
- `email` (String, indexed, stored lowercased)
- `token_hash` (String, unique, indexed) — sha256 hex of the plaintext token; plaintext never persisted
- `expires_at` (DateTime tz)
- `used_at` (DateTime tz, nullable)
- `uid` + `created_at` from `BaseModel`

**2. Migration** — `0006_add_login_token_table.py` via `uv run alembic revision --autogenerate` (down_revision = d7e3a2b9f4c1). No app imports → lazy-import rule moot.

**3. Service** `services/login_token.py` (noun-named):
- `_hash_token(token) -> str`: sha256 hexdigest
- `issue_login_token(db, email) -> str`: lowercase email, **delete any existing tokens for that email** (supersede → one outstanding per email), generate `secrets.token_urlsafe(32)`, persist only its hash with `expires_at = now + LOGIN_TOKEN_EXPIRY_MINUTES`, return the **plaintext** token for the caller to email
- `verify_login_token(db, token) -> str | None`: hash, look up by `token_hash`, `hmac.compare_digest` confirm, reject if missing / expired / `used_at` set; on success set `used_at` and return the email. Mirrors `user_session.py` tz-handling for SQLite.
- `is_email_allowed(email) -> bool`: case-insensitive membership in `settings.ALLOWED_EMAILS`. **Empty list = deny-all** (secure default for an invite-only whitelist); documented.

**4. Email template** — `send_login_link_email(email, *, to_email, token)` in `services/email.py`, mirroring `send_welcome_email`: link to `${APP_BASE_URL}/auth/verify?token=...`, recipient masked, body never logged.

**5. Settings** — `LOGIN_TOKEN_EXPIRY_MINUTES: int = 10`, `ALLOWED_EMAILS: list[str] = []` (JSON-from-env, matching existing `list[str]` settings). Add both to `.env.example` with a sample.

**6. Tests** `tests/app/services/test_login_token.py` — issue→verify happy path; expired rejected; reused rejected; unknown rejected; superseded-prior rejected; allowlist allow + deny (+ empty=deny); stored value is a hash, not the plaintext. Plus a small `send_login_link_email` test (link shape + masking). Settings overrides via autouse `monkeypatch` on the `settings` singleton (project convention).

**Additive only** — no endpoints, no removals; password login untouched. Endpoints are TASK-0019.

## Revision — security hardening (per review)

Added after review raised replay/interception/prefetcher risks. These shape the domain API:

- **Browser-binding nonce (PKCE-for-magic-links).** `issue_login_token` now also mints a nonce (`secrets.token_urlsafe(32)`) and returns `IssuedLoginToken(token, nonce)` (Pydantic). Model gains `nonce_hash` (nullable) — populated only when `settings.LOGIN_TOKEN_BIND_BROWSER` is True. `verify_login_token(db, token, *, nonce=None)` enforces the nonce iff the stored row has a `nonce_hash`. New setting `LOGIN_TOKEN_BIND_BROWSER: bool = False` (default OFF — binding breaks request-on-desktop/open-on-phone). The cookie is wired in TASK-0019.
- **Consume-only verify + non-consuming peek (prefetcher safety).** `verify_login_token` is the single-use CONSUME step and is documented POST-only. Added `peek_login_token(db, token, *, nonce=None) -> bool` that validates WITHOUT spending, so the idempotent GET landing page (TASK-0020) can show expired/invalid without burning the link. Shared `_find_spendable_token` helper does hash + `compare_digest` + expiry + used + nonce checks; verify stamps `used_at`, peek doesn't.
- **No token/nonce in logs.** Domain never logs the plaintext token or nonce (only masked email). Log/trace scrubbing at the HTTP edge is TASK-0019.

Net new vs original plan: `nonce_hash` column, `IssuedLoginToken` return type, `peek_login_token`, `LOGIN_TOKEN_BIND_BROWSER` setting, and nonce coverage in tests.

## Correction — nonce binding is ALWAYS ON

Supersedes the `LOGIN_TOKEN_BIND_BROWSER` idea in the revision note above. Per the user, browser binding is not configurable — it is always on. So: `nonce_hash` is NOT NULL, `issue_login_token` always mints a nonce and returns `IssuedLoginToken(token, nonce)` (a NamedTuple, not Pydantic — the service-return architecture test forbids returning BaseSchema), `verify_login_token(db, token, nonce)` and `peek_login_token(db, token, nonce)` both take a required `nonce`. No `LOGIN_TOKEN_BIND_BROWSER` setting was added. Accepted tradeoff: sign-in must complete in the same browser that requested the link (no cross-device).
<!-- SECTION:PLAN:END -->
