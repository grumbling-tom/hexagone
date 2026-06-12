"use client";

import { useRouter } from "next/navigation";
import { type ReactNode, useEffect } from "react";
import { useGetCurrentUser } from "@/__generated__/backend-client/users";
import Nav from "../Nav";

// Layout for the auth-gated routes: hosts <Nav> and acts as the client-side
// backstop to the middleware gate. middleware.ts is the primary gate — it
// redirects unauthed (no-cookie) requests before this renders. The session
// cookie is opaque, so middleware can't catch a present-but-invalid/expired
// cookie; that case lands here, useGetCurrentUser returns no user, and we
// redirect to /login.
export default function AuthedLayout({ children }: { children: ReactNode }) {
  const router = useRouter();
  const { data: user, isLoading } = useGetCurrentUser({
    query: { retry: false },
  });

  useEffect(() => {
    if (!isLoading && !user) {
      router.replace("/login");
    }
  }, [isLoading, user, router]);

  if (isLoading || !user) {
    return <div className="auth-loading">Loading</div>;
  }

  return (
    <>
      <Nav />
      {children}
    </>
  );
}
