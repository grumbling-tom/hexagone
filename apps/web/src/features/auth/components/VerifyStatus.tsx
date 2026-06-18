"use client";

import type { ReactNode } from "react";
import {
  startTransition,
  useActionState,
  useEffect,
  useRef,
  useState,
} from "react";
import type { AuthFormState } from "@/features/auth/types";

// How long the "redirecting…" countdown runs before auto-submitting.
const REDIRECT_SECONDS = 3;

// `verify` (consumes the token + redirects) and `requestNewLink` (a navigation
// link) are supplied by the route, keeping routing out of the feature.
export default function VerifyStatus({
  token,
  verify,
  requestNewLink,
}: {
  token: string | null;
  verify: (state: AuthFormState, formData: FormData) => Promise<AuthFormState>;
  requestNewLink: ReactNode;
}) {
  const [state, submit, pending] = useActionState(verify, {});
  const [secondsLeft, setSecondsLeft] = useState(REDIRECT_SECONDS);
  const remaining = useRef(REDIRECT_SECONDS);
  const autoSubmitted = useRef(false);

  // Tick a countdown, then auto-submit — consuming the token client-side AFTER
  // the GET render, so an email prefetcher that only fetches HTML never burns
  // the link. `remaining` holds the live count in a ref (so the interval reads
  // the latest value without a stale closure); the interval itself needs a
  // useEffect to set it up and tear it down on unmount — the canonical,
  // justified effect. The visible button is the manual fallback and stops the
  // countdown (clicking it flips `pending`, which clears the interval here).
  useEffect(() => {
    if (!token || state.error || pending) return;
    const id = setInterval(() => {
      remaining.current -= 1;
      setSecondsLeft(remaining.current);
      if (remaining.current <= 0 && !autoSubmitted.current) {
        autoSubmitted.current = true;
        clearInterval(id);
        const formData = new FormData();
        formData.set("token", token);
        // Dispatching the action programmatically must be wrapped in a
        // transition so `pending` updates correctly (the form-submit path does
        // this for us).
        startTransition(() => submit(formData));
      }
    }, 1000);
    return () => clearInterval(id);
  }, [token, state.error, pending, submit]);

  if (!token || state.error) {
    return (
      <div className="auth-form">
        <h1 className="auth-form__title">Sign-in link problem</h1>
        <p className="auth-form__error">
          {state.error ?? "This sign-in link is invalid or has expired."}
        </p>
        <p className="auth-form__footer">{requestNewLink}</p>
      </div>
    );
  }

  const counting = !pending && secondsLeft > 0;

  return (
    <form className="auth-form" action={submit}>
      <input type="hidden" name="token" value={token} />
      <h1 className="auth-form__title">Signing you in</h1>
      <p className="auth-form__notice">
        {counting
          ? `Redirecting you in ${secondsLeft}s. If nothing happens, use the button below.`
          : "Signing you in…"}
      </p>
      <button
        className={`button button--primary auth-form__submit${pending ? " button--pending" : ""}`}
        type="submit"
        disabled={pending}
      >
        {pending ? "Signing in" : "Sign in now"}
      </button>
    </form>
  );
}
