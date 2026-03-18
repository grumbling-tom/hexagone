import { SignIn as ClerkSignIn } from "@clerk/clerk-react";

export default function SignIn() {
  return (
    <div className="auth-form">
      <ClerkSignIn />
    </div>
  );
}
