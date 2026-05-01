import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import Login from "@/app/pages/Login";
import MapPage from "@/app/pages/MapPage";
import Signup from "@/app/pages/Signup";
import UploadsPage from "@/app/pages/UploadsPage";
import ProtectedRoute from "@/components/ProtectedRoute";

const queryClient = new QueryClient();

export function AppRoutes() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route path="/signup" element={<Signup />} />
      {/* FIXME: After u/p input, the "Loading" text flashes up again */}
      <Route element={<ProtectedRoute />}>
        <Route path="/" element={<MapPage />} />
        <Route path="/uploads" element={<UploadsPage />} />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter basename="/app">
        <AppRoutes />
      </BrowserRouter>
    </QueryClientProvider>
  );
}
