"use client";

import { useQueryClient } from "@tanstack/react-query";
import type { ReactNode, SubmitEvent } from "react";
import { useState } from "react";
import {
  getGetCurrentUserQueryOptions,
  useCreateUser,
} from "@/__generated__/backend-client/users";
import { HttpStatus } from "@/lib/fetch-client";

// Navigation is an app-level concern (CLAUDE.md rule 3): the route owns the
// redirect via `onAuthenticated` and supplies the log-in link via `footer`.
export default function SignupForm({
  onAuthenticated,
  footer,
}: {
  onAuthenticated: () => void;
  footer: ReactNode;
}) {
  const queryClient = useQueryClient();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");

  const signup = useCreateUser({
    mutation: {
      onSuccess: async () => {
        // Proactively update the current user data in the cache after logging in,
        // so that we don't have to wait for the next refetch to update the UI.
        await queryClient.fetchQuery(getGetCurrentUserQueryOptions());
        onAuthenticated();
      },
      onError: (err) => {
        switch (err.httpStatus) {
          case HttpStatus.CONFLICT:
            // Consider obscuring this error to avoid leaking information about existing accounts.
            setError("An account with this email already exists");
            break;
          default:
            setError("Something went wrong. Please try again.");
        }
      },
    },
  });

  function handleSubmit(e: SubmitEvent) {
    e.preventDefault();
    setError("");
    signup.mutate({ data: { email, password } });
  }

  return (
    <form className="auth-form" onSubmit={handleSubmit}>
      <h1 className="auth-form__title">Sign up</h1>

      {error && <p className="auth-form__error">{error}</p>}

      <label className="auth-form__label" htmlFor="email">
        Email
      </label>
      <input
        className="auth-form__input"
        id="email"
        type="email"
        required
        value={email}
        onChange={(e) => setEmail(e.target.value)}
      />

      <label className="auth-form__label" htmlFor="password">
        Password
      </label>
      <input
        className="auth-form__input"
        id="password"
        type="password"
        required
        value={password}
        onChange={(e) => setPassword(e.target.value)}
      />

      <button
        className={`button button--primary auth-form__submit${signup.isPending ? " button--pending" : ""}`}
        type="submit"
        disabled={signup.isPending}
      >
        {signup.isPending ? "Signing up" : "Sign up"}
      </button>

      <p className="auth-form__footer">{footer}</p>
    </form>
  );
}
