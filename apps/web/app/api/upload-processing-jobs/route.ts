import "server-only";

import type { UploadNotification } from "@/__generated__/backend-client/backend.schemas";
import { createUploadProcessingJob } from "@/__generated__/backend-client/upload-processing-jobs";
import { ApiError } from "@/lib/fetch-client";

// Upload-processing-job ingress, driven by the Tigris object-notification
// webhook. Next.js is the system's sole public entrypoint (reached via
// cloudflared); the backend has no public route. This is a thin passthrough to
// the backend's internal endpoint, which owns the contract: it validates the
// Bearer shared secret and creates the processing job. Keeping it dumb means
// auth and payload validation live in one place — we forward the Bearer header
// untouched and let the backend accept (202) or reject (401) it.

export async function POST(request: Request): Promise<Response> {
  const body = (await request.json()) as UploadNotification;
  const authorization = request.headers.get("authorization");

  try {
    await createUploadProcessingJob(body, {
      headers: authorization ? { authorization } : {},
    });
  } catch (error) {
    // The backend rejected it (e.g. 401 on a bad/absent secret) — pass the
    // status straight back. Anything else means the backend was unreachable; a
    // 502 tells Tigris to retry later.
    if (error instanceof ApiError) {
      return new Response(null, { status: error.httpStatus });
    }
    return new Response(null, { status: 502 });
  }

  // Ack the webhook. Tigris only cares about 2xx vs. not.
  return new Response(null, { status: 202 });
}
