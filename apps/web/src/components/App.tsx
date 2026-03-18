import { ClerkProvider, useAuth } from "@clerk/clerk-react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useEffect } from "react";
import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import Dashboard from "@/app/pages/Dashboard";
import Login from "@/app/pages/Login";
import Settings from "@/app/pages/Settings";
import ProtectedRoute from "@/components/ProtectedRoute";
import { setTokenGetter } from "@/lib/fetch-client";

const queryClient = new QueryClient();

function AuthTokenSync() {
  const { getToken } = useAuth();
  useEffect(() => {
    setTokenGetter(getToken);
  }, [getToken]);
  return null;
}

export function AppRoutes() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route element={<ProtectedRoute />}>
        <Route path="/" element={<Dashboard />} />
        <Route path="/settings" element={<Settings />} />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}

export default function App() {
  return (
    <ClerkProvider
      publishableKey={import.meta.env.PUBLIC_CLERK_PUBLISHABLE_KEY}
      signInUrl="/app/login"
      afterSignOutUrl="/app/login"
    >
      <AuthTokenSync />
      <QueryClientProvider client={queryClient}>
        <BrowserRouter basename="/app">
          <AppRoutes />
        </BrowserRouter>
      </QueryClientProvider>
    </ClerkProvider>
  );
}
