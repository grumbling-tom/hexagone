import "server-only";

import { isSpanContextValid, trace } from "@opentelemetry/api";

// Structured, server-side logger for the Next.js app — the frontend analogue of
// the backend's structlog setup (apps/backend/src/app/utils/logger.py).
//
// Every line is stamped with the active OpenTelemetry span's `trace_id` and
// `span_id`, rendered exactly as the backend stamps them (32- / 16-hex
// lowercase, the same ids carried in the W3C `traceparent` header that Next's
// fetch instrumentation injects). So a single request is one correlated trace:
// grep a `trace_id` from a web log line and it matches the backend log lines —
// and the span output on both sides — for the same request.
//
// Output is single-line JSON to stdout/stderr (stderr for `error`), which the
// Next standalone server writes through to the container logs.

type LogLevel = "debug" | "info" | "warn" | "error";

type LogContext = Record<string, unknown>;

function emit(level: LogLevel, event: string, context: LogContext = {}): void {
  const spanContext = trace.getActiveSpan()?.spanContext();
  const traceFields =
    spanContext && isSpanContextValid(spanContext)
      ? { trace_id: spanContext.traceId, span_id: spanContext.spanId }
      : {};

  const line = JSON.stringify({
    level,
    timestamp: new Date().toISOString(),
    event,
    ...traceFields,
    ...context,
  });

  if (level === "error") {
    console.error(line);
  } else {
    console.log(line);
  }
}

export const logger = {
  debug: (event: string, context?: LogContext) => emit("debug", event, context),
  info: (event: string, context?: LogContext) => emit("info", event, context),
  warn: (event: string, context?: LogContext) => emit("warn", event, context),
  error: (event: string, context?: LogContext) => emit("error", event, context),
};

export default logger;
