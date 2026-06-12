"use client";

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { type ReactNode, useState } from "react";

export default function Providers({ children }: { children: ReactNode }) {
  // One QueryClient per browser session. useState keeps it stable across
  // re-renders without sharing a single client between requests during SSR.
  const [queryClient] = useState(() => new QueryClient());

  return (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  );
}
