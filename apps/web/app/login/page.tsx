"use client";

import { useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { useRouter } from "next/navigation";
import type { SubmitEvent } from "react";
import { useState } from "react";
import { useCreateUserSession } from "@/__generated__/backend-client/user-sessions";
import { getGetCurrentUserQueryOptions } from "@/__generated__/backend-client/users";
import { HttpStatus } from "@/lib/fetch-client";

export default function LoginPage() {
  const router = useRouter();
  const queryClient = useQueryClient();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");

  const login = useCreateUserSession({
    mutation: {
      onSuccess: async () => {
        // Proactively update the current user data in the cache after logging in,
        // so that we don't have to wait for the next refetch to update the UI.
        await queryClient.fetchQuery(getGetCurrentUserQueryOptions());
        router.replace("/map");
      },
      onError: (err) => {
        switch (err.httpStatus) {
          case HttpStatus.UNAUTHORIZED:
            setError("Invalid email or password");
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
    login.mutate({ data: { email, password } });
  }

  return (
    <form className="auth-form" onSubmit={handleSubmit}>
      <h1 className="auth-form__title">Log in</h1>

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
        className={`button button--primary auth-form__submit${login.isPending ? " button--pending" : ""}`}
        type="submit"
        disabled={login.isPending}
      >
        {login.isPending ? "Logging in" : "Log in"}
      </button>

      <p className="auth-form__footer">
        Don&apos;t have an account? <Link href="/signup">Sign up</Link>
      </p>
    </form>
  );
}
