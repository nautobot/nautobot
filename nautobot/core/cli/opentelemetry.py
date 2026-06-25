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
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter

from nautobot import __version__

# Read the settings module directly rather than django.conf.settings: instrument() runs before
# django.setup() (see the instrument() docstring for why), so django.conf.settings is not yet configured.
from nautobot.core import settings

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

    A consequence of running pre-``django.setup()`` is that ``django.conf.settings`` is not
    yet configured here, which is why this module reads ``nautobot.core.settings`` directly.
    """
    resource = Resource(attributes={SERVICE_NAME: "nautobot", SERVICE_VERSION: __version__})
    provider = TracerProvider(resource=resource)
    trace.set_tracer_provider(provider)

    if "none" not in settings.OTEL_TRACES_EXPORTER:
        if "console" in settings.OTEL_TRACES_EXPORTER:
            trace.get_tracer_provider().add_span_processor(BatchSpanProcessor(ConsoleSpanExporter()))

        if "otlp" in settings.OTEL_TRACES_EXPORTER:
            if not settings.OTEL_EXPORTER_OTLP_ENDPOINT:
                logger.warning(
                    "OTEL_TRACES_EXPORTER includes 'otlp' but OTEL_EXPORTER_OTLP_ENDPOINT is not set; "
                    "skipping the OTLP trace exporter to avoid connection errors."
                )
            else:
                otlp_settings = {"endpoint": settings.OTEL_EXPORTER_OTLP_ENDPOINT}
                if settings.OTEL_EXPORTER_OTLP_PROTOCOL == "http":
                    from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
                else:
                    from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter

                    otlp_settings["insecure"] = settings.OTEL_EXPORTER_OTLP_INSECURE
                trace.get_tracer_provider().add_span_processor(BatchSpanProcessor(OTLPSpanExporter(**otlp_settings)))

    if settings.OTEL_METRICS_EXPORTER and "none" not in settings.OTEL_METRICS_EXPORTER:
        readers = []
        if "otlp" in settings.OTEL_METRICS_EXPORTER:
            if not settings.OTEL_EXPORTER_OTLP_ENDPOINT:
                logger.warning(
                    "OTEL_METRICS_EXPORTER includes 'otlp' but OTEL_EXPORTER_OTLP_ENDPOINT is not set; "
                    "skipping the OTLP metric exporter to avoid connection errors."
                )
            else:
                otlp_settings = {"endpoint": settings.OTEL_EXPORTER_OTLP_ENDPOINT}
                if settings.OTEL_EXPORTER_OTLP_PROTOCOL == "http":
                    from opentelemetry.exporter.otlp.proto.http.metric_exporter import OTLPMetricExporter
                else:
                    from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter

                    otlp_settings["insecure"] = settings.OTEL_EXPORTER_OTLP_INSECURE
                readers.append(PeriodicExportingMetricReader(OTLPMetricExporter(**otlp_settings)))
        if "console" in settings.OTEL_METRICS_EXPORTER:
            readers.append(PeriodicExportingMetricReader(ConsoleMetricExporter()))
        meter_provider = MeterProvider(resource=resource, metric_readers=readers)
        metrics.set_meter_provider(meter_provider)

    DjangoInstrumentor().instrument(tracer_provider=provider, is_sql_commentor_enabled=True)
    RequestsInstrumentor().instrument(tracer_provider=provider)
    RedisInstrumentor().instrument(tracer_provider=provider)
    CeleryInstrumentor().instrument(tracer_provider=provider)

    if settings.OTEL_PYTHON_LOG_CORRELATION:
        LoggingInstrumentor().instrument(tracer_provider=provider, set_logging_format=True)

    if "mysql" in settings.DATABASES["default"]["ENGINE"]:
        from opentelemetry.instrumentation.mysqlclient import MySQLClientInstrumentor

        MySQLClientInstrumentor().instrument(tracer_provider=provider, skip_dep_check=True, enable_commenter=True)
    else:
        from opentelemetry.instrumentation.psycopg2 import Psycopg2Instrumentor

        Psycopg2Instrumentor().instrument(tracer_provider=provider, skip_dep_check=True, enable_commenter=True)
