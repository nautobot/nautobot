"""Logging helpers for Nautobot.

Intentionally stdlib-only: this module is imported from `nautobot.core.settings` while the `LOGGING`
dict is being built (before `django.setup()`), so it must not import Django, the OpenTelemetry SDK, or
anything heavy.
"""

import logging

# Attributes that `opentelemetry.instrumentation.logging.LoggingInstrumentor(inject_trace_context=True)`
# adds to each log record, with the same "no active span" sentinels the instrumentor itself uses. See
# `OtelTraceContextFilter` for why we default them defensively.
_OTEL_RECORD_ATTRS = (
    ("otelTraceID", "0"),
    ("otelSpanID", "0"),
    ("otelTraceSampled", False),
    ("otelServiceName", ""),
)


class OtelTraceContextFilter(logging.Filter):
    """Guarantee the OpenTelemetry trace-context attributes exist on every record.

    When `OTEL_PYTHON_LOG_CORRELATION` is enabled, Nautobot's default formatters reference
    `%(otelTraceID)s` / `%(otelSpanID)s`. Those attributes are populated by the OpenTelemetry logging
    instrumentor's record factory, but only for records created *after* `instrument()` runs and only in
    processes where instrumentation is active. A record that reaches these formatters without the
    attributes (e.g. emitted during early startup before instrumentation, or constructed directly by a
    third-party library) would otherwise raise `ValueError: Formatting field not found in record`.

    This filter fills in the standard "no active span" sentinels (`"0"` trace/span IDs) for any missing
    attribute, so formatting never fails, while leaving real injected values untouched. It is attached
    to the default handlers only when correlation is enabled.
    """

    def filter(self, record):
        for attr, default in _OTEL_RECORD_ATTRS:
            if not hasattr(record, attr):
                setattr(record, attr, default)
        return True
