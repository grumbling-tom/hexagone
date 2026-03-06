import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import Dashboard from "@/app/pages/Dashboard";
import Settings from "@/app/pages/Settings";
import Nav from "@/components/Nav";

const queryClient = new QueryClient();

export function AppRoutes() {
  return (
    <>
      <Nav />
      <Routes>
        <Route path="/" element={<Dashboard />} />
        <Route path="/settings" element={<Settings />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </>
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
