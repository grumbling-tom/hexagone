import { SignIn as ClerkSignIn } from "@clerk/clerk-react";

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

export default function SignIn() {
  return (
    <div className="auth-form">
      <h1 className="auth-form__title">Log in</h1>
      <ClerkSignIn
        appearance={clerkAppearance}
        routing="path"
        path="/app/sign-in"
        fallbackRedirectUrl="/app"
      />
    </div>
  );
}
