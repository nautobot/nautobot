from unittest.mock import patch

from django.urls import reverse
from opentelemetry import trace as otel_trace
from opentelemetry.instrumentation.celery import CeleryInstrumentor
from opentelemetry.instrumentation.django import DjangoInstrumentor
from opentelemetry.instrumentation.psycopg2 import Psycopg2Instrumentor
from opentelemetry.instrumentation.redis import RedisInstrumentor
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

from nautobot.core import testing
from nautobot.core.cli.opentelemetry import instrument


class InstrumentFunctionTest(testing.TestCase):
    """Verify that instrument() correctly sets up the global TracerProvider."""

    def setUp(self):
        super().setUp()
        self._original_provider = otel_trace.get_tracer_provider()
        DjangoInstrumentor().uninstrument()
        RedisInstrumentor().uninstrument()
        CeleryInstrumentor().uninstrument()
        Psycopg2Instrumentor().uninstrument()

    def tearDown(self):
        DjangoInstrumentor().uninstrument()
        RedisInstrumentor().uninstrument()
        CeleryInstrumentor().uninstrument()
        Psycopg2Instrumentor().uninstrument()
        otel_trace.set_tracer_provider(self._original_provider)
        super().tearDown()

    def test_instrument_sets_tracer_provider(self):
        """instrument() should configure a TracerProvider as the global provider."""
        with patch.multiple(
            "nautobot.core.cli.opentelemetry.settings",
            OTEL_TRACES_EXPORTER=["none"],
            OTEL_METRICS_EXPORTER=["none"],
            OTEL_PYTHON_LOG_CORRELATION=False,
        ):
            instrument()

        self.assertIsInstance(otel_trace.get_tracer_provider(), TracerProvider)


class APITraceGenerationTest(testing.APITestCase):
    """Verify that OpenTelemetry spans are generated when an API endpoint is called."""

    def setUp(self):
        super().setUp()
        self._exporter = InMemorySpanExporter()
        self._provider = TracerProvider()
        self._provider.add_span_processor(SimpleSpanProcessor(self._exporter))
        DjangoInstrumentor().uninstrument()
        DjangoInstrumentor().instrument(tracer_provider=self._provider)
        self.client.handler.load_middleware()

    def tearDown(self):
        DjangoInstrumentor().uninstrument()
        self.client.handler.load_middleware()
        super().tearDown()

    def test_api_request_generates_span(self):
        """A GET request to /api/status/ should produce at least one span with HTTP 200."""
        url = reverse("api-status")
        response = self.client.get(url, **self.header)
        self.assertEqual(response.status_code, 200)

        spans = self._exporter.get_finished_spans()
        self.assertGreater(len(spans), 0, "Expected at least one span to be exported")

        http_span = next(
            (s for s in spans if s.attributes.get("http.status_code") == 200),
            None,
        )
        if http_span is None:
            self.fail("Expected a span with http.status_code=200")
        # http.target (old semconv) or url.path (new semconv) or http.url (test client fallback:
        # the Django test client does not set RAW_URI/REQUEST_URI in the WSGI environ, so
        # the OTEL WSGI library sets http.url with the full URL instead of http.target)
        path = (
            http_span.attributes.get("http.target")
            or http_span.attributes.get("url.path")
            or http_span.attributes.get("http.url", "")
        )
        self.assertIn(url, path, "Expected span to contain the request path")
