import { type NextRequest, NextResponse } from "next/server";

// Optimistic auth gate for the protected routes. The session cookie is httpOnly
// and opaque (a UUID the backend looks up in the DB — see
// apps/backend/src/app/settings.py SESSION_COOKIE_NAME), so middleware can't
// validate it; it only checks *presence* and redirects when it's missing — the
// common not-logged-in case, server-side and flash-free. A present-but-invalid
// cookie passes here and is caught by the client backstop in
// app/(authed)/layout.tsx; the backend stays the real authority (it 401s every
// /api call). See Next's docs: optimistic checks in middleware, real validation
// in the data layer.
//
// TODO: When we move to a separate auth provider with JWT-based access tokens,
// add a real Next.js-level auth check here. Unlike the opaque sessionid, a JWT
// is self-validating (verify signature + expiry + claims with no DB lookup), so
// middleware can do genuine validation rather than a presence-only gate — and we
// should also enforce it inside the protected server actions
// (app/(authed)/.../actions.ts) for defence-in-depth, since the backend 401 is
// currently the only thing protecting them.
const SESSION_COOKIE_NAME = "sessionid";

export function middleware(request: NextRequest) {
  if (request.cookies.get(SESSION_COOKIE_NAME)) {
    return NextResponse.next();
  }
  return NextResponse.redirect(new URL("/login", request.url));
}

export const config = {
  // Only the auth-gated routes. Intentionally not /login or /signup: with a
  // presence-only check, redirecting an authed user away from /login could loop
  // against the layout's backstop when the cookie is present but expired.
  matcher: ["/map/:path*", "/uploads/:path*"],
};
