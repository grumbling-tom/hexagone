"use server";

import { createLoginToken } from "@/__generated__/backend-client/login-tokens";
import type { AuthFormState } from "@/features/auth/types";
import { ApiError, HttpStatus } from "@/lib/fetch-client";

export async function requestLink(
  _prevState: AuthFormState,
  formData: FormData,
): Promise<AuthFormState> {
  const email = String(formData.get("email") ?? "");

  try {
    // 202 + an always-set nonce cookie, identical whether or not the address is
    // allow-listed (the backend never reveals membership). fetchClient
    // propagates the nonce cookie to the browser for the later verify step.
    await createLoginToken({ email });
  } catch (err) {
    if (err instanceof ApiError && err.httpStatus === HttpStatus.BAD_GATEWAY) {
      // The address was allow-listed but the email provider failed.
      return { error: "We couldn't send your sign-in link. Please try again." };
    }
    return { error: "Something went wrong. Please try again." };
  }

  return { sent: true };
}
