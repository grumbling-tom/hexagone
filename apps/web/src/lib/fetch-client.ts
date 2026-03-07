const PUBLIC_BACKEND_BASE_URL = (
  import.meta.env.PUBLIC_BACKEND_BASE_URL ?? ""
).replace(/\/+$/, "");

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
  params?: Record<string, string>;
  signal?: AbortSignal;
}): Promise<T> {
  const url = new URL(
    `${PUBLIC_BACKEND_BASE_URL}${config.url}`,
    window.location.origin,
  );

  if (config.params) {
    for (const [key, value] of Object.entries(config.params)) {
      url.searchParams.set(key, value);
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
