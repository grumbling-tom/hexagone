import { redirect } from "next/navigation";

// Sign-up and sign-in have converged into one passwordless email flow, so
// /signup just sends people to the single /login entry point. Kept as a route
// so existing links (e.g. the landing-page CTAs) keep working.
export default function SignupPage() {
  redirect("/login");
}
