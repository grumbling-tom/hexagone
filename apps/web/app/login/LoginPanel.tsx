"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import LoginForm from "@/features/auth/LoginForm";

// App-level wrapper: owns the post-auth redirect and the cross-link, keeping
// routing out of the feature (CLAUDE.md → Frontend Import Rules, rule 3).
export default function LoginPanel() {
  const router = useRouter();
  return (
    <LoginForm
      onAuthenticated={() => router.replace("/map")}
      footer={
        <>
          Don&apos;t have an account? <Link href="/signup">Sign up</Link>
        </>
      }
    />
  );
}
