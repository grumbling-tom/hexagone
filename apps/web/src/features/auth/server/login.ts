"use server";

import { redirect } from "next/navigation";
import { createUserSession } from "@/__generated__/backend-client/user-sessions";
import type { AuthFormState } from "@/features/auth/types";
import { ApiError, HttpStatus } from "@/lib/fetch-client";

export async function login(
  _prevState: AuthFormState,
  formData: FormData,
): Promise<AuthFormState> {
  const email = String(formData.get("email") ?? "");
  const password = String(formData.get("password") ?? "");

  try {
    await createUserSession({ email, password });
  } catch (err) {
    if (err instanceof ApiError && err.httpStatus === HttpStatus.UNAUTHORIZED) {
      return { error: "Invalid email or password" };
    }
    return { error: "Something went wrong. Please try again." };
  }

  // redirect() throws a control-flow signal — keep it outside the try/catch.
  redirect("/map");
}
