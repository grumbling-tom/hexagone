import { RedirectToSignIn } from "@clerk/clerk-react";
import { Outlet } from "react-router-dom";
import Nav from "@/components/Nav";
import { useAuthContext } from "@/lib/auth";

export default function ProtectedRoute() {
  const { isSignedIn, isLoaded } = useAuthContext();

  if (!isLoaded) {
    return <div className="auth-loading">Loading</div>;
  }

  if (!isSignedIn) {
    return <RedirectToSignIn />;
  }

  return (
    <>
      <Nav />
      <Outlet />
    </>
  );
}
