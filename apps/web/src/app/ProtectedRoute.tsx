import { Navigate, Outlet } from "react-router-dom";
import { useGetCurrentUser } from "@/__generated__/backend-client/users";
import Nav from "@/app/Nav";

export default function ProtectedRoute() {
  // FIXME: If we navigate directly to a protected route or refresh the page, rather
  // than logging in or signing up, we see two flashes of loading state - one, for this
  // query, then another for the component's loading state.
  const { data: user, isLoading } = useGetCurrentUser({
    query: { retry: false },
  });

  if (isLoading) {
    return <div className="auth-loading">Loading</div>;
  }

  if (!user) {
    return <Navigate to="/login" replace />;
  }

  return (
    <>
      <Nav />
      <Outlet />
    </>
  );
}
