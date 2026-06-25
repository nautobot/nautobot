"""OpenTelemetry helper utilities for instrumenting Nautobot internals."""

from contextlib import contextmanager

from opentelemetry import trace


@contextmanager
def traced_span(tracer_name, span_name, **attributes):
    """Start an OpenTelemetry span and yield it for the duration of the ``with`` block.

    This centralizes the otherwise-repeated ``get_tracer(...).start_as_current_span(...)``
    boilerplate used to manually instrument cache lookups and similar hot paths. The active
    span is yielded so callers can set additional attributes conditionally (for example a
    ``<namespace>.hit`` boolean once a cache result is known).

    Args:
        tracer_name (str): Tracer name, conventionally the dotted module namespace
            (e.g. ``"nautobot.extras.relationships"``).
        span_name (str): Span name (e.g. ``"relationship_cache.get [source]"``).
        **attributes: Initial span attributes to set immediately. ``None`` values are skipped.

    Yields:
        opentelemetry.trace.Span: The active span.

    Example:
        with traced_span(
            "nautobot.extras.relationships",
            "relationship_cache.get [source]",
            **{"relationship_cache.model": label, "relationship_cache.hidden": str(hidden)},
        ) as span:
            result = cache.get(cache_key)
            span.set_attribute("relationship_cache.hit", result is not None)
    """
    tracer = trace.get_tracer(tracer_name)
    with tracer.start_as_current_span(span_name) as span:
        for key, value in attributes.items():
            if value is not None:
                span.set_attribute(key, value)
        yield span
