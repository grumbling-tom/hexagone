import { createEnv } from "@t3-oss/env-nextjs";
import { z } from "zod";

/**
 * Typed, validated settings — the Next.js analogue of the backend's
 * pydantic-settings `Settings`.
 *
 * `@t3-oss/env-nextjs` parses `process.env` once (on first import) against the
 * schemas below and throws on anything missing or malformed, so a config
 * mistake fails loudly at boot/build instead of surfacing as a confusing error
 * deep inside a request. Import `env` from here instead of touching
 * `process.env` directly — that keeps the schema the single source of truth for
 * what configuration exists and what shape it has.
 *
 * The server/client split is the part pydantic-settings never has to model:
 *   - `server` vars are stripped from the browser bundle; reading one from
 *     client code throws (see `onInvalidAccess`, on by default).
 *   - `client` vars MUST be `NEXT_PUBLIC_`-prefixed and are inlined into the
 *     client bundle at *build* time, so changing one needs a rebuild.
 *
 * There are no client vars today — Next.js is the sole entrypoint and the
 * browser makes zero direct backend calls (reads in RSC, writes via Server
 * Actions). The `client` block is kept (empty) to document where a future
 * `NEXT_PUBLIC_*` var would go.
 */
export const env = createEnv({
  server: {
    // Origin the server-side fetch client talks to (src/lib/fetch-client.ts).
    // Points at the in-cluster backend Service in production (set on the
    // Deployment) and defaults to the local uvicorn server in dev.
    BACKEND_ORIGIN: z.url().default("http://localhost:8000"),

    // Mirrors the backend's `settings.DEBUG`. Gates the OpenTelemetry console
    // span exporter in instrumentation.ts — tracing always runs, but spans are
    // only printed to the console when this is on. Enum-then-transform rather
    // than `z.coerce.boolean` so only the literal "true" is truthy ("false"
    // coerces to `true` under `coerce`).
    DEBUG: z
      .enum(["true", "false"])
      .default("false")
      .transform((v) => v === "true"),
  },

  // No browser-exposed config yet. A future client var goes here as
  // `NEXT_PUBLIC_FOO: z.string()` and must also be listed in
  // `experimental__runtimeEnv` below by literal name.
  client: {},

  // Next.js >= 13.4.4 only statically analyzes client (`NEXT_PUBLIC_`) vars, so
  // only those must be destructured here by literal name. Server vars are read
  // from `process.env` directly, so this stays empty until a client var lands.
  experimental__runtimeEnv: {},

  // Treat "" as unset so empty values fall back to defaults instead of failing
  // validation (e.g. `BACKEND_ORIGIN=` in a .env file).
  emptyStringAsUndefined: true,

  // Escape hatch for unit tests, CI, and container builds where the real env
  // isn't present. Set SKIP_ENV_VALIDATION=1 to bypass parsing entirely.
  skipValidation: !!process.env.SKIP_ENV_VALIDATION,
});
