/**
 * Auth abstraction layer — decouples app code from the auth provider.
 *
 * All app code should use `useAuthContext()` instead of importing from
 * the auth provider directly. To migrate away from Clerk, reimplement
 * this file against the new provider.
 */

import { useAuth, useUser } from "@clerk/clerk-react";

export function useAuthContext() {
  const { isSignedIn, isLoaded, getToken, signOut } = useAuth();
  const { user } = useUser();

  return {
    isSignedIn: isSignedIn ?? false,
    isLoaded,
    getToken,
    signOut: () => signOut(),
    email: user?.primaryEmailAddress?.emailAddress,
  };
}
