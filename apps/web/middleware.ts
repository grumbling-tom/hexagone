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
