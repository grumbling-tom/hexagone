// Single cluster entrypoint: Next.js serves the UI and reaches the backend
// server-side (RSC + Server Actions, via src/lib/fetch-client). The browser no
// longer calls /api, so the old proxy rewrite is gone. BACKEND_ORIGIN points at
// the in-cluster backend Service in production (set in the Deployment) and is
// read by the fetch client; it defaults to the local uvicorn server in dev.

/** @type {import('next').NextConfig} */
const nextConfig = {
  // Self-contained server bundle for a slim Docker runtime image.
  output: "standalone",
};

export default nextConfig;
