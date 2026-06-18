"use client";

import type { ReactNode } from "react";
import { useActionState } from "react";
import type { AuthFormState } from "@/features/auth/types";

// The `action` (which requests the magic-link email) and the optional `footer`
// are supplied by the route (app/), keeping routing and data access out of the
// feature — see CLAUDE.md → Frontend Import Rules.
export default function RequestLinkForm({
  action,
  footer,
}: {
  action: (state: AuthFormState, formData: FormData) => Promise<AuthFormState>;
  footer?: ReactNode;
}) {
  const [state, formAction, pending] = useActionState(action, {});

  if (state.sent) {
    return (
      <div className="auth-form">
        <h1 className="auth-form__title">Check your email</h1>
        <p className="auth-form__notice">
          If your email is on the invite list, a sign-in link is on its way.
          Open it in this browser to finish signing in.
        </p>
        {footer && <p className="auth-form__footer">{footer}</p>}
      </div>
    );
  }

  return (
    <form className="auth-form" action={formAction}>
      <h1 className="auth-form__title">Sign in</h1>

      {state.error && <p className="auth-form__error">{state.error}</p>}

      <label className="auth-form__label" htmlFor="email">
        Email
      </label>
      <input
        className="auth-form__input"
        id="email"
        name="email"
        type="email"
        autoComplete="email"
        required
      />

      <button
        className={`button button--primary auth-form__submit${pending ? " button--pending" : ""}`}
        type="submit"
        disabled={pending}
      >
        {pending ? "Sending link" : "Send sign-in link"}
      </button>

      {footer && <p className="auth-form__footer">{footer}</p>}
    </form>
  );
}
