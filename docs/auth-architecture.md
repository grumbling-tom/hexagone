# Authentication Architecture

How sign-in works in Hexagone: **passwordless, email magic-link, invite-only**.
Built in-house on the standard library, reusing the existing opaque-cookie
session layer — no third-party auth vendor.

> **Status.** This describes the target flow for milestone **m-0**. Not all of
> it is implemented yet:
>
> | Part | Status | Where |
> |------|--------|-------|
> | Token domain (model, issue/verify/peek, allowlist, email) | ✅ implemented | `TASK-0018` / PR #56 |
> | HTTP endpoints (`POST /login-tokens`, `POST /user-sessions {token}`) + nonce cookie | ✅ implemented | `TASK-0019` |
> | Frontend (email-only forms, verify route, auto-redirect) | ⏳ planned | `TASK-0020` |
> | Remove password auth | ⏳ planned | `TASK-0021` |
> | Centralised email masking in logs | ⏳ planned | `TASK-0022` |

## Overview

There are no passwords. To sign in you enter your email; if it's on the invite
allowlist we email a single-use **magic link**. Opening the link and letting the
page verify it creates a session — the same opaque, httpOnly `sessionid` cookie
the app already used. Sign-up and sign-in are the **same flow**: the allowlist is
the gate, so a first-time allow-listed email is created on first verify.

Two secrets travel over two channels (the PKCE-for-magic-links pattern):

- the **token**, in the emailed link (`?token=…`), and
- the **nonce**, in an httpOnly cookie set in the browser that requested the link.

Redemption requires **both**, so a token scraped from an intercepted email is
useless without the browser that asked for it.

## Components

| Concern | Location |
|---------|----------|
| `LoginToken` model | `apps/backend/src/app/repository/models.py` |
| Issue / verify / peek / allowlist | `apps/backend/src/app/services/login_token.py` |
| Magic-link email template | `apps/backend/src/app/services/email.py` (`send_login_link_email`) |
| Session minting (reused) | `apps/backend/src/app/services/user_session.py` (`create_session`) |
| Settings | `apps/backend/src/app/settings.py` (`ALLOWED_EMAILS`, `LOGIN_TOKEN_*`) |
| Endpoints | `routers/login_tokens.py` (`POST /login-tokens`); `routers/user_sessions.py` (`POST /user-sessions` token mode) |
| Frontend forms + verify route (planned) | `apps/web/src/features/auth/`, `apps/web/app/auth/verify/` |

## Flow 1 — request a link (issue)

1. User submits their email on `/login` (a Server Action → `POST /login-tokens`).
2. Backend checks `is_email_allowed`. The response is **identical** whether or not
   the email is allow-listed/known — *"if your email is allowed, we've sent a
   link"* — so the endpoint never reveals who has an account (no enumeration).
3. If allowed, `issue_login_token`:
   - mints `token` and `nonce` (`secrets.token_urlsafe`, entropy from
     `LOGIN_TOKEN_SECRET_BYTES`),
   - stores **only the SHA-256 hashes** (`token_hash`, `nonce_hash`) plus
     `expires_at` (`LOGIN_TOKEN_EXPIRY_MINUTES`, default 10),
   - **revokes** any currently-live token for that email (`revoked_at` — a soft
     delete that keeps the row for audit), so at most one token is live per email.
4. The endpoint emails the link (`${APP_BASE_URL}/auth/verify?token=…`) and sets
   the `nonce` as an httpOnly, Secure cookie in the requester's browser.

## Flow 2 — verify a link (consume)

The link is a normal URL, so **both** an email security scanner (Outlook
SafeLinks, gateways, AV) and the human click it the same way — a `GET`. The
design makes that `GET` harmless and only ever consumes the token on a
deliberate, browser-bound action.

```
nonce cookie lives ONLY in the human's browser (httpOnly, app origin).
The browser never calls the backend directly — only Next.js does
(RSC reads / Server Action writes).

  ┌───────────┐      ┌───────────┐      ┌──────────────┐      ┌──────────────┐
  │  Email    │      │  Browser  │      │   Next.js    │      │   Backend    │
  │  scanner  │      │  (human)  │      │ (RSC + SA)   │      │  (FastAPI)   │
  └─────┬─────┘      └─────┬─────┘      └──────┬───────┘      └──────┬───────┘
        │                  │                   │                     │
 ══ Automated scanner, BEFORE the human ════════════════════════════════════
        │  GET /auth/verify?token=T            │                     │
        │─────────────────────────────────────▶│  peek(T) (optional) │
        │                                      │────────────────────▶│ peek_login_token
        │   200 HTML "Link valid! Redirecting…"│   valid? NO consume  │
        │◀─────────────────────────────────────│◀────────────────────│
        │   scanner runs no JS / has no nonce  │                      │
        │   → token STILL LIVE ✅               │                      │
        │                                      │                      │
 ══ The human, same link ═══════════════════════════════════════════════════
        │                  │  GET /auth/verify?token=T                │
        │                  │──────────────────▶│  peek(T) → "valid"   │
        │                  │◀──────────────────│                      │
        │                  │  (client mounts → auto-fires, no button) │
        │                  │  POST verify (Server Action)             │
        │                  │   + nonce cookie (auto-sent)             │
        │                  │──────────────────▶│ POST /user-sessions  │
        │                  │                   │  {token:T} + nonce   │
        │                  │                   │─────────────────────▶│ verify_login_token
        │                  │                   │                      │  secrets? revoked?
        │                  │                   │                      │  used? expired?
        │                  │                   │                      │  stamp used_at ◀ CONSUME
        │                  │                   │                      │  create_session()
        │                  │                   │◀─────────────────────│ Set-Cookie sessionid
        │                  │  Set-Cookie sessionid; 303 → /map (clean URL)
        │                  │◀──────────────────│                      │
        │                  │  authenticated ✓ — token spent, no replay │
```

Key points:

- **The `GET` never consumes.** The RSC render is side-effect-free; it may call
  the read-only `peek_login_token` to show *"Link valid! Redirecting…"* or
  *"expired — request a new link"*.
- **Consume is automatic, not a button.** A client component fires the verify
  Server Action **on mount**; on success the backend stamps `used_at`, calls
  `create_session`, and the user is redirected to a clean URL (token stripped).
- **Why auto-redirect is safe** (see the threat table below): the always-on
  nonce is the real gate, not the click.

## Security properties

- **Hash-only storage.** Only SHA-256 of the token and nonce are persisted; a DB
  leak can't be replayed.
- **Single-use + expiry + revoke.** `used_at` (spent), `expires_at` (short TTL),
  and `revoked_at` (superseded by a newer token) are each checked at verify, with
  `hmac.compare_digest` for the secret comparisons.
- **Always-on browser binding (nonce).** Verify requires the nonce cookie, which
  exists only in the original browser. This is what stops *any* other client —
  scanners, link unfurlers, an email interceptor — from consuming the token. The
  deliberate trade-off: sign-in must finish in the same browser that started it
  (no request-on-desktop / open-on-phone).
- **Prefetcher safety.** The token is consumed only by a client-side action after
  render, never by the `GET`:

  | Who opens the link | Runs JS? | Has the nonce? | Can consume? |
  |--------------------|----------|----------------|--------------|
  | Classic scanner (SafeLinks, gateway) | ✗ | ✗ | No |
  | Headless / JS-rendering scanner | ✓ | ✗ | No — nonce rejects |
  | Slack / iMessage unfurl | ✗ | ✗ | No |
  | The genuine user's browser | ✓ | ✓ | **Yes** |

  The only residual is the user's *own* browser aggressively prefetching the URL
  (same browser → has the nonce); in practice preload fetches HTML without
  mounting components and firing the action, so it doesn't consume. A manual
  button would close even this, at the cost of the click — we accept the residual.
- **Enumeration-safe.** `POST /login-tokens` responds identically (same 202 with
  an empty body, and a nonce cookie is always set) regardless of whether the
  email exists or is allow-listed. The backend returns no message; how to inform
  the user is the frontend's call. The one exception: if the email provider fails
  for an allow-listed address the request returns 502 (so the frontend can
  surface it) — a theoretical allow-status signal, accepted because provider
  failures aren't attacker-controllable per address.
- **No secrets in logs.** The plaintext token and nonce are never logged; emails
  are masked (`mask_email`, and centrally via `TASK-0022`). Tokens must also be
  kept out of access logs / OpenTelemetry spans (`TASK-0019`).

## Data model — `login_token`

| Column | Notes |
|--------|-------|
| `email` | EmailStr-normalised at the request boundary (local-part case preserved per RFC 5321 §2.4) |
| `token_hash` | SHA-256 of the link token (unique) |
| `nonce_hash` | SHA-256 of the browser-binding nonce (NOT NULL — binding is always on) |
| `expires_at` | Short TTL (`LOGIN_TOKEN_EXPIRY_MINUTES`) |
| `used_at` | Set on consume; single-use |
| `revoked_at` | Set when superseded by a newer token for the same email (soft delete, kept for audit) |

Because tokens are soft-deleted, the table grows over time; a periodic retention
job is expected eventually (not yet built).

## Settings

| Setting | Default | Purpose |
|---------|---------|---------|
| `ALLOWED_EMAILS` | `[]` (deny all) | Invite gate, `list[EmailStr]`; bad address fails boot |
| `LOGIN_TOKEN_EXPIRY_MINUTES` | `10` | Link lifetime |
| `LOGIN_TOKEN_SECRET_BYTES` | `32` | Token/nonce entropy |
| `LOGIN_NONCE_COOKIE_NAME` | `login_nonce` | Cookie holding the browser-binding nonce |
