"use server";

import { createLoginToken } from "@/__generated__/backend-client/login-tokens";
import type { AuthFormState } from "@/features/auth/types";

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
  } catch {
    // Any failure (the backend couldn't send the link, a bad address, the
    // backend being unreachable) means we must NOT claim "check your email" —
    // tell the user to retry. We deliberately don't branch on HTTP status: a
    // 502 from a dead backend is indistinguishable from one the app raised.
    return { error: "We couldn't send your sign-in link. Please try again." };
  }

  return { sent: true };
}
