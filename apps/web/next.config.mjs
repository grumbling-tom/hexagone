// Single cluster entrypoint: Next.js serves the UI and proxies /api to the
// backend, so cloudflared no longer needs to path-split. BACKEND_ORIGIN points
// at the in-cluster backend Service in production (set in the Deployment) and
// defaults to the local uvicorn server in dev.
const BACKEND_ORIGIN = process.env.BACKEND_ORIGIN || "http://localhost:8000";

/** @type {import('next').NextConfig} */
const nextConfig = {
  // Self-contained server bundle for a slim Docker runtime image.
  output: "standalone",
  async rewrites() {
    return [
      {
        source: "/api/:path*",
        destination: `${BACKEND_ORIGIN}/api/:path*`,
      },
    ];
  },
};

export default nextConfig;
