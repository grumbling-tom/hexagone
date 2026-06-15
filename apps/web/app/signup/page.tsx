import Link from "next/link";
import SignupForm from "@/features/auth/components/SignupForm";
import { signup } from "@/features/auth/server/signup";

export default function SignupPage() {
  return (
    <SignupForm
      action={signup}
      footer={
        <>
          Already have an account? <Link href="/login">Log in</Link>
        </>
      }
    />
  );
}
