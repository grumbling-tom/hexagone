import Link from "next/link";
import SignupForm from "@/features/auth/SignupForm";
import { signup } from "./actions";

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
