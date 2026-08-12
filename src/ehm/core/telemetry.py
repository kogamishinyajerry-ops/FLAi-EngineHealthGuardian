"""OpenTelemetry bootstrap — tracing wired, exporters are no-ops by default.

Retrofitting observability is painful, so every brain emits spans from day 1.
Attach a real exporter (OTLP) in deployment; v0 keeps everything local so the
demo runs offline with no collector.
"""

from __future__ import annotations

from opentelemetry import trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import ConsoleSpanExporter, SimpleSpanProcessor

_provider: TracerProvider | None = None


def setup_telemetry(service_name: str = "ehm", *, console: bool = False) -> TracerProvider:
    """Idempotently configure a global TracerProvider. Safe to call once at startup."""
    global _provider
    if _provider is not None:
        return _provider
    provider = TracerProvider(resource=Resource.create({"service.name": service_name}))
    if console:
        provider.add_span_processor(SimpleSpanProcessor(ConsoleSpanExporter()))
    trace.set_tracer_provider(provider)
    _provider = provider
    return provider


def tracer() -> trace.Tracer:
    """Return a tracer; sets up a default provider if none exists yet."""
    if _provider is None:
        setup_telemetry()
    return trace.get_tracer("ehm")
