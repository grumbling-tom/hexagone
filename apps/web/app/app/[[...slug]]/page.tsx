"use client";

import dynamic from "next/dynamic";

// The existing React Router SPA (basename="/app"), mounted client-only. The
// optional catch-all route serves /app and every /app/* deep link so react-router
// can take over — replacing app.astro + the old spaFallback Vite plugin.
// ssr: false because deck.gl / maplibre touch `window` at import time.
const App = dynamic(() => import("@/app/App"), { ssr: false });

export default function AppPage() {
  return <App />;
}
