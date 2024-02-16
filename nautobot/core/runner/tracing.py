"""Enable OTEL Tracing"""
from opentelemetry.sdk.resources import SERVICE_NAME, Resource, SERVICE_VERSION

from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.psycopg2 import Psycopg2Instrumentor
from opentelemetry.instrumentation.mysqlclient import MySQLClientInstrumentor
from opentelemetry.instrumentation.django import DjangoInstrumentor
from opentelemetry.instrumentation.redis import RedisInstrumentor
from opentelemetry.instrumentation.celery import CeleryInstrumentor
from opentelemetry.instrumentation.logging import LoggingInstrumentor

from opentelemetry import metrics
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader, ConsoleMetricExporter
from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter
from nautobot.core import settings
from nautobot import __version__


def request_hook(span, request):
    pass
    # print("TESTING request_hook")


def response_hook(span, request, response):
    pass
    # print("TESTING response_hook")


def log_hook(span, record):
    pass
    # print("LOG HOOK")


def instrument():
    """Instrument Nautobot."""
    # Service name is required for most backends,
    # and although it's not necessary for console export,
    # it's good to set service name anyways.
    resource = Resource(attributes={
        SERVICE_NAME: "nautobot",
        SERVICE_VERSION: __version__
    })
    provider = TracerProvider(resource=resource)
    trace.set_tracer_provider(provider)

    if "console" in settings.OTEL_TRACES_EXPORTER:
        trace.get_tracer_provider().add_span_processor(
            BatchSpanProcessor(
                ConsoleSpanExporter()
            )
        )

    if "otlp" in settings.OTEL_TRACES_EXPORTER:
        trace.get_tracer_provider().add_span_processor(
            BatchSpanProcessor(
                OTLPSpanExporter(
                    endpoint=settings.OTEL_EXPORTER_OTLP_ENDPOINT,
                    insecure=settings.OTEL_EXPORTER_OTLP_INSECURE
                )
            )
        )

    DjangoInstrumentor().instrument(tracer_provider=provider, is_sql_commentor_enabled=True, request_hook=request_hook, response_hook=response_hook)
    RedisInstrumentor().instrument(tracer_provider=provider)
    CeleryInstrumentor().instrument(tracer_provider=provider)
    LoggingInstrumentor(set_logging_format=True).instrument(tracer_provider=provider)
    if "mysql" in settings.DATABASES["default"]["ENGINE"]:
        MySQLClientInstrumentor().instrument(tracer_provider=provider, skip_dep_check=True, enable_commenter=True)
    else:
        Psycopg2Instrumentor().instrument(tracer_provider=provider, skip_dep_check=True, enable_commenter=True)
