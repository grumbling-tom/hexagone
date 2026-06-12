import "server-only";

import { env } from "@/config/env";

// Tigris object-notification webhook ingress. Next.js is the system's sole
// public entrypoint (reached via cloudflared); the backend has no public route.
// This is a thin passthrough to the backend's internal endpoint, which owns the
// contract: it validates the Bearer shared secret and enqueues the processing
// job. Keeping it dumb means auth and payload validation live in one place.

const BACKEND_PATH = "/api/v1/upload-notifications";

export async function POST(request: Request): Promise<Response> {
  const body = await request.text();
  const authorization = request.headers.get("authorization");

  let backendResponse: Response;
  try {
    backendResponse = await fetch(new URL(BACKEND_PATH, env.BACKEND_ORIGIN), {
      method: "POST",
      headers: {
        "content-type": "application/json",
        ...(authorization ? { authorization } : {}),
      },
      body,
      cache: "no-store",
    });
  } catch {
    // Backend unreachable — a 5xx tells Tigris to retry later.
    return new Response(null, { status: 502 });
  }

  // Pass the backend's status straight back: 202 acks the webhook, 401 rejects a
  // bad/absent secret. Tigris only cares about 2xx vs. not.
  return new Response(null, { status: backendResponse.status });
}
