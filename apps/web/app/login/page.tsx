import Link from "next/link";
import LoginForm from "@/features/auth/LoginForm";
import { login } from "./actions";

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
