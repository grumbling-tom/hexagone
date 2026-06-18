"use client";

import type { ReactNode } from "react";
import { useEffect, useRef, useState } from "react";
import type { AuthFormState } from "@/features/auth/types";

// `verify` (consumes the token + redirects) and `requestNewLink` (a navigation
// link) are supplied by the route, keeping routing out of the feature.
export default function VerifyStatus({
  token,
  verify,
  requestNewLink,
}: {
  token: string | null;
  verify: (token: string) => Promise<AuthFormState>;
  requestNewLink: ReactNode;
}) {
  const [error, setError] = useState<string | undefined>(
    token ? undefined : "This sign-in link is invalid or has expired.",
  );
  const fired = useRef(false);

  // Consume the token on mount — client-side, AFTER render, never during the
  // GET/RSC render — so email prefetchers that only fetch HTML can't burn the
  // link (and a JS-running scanner lacks the browser-binding nonce anyway). The
  // ref fires it exactly once (React StrictMode double-invokes effects in dev).
  // Justified useEffect: a one-shot side effect that must run on mount in the
  // browser; on success `verify` redirects server-side and navigates away.
  useEffect(() => {
    if (!token || fired.current) return;
    fired.current = true;
    verify(token).then((result) => {
      if (result?.error) setError(result.error);
    });
  }, [token, verify]);

  if (error) {
    return (
      <div className="auth-form">
        <h1 className="auth-form__title">Sign-in link problem</h1>
        <p className="auth-form__error">{error}</p>
        <p className="auth-form__footer">{requestNewLink}</p>
      </div>
    );
  }

  return <p className="auth-loading">Signing you in</p>;
}
