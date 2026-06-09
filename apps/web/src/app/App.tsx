import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import ProtectedRoute from "@/app/ProtectedRoute";
import HexMap from "@/app/pages/HexMap";
import Login from "@/app/pages/Login";
import Signup from "@/app/pages/Signup";
import Uploads from "@/app/pages/Uploads";

const queryClient = new QueryClient();

export function AppRoutes() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route path="/signup" element={<Signup />} />
      {/* FIXME: After u/p input, the "Loading" text flashes up again */}
      <Route element={<ProtectedRoute />}>
        <Route path="/" element={<HexMap />} />
        <Route path="/uploads" element={<Uploads />} />
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
