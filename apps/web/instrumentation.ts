// Next.js runtime instrumentation hook (stable in Next 15 — no experimental flag
// needed). Runs once per server runtime at startup.
//
// We export spans to the console only: there is no collector or OTLP endpoint
// yet. That is enough to prove traces are correlated across services — @vercel/otel
// wires up Next's fetch instrumentation, which injects a W3C `traceparent` header
// into every server-side fetch (including src/lib/fetch-client.ts), so the FastAPI
// backend continues the same trace. Grep the 32-hex trace id across this console
// and the backend console to see one request as one trace.
//
// Supplying `spanProcessors` overrides @vercel/otel's default OTLP exporter, so no
// network export is attempted. Swapping in an OTLP exporter later is a one-liner.
//
// Tracing is always registered so Next's fetch instrumentation keeps injecting the
// W3C `traceparent` header and a request stays one correlated trace. The console
// exporter is the only export target, so it's only attached under DEBUG (mirroring
// the backend's `settings.DEBUG`) — otherwise its per-span output is just noise.
// An empty `spanProcessors` array still overrides the default OTLP exporter, so no
// network export is attempted when debug is off.

import {
  ConsoleSpanExporter,
  SimpleSpanProcessor,
} from "@opentelemetry/sdk-trace-node";
import { registerOTel } from "@vercel/otel";

import { env } from "@/config/env";

export function register() {
  registerOTel({
    serviceName: "hexagone-web",
    spanProcessors: env.DEBUG
      ? [new SimpleSpanProcessor(new ConsoleSpanExporter())]
      : [],
  });
}
