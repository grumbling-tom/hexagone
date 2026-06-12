"use server";

import { redirect } from "next/navigation";
import { createUser } from "@/__generated__/backend-client/users";
import type { AuthFormState } from "@/features/auth/types";
import { ApiError, HttpStatus } from "@/lib/fetch-client";

export async function signup(
  _prevState: AuthFormState,
  formData: FormData,
): Promise<AuthFormState> {
  const email = String(formData.get("email") ?? "");
  const password = String(formData.get("password") ?? "");

  try {
    await createUser({ email, password });
  } catch (err) {
    if (err instanceof ApiError && err.httpStatus === HttpStatus.CONFLICT) {
      // Consider obscuring this error to avoid leaking information about existing accounts.
      return { error: "An account with this email already exists" };
    }
    return { error: "Something went wrong. Please try again." };
  }

  // redirect() throws a control-flow signal — keep it outside the try/catch.
  redirect("/map");
}
