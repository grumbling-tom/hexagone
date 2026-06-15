import { redirect } from "next/navigation";
import type { ReactNode } from "react";
import { getCurrentUser } from "@/__generated__/backend-client/users";
import { logout } from "@/features/auth/server/logout";
import { ApiError, HttpStatus } from "@/lib/fetch-client";
import Nav from "../Nav";

// Layout for the auth-gated routes: validates the session server-side and hosts
// <Nav>. middleware.ts is the optimistic gate (presence-only cookie check); the
// cookie is opaque, so a present-but-invalid/expired cookie is only caught here,
// where getCurrentUser 401s and we redirect to /login — no client backstop, no
// loading flash.
export default async function AuthedLayout({
  children,
}: {
  children: ReactNode;
}) {
  try {
    await getCurrentUser();
  } catch (err) {
    if (err instanceof ApiError && err.httpStatus === HttpStatus.UNAUTHORIZED) {
      redirect("/login");
    }
    throw err;
  }

  return (
    <>
      <Nav logout={logout} />
      {children}
    </>
  );
}
