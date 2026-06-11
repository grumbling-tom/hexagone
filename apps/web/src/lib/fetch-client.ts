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
  // Same-origin: Next proxies /api to the backend (next.config.mjs rewrites).
  const url = new URL(config.url, window.location.origin);

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

  const response = await fetch(url, {
    method: config.method,
    headers: config.headers,
    body: config.data ? JSON.stringify(config.data) : undefined,
    signal: config.signal,
    credentials: "include",
  });

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
