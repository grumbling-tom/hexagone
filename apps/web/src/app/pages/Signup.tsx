import { useQueryClient } from "@tanstack/react-query";
import type { SubmitEvent } from "react";
import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useCreateUser } from "@/__generated__/backend-client/users";
import { getGetCurrentUserQueryKey } from "@/hooks/useAuth";

export default function Signup() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");

  const signup = useCreateUser({
    mutation: {
      onSuccess: async () => {
        await queryClient.invalidateQueries({
          queryKey: getGetCurrentUserQueryKey(),
        });
        navigate("/");
      },
      onError: (err) => {
        const response = err as unknown as Response;
        if (response.status === 409) {
          setError("An account with this email already exists");
        } else {
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

      <p className="auth-form__footer">
        Already have an account? <Link to="/login">Log in</Link>
      </p>
    </form>
  );
}
