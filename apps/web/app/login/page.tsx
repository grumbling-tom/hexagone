import Link from "next/link";
import LoginForm from "@/features/auth/components/LoginForm";
import { login } from "@/features/auth/server/login";

export default function LoginPage() {
  return (
    <LoginForm
      action={login}
      footer={
        <>
          Don&apos;t have an account? <Link href="/signup">Sign up</Link>
        </>
      }
    />
  );
}
