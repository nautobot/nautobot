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

logger = logging.getLogger(__name__)


def instrument():
    """Instrument Nautobot with OpenTelemetry.

    This must run during CLI startup *before* ``django.setup()`` (invoked by
    ``execute_from_command_line()`` in ``nautobot.core.cli.main``). The OpenTelemetry
    auto-instrumentors (Django, psycopg2/MySQL, Redis, Celery, requests, ...) work by
    monkeypatching their target libraries; the patch only takes effect for code imported
    *after* the instrumentor is installed. ``django.setup()`` imports and binds the app
    registry, middleware, and DB engine, so instrumenting after it would silently miss
    those already-bound code paths. Running first guarantees every layer is wrapped.

    A consequence of running pre-``django.setup()`` is that ``django.conf.settings`` is not yet
    configured here. Instead this reads the already-loaded ``nautobot_config`` module, which
    ``main()`` registers in ``sys.modules`` via ``load_settings()`` before calling ``instrument()``.
    Unlike ``nautobot.core.settings`` (env-var defaults only), that module reflects any overrides the
    user set in their ``nautobot_config.py``.
    """
    # Resolve to the loaded config registered by load_settings(); honors nautobot_config.py overrides
    # (e.g. OTEL_EXPORTER_OTLP_ENDPOINT), unlike the base nautobot.core.settings module.
    import nautobot_config  # runtime module registered by load_settings(), only available here

    resource = Resource(attributes={SERVICE_NAME: "nautobot", SERVICE_VERSION: __version__})
    # Cap attribute value length so large values (e.g. GraphQL queries) don't bloat spans. The OTEL
    # SDK is unbounded by default; OTEL_ATTRIBUTE_VALUE_LENGTH_LIMIT defaults to 8192 (see settings.py).
    span_limits = SpanLimits(max_attribute_length=nautobot_config.OTEL_ATTRIBUTE_VALUE_LENGTH_LIMIT)
    provider = TracerProvider(resource=resource, span_limits=span_limits)
    trace.set_tracer_provider(provider)

    if "none" not in nautobot_config.OTEL_TRACES_EXPORTER:
        if "console" in nautobot_config.OTEL_TRACES_EXPORTER:
            trace.get_tracer_provider().add_span_processor(BatchSpanProcessor(ConsoleSpanExporter()))

        if "otlp" in nautobot_config.OTEL_TRACES_EXPORTER:
            if not nautobot_config.OTEL_EXPORTER_OTLP_ENDPOINT:
                logger.warning(
                    "OTEL_TRACES_EXPORTER includes 'otlp' but OTEL_EXPORTER_OTLP_ENDPOINT is not set; "
                    "skipping the OTLP trace exporter to avoid connection errors."
                )
            else:
                otlp_settings = {"endpoint": nautobot_config.OTEL_EXPORTER_OTLP_ENDPOINT}
                if nautobot_config.OTEL_EXPORTER_OTLP_PROTOCOL == "http":
                    from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
                else:
                    from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter

                    otlp_settings["insecure"] = nautobot_config.OTEL_EXPORTER_OTLP_INSECURE
                trace.get_tracer_provider().add_span_processor(BatchSpanProcessor(OTLPSpanExporter(**otlp_settings)))

    if nautobot_config.OTEL_METRICS_EXPORTER and "none" not in nautobot_config.OTEL_METRICS_EXPORTER:
        readers = []
        if "otlp" in nautobot_config.OTEL_METRICS_EXPORTER:
            if not nautobot_config.OTEL_EXPORTER_OTLP_ENDPOINT:
                logger.warning(
                    "OTEL_METRICS_EXPORTER includes 'otlp' but OTEL_EXPORTER_OTLP_ENDPOINT is not set; "
                    "skipping the OTLP metric exporter to avoid connection errors."
                )
            else:
                otlp_settings = {"endpoint": nautobot_config.OTEL_EXPORTER_OTLP_ENDPOINT}
                if nautobot_config.OTEL_EXPORTER_OTLP_PROTOCOL == "http":
                    from opentelemetry.exporter.otlp.proto.http.metric_exporter import OTLPMetricExporter
                else:
                    from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter

                    otlp_settings["insecure"] = nautobot_config.OTEL_EXPORTER_OTLP_INSECURE
                readers.append(PeriodicExportingMetricReader(OTLPMetricExporter(**otlp_settings)))
        if "console" in nautobot_config.OTEL_METRICS_EXPORTER:
            readers.append(PeriodicExportingMetricReader(ConsoleMetricExporter()))
        meter_provider = MeterProvider(resource=resource, metric_readers=readers)
        metrics.set_meter_provider(meter_provider)

    DjangoInstrumentor().instrument(tracer_provider=provider, is_sql_commentor_enabled=True)
    RequestsInstrumentor().instrument(tracer_provider=provider)
    RedisInstrumentor().instrument(tracer_provider=provider)
    CeleryInstrumentor().instrument(tracer_provider=provider)

    if nautobot_config.OTEL_PYTHON_LOG_CORRELATION:
        LoggingInstrumentor().instrument(tracer_provider=provider, set_logging_format=True)

    if "mysql" in nautobot_config.DATABASES["default"]["ENGINE"]:
        from opentelemetry.instrumentation.mysqlclient import MySQLClientInstrumentor

        MySQLClientInstrumentor().instrument(tracer_provider=provider, skip_dep_check=True, enable_commenter=True)
    else:
        from opentelemetry.instrumentation.psycopg2 import Psycopg2Instrumentor

        Psycopg2Instrumentor().instrument(tracer_provider=provider, skip_dep_check=True, enable_commenter=True)
