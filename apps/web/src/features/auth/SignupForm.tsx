"use client";

import type { ReactNode } from "react";
import { useActionState } from "react";
import type { AuthFormState } from "@/features/auth/types";

// The `action` (which creates the account + redirects) and the `footer`
// cross-link are supplied by the route (app/), keeping routing and data access
// out of the feature — see CLAUDE.md → Frontend Import Rules.
export default function SignupForm({
  action,
  footer,
}: {
  action: (state: AuthFormState, formData: FormData) => Promise<AuthFormState>;
  footer: ReactNode;
}) {
  const [state, formAction, pending] = useActionState(action, {});

  return (
    <form className="auth-form" action={formAction}>
      <h1 className="auth-form__title">Sign up</h1>

      {state.error && <p className="auth-form__error">{state.error}</p>}

      <label className="auth-form__label" htmlFor="email">
        Email
      </label>
      <input
        className="auth-form__input"
        id="email"
        name="email"
        type="email"
        required
      />

      <label className="auth-form__label" htmlFor="password">
        Password
      </label>
      <input
        className="auth-form__input"
        id="password"
        name="password"
        type="password"
        required
      />

      <button
        className={`button button--primary auth-form__submit${pending ? " button--pending" : ""}`}
        type="submit"
        disabled={pending}
      >
        {pending ? "Signing up" : "Sign up"}
      </button>

      <p className="auth-form__footer">{footer}</p>
    </form>
  );
}
