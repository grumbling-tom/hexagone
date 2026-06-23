import type { Metadata } from "next";
import Link from "next/link";
import { redirect } from "next/navigation";
import { getCurrentUser } from "@/__generated__/backend-client/users";
import VerifyStatus from "@/features/auth/components/VerifyStatus";
import { verifyLogin } from "@/features/auth/server/verifyLogin";
import { ApiError, HttpStatus } from "@/lib/fetch-client";

// Keep the token (in this page's URL) out of Referer headers on any request the
// page makes — defence-in-depth alongside redirecting to a clean URL on success.
export const metadata: Metadata = { referrer: "no-referrer" };

export default async function VerifyPage({
  searchParams,
}: {
  searchParams: Promise<{ token?: string | string[] }>;
}) {
  // Already signed in (e.g. a refresh after a successful verify, where the token
  // is now spent)? Don't dead-end the user — send them through /welcome, which
  // routes them on (onboarding if new, /map if they have uploads).
  let authenticated = false;
  try {
    await getCurrentUser();
    authenticated = true;
  } catch (err) {
    if (
      !(err instanceof ApiError && err.httpStatus === HttpStatus.UNAUTHORIZED)
    ) {
      throw err;
    }
  }
  if (authenticated) redirect("/welcome");

  const { token } = await searchParams;
  const tokenValue = typeof token === "string" ? token : null;

  return (
    <VerifyStatus
      token={tokenValue}
      verify={verifyLogin}
      requestNewLink={<Link href="/login">Request a new link</Link>}
    />
  );
}
