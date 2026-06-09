import { Navigate, Outlet } from "react-router-dom";
import { useGetCurrentUser } from "@/__generated__/backend-client/users";
import Nav from "@/app/Nav";

export default function ProtectedRoute() {
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
