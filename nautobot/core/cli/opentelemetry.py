"""Enable OTEL Tracing."""

import logging

from opentelemetry import metrics, trace
from opentelemetry.instrumentation.celery import CeleryInstrumentor
from opentelemetry.instrumentation.django import DjangoInstrumentor
from opentelemetry.instrumentation.logging import LoggingInstrumentor
from opentelemetry.instrumentation.redis import RedisInstrumentor
from opentelemetry.instrumentation.requests import RequestsInstrumentor
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import (
    ConsoleMetricExporter,
    PeriodicExportingMetricReader,
)
from opentelemetry.sdk.resources import Resource, SERVICE_NAME, SERVICE_VERSION
from opentelemetry.sdk.trace import SpanLimits, TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter

from nautobot import __version__
from nautobot.core.utils.module_loading import import_string_optional

logger = logging.getLogger(__name__)

# Set once install_exporters() has attached the OTLP/console exporters, so repeated post-fork hook
# calls (uWSGI @postfork + a non-forking fallback, or multiple Celery children in one process) don't
# double-register span processors / meter providers.
_exporters_installed = False


def instrument():
    """Instrument Nautobot with OpenTelemetry (auto-instrumentors + tracer provider only).

    This must run during CLI startup *before* `django.setup()` (invoked by
    `execute_from_command_line()` in `nautobot.core.cli.main`). The OpenTelemetry
    auto-instrumentors (Django, psycopg2/MySQL, Redis, Celery, requests, ...) work by
    monkeypatching their target libraries; the patch only takes effect for code imported
    *after* the instrumentor is installed. `django.setup()` imports and binds the app
    registry, middleware, and DB engine, so instrumenting after it would silently miss
    those already-bound code paths. Running first guarantees every layer is wrapped.

    A consequence of running pre-`django.setup()` is that `django.conf.settings` is not yet
    configured here. Instead this reads the already-loaded `nautobot_config` module, which
    `main()` registers in `sys.modules` via `load_settings()` before calling `instrument()`.
    Unlike `nautobot.core.settings` (env-var defaults only), that module reflects any overrides the
    user set in their `nautobot_config.py`.

    Crucially, this function does NOT create the OTLP exporters. The OTLP gRPC exporter builds a
    grpc channel whose C-core spawns background threads and epoll fds at construction; grpc's C-core
    is not fork-safe, so a channel created here (in the uWSGI master or a Celery parent) is inherited
    broken by forked workers and segfaults when used. Exporter/provider creation is therefore
    deferred to `install_exporters()`. For forking servers each worker calls it *after* fork (see the
    `nautobot.core.wsgi` uWSGI postfork hook and the Celery `worker_process_init` handler). For
    non-forking processes (`runserver`, one-off management commands) the CLI entrypoint
    (`nautobot.core.cli.main`) calls `install_exporters()` right after this function returns, where
    in-process channel creation is safe.
    """
    # Resolve to the loaded config registered by load_settings(); honors nautobot_config.py overrides
    # (e.g. OTEL_EXPORTER_OTLP_ENDPOINT), unlike the base nautobot.core.settings module.
    import nautobot_config  # runtime module registered by load_settings(), only available here

    resource = Resource(attributes={SERVICE_NAME: "nautobot", SERVICE_VERSION: __version__})
    # Cap span attribute value length so large values (e.g. GraphQL queries) don't bloat spans. The OTEL
    # SDK is unbounded by default; OTEL_SPAN_ATTRIBUTE_VALUE_LENGTH_LIMIT defaults to 8192 (see settings.py).
    # A None setting (empty env var) means "unlimited": map it to SpanLimits.UNSET, which deterministically
    # disables the cap. Passing None directly would instead make SpanLimits re-read the env var/global default.
    span_attr_limit = nautobot_config.OTEL_SPAN_ATTRIBUTE_VALUE_LENGTH_LIMIT
    if span_attr_limit is None:
        span_attr_limit = SpanLimits.UNSET
    span_limits = SpanLimits(max_span_attribute_length=span_attr_limit)
    provider = TracerProvider(resource=resource, span_limits=span_limits)
    trace.set_tracer_provider(provider)

    DjangoInstrumentor().instrument(tracer_provider=provider, is_sql_commentor_enabled=True)
    RequestsInstrumentor().instrument(tracer_provider=provider)
    RedisInstrumentor().instrument(tracer_provider=provider)
    CeleryInstrumentor().instrument(tracer_provider=provider)

    if nautobot_config.OTEL_PYTHON_LOG_CORRELATION:
        # inject_trace_context=True adds otelTraceID/otelSpanID/otelTraceSampled/otelServiceName to
        # every log record so logs can be correlated to their trace. Do NOT use set_logging_format=True:
        # that additionally calls logging.basicConfig(), which attaches a StreamHandler to the root
        # logger. Nautobot's own LOGGING config (settings.py) sets handlers on the "nautobot"/"django"
        # loggers, which propagate to root by default, so the added root handler re-emits every record
        # in a different format -- producing duplicate, oddly-formatted log lines. Injection alone gives
        # the correlation attributes without clobbering the operator's LOGGING config; operators surface
        # the IDs by adding e.g. %(otelTraceID)s to their own formatters.
        LoggingInstrumentor().instrument(tracer_provider=provider, inject_trace_context=True)

    if "mysql" in nautobot_config.DATABASES["default"]["ENGINE"]:
        from opentelemetry.instrumentation.mysqlclient import MySQLClientInstrumentor

        MySQLClientInstrumentor().instrument(tracer_provider=provider, skip_dep_check=True, enable_commenter=True)
    else:
        from opentelemetry.instrumentation.psycopg2 import Psycopg2Instrumentor

        Psycopg2Instrumentor().instrument(tracer_provider=provider, skip_dep_check=True, enable_commenter=True)

    # getattr with a default (unlike the direct reads above) so a hand-rolled nautobot_config.py that
    # predates this setting still works; settings.py always defines it, so the default only covers overrides.
    for path in getattr(nautobot_config, "NAUTOBOT_OTEL_EXTRA_INSTRUMENTORS", []):
        try:
            # Returns None for a missing module/attribute; a dotless path raises ValueError.
            instrumentor_cls = import_string_optional(path)
        except ValueError:
            instrumentor_cls = None
        if instrumentor_cls is None:
            logger.warning("Could not load OTEL instrumentor %s; skipping.", path)
            continue
        try:
            instrumentor = instrumentor_cls()
            if not instrumentor.is_instrumented_by_opentelemetry:
                instrumentor.instrument(tracer_provider=provider)
        except Exception:
            logger.warning("Failed to enable OTEL instrumentor %s; skipping.", path, exc_info=True)


def _otel_config():
    """Return the config object exposing the OTEL_* settings, preferring configured Django settings.

    In a post-fork worker `django.setup()` has already run, so `django.conf.settings` is the source of
    truth (honors every layer, including `nautobot_config.py` overrides). During the pre-`django.setup()`
    CLI path (non-forking fallback in `instrument()`) settings are not configured yet, so fall back to
    the loaded `nautobot_config` module that `load_settings()` registered in `sys.modules`.
    """
    from django.conf import settings

    if settings.configured:
        return settings
    import nautobot_config

    return nautobot_config


def install_exporters(config=None):
    """Attach the OTLP/console span processors and metric readers to the global providers.

    This is the only place that constructs the OTLP exporters, and therefore the OTLP gRPC channel.
    It MUST run in the process that will actually export -- i.e. after `fork()` in each uWSGI/Celery
    worker -- because grpc's C-core is not fork-safe (a channel built pre-fork is inherited broken and
    segfaults on use). It is idempotent: the module-level `_exporters_installed` guard makes repeated
    calls (a worker's postfork hook plus the non-forking fallback in `instrument()`) no-ops.

    Args:
        config: Optional settings-like object exposing the OTEL_* attributes. Defaults to the
            configured Django settings (post-fork) or the loaded `nautobot_config` module (pre-setup).
    """
    global _exporters_installed
    if _exporters_installed:
        return
    if config is None:
        config = _otel_config()

    provider = trace.get_tracer_provider()
    if not isinstance(provider, TracerProvider):
        logger.warning(
            "OpenTelemetry tracer provider is not configured; skipping exporter installation. "
            "Ensure `instrument()` runs before `install_exporters()`."
        )
        return

    if "none" not in config.OTEL_TRACES_EXPORTER:
        if "console" in config.OTEL_TRACES_EXPORTER:
            trace.get_tracer_provider().add_span_processor(BatchSpanProcessor(ConsoleSpanExporter()))

        if "otlp" in config.OTEL_TRACES_EXPORTER:
            if not config.OTEL_EXPORTER_OTLP_ENDPOINT:
                logger.warning(
                    "OTEL_TRACES_EXPORTER includes 'otlp' but OTEL_EXPORTER_OTLP_ENDPOINT is not set; "
                    "skipping the OTLP trace exporter to avoid connection errors."
                )
            else:
                otlp_settings = {"endpoint": config.OTEL_EXPORTER_OTLP_ENDPOINT}
                if config.OTEL_EXPORTER_OTLP_PROTOCOL == "http":
                    from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
                else:
                    from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter

                    otlp_settings["insecure"] = config.OTEL_EXPORTER_OTLP_INSECURE
                trace.get_tracer_provider().add_span_processor(BatchSpanProcessor(OTLPSpanExporter(**otlp_settings)))

    if config.OTEL_METRICS_EXPORTER and "none" not in config.OTEL_METRICS_EXPORTER:
        readers = []
        if "otlp" in config.OTEL_METRICS_EXPORTER:
            if not config.OTEL_EXPORTER_OTLP_ENDPOINT:
                logger.warning(
                    "OTEL_METRICS_EXPORTER includes 'otlp' but OTEL_EXPORTER_OTLP_ENDPOINT is not set; "
                    "skipping the OTLP metric exporter to avoid connection errors."
                )
            else:
                otlp_settings = {"endpoint": config.OTEL_EXPORTER_OTLP_ENDPOINT}
                if config.OTEL_EXPORTER_OTLP_PROTOCOL == "http":
                    from opentelemetry.exporter.otlp.proto.http.metric_exporter import OTLPMetricExporter
                else:
                    from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter

                    otlp_settings["insecure"] = config.OTEL_EXPORTER_OTLP_INSECURE
                readers.append(PeriodicExportingMetricReader(OTLPMetricExporter(**otlp_settings)))
        if "console" in config.OTEL_METRICS_EXPORTER:
            readers.append(PeriodicExportingMetricReader(ConsoleMetricExporter()))
        if readers:
            resource = Resource(attributes={SERVICE_NAME: "nautobot", SERVICE_VERSION: __version__})
            meter_provider = MeterProvider(resource=resource, metric_readers=readers)
            metrics.set_meter_provider(meter_provider)

    _exporters_installed = True
