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

# Suffix appended to the default console formatters to surface the trace/span IDs. Kept here (rather
# than in settings.py) as the single source of truth for `enable_otel_log_correlation()`.
_OTEL_LOG_SUFFIX = " [trace_id=%(otelTraceID)s span_id=%(otelSpanID)s]"
# Marker in the default `normal`/`verbose` formats that the suffix is inserted immediately before, so
# the trace/span IDs land at the end of the header line rather than after the message body.
_OTEL_LOG_SUFFIX_ANCHOR = " :\n  %(message)s"
# The formatters/handlers Nautobot defines in its default LOGGING config. `enable_otel_log_correlation`
# only ever touches these by name, and only in the shipped LOGGING dict itself (see its identity gate).
_OTEL_DEFAULT_FORMATTERS = ("normal", "verbose")
_OTEL_DEFAULT_HANDLERS = ("normal_console", "verbose_console")
_OTEL_TRACE_CONTEXT_FILTER = "otel_trace_context"


def enable_otel_log_correlation(logging_config):
    """Augment Nautobot's default LOGGING dict in place to surface OpenTelemetry trace/span IDs.

    Called from `nautobot.core.cli._preprocess_settings` *after* the resolved config is known (so a
    `OTEL_PYTHON_DJANGO_INSTRUMENT`/`OTEL_PYTHON_LOG_CORRELATION` set in `nautobot_config.py` is honored,
    not just the env-var defaults baked into the LOGGING dict at settings-import time).

    No-op unless `logging_config` *is* `nautobot.core.settings.LOGGING`. Because `nautobot_config.py`
    does `from nautobot.core.settings import *`, an operator who leaves `LOGGING` alone still holds that
    exact object, while *any* customization -- reassigning `LOGGING` to a new dict, even one that merely
    tweaks a level -- rebinds the name and so is left entirely untouched. Identity rather than equality:
    this function mutates in place, so an equality check would accept a pre-mutation copy of the defaults
    and reject it afterwards. Operators with a custom `LOGGING` surface the IDs via their own formatters
    (see `OTEL_PYTHON_LOG_CORRELATION` in settings.py).

    Idempotent: appending an already-present suffix or filter is skipped, so repeat calls are safe.
    """
    # Imported lazily: this module is imported *from* nautobot.core.settings while LOGGING is being
    # built, so a module-level import would be circular.
    from nautobot.core import settings as core_settings

    if logging_config is not getattr(core_settings, "LOGGING", None):
        return

    formatters = logging_config.get("formatters", {})
    for name in _OTEL_DEFAULT_FORMATTERS:
        formatter = formatters.get(name)
        if not formatter:
            continue
        fmt = formatter.get("format", "")
        if "%(otelTraceID)s" in fmt or _OTEL_LOG_SUFFIX_ANCHOR not in fmt:
            continue
        formatter["format"] = fmt.replace(_OTEL_LOG_SUFFIX_ANCHOR, _OTEL_LOG_SUFFIX + _OTEL_LOG_SUFFIX_ANCHOR, 1)

    logging_config.setdefault("filters", {}).setdefault(
        _OTEL_TRACE_CONTEXT_FILTER, {"()": "nautobot.core.logging.OtelTraceContextFilter"}
    )

    handlers = logging_config.get("handlers", {})
    for name in _OTEL_DEFAULT_HANDLERS:
        handler = handlers.get(name)
        if handler is None:
            continue
        handler_filters = handler.setdefault("filters", [])
        if _OTEL_TRACE_CONTEXT_FILTER not in handler_filters:
            handler_filters.append(_OTEL_TRACE_CONTEXT_FILTER)


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
