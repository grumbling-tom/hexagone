import { SignIn as ClerkSignIn } from "@clerk/clerk-react";
import { useAuthContext } from "@/lib/auth";

const clerkAppearance = {
  layout: {
    socialButtonsPlacement: "bottom" as const,
    logoPlacement: "none" as const,
  },
  variables: {
    colorPrimary: "#333",
    colorText: "#333",
    colorTextSecondary: "#333",
    colorBackground: "#fafafa",
    fontFamily: '"Architects Daughter", cursive',
    fontFamilyButtons: "system-ui, -apple-system, sans-serif",
    borderRadius: "4px",
  },
};

export default function Login() {
  const { isLoaded } = useAuthContext();

  return (
    <div className="auth-form">
      <h1 className="auth-form__title">Log in</h1>
      <p className="auth-form__hint">
        Sign in with your Google account to get started.
      </p>
      {isLoaded ? (
        <ClerkSignIn
          appearance={clerkAppearance}
          routing="path"
          path="/app/login"
          fallbackRedirectUrl="/app"
        />
      ) : (
        <div className="auth-form__skeleton" />
      )}
    </div>
  );
}
