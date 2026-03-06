import { Navigate, Outlet } from "react-router-dom";
import Nav from "@/components/Nav";
import { useAuth } from "@/hooks/useAuth";

export default function ProtectedRoute() {
  const { isLoading, isAuthenticated } = useAuth();

  if (isLoading) {
    return <div className="auth-loading">Loading...</div>;
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  return (
    <>
      <Nav />
      <Outlet />
    </>
  );
}
