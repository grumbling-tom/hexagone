import "server-only";

import { cookies } from "next/headers";
import setCookieParser from "set-cookie-parser";

// Next.js is the sole entrypoint: this client runs server-side only (RSC + Server
// Actions) and talks to the backend over the cluster network. BACKEND_ORIGIN is
// set in the Deployment and defaults to the local uvicorn server in dev.
const BACKEND_ORIGIN = process.env.BACKEND_ORIGIN ?? "http://localhost:8000";

export enum HttpStatus {
  UNAUTHORIZED = 401,
  CONFLICT = 409,
}

export class ApiError<T> extends Error {
  constructor(
    public httpStatus: HttpStatus,
    public data: T,
  ) {
    super(`Request failed with status ${httpStatus}`);
    this.name = "ApiError";
  }
}

export type ErrorType<E> = ApiError<E>;

export async function fetchClient<T>(config: {
  url: string;
  method: string;
  headers?: HeadersInit;
  data?: unknown;
  params?: Record<
    string,
    string | number | boolean | string[] | null | undefined
  >;
  signal?: AbortSignal;
}): Promise<T> {
  const cookieStore = await cookies();
  const url = new URL(config.url, BACKEND_ORIGIN);

  if (config.params) {
    for (const [key, value] of Object.entries(config.params)) {
      if (value == null) continue;
      if (Array.isArray(value)) {
        for (const item of value) {
          url.searchParams.append(key, item);
        }
      } else {
        url.searchParams.set(key, String(value));
      }
    }
  }

  // Forward the browser's cookies (incl. the opaque httpOnly `sessionid`) so the
  // backend can authenticate the request — server-side fetch has no cookie jar.
  const headers = new Headers(config.headers);
  const jar = cookieStore.toString();
  if (jar) headers.set("cookie", jar);

  const response = await fetch(url, {
    method: config.method,
    headers,
    body: config.data ? JSON.stringify(config.data) : undefined,
    signal: config.signal,
    // Per-user data: never cache across requests.
    cache: "no-store",
  });

  // Propagate the backend's Set-Cookie back to the browser (login/signup set
  // `sessionid`, logout clears it). Writing cookies is only permitted inside
  // Server Actions / Route Handlers; during an RSC render it throws — reads
  // carry no Set-Cookie, so guard and ignore.
  const setCookies = response.headers.getSetCookie();
  if (setCookies.length > 0) {
    try {
      for (const cookie of setCookieParser.parse(setCookies)) {
        cookieStore.set(cookie.name, cookie.value, {
          httpOnly: cookie.httpOnly,
          path: cookie.path,
          domain: cookie.domain,
          expires: cookie.expires,
          maxAge: cookie.maxAge,
          secure: cookie.secure,
          sameSite: cookie.sameSite as "lax" | "strict" | "none" | undefined,
        });
      }
    } catch {
      // Not a writable cookie context (e.g. a Server Component render) — ignore.
    }
  }

  if (!response.ok) {
    const data = await response.json().catch(() => undefined);
    throw new ApiError(response.status as HttpStatus, data);
  }

  if (response.status === 204) {
    return undefined as T;
  }

  return response.json();
}

export default fetchClient;
