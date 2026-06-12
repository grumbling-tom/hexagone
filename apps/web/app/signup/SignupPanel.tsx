"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import SignupForm from "@/features/auth/SignupForm";

// App-level wrapper: owns the post-auth redirect and the cross-link, keeping
// routing out of the feature (CLAUDE.md → Frontend Import Rules, rule 3).
export default function SignupPanel() {
  const router = useRouter();
  return (
    <SignupForm
      onAuthenticated={() => router.replace("/map")}
      footer={
        <>
          Already have an account? <Link href="/login">Log in</Link>
        </>
      }
    />
  );
}
