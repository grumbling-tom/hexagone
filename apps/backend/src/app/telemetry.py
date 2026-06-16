"""OpenTelemetry tracing setup.

Spans are exported to the console only — there is no collector or OTLP
endpoint yet. The console exporter is enough to prove that traces are
correlated across the Next.js frontend and this backend: an inbound request
carries a W3C ``traceparent`` header (injected by Next's fetch instrumentation),
the FastAPI instrumentor continues that trace, and each SQLAlchemy query opens a
child span so the time spent waiting on the database is visible within the
request.

Swapping the console exporter for an OTLP one later is a one-line change here.
"""

from fastapi import FastAPI
from opentelemetry import trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import ConsoleSpanExporter, SimpleSpanProcessor

from src.app.settings import Settings

# Guard against instrumenting more than once. The FastAPI and SQLAlchemy
# instrumentors raise if applied twice, and create_app() can be called repeatedly
# in a single process (e.g. tests that build an app with non-default settings).
_instrumented = False


def setup_tracing(app: FastAPI, settings: Settings) -> None:
    """Instrument FastAPI + SQLAlchemy, exporting spans to the console under DEBUG.

    Tracing (and the trace-context stamping on log lines) is always set up so a
    request stays one correlated trace; the console exporter is only attached when
    ``settings.DEBUG`` is set, since it's the sole export target and its per-span
    output is just noise otherwise. A no-op under ENV=TEST so the test suite stays
    quiet and the in-memory test engine is never wrapped. Uses
    ``SimpleSpanProcessor`` (not batch) so spans flush to the console as they
    close, keeping them in causal order against the structured log lines.
    """
    global _instrumented  # noqa: PLW0603 — one-shot guard against double instrumentation
    if _instrumented or settings.ENV == "TEST":
        return

    provider = TracerProvider(
        resource=Resource.create(
            {
                "service.name": "hexagone-backend",
                "service.version": settings.GIT_SHA,
                "deployment.environment": settings.ENV,
            }
        )
    )
    if settings.DEBUG:
        provider.add_span_processor(SimpleSpanProcessor(ConsoleSpanExporter()))
    trace.set_tracer_provider(provider)

    # Imported lazily so the OTel instrumentation packages aren't pulled in (and
    # the singleton engine isn't touched) when tracing is disabled. These packages
    # ship no type stubs, hence the reportMissingTypeStubs suppression.
    from opentelemetry.instrumentation.fastapi import (  # noqa: PLC0415  # pyright: ignore[reportMissingTypeStubs]
        FastAPIInstrumentor,
    )
    from opentelemetry.instrumentation.sqlalchemy import (  # noqa: PLC0415  # pyright: ignore[reportMissingTypeStubs]
        SQLAlchemyInstrumentor,
    )

    from src.app.repository.database import engine  # noqa: PLC0415

    FastAPIInstrumentor.instrument_app(app)
    SQLAlchemyInstrumentor().instrument(engine=engine)

    _instrumented = True
