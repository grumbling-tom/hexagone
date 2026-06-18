"use server";

import { redirect } from "next/navigation";
import { createUserSession } from "@/__generated__/backend-client/user-sessions";
import type { AuthFormState } from "@/features/auth/types";

export async function verifyLogin(token: string): Promise<AuthFormState> {
  try {
    // Consume the token. fetchClient forwards the browser-binding nonce cookie
    // (set when the link was requested) and propagates the new `sessionid`
    // cookie back. A bad/expired/used token or missing nonce -> 401.
    await createUserSession({ token });
  } catch {
    return { error: "This sign-in link is invalid or has expired." };
  }

  // redirect() throws a control-flow signal — keep it outside the try/catch.
  // Land on /welcome (a clean URL, token stripped). /welcome is the onboarding
  // gate: it shows onboarding for a user with no uploads (e.g. a brand-new
  // account auto-created on first verify) and bounces to /map otherwise — so
  // sign-in and sign-up converge on one destination that routes correctly.
  redirect("/welcome");
}
