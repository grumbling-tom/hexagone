import RequestLinkForm from "@/features/auth/components/RequestLinkForm";
import { requestLink } from "@/features/auth/server/requestLink";

// Passwordless: sign-in and sign-up have converged into one email-only flow.
export default function LoginPage() {
  return <RequestLinkForm action={requestLink} />;
}
