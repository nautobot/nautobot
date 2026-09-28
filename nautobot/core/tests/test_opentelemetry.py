"""Tests for OpenTelemetry instrumentation in Nautobot."""

from contextlib import contextmanager
from copy import deepcopy
import json
import logging
import os
from types import SimpleNamespace
import unittest
from unittest.mock import MagicMock, patch

from django.conf import settings
from django.http.request import RawPostDataException
from django.test import override_settings, RequestFactory
from django.urls import reverse
from opentelemetry import trace as otel_trace
from opentelemetry.instrumentation.celery import CeleryInstrumentor
from opentelemetry.instrumentation.django import DjangoInstrumentor
from opentelemetry.instrumentation.psycopg2 import Psycopg2Instrumentor
from opentelemetry.instrumentation.redis import RedisInstrumentor
from opentelemetry.instrumentation.requests import RequestsInstrumentor
from opentelemetry.propagate import get_global_textmap, set_global_textmap
from opentelemetry.sdk.trace import SpanLimits, TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter
from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator
import requests
from silk.collector import DataCollector
from silk.middleware import SilkyMiddleware

from nautobot.core import settings as core_settings, testing
from nautobot.core.cli.opentelemetry import instrument
from nautobot.core.logging import OtelTraceContextFilter
from nautobot.core.middleware import GraphQLOpenTelemetryMiddleware
from nautobot.dcim.models import Location

try:
    import MySQLdb  # noqa: F401  # mysqlclient C-extension; only present on the MySQL CI job

    _MYSQLCLIENT_AVAILABLE = True
except ImportError:
    _MYSQLCLIENT_AVAILABLE = False


def _db_instrumentor_for_engine(engine):
    """Return the DB instrumentor class matching `engine`, mirroring `instrument()` in opentelemetry.py.

    Production selects the instrumentor with the same `"mysql" in engine` test, so tests read the live
    `settings.DATABASES` engine to instrument/uninstrument the backend the suite is actually running against
    (e.g. CI's dedicated MySQL job), rather than hardcoding Psycopg2.

    The mysqlclient instrumentor is imported lazily (only in the MySQL branch) because its package runs
    `import MySQLdb` at import time, which fails on Postgres CI jobs where mysqlclient is not installed.
    """
    if "mysql" in engine:
        from opentelemetry.instrumentation.mysqlclient import MySQLClientInstrumentor

        return MySQLClientInstrumentor
    return Psycopg2Instrumentor


def _fake_otel_config(**overrides):
    """Build a stand-in for the loaded `nautobot_config` module that `instrument()` reads.

    `instrument()` reads its config from `sys.modules["nautobot_config"]` (registered by
    `load_settings()`), not from `nautobot.core.settings`. Tests inject this fake via
    `patch.dict("sys.modules", {"nautobot_config": _fake_otel_config(...)})`, or pass it directly to
    `install_exporters(config=...)`. It carries every attribute both functions read, with real types:
    `DATABASES` is a real dict so the `"mysql" in ...["ENGINE"]` check works, and
    `OTEL_SPAN_ATTRIBUTE_VALUE_LENGTH_LIMIT` is an int (or `None` for unlimited, mirroring an empty
    env var). Defaults disable all noisy exporters/layers; pass `overrides` to drive a specific branch.
    """
    defaults = {
        "OTEL_TRACES_EXPORTER": ["none"],
        "OTEL_METRICS_EXPORTER": ["none"],
        "OTEL_EXPORTER_OTLP_ENDPOINT": "",
        "OTEL_EXPORTER_OTLP_PROTOCOL": "grpc",
        "OTEL_EXPORTER_OTLP_INSECURE": False,
        "OTEL_PYTHON_LOG_CORRELATION": False,
        "OTEL_SPAN_ATTRIBUTE_VALUE_LENGTH_LIMIT": 8192,
        "NAUTOBOT_OTEL_EXTRA_INSTRUMENTORS": [],
        # Default to the live DB engine so instrument() exercises the branch (psycopg2 vs mysqlclient)
        # matching the backend the suite is running against; tests pin a specific branch via a DATABASES override.
        "DATABASES": {"default": {"ENGINE": settings.DATABASES["default"]["ENGINE"]}},
    }
    defaults.update(overrides)
    return SimpleNamespace(**defaults)


class InstrumentFunctionTest(testing.TestCase):
    """Verify that instrument() correctly sets up the global TracerProvider."""

    def setUp(self):
        super().setUp()
        self._original_provider = otel_trace.get_tracer_provider()
        # Uninstrument the DB instrumentor matching the live engine, mirroring instrument()'s selection,
        # so cleanup is correct on both Postgres and MySQL runs (CI has a dedicated MySQL job).
        self._db_instrumentor_cls = _db_instrumentor_for_engine(settings.DATABASES["default"]["ENGINE"])
        DjangoInstrumentor().uninstrument()
        RedisInstrumentor().uninstrument()
        CeleryInstrumentor().uninstrument()
        self._db_instrumentor_cls().uninstrument()

    def tearDown(self):
        DjangoInstrumentor().uninstrument()
        RedisInstrumentor().uninstrument()
        CeleryInstrumentor().uninstrument()
        self._db_instrumentor_cls().uninstrument()
        otel_trace.set_tracer_provider(self._original_provider)
        super().tearDown()

    def test_instrument_sets_tracer_provider(self):
        """instrument() should configure a TracerProvider as the global provider."""
        # instrument() reads the loaded `nautobot_config` from sys.modules (registered by load_settings())
        # because it runs before django.setup(), so django.conf.settings is not configured and
        # override_settings() would have no effect here. Replace the whole sys.modules entry with a fake.
        with patch.dict("sys.modules", {"nautobot_config": _fake_otel_config()}):
            instrument()

        self.assertIsInstance(otel_trace.get_tracer_provider(), TracerProvider)

    def _provider_built_by_instrument(self, span_attr_limit):
        """Run instrument() with the given limit and return the TracerProvider it constructs.

        The global TracerProvider can only be set once per process (`set_tracer_provider` refuses to
        override an existing provider), so reading `get_tracer_provider()` after a second instrument()
        would return a stale provider. Instead, patch set_tracer_provider to capture the provider that
        instrument() actually builds.
        """
        captured = {}

        def _capture(provider):
            captured["provider"] = provider

        with patch.dict(
            "sys.modules",
            {"nautobot_config": _fake_otel_config(OTEL_SPAN_ATTRIBUTE_VALUE_LENGTH_LIMIT=span_attr_limit)},
        ):
            with patch(
                "nautobot.core.cli.opentelemetry.trace.set_tracer_provider",
                side_effect=_capture,
            ):
                instrument()
        return captured["provider"]

    def test_span_attribute_length_limit_applied(self):
        """instrument() should cap span attribute value length using OTEL_SPAN_ATTRIBUTE_VALUE_LENGTH_LIMIT."""
        provider = self._provider_built_by_instrument(8192)
        self.assertEqual(provider._span_limits.max_span_attribute_length, 8192)

    def test_span_attribute_length_limit_unlimited(self):
        """A None limit (empty env var) maps to SpanLimits.UNSET, leaving span attribute length unlimited."""
        provider = self._provider_built_by_instrument(None)
        self.assertIsNone(provider._span_limits.max_span_attribute_length)

    @unittest.skipUnless(_MYSQLCLIENT_AVAILABLE, "mysqlclient (MySQLdb) is not installed")
    def test_postgres_engine_instruments_psycopg2(self):
        """A PostgreSQL DATABASES engine must instrument psycopg2, not mysqlclient."""
        # instrument() imports these lazily inside the function, so patch them at their source modules.
        with patch("opentelemetry.instrumentation.psycopg2.Psycopg2Instrumentor") as mock_psycopg2:
            with patch("opentelemetry.instrumentation.mysqlclient.MySQLClientInstrumentor") as mock_mysql:
                with patch.dict(
                    "sys.modules",
                    {
                        "nautobot_config": _fake_otel_config(
                            DATABASES={"default": {"ENGINE": "django.db.backends.postgresql"}}
                        )
                    },
                ):
                    instrument()

        mock_psycopg2.return_value.instrument.assert_called_once()
        mock_mysql.return_value.instrument.assert_not_called()

    @unittest.skipUnless(_MYSQLCLIENT_AVAILABLE, "mysqlclient (MySQLdb) is not installed")
    def test_mysql_engine_instruments_mysqlclient(self):
        """A MySQL DATABASES engine must instrument mysqlclient, not psycopg2."""
        # instrument() imports these lazily inside the function, so patch them at their source modules.
        with patch("opentelemetry.instrumentation.psycopg2.Psycopg2Instrumentor") as mock_psycopg2:
            with patch("opentelemetry.instrumentation.mysqlclient.MySQLClientInstrumentor") as mock_mysql:
                with patch.dict(
                    "sys.modules",
                    {
                        "nautobot_config": _fake_otel_config(
                            DATABASES={"default": {"ENGINE": "django.db.backends.mysql"}}
                        )
                    },
                ):
                    instrument()

        mock_mysql.return_value.instrument.assert_called_once()
        mock_psycopg2.return_value.instrument.assert_not_called()

    def test_log_correlation_injects_context_without_clobbering_logging(self):
        """OTEL_PYTHON_LOG_CORRELATION=True must inject trace context, not override the logging format.

        set_logging_format=True would call logging.basicConfig() and attach a StreamHandler to the root
        logger; Nautobot's own loggers propagate to root, so that handler re-emits every record in a
        different format, producing duplicate, oddly-formatted log lines. instrument() must instead pass
        inject_trace_context=True, which adds the otel* attributes without touching handlers/format.
        """
        with patch("nautobot.core.cli.opentelemetry.LoggingInstrumentor") as mock_logging:
            with patch.dict(
                "sys.modules",
                {"nautobot_config": _fake_otel_config(OTEL_PYTHON_LOG_CORRELATION=True)},
            ):
                instrument()

        mock_logging.return_value.instrument.assert_called_once()
        _, kwargs = mock_logging.return_value.instrument.call_args
        self.assertTrue(kwargs.get("inject_trace_context"))
        # Guard against a regression back to the root-handler-clobbering behavior.
        self.assertNotIn("set_logging_format", kwargs)

    def test_log_correlation_disabled_skips_logging_instrumentor(self):
        """OTEL_PYTHON_LOG_CORRELATION=False must not instrument stdlib logging at all."""
        with patch("nautobot.core.cli.opentelemetry.LoggingInstrumentor") as mock_logging:
            with patch.dict(
                "sys.modules",
                {"nautobot_config": _fake_otel_config(OTEL_PYTHON_LOG_CORRELATION=False)},
            ):
                instrument()

        mock_logging.return_value.instrument.assert_not_called()


class OtelTraceContextFilterTest(testing.TestCase):
    """Verify OtelTraceContextFilter guarantees the otel* attributes so formatters never raise."""

    def _record(self):
        return logging.LogRecord("nautobot", logging.INFO, "f.py", 1, "hello", None, None)

    def test_missing_attributes_filled_with_sentinels(self):
        """A record lacking the otel* attributes gets the standard 'no active span' sentinels."""
        record = self._record()
        self.assertFalse(hasattr(record, "otelTraceID"))

        self.assertTrue(OtelTraceContextFilter().filter(record))

        # The filter sets these dynamically; pylint can't infer them on a bare LogRecord.
        self.assertEqual(record.otelTraceID, "0")
        self.assertEqual(record.otelSpanID, "0")
        self.assertFalse(record.otelTraceSampled)  # pylint: disable=no-member
        self.assertEqual(record.otelServiceName, "")  # pylint: disable=no-member

    def test_existing_attributes_preserved(self):
        """Real injected trace IDs must not be overwritten by the filter's defaults."""
        record = self._record()
        record.otelTraceID = "abc123"
        record.otelSpanID = "def456"

        OtelTraceContextFilter().filter(record)

        self.assertEqual(record.otelTraceID, "abc123")
        self.assertEqual(record.otelSpanID, "def456")

    def test_formatter_referencing_ids_survives_attr_less_record(self):
        """A formatter with %(otelTraceID)s must not raise on a record processed through the filter.

        Without the filter, logging.Formatter raises ValueError: 'Formatting field not found in record'
        for a record that predates instrumentation. The filter is what makes the default correlation
        formatters safe for such records.
        """
        formatter = logging.Formatter("[trace_id=%(otelTraceID)s span_id=%(otelSpanID)s] %(message)s")
        record = self._record()

        # Sanity: the unfiltered record would blow up the formatter.
        with self.assertRaises(ValueError):
            formatter.format(record)

        OtelTraceContextFilter().filter(record)
        self.assertEqual(formatter.format(record), "[trace_id=0 span_id=0] hello")


class DefaultLoggingCorrelationTest(testing.TestCase):
    """Verify the default LOGGING built in settings.py never bakes in the correlation suffix itself.

    The correlation suffix/filter used to be interpolated into LOGGING from env vars at settings-import
    time; that missed operators who set OTEL_PYTHON_* in nautobot_config.py (a Python assignment, not an
    env var). The decision now happens post-load in _preprocess_settings via enable_otel_log_correlation
    (covered by EnableOtelLogCorrelationTest). These tests reload nautobot.core.settings under patched
    env vars and confirm the *default* dict stays suffix-free regardless -- so the env var no longer
    short-circuits the post-load reconciliation.
    """

    def _reload_settings_logging(self, env):
        import importlib
        import sys

        settings_module = core_settings

        try:
            # settings.py takes a NullHandler LOGGING branch when TESTING (`"test" in sys.argv`), which
            # is always true under the test runner. Patch sys.argv so the reload builds the real
            # (non-TESTING) console LOGGING branch this test targets.
            with patch.dict(os.environ, env, clear=False), patch.object(sys, "argv", ["nautobot-server"]):
                logging_dict = importlib.reload(settings_module).LOGGING
        finally:
            # Always restore the module to the ambient test environment so later imports/tests see
            # normal settings, even if the reload under the patched env raised.
            importlib.reload(settings_module)
        return logging_dict

    def test_default_logging_never_bakes_in_suffix_even_with_env_on(self):
        """Even with tracing + correlation env vars on, settings.py must not pre-bake the suffix/filter.

        Regression guard for the env-var-driven bake-in being removed: surfacing the IDs is now the
        post-load helper's job, so the raw settings default stays plain regardless of the env vars.
        """
        logging_dict = self._reload_settings_logging(
            {"OTEL_PYTHON_DJANGO_INSTRUMENT": "True", "OTEL_PYTHON_LOG_CORRELATION": "True", "NAUTOBOT_DEBUG": "False"}
        )
        self.assertNotIn("otelTraceID", logging_dict["formatters"]["normal"]["format"])
        self.assertNotIn("otelTraceID", logging_dict["formatters"]["verbose"]["format"])
        # The filter is still defined (available for custom configs / the helper) but wired to nothing.
        self.assertIn("otel_trace_context", logging_dict["filters"])
        self.assertEqual(logging_dict["handlers"]["normal_console"]["filters"], [])
        self.assertEqual(logging_dict["handlers"]["verbose_console"]["filters"], [])

    def test_default_logging_plain_with_env_off(self):
        """With correlation off, the default LOGGING is likewise plain (unchanged behavior)."""
        logging_dict = self._reload_settings_logging(
            {"OTEL_PYTHON_DJANGO_INSTRUMENT": "False", "OTEL_PYTHON_LOG_CORRELATION": "True", "NAUTOBOT_DEBUG": "False"}
        )
        self.assertNotIn("otelTraceID", logging_dict["formatters"]["normal"]["format"])
        self.assertEqual(logging_dict["handlers"]["normal_console"]["filters"], [])


class InstrumentExporterBranchTest(testing.TestCase):
    """Verify install_exporters() wires up the correct exporters per OTEL_*_EXPORTER setting, including the empty-endpoint guard.

    Exporter creation lives in install_exporters(), NOT instrument(): the OTLP gRPC channel is
    fork-unsafe, so instrument() (which runs pre-fork) only sets up the provider + auto-instrumentors,
    and each worker builds its exporters post-fork via install_exporters(). These tests therefore drive
    install_exporters() directly with a fake config.
    """

    def setUp(self):
        super().setUp()
        self._original_provider = otel_trace.get_tracer_provider()
        # A real TracerProvider so add_span_processor() (called by install_exporters) has somewhere to go.
        otel_trace.set_tracer_provider(TracerProvider())
        # install_exporters() may call metrics.set_meter_provider(), which is set-once per process
        # (like set_tracer_provider) and so can't be captured/restored. Patch it out instead so a test
        # exercising the metrics branch can't leak a global meter provider into later tests.
        self._meter_provider_patcher = patch("nautobot.core.cli.opentelemetry.metrics.set_meter_provider")
        self._meter_provider_patcher.start()
        self._reset_exporters_guard()

    def tearDown(self):
        self._meter_provider_patcher.stop()
        otel_trace.set_tracer_provider(self._original_provider)
        self._reset_exporters_guard()
        super().tearDown()

    @staticmethod
    def _reset_exporters_guard():
        """Reset install_exporters()'s idempotency guard so each test starts clean."""
        import nautobot.core.cli.opentelemetry as otel_module

        otel_module._exporters_installed = False

    def _install(self, **overrides):
        """Call install_exporters() with a fake config carrying the requested OTEL_* overrides."""
        from nautobot.core.cli.opentelemetry import install_exporters

        self._reset_exporters_guard()
        install_exporters(config=_fake_otel_config(**overrides))

    def test_otlp_trace_exporter_skipped_when_endpoint_unset(self):
        """The OTLP trace exporter must be skipped (with a warning) when the endpoint is empty."""
        with patch("opentelemetry.exporter.otlp.proto.grpc.trace_exporter.OTLPSpanExporter") as mock_exporter:
            with self.assertLogs("nautobot.core.cli.opentelemetry", level="WARNING") as logs:
                self._install(OTEL_TRACES_EXPORTER=["otlp"], OTEL_EXPORTER_OTLP_ENDPOINT="")

        mock_exporter.assert_not_called()
        self.assertTrue(any("OTEL_EXPORTER_OTLP_ENDPOINT is not set" in message for message in logs.output))

    def test_otlp_metric_exporter_skipped_when_endpoint_unset(self):
        """The OTLP metric exporter must be skipped (with a warning) when the endpoint is empty."""
        with patch("opentelemetry.exporter.otlp.proto.grpc.metric_exporter.OTLPMetricExporter") as mock_exporter:
            with self.assertLogs("nautobot.core.cli.opentelemetry", level="WARNING") as logs:
                self._install(OTEL_METRICS_EXPORTER=["otlp"], OTEL_EXPORTER_OTLP_ENDPOINT="")

        mock_exporter.assert_not_called()
        self.assertTrue(any("OTEL_EXPORTER_OTLP_ENDPOINT is not set" in message for message in logs.output))

    def test_otlp_trace_exporter_created_when_endpoint_set(self):
        """The OTLP trace exporter must be constructed with the configured endpoint when it is set."""
        with patch("opentelemetry.exporter.otlp.proto.grpc.trace_exporter.OTLPSpanExporter") as mock_exporter:
            self._install(
                OTEL_TRACES_EXPORTER=["otlp"],
                OTEL_EXPORTER_OTLP_ENDPOINT="http://collector:4317",
                OTEL_EXPORTER_OTLP_INSECURE=True,
            )

        mock_exporter.assert_called_once_with(endpoint="http://collector:4317", insecure=True)

    def test_otlp_endpoint_override_from_config_is_honored(self):
        """An OTEL_EXPORTER_OTLP_ENDPOINT set only on the passed config must be honored (endpoint built)."""
        with patch("opentelemetry.exporter.otlp.proto.grpc.trace_exporter.OTLPSpanExporter") as mock_exporter:
            self._install(
                OTEL_TRACES_EXPORTER=["otlp"],
                OTEL_EXPORTER_OTLP_ENDPOINT="http://collector:4317",
            )

        mock_exporter.assert_called_once_with(endpoint="http://collector:4317", insecure=False)

    def test_console_trace_exporter_used_without_endpoint(self):
        """The console trace exporter does not require an endpoint and must be attached regardless."""
        with patch("nautobot.core.cli.opentelemetry.ConsoleSpanExporter") as mock_exporter:
            self._install(OTEL_TRACES_EXPORTER=["console"], OTEL_EXPORTER_OTLP_ENDPOINT="")

        mock_exporter.assert_called_once()

    def test_none_exporter_attaches_no_trace_processors(self):
        """When OTEL_TRACES_EXPORTER is 'none', neither OTLP nor console exporters are constructed."""
        with patch("nautobot.core.cli.opentelemetry.ConsoleSpanExporter") as mock_console:
            with patch("opentelemetry.exporter.otlp.proto.grpc.trace_exporter.OTLPSpanExporter") as mock_otlp:
                self._install(OTEL_TRACES_EXPORTER=["none"])

        mock_console.assert_not_called()
        mock_otlp.assert_not_called()

    def test_instrument_does_not_create_exporters_pre_fork(self):
        """Regression: instrument() must NOT construct any OTLP exporter (fork-unsafe pre-fork gRPC channel).

        The segfault root cause was building the OTLP gRPC channel in the uWSGI master before fork.
        instrument() now only installs the provider + auto-instrumentors; exporters come from
        install_exporters() post-fork. This asserts no exporter is created by instrument() even when
        an endpoint is configured.
        """
        for instrumentor in (DjangoInstrumentor, RedisInstrumentor, CeleryInstrumentor):
            instrumentor().uninstrument()
        try:
            with patch("opentelemetry.exporter.otlp.proto.grpc.trace_exporter.OTLPSpanExporter") as mock_span:
                with patch("opentelemetry.exporter.otlp.proto.grpc.metric_exporter.OTLPMetricExporter") as mock_metric:
                    with patch(
                        "nautobot.core.cli.opentelemetry.trace.set_tracer_provider"
                    ):  # don't clobber the global provider (set-once)
                        with patch.dict(
                            "sys.modules",
                            {
                                "nautobot_config": _fake_otel_config(
                                    OTEL_TRACES_EXPORTER=["otlp"],
                                    OTEL_METRICS_EXPORTER=["otlp"],
                                    OTEL_EXPORTER_OTLP_ENDPOINT="http://collector:4317",
                                )
                            },
                        ):
                            instrument()
            mock_span.assert_not_called()
            mock_metric.assert_not_called()
        finally:
            for instrumentor in (DjangoInstrumentor, RedisInstrumentor, CeleryInstrumentor):
                instrumentor().uninstrument()

    def test_install_exporters_is_idempotent(self):
        """install_exporters() must be a no-op after the first call (post-fork hooks may call it repeatedly)."""
        with patch("opentelemetry.exporter.otlp.proto.grpc.trace_exporter.OTLPSpanExporter") as mock_exporter:
            self._reset_exporters_guard()
            from nautobot.core.cli.opentelemetry import install_exporters

            config = _fake_otel_config(
                OTEL_TRACES_EXPORTER=["otlp"], OTEL_EXPORTER_OTLP_ENDPOINT="http://collector:4317"
            )
            install_exporters(config=config)
            install_exporters(config=config)
            install_exporters(config=config)

        mock_exporter.assert_called_once()

    def test_http_trace_exporter_used_for_http_protocol(self):
        """OTEL_EXPORTER_OTLP_PROTOCOL='http' selects the HTTP OTLPSpanExporter (not the gRPC one)."""
        with patch("opentelemetry.exporter.otlp.proto.http.trace_exporter.OTLPSpanExporter") as mock_exporter:
            self._install(
                OTEL_TRACES_EXPORTER=["otlp"],
                OTEL_EXPORTER_OTLP_PROTOCOL="http",
                OTEL_EXPORTER_OTLP_ENDPOINT="http://collector:4318",
            )

        mock_exporter.assert_called_once_with(endpoint="http://collector:4318")

    def test_otlp_metric_exporter_created_when_endpoint_set(self):
        """The OTLP metric exporter is constructed and a MeterProvider is installed when metrics are enabled."""
        with patch("opentelemetry.exporter.otlp.proto.grpc.metric_exporter.OTLPMetricExporter") as mock_exporter:
            with patch("nautobot.core.cli.opentelemetry.MeterProvider") as mock_meter_provider:
                self._install(
                    OTEL_METRICS_EXPORTER=["otlp"],
                    OTEL_EXPORTER_OTLP_ENDPOINT="http://collector:4317",
                    OTEL_EXPORTER_OTLP_INSECURE=True,
                )

        mock_exporter.assert_called_once_with(endpoint="http://collector:4317", insecure=True)
        mock_meter_provider.assert_called_once()

    def test_http_metric_exporter_used_for_http_protocol(self):
        """OTEL_EXPORTER_OTLP_PROTOCOL='http' selects the HTTP OTLPMetricExporter (not the gRPC one)."""
        with patch("opentelemetry.exporter.otlp.proto.http.metric_exporter.OTLPMetricExporter") as mock_exporter:
            self._install(
                OTEL_METRICS_EXPORTER=["otlp"],
                OTEL_EXPORTER_OTLP_PROTOCOL="http",
                OTEL_EXPORTER_OTLP_ENDPOINT="http://collector:4318",
            )

        mock_exporter.assert_called_once_with(endpoint="http://collector:4318")

    def test_console_metric_exporter_used_without_endpoint(self):
        """The console metric exporter needs no endpoint and installs a MeterProvider."""
        with patch("nautobot.core.cli.opentelemetry.ConsoleMetricExporter") as mock_exporter:
            with patch("nautobot.core.cli.opentelemetry.MeterProvider") as mock_meter_provider:
                self._install(OTEL_METRICS_EXPORTER=["console"], OTEL_EXPORTER_OTLP_ENDPOINT="")

        mock_exporter.assert_called_once()
        mock_meter_provider.assert_called_once()

    def test_install_exporters_uses_otel_config_when_config_arg_omitted(self):
        """install_exporters() with no config= falls back to _otel_config() (the post-fork/CLI resolver)."""
        from nautobot.core.cli import opentelemetry as otel_module

        fake = _fake_otel_config(OTEL_TRACES_EXPORTER=["otlp"], OTEL_EXPORTER_OTLP_ENDPOINT="http://collector:4317")
        with patch("opentelemetry.exporter.otlp.proto.grpc.trace_exporter.OTLPSpanExporter") as mock_exporter:
            with patch.object(otel_module, "_otel_config", return_value=fake) as mock_otel_config:
                self._reset_exporters_guard()
                otel_module.install_exporters()

        mock_otel_config.assert_called_once()
        mock_exporter.assert_called_once()

    def test_otel_config_prefers_configured_django_settings(self):
        """_otel_config() returns django settings when configured, else the loaded nautobot_config module."""
        from nautobot.core.cli import opentelemetry as otel_module

        # django.conf.settings is imported inside _otel_config(); it is already configured in the test
        # process, so the happy path returns it directly.
        self.assertIs(otel_module._otel_config(), settings)

        # Force the not-configured fallback: _otel_config() then imports the loaded nautobot_config module.
        fake_config = _fake_otel_config()
        with patch.object(type(settings), "configured", property(lambda self: False)):
            with patch.dict("sys.modules", {"nautobot_config": fake_config}):
                self.assertIs(otel_module._otel_config(), fake_config)


class CeleryExporterHookTest(testing.TestCase):
    """Verify the Celery signal handlers that install OTLP exporters per process.

    `instrument()` runs pre-fork and deliberately defers exporter creation because the OTLP gRPC
    channel is fork-unsafe. The Celery worker builds its exporters post-fork via the
    `worker_process_init` handler; the (non-forking) beat scheduler builds them in-process via the
    `beat_init` handler, because the CLI entrypoint cannot distinguish `celery beat` from
    `celery worker` and so skips in-process install for every `celery` subcommand. Both handlers must
    delegate to `install_exporters()` when OTel is enabled and be no-ops when it is disabled.
    """

    @override_settings(OTEL_PYTHON_DJANGO_INSTRUMENT=True)
    def test_worker_process_init_installs_exporters_when_enabled(self):
        """The worker_process_init handler must install exporters when OTel is enabled."""
        from nautobot.core.celery import install_otel_exporters

        with patch("nautobot.core.cli.opentelemetry.install_exporters") as mock_install:
            install_otel_exporters()

        mock_install.assert_called_once_with()

    @override_settings(OTEL_PYTHON_DJANGO_INSTRUMENT=True)
    def test_beat_init_installs_exporters_when_enabled(self):
        """The beat_init handler must install exporters when OTel is enabled.

        Regression: beat is launched as `celery beat`, which the CLI entrypoint sees only as `celery`
        and excludes from in-process exporter creation. Without this handler beat would run instrumented
        but export nothing.
        """
        from nautobot.core.celery import install_otel_exporters_beat

        with patch("nautobot.core.cli.opentelemetry.install_exporters") as mock_install:
            install_otel_exporters_beat()

        mock_install.assert_called_once_with()

    @override_settings(OTEL_PYTHON_DJANGO_INSTRUMENT=False)
    def test_beat_init_is_noop_when_disabled(self):
        """The beat_init handler must not create exporters when OTel is disabled (the default)."""
        from nautobot.core.celery import install_otel_exporters_beat

        with patch("nautobot.core.cli.opentelemetry.install_exporters") as mock_install:
            install_otel_exporters_beat()

        mock_install.assert_not_called()

    @override_settings(OTEL_PYTHON_DJANGO_INSTRUMENT=False)
    def test_worker_process_init_is_noop_when_disabled(self):
        """The worker_process_init handler must not create exporters when OTel is disabled (the default)."""
        from nautobot.core.celery import install_otel_exporters

        with patch("nautobot.core.cli.opentelemetry.install_exporters") as mock_install:
            install_otel_exporters()

        mock_install.assert_not_called()

    def test_beat_init_handler_is_connected_to_signal(self):
        """The beat_init handler must actually be wired to Celery's beat_init signal."""
        from celery import signals

        from nautobot.core.celery import install_otel_exporters_beat

        receivers = [ref() for _, ref in signals.beat_init.receivers]
        self.assertIn(install_otel_exporters_beat, receivers)


class APITraceGenerationTest(testing.APITestCase):
    """Verify that OpenTelemetry spans are generated when an API endpoint is called."""

    def setUp(self):
        super().setUp()
        self._exporter = InMemorySpanExporter()
        self._provider = TracerProvider()
        self._provider.add_span_processor(SimpleSpanProcessor(self._exporter))
        # DjangoInstrumentor.instrument() is a no-op when the OTEL_PYTHON_DJANGO_INSTRUMENT environment
        # variable is the string "False" (as it is in the default development environment). Force it on for
        # the duration of this test so instrumentation actually attaches regardless of the ambient value.
        self._env_patcher = patch.dict(os.environ, {"OTEL_PYTHON_DJANGO_INSTRUMENT": "True"})
        self._env_patcher.start()
        DjangoInstrumentor().uninstrument()
        DjangoInstrumentor().instrument(tracer_provider=self._provider)
        self.client.handler.load_middleware()

    def tearDown(self):
        DjangoInstrumentor().uninstrument()
        self.client.handler.load_middleware()
        self._env_patcher.stop()
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


@override_settings(ALLOW_REQUEST_PROFILING=True)
class OtelWithSilkProfilingTest(testing.APITestCase):
    """Guard against 5xx (e.g. 502) when OpenTelemetry and django-silk profiling are both active.

    `SilkyMiddleware` (outer) wraps the request/response streams while it profiles, the OTEL
    `DjangoInstrumentor` wraps the WSGI/view layer, and `GraphQLOpenTelemetryMiddleware` (inner)
    reads `request.body` on GraphQL POSTs. This combination is where a stream re-read or
    double-wrapping could surface as a gateway 502 at the middleware layer.

    SCOPE / LIMITATION: this runs through the Django test client, which is single-process and in-memory
    -- there is NO os.fork() and NO OTLP gRPC channel. It therefore CANNOT reproduce the separate,
    more severe production crash where OTLP-gRPC + uWSGI pre-fork + silk profiling segfaults workers
    (SIGSEGV) because the fork-unsafe gRPC channel is built in the master pre-fork. A green result here
    must NOT be read as "OTEL + Silk is safe under uWSGI." That fork/gRPC path is fixed by building the
    OTLP exporters post-fork (see `nautobot.core.cli.opentelemetry.install_exporters` + `InstrumentExporterBranchTest`),
    not by this unit test.
    """

    def setUp(self):
        super().setUp()
        # SilkyMiddleware.process_request stashes a request model in the thread-local DataCollector,
        # and only the *next* request through the middleware clears it. Reset it after each test.
        self.addCleanup(DataCollector().clear)
        self._exporter = InMemorySpanExporter()
        self._provider = TracerProvider()
        self._provider.add_span_processor(SimpleSpanProcessor(self._exporter))
        # DjangoInstrumentor.instrument() is a no-op while OTEL_PYTHON_DJANGO_INSTRUMENT == "False"
        # (the dev/test default). Force it on and attach our in-memory provider, mirroring
        # APITraceGenerationTest, then rebuild the middleware stack so instrumentation attaches.
        self._env_patcher = patch.dict(os.environ, {"OTEL_PYTHON_DJANGO_INSTRUMENT": "True"})
        self._env_patcher.start()
        self._settings_override = override_settings(OTEL_PYTHON_DJANGO_INSTRUMENT=True)
        self._settings_override.enable()
        DjangoInstrumentor().uninstrument()
        DjangoInstrumentor().instrument(tracer_provider=self._provider)
        self.client.handler.load_middleware()
        # GraphQLOpenTelemetryMiddleware reads the process-global tracer provider (set once at
        # startup), which our in-memory exporter is not attached to. Patch the middleware's `trace`
        # so its GraphQL span is routed to our exporter, letting us assert it stays active (and that
        # enduser.id resolves to the token user) alongside Silk. Mirrors GraphQLOpenTelemetryMiddlewareTest.
        self._trace_patcher = patch("nautobot.core.middleware.trace")
        mock_trace = self._trace_patcher.start()
        mock_trace.get_tracer.return_value = self._provider.get_tracer("nautobot.graphql")

    def tearDown(self):
        self._trace_patcher.stop()
        DjangoInstrumentor().uninstrument()
        self.client.handler.load_middleware()
        self._settings_override.disable()
        self._env_patcher.stop()
        super().tearDown()

    @contextmanager
    def _silk_profiling_enabled(self):
        """Profile requests made in this block with Silk, and assert that Silk did intercept exactly one.

        Nautobot's `SILKY_INTERCEPT_FUNC` profiles a request only when `silk_record_requests` is set on the
        session, so enable it there rather than tampering with the process-wide `SilkyConfig` singleton.
        """
        session = self.client.session
        session["silk_record_requests"] = True
        session.save()
        original_process_response = SilkyMiddleware.process_response
        intercepted = []

        def spy(middleware, request, response):
            intercepted.append(getattr(request, "silk_is_intercepted", False))
            # Delegate to the real implementation: it is what reads the response stream
            # (ResponseModelFactory) and finalizes the profiler, i.e. the response half of the
            # OTEL + Silk interaction that this test class exists to guard.
            return original_process_response(middleware, request, response)

        # autospec so the mock receives the middleware instance and can pass it on to the original method.
        with patch.object(SilkyMiddleware, "process_response", autospec=True, side_effect=spy):
            yield
        self.assertEqual(intercepted, [True], "Expected Silk to intercept exactly one request.")

    def test_graphql_post_with_otel_and_silk_returns_200(self):
        """A token-authenticated GraphQL POST must succeed (not 5xx) with OTEL + Silk both active."""
        self.add_permissions("dcim.view_location")
        url = reverse("graphql-api")
        with self._silk_profiling_enabled():
            response = self.client.post(
                url,
                data=json.dumps({"query": "query GetLocations { locations { id name } }"}),
                content_type="application/json",
                **self.header,
            )
        self.assertLess(
            response.status_code,
            500,
            f"OTEL + Silk profiling produced a server error ({response.status_code}) on a GraphQL POST: "
            f"{getattr(response, 'content', b'')!r}",
        )
        self.assertEqual(response.status_code, 200)

        # OTEL must genuinely still be active alongside Silk (otherwise a 200 would prove nothing).
        spans = self._exporter.get_finished_spans()
        self.assertGreater(len(spans), 0, "Expected at least one span; OTEL should stay active with Silk on.")

        # The GraphQL middleware span must attribute the request to the token user, not "anonymous"
        # (DRF resolves the user during view dispatch, after middleware; the span reads it post-response).
        graphql_spans = [s for s in spans if s.attributes.get("graphql.document")]
        self.assertTrue(graphql_spans, "Expected a GraphQL span carrying graphql.document.")
        self.assertEqual(graphql_spans[0].attributes.get("enduser.id"), self.user.username)

    def test_non_graphql_request_with_otel_and_silk_returns_200(self):
        """A non-GraphQL API request must also succeed with OTEL + Silk both active (control case)."""
        with self._silk_profiling_enabled():
            response = self.client.get(reverse("api-status"), **self.header)
        self.assertLess(response.status_code, 500, "OTEL + Silk profiling produced a server error on /api/status/.")
        self.assertEqual(response.status_code, 200)

    def test_silk_profiling_state_is_resettable(self):
        """Regression guard: Silk's thread-local state must not leak out of this test class.

        `SilkyMiddleware` leaves the recorded request (and a running cProfile profiler) in the `DataCollector`
        until the *next* request it handles, and a leaked request makes silk's `execute_sql` wrapper add an
        EXPLAIN to every subsequent query -- breaking `assertNumQueries` in unrelated tests. `setUp` registers
        the reset performed here as a cleanup for every test in this class.
        """
        with self._silk_profiling_enabled():
            response = self.client.get(reverse("api-status"), **self.header)
        self.assertEqual(response.status_code, 200)
        self.assertIsNotNone(DataCollector().request, "Expected Silk to have recorded this request.")

        DataCollector().clear()

        self.assertIsNone(DataCollector().request)
        self.assertIsNone(getattr(DataCollector().local, "pythonprofiler", None))
        # An ordinary query must no longer be intercepted by silk, which would add an EXPLAIN alongside it.
        with self.assertNumQueries(1):
            list(Location.objects.all()[:1])


class RequestsInstrumentationTraceparentTest(testing.TestCase):
    """Verify that OpenTelemetry Requests instrumentation injects the traceparent header into outgoing HTTP requests."""

    def setUp(self):
        super().setUp()
        # Uninstrument first in case requests was already instrumented during app startup
        RequestsInstrumentor().uninstrument()
        # Set up an isolated in-memory tracer provider
        self._exporter = InMemorySpanExporter()
        self._provider = TracerProvider()
        self._provider.add_span_processor(SimpleSpanProcessor(self._exporter))
        # Swap in the test provider and W3C TraceContext propagator
        self._original_provider = otel_trace.get_tracer_provider()
        self._original_propagator = get_global_textmap()
        otel_trace.set_tracer_provider(self._provider)
        set_global_textmap(TraceContextTextMapPropagator())
        # Instrument requests with the test tracer provider
        self._instrumentor = RequestsInstrumentor()
        self._instrumentor.instrument(tracer_provider=self._provider)

    def tearDown(self):
        self._instrumentor.uninstrument()
        otel_trace.set_tracer_provider(self._original_provider)
        set_global_textmap(self._original_propagator)
        super().tearDown()

    def test_traceparent_header_injected_in_outgoing_requests(self):
        """Outgoing HTTP requests made within an active span must include the W3C traceparent header.

        RequestsInstrumentor wraps requests.Session.send and uses the active propagator to inject
        trace context into the PreparedRequest headers before the request hits the network.
        Patching at the HTTPAdapter level lets the instrumentation wrapper run in full while
        still capturing the headers that would have been sent on the wire.
        """
        captured_headers = {}

        def mock_adapter_send(self_adapter, request, **kwargs):
            captured_headers.update(request.headers)
            response = MagicMock()
            response.status_code = 200
            response.headers = {}
            response.history = []
            response.is_redirect = False
            response.content = b""
            return response

        tracer = self._provider.get_tracer(__name__)

        with patch("requests.adapters.HTTPAdapter.send", mock_adapter_send):
            with tracer.start_as_current_span("test-parent-span"):  # pylint: disable=not-context-manager
                requests.get("https://example.com/api/test", timeout=5)

        self.assertIn(
            "traceparent",
            captured_headers,
            "The traceparent header was not injected into the outgoing HTTP request.",
        )

        # Validate the W3C Trace Context format: version-traceid-parentid-flags
        traceparent = captured_headers["traceparent"]
        parts = traceparent.split("-")
        self.assertEqual(
            len(parts),
            4,
            f"traceparent header has unexpected format (expected version-traceid-parentid-flags): {traceparent!r}",
        )
        self.assertEqual(parts[0], "00", f"traceparent version should be '00', got: {parts[0]!r}")
        self.assertEqual(
            len(parts[1]),
            32,
            f"traceparent trace-id should be 32 lowercase hex chars, got: {parts[1]!r}",
        )
        self.assertEqual(
            len(parts[2]),
            16,
            f"traceparent parent-id should be 16 lowercase hex chars, got: {parts[2]!r}",
        )


@override_settings(OTEL_PYTHON_DJANGO_INSTRUMENT=True)
class GraphQLOpenTelemetryMiddlewareTest(testing.TestCase):
    """Verify GraphQLOpenTelemetryMiddleware emits correct OTel spans and structured log entries."""

    _SAMPLE_QUERY = "query GetLocations { locations { id name } }"
    _SAMPLE_VARIABLES = {"limit": 10}

    def setUp(self):
        super().setUp()
        self._exporter = InMemorySpanExporter()
        self._provider = TracerProvider()
        self._provider.add_span_processor(SimpleSpanProcessor(self._exporter))
        # The global TracerProvider can only be set once (it is set at startup via instrument()),
        # so patch nautobot.core.middleware.trace directly to route spans to our in-memory exporter.
        self._trace_patcher = patch("nautobot.core.middleware.trace")
        self._mock_trace = self._trace_patcher.start()
        self._mock_trace.get_tracer.return_value = self._provider.get_tracer("nautobot.graphql")

    def tearDown(self):
        self._trace_patcher.stop()
        super().tearDown()

    def _make_middleware(self, status_code=200):
        mock_response = MagicMock()
        mock_response.status_code = status_code
        return GraphQLOpenTelemetryMiddleware(MagicMock(return_value=mock_response))

    def _build_request(self, path="/api/graphql", query=None, variables=None, xff="203.0.113.5, 10.0.0.1"):
        """Return a POST WSGIRequest pre-populated with a JSON GraphQL body."""
        if query is None:
            query = self._SAMPLE_QUERY
        body = {"query": query}
        if variables is not None:
            body["variables"] = variables
        request = RequestFactory().post(path, data=json.dumps(body), content_type="application/json")
        request.user = self.user
        if xff:
            request.META["HTTP_X_FORWARDED_FOR"] = xff
        return request

    def test_span_created_with_correct_attributes(self):
        """A GraphQL request must produce a span named after the operation type with all expected attributes."""
        middleware = self._make_middleware(status_code=200)
        request = self._build_request(variables=self._SAMPLE_VARIABLES, xff="203.0.113.5, 10.0.0.1")

        middleware(request)

        spans = self._exporter.get_finished_spans()
        self.assertEqual(len(spans), 1, "Expected exactly one span to be emitted for a GraphQL request.")
        span = spans[0]

        self.assertEqual(span.name, "graphql query")

        attrs = span.attributes
        self.assertEqual(attrs.get("enduser.id"), self.user.username)
        self.assertEqual(attrs.get("http.client_ip"), "203.0.113.5", "Should use the leftmost X-Forwarded-For entry.")
        self.assertEqual(attrs.get("graphql.document"), self._SAMPLE_QUERY)
        self.assertEqual(attrs.get("graphql.variables"), json.dumps(self._SAMPLE_VARIABLES))
        self.assertEqual(attrs.get("graphql.operation.type"), "query")
        self.assertEqual(attrs.get("http.status_code"), 200)

    def test_operation_type_detected_past_leading_comment(self):
        """A leading GraphQL # comment (and blank lines) must not defeat operation-type detection.

        Regression: the detector previously matched the operation keyword only after leading
        whitespace, so a document beginning with a `# ...` comment line produced operation_type=None,
        degrading the span name to bare "graphql" and dropping the operation.type attribute.
        """
        commented_query = "# fetch all locations\n\nquery GetLocations { locations { id name } }"
        middleware = self._make_middleware(status_code=200)
        request = self._build_request(query=commented_query)

        middleware(request)

        spans = self._exporter.get_finished_spans()
        self.assertEqual(len(spans), 1)
        span = spans[0]
        self.assertEqual(span.name, "graphql query", "Span name should reflect the detected operation type.")
        self.assertEqual(span.attributes.get("graphql.operation.type"), "query")

    def test_long_document_truncated_by_span_limits(self):
        """A large graphql.document is truncated by OTEL_SPAN_ATTRIBUTE_VALUE_LENGTH_LIMIT.

        The middleware itself does not truncate; it relies on the standard OTel span attribute value
        length limit, which the production TracerProvider picks up from the environment. Here we build a
        provider with an explicit limit to confirm our graphql document attribute is subject to it.
        """
        limit = 64
        limited_provider = TracerProvider(span_limits=SpanLimits(max_span_attribute_length=limit))
        limited_provider.add_span_processor(SimpleSpanProcessor(self._exporter))
        self._mock_trace.get_tracer.return_value = limited_provider.get_tracer("nautobot.graphql")

        long_query = "query Big { roles { " + ("name " * 200) + "} }"
        middleware = self._make_middleware(status_code=200)
        request = self._build_request(query=long_query)

        middleware(request)

        spans = self._exporter.get_finished_spans()
        self.assertEqual(len(spans), 1)
        document = spans[0].attributes.get("graphql.document")
        self.assertEqual(len(document), limit, "graphql document should be truncated to the span attribute limit.")
        self.assertEqual(document, long_query[:limit])

    def test_log_emitted_with_correct_fields(self):
        """The INFO log for a GraphQL request must include username, IP, query, variables, status, and duration."""
        middleware = self._make_middleware(status_code=200)
        request = self._build_request(variables=self._SAMPLE_VARIABLES, xff="203.0.113.5")

        with self.assertLogs("nautobot.core.middleware", level="INFO") as captured:
            middleware(request)

        graphql_records = [r for r in captured.records if r.getMessage() == "graphql.request"]
        self.assertEqual(
            len(graphql_records), 1, f"Expected exactly one graphql.request log entry; got: {captured.records!r}"
        )
        record = graphql_records[0]

        self.assertEqual(record.levelname, "INFO")
        self.assertEqual(record.username, self.user.username)
        self.assertEqual(record.client_ip, "203.0.113.5")
        self.assertEqual(record.query, self._SAMPLE_QUERY)
        self.assertEqual(record.variables, self._SAMPLE_VARIABLES)
        self.assertEqual(record.http_status, 200)
        self.assertTrue(hasattr(record, "duration_ms"), "duration_ms must be present in the log entry.")
        self.assertIsInstance(record.duration_ms, float)
        self.assertGreaterEqual(record.duration_ms, 0.0)

    @override_settings(OTEL_PYTHON_DJANGO_INSTRUMENT=False)
    def test_disabled_emits_no_span_or_log(self):
        """Regression: with OTel disabled (the default), a GraphQL request must produce no span and no log.

        GraphQLOpenTelemetryMiddleware is unconditionally present in MIDDLEWARE, so without an enablement
        guard it would span and log every /graphql request -- leaking the query/variables into INFO logs in
        deployments that never enabled OTel. This asserts the opt-in guard: no span, no graphql.request log,
        and the response still passes through. Removing the guard makes this test fail.
        """
        mock_response = MagicMock(status_code=200)
        middleware = GraphQLOpenTelemetryMiddleware(MagicMock(return_value=mock_response))
        request = self._build_request(variables=self._SAMPLE_VARIABLES)

        with self.assertNoLogs("nautobot.core.middleware", level="INFO"):
            response = middleware(request)

        self.assertIs(response, mock_response, "Response must still pass through when OTel is disabled.")
        self.assertEqual(
            len(self._exporter.get_finished_spans()), 0, "No span should be emitted when OTel is disabled."
        )

    # --- _parse_graphql_body edge cases (called directly; no span needed) ---

    def test_parse_body_non_post_returns_none(self):
        """A non-POST request yields no query/variables (GraphQL bodies only ride on POST)."""
        request = RequestFactory().get("/api/graphql")
        self.assertEqual(GraphQLOpenTelemetryMiddleware._parse_graphql_body(request), (None, None))

    def test_parse_body_malformed_json_returns_none(self):
        """A POST with `application/json` content type but invalid JSON yields no query/variables."""
        request = RequestFactory().post("/api/graphql", data="{not valid json", content_type="application/json")
        self.assertEqual(GraphQLOpenTelemetryMiddleware._parse_graphql_body(request), (None, None))

    def test_parse_body_application_graphql_content_type(self):
        """A POST with `application/graphql` returns the raw body as the document and no variables."""
        query = "query Ping { __typename }"
        request = RequestFactory().post("/api/graphql", data=query, content_type="application/graphql")
        self.assertEqual(GraphQLOpenTelemetryMiddleware._parse_graphql_body(request), (query, None))

    def test_parse_body_application_graphql_invalid_utf8_returns_none(self):
        """An `application/graphql` body that is not valid UTF-8 yields no query/variables."""
        request = RequestFactory().post("/api/graphql", data=b"\xff\xfe", content_type="application/graphql")
        self.assertEqual(GraphQLOpenTelemetryMiddleware._parse_graphql_body(request), (None, None))

    def test_parse_body_unknown_content_type_returns_none(self):
        """A POST with a content type that is neither json nor graphql yields no query/variables."""
        request = RequestFactory().post("/api/graphql", data="anything", content_type="text/plain")
        self.assertEqual(GraphQLOpenTelemetryMiddleware._parse_graphql_body(request), (None, None))

    def test_parse_body_unreadable_body_returns_none(self):
        """If reading `request.body` raises (e.g. the stream was already consumed), yield no query/variables."""

        class _BodyRaisesRequest:
            method = "POST"
            content_type = "application/json"

            @property
            def body(self):
                raise RawPostDataException("You cannot access body after reading from request's data stream")

        self.assertEqual(GraphQLOpenTelemetryMiddleware._parse_graphql_body(_BodyRaisesRequest()), (None, None))

    # --- _get_operation_type edge cases ---

    def test_operation_type_empty_query_returns_none(self):
        """An empty or None query has no detectable operation type."""
        self.assertIsNone(GraphQLOpenTelemetryMiddleware._get_operation_type(""))
        self.assertIsNone(GraphQLOpenTelemetryMiddleware._get_operation_type(None))

    def test_operation_type_comment_only_document_returns_none(self):
        """A document with only comment/blank lines (no operation keyword) has no operation type."""
        self.assertIsNone(GraphQLOpenTelemetryMiddleware._get_operation_type("# just a comment\n\n"))


class MainInstrumentGatingTest(testing.TestCase):
    """Verify main() decides whether to call instrument() from the loaded nautobot_config, not nautobot.core.settings.

    Regression coverage for the case where OTEL_PYTHON_DJANGO_INSTRUMENT is enabled via a nautobot_config.py
    override (not the OTEL_PYTHON_DJANGO_INSTRUMENT environment variable). Reading the flag from
    nautobot.core.settings missed such overrides because that base module only reflects the env-var default;
    main() now reads it from the loaded config module in sys.modules["nautobot_config"].
    """

    def _run_main(self, *, config_instrument):
        """Drive main() up to the instrument() gate with a fake loaded config and stubbed Django hand-off.

        Args:
            config_instrument: Value of OTEL_PYTHON_DJANGO_INSTRUMENT on the loaded nautobot_config module.

        Returns:
            The MagicMock standing in for nautobot.core.cli.opentelemetry.instrument.
        """
        fake_settings = MagicMock()
        fake_settings.OTEL_PYTHON_DJANGO_INSTRUMENT = config_instrument

        with (
            patch("nautobot.core.cli.load_settings") as mock_load_settings,
            patch.dict("sys.modules", {"nautobot_config": fake_settings}),
            patch("nautobot.core.cli.opentelemetry.instrument") as mock_instrument,
            patch("nautobot.core.cli.execute_from_command_line"),
            patch("sys.argv", ["nautobot-server", "migrate"]),
        ):
            from nautobot.core.cli import main

            main()

        mock_load_settings.assert_called_once()
        return mock_instrument

    def test_instrument_called_when_config_enables_it(self):
        """instrument() runs when the loaded nautobot_config sets OTEL_PYTHON_DJANGO_INSTRUMENT True."""
        mock_instrument = self._run_main(config_instrument=True)
        mock_instrument.assert_called_once()

    def test_instrument_not_called_when_config_disables_it(self):
        """instrument() is skipped when the loaded nautobot_config sets OTEL_PYTHON_DJANGO_INSTRUMENT False."""
        mock_instrument = self._run_main(config_instrument=False)
        mock_instrument.assert_not_called()


class MainForkingCommandGatingTest(testing.TestCase):
    """Verify main() only installs OTLP exporters in-process for non-forking commands.

    instrument() defers exporter creation because the OTLP gRPC channel is fork-unsafe; the forking
    servers (`start` uWSGI, `celery` worker/beat) build their exporters per process AFTER fork via
    their own hooks. main() installs them in-process only for single-process commands.

    Regression: the command used to be identified as the first non-option token, so a value-bearing
    option preceding it (e.g. `--verbosity 2 start`) was misread as the command, wrongly installing the
    fork-unsafe exporter in the pre-fork parent. The check now skips whenever a forking command appears
    anywhere in the args, which is robust against argument ordering.
    """

    def _install_exporters_called_for_argv(self, argv):
        """Drive main() with the given argv and return whether install_exporters() was called."""
        fake_settings = MagicMock()
        fake_settings.OTEL_PYTHON_DJANGO_INSTRUMENT = True

        with (
            patch("nautobot.core.cli.load_settings"),
            patch.dict("sys.modules", {"nautobot_config": fake_settings}),
            patch("nautobot.core.cli.opentelemetry.instrument"),
            patch("nautobot.core.cli.opentelemetry.install_exporters") as mock_install_exporters,
            patch("nautobot.core.cli.execute_from_command_line"),
            patch("sys.argv", argv),
        ):
            from nautobot.core.cli import main

            main()

        return mock_install_exporters.called

    def test_single_process_command_installs_in_process(self):
        """A single-process command (migrate) installs the exporters in-process."""
        self.assertTrue(self._install_exporters_called_for_argv(["nautobot-server", "migrate"]))

    def test_runserver_installs_in_process(self):
        """runserver is single-process and installs the exporters in-process."""
        self.assertTrue(self._install_exporters_called_for_argv(["nautobot-server", "runserver"]))

    def test_start_skips_in_process_install(self):
        """`start` (uWSGI, forking) must not install exporters pre-fork."""
        self.assertFalse(self._install_exporters_called_for_argv(["nautobot-server", "start", "--ini", "x"]))

    def test_celery_worker_skips_in_process_install(self):
        """`celery worker` (forking) must not install exporters pre-fork."""
        self.assertFalse(self._install_exporters_called_for_argv(["nautobot-server", "celery", "worker"]))

    def test_start_with_preceding_value_option_still_skips(self):
        """Regression: a value-bearing option before `start` must not defeat the forking-command skip."""
        self.assertFalse(
            self._install_exporters_called_for_argv(["nautobot-server", "--verbosity", "2", "start"]),
            "A leading `--verbosity 2` must not cause install_exporters() to run pre-fork for `start`.",
        )

    def test_celery_with_preceding_value_option_still_skips(self):
        """Regression: a value-bearing option before `celery` must not defeat the forking-command skip."""
        self.assertFalse(
            self._install_exporters_called_for_argv(["nautobot-server", "--pythonpath", "/opt", "celery", "beat"]),
        )


class ExtraInstrumentorsTest(testing.TestCase):
    """Verify instrument() installs the instrumentors listed in NAUTOBOT_OTEL_EXTRA_INSTRUMENTORS."""

    def setUp(self):
        super().setUp()
        self._original_provider = otel_trace.get_tracer_provider()
        # Include the DB instrumentor matching the live engine (psycopg2 vs mysqlclient), mirroring instrument().
        self._db_instrumentor_cls = _db_instrumentor_for_engine(settings.DATABASES["default"]["ENGINE"])
        for instrumentor in (DjangoInstrumentor, RedisInstrumentor, CeleryInstrumentor, self._db_instrumentor_cls):
            instrumentor().uninstrument()

    def tearDown(self):
        for instrumentor in (DjangoInstrumentor, RedisInstrumentor, CeleryInstrumentor, self._db_instrumentor_cls):
            instrumentor().uninstrument()
        otel_trace.set_tracer_provider(self._original_provider)
        super().tearDown()

    @staticmethod
    def _fake_instrumentor_module(instrumentor_instance):
        """Return a fake module exposing a FakeInstrumentor class that returns the given instance."""
        instrumentor_cls = MagicMock(return_value=instrumentor_instance)
        return SimpleNamespace(FakeInstrumentor=instrumentor_cls), instrumentor_cls

    def test_listed_instrumentor_is_installed_with_provider(self):
        """A valid dotted path has its instrumentor's .instrument() called once with the core provider."""
        instance = MagicMock()
        instance.is_instrumented_by_opentelemetry = False
        fake_module, instrumentor_cls = self._fake_instrumentor_module(instance)

        with patch.dict("sys.modules", {"fake_otel_pkg": fake_module}):
            with patch.dict(
                "sys.modules",
                {
                    "nautobot_config": _fake_otel_config(
                        NAUTOBOT_OTEL_EXTRA_INSTRUMENTORS=["fake_otel_pkg.FakeInstrumentor"]
                    )
                },
            ):
                instrument()

        instrumentor_cls.assert_called_once()
        instance.instrument.assert_called_once()
        _, kwargs = instance.instrument.call_args
        self.assertIsInstance(kwargs["tracer_provider"], TracerProvider)

    def test_already_instrumented_is_skipped(self):
        """When is_instrumented_by_opentelemetry is True, .instrument() is not called again."""
        instance = MagicMock()
        instance.is_instrumented_by_opentelemetry = True
        fake_module, _ = self._fake_instrumentor_module(instance)

        with patch.dict("sys.modules", {"fake_otel_pkg": fake_module}):
            with patch.dict(
                "sys.modules",
                {
                    "nautobot_config": _fake_otel_config(
                        NAUTOBOT_OTEL_EXTRA_INSTRUMENTORS=["fake_otel_pkg.FakeInstrumentor"]
                    )
                },
            ):
                instrument()

        instance.instrument.assert_not_called()

    def test_bad_import_path_warns_and_does_not_raise(self):
        """A path whose module/class cannot be imported logs a warning and does not abort instrument()."""
        with patch.dict(
            "sys.modules",
            {
                "nautobot_config": _fake_otel_config(
                    NAUTOBOT_OTEL_EXTRA_INSTRUMENTORS=["nonexistent.module.DoesNotExist"]
                )
            },
        ):
            with self.assertLogs("nautobot.core.cli.opentelemetry", level="WARNING") as logs:
                instrument()  # must not raise

        self.assertTrue(
            any("nonexistent.module.DoesNotExist" in message for message in logs.output),
            f"Expected a warning naming the bad path; got: {logs.output!r}",
        )

    def test_instrument_error_warns_and_does_not_raise(self):
        """If an instrumentor's .instrument() raises, it is logged and the rest of startup continues."""
        instance = MagicMock()
        instance.is_instrumented_by_opentelemetry = False
        instance.instrument.side_effect = RuntimeError("boom")
        fake_module, _ = self._fake_instrumentor_module(instance)

        with patch.dict("sys.modules", {"fake_otel_pkg": fake_module}):
            with patch.dict(
                "sys.modules",
                {
                    "nautobot_config": _fake_otel_config(
                        NAUTOBOT_OTEL_EXTRA_INSTRUMENTORS=["fake_otel_pkg.FakeInstrumentor"]
                    )
                },
            ):
                with self.assertLogs("nautobot.core.cli.opentelemetry", level="WARNING") as logs:
                    instrument()  # must not raise

        self.assertTrue(
            any("fake_otel_pkg.FakeInstrumentor" in message for message in logs.output),
            f"Expected a warning naming the failing instrumentor; got: {logs.output!r}",
        )

    def test_empty_setting_is_noop(self):
        """With no extra instrumentors configured, instrument() completes and sets a provider."""
        with patch.dict("sys.modules", {"nautobot_config": _fake_otel_config(NAUTOBOT_OTEL_EXTRA_INSTRUMENTORS=[])}):
            instrument()

        self.assertIsInstance(otel_trace.get_tracer_provider(), TracerProvider)

    def test_dotless_path_warns_and_does_not_raise(self):
        """A path with no dot (empty module) is handled gracefully with a warning, not a crash."""
        with patch.dict(
            "sys.modules",
            {"nautobot_config": _fake_otel_config(NAUTOBOT_OTEL_EXTRA_INSTRUMENTORS=["NoDotHere"])},
        ):
            with self.assertLogs("nautobot.core.cli.opentelemetry", level="WARNING") as logs:
                instrument()  # must not raise

        self.assertTrue(
            any("NoDotHere" in message for message in logs.output),
            f"Expected a warning naming the dotless path; got: {logs.output!r}",
        )

    def test_failing_instrumentor_does_not_block_later_ones(self):
        """A load failure on one entry must not prevent a later valid entry from being installed."""
        good_instance = MagicMock()
        good_instance.is_instrumented_by_opentelemetry = False
        good_module, good_cls = self._fake_instrumentor_module(good_instance)

        with patch.dict("sys.modules", {"good_otel_pkg": good_module}):
            with patch.dict(
                "sys.modules",
                {
                    "nautobot_config": _fake_otel_config(
                        NAUTOBOT_OTEL_EXTRA_INSTRUMENTORS=[
                            "nonexistent.module.DoesNotExist",
                            "good_otel_pkg.FakeInstrumentor",
                        ]
                    )
                },
            ):
                with self.assertLogs("nautobot.core.cli.opentelemetry", level="WARNING"):
                    instrument()

        good_cls.assert_called_once()
        good_instance.instrument.assert_called_once()


def _default_logging_config():
    """A copy of Nautobot's default (correlation-off) LOGGING shape, for exercising the helper.

    Mirrors the `normal`/`verbose` formatters and `normal_console`/`verbose_console` handlers built in
    nautobot.core.settings, without booting Django (whose LOGGING is the NullHandler TESTING variant
    while the suite runs). test_default_settings_logging_has_no_suffix guards this copy against drift.
    """
    return {
        "version": 1,
        "disable_existing_loggers": False,
        "filters": {
            "otel_trace_context": {"()": "nautobot.core.logging.OtelTraceContextFilter"},
        },
        "formatters": {
            "normal": {
                "format": "%(asctime)s.%(msecs)03d %(levelname)-7s %(name)s :\n  %(message)s",
                "datefmt": "%H:%M:%S",
            },
            "verbose": {
                "format": (
                    "%(asctime)s.%(msecs)03d %(levelname)-7s %(name)-20s %(filename)-15s "
                    "%(funcName)30s() :\n  %(message)s"
                ),
                "datefmt": "%H:%M:%S",
            },
        },
        "handlers": {
            "normal_console": {
                "level": "INFO",
                "class": "logging.StreamHandler",
                "formatter": "normal",
                "filters": [],
            },
            "verbose_console": {
                "level": "DEBUG",
                "class": "logging.StreamHandler",
                "formatter": "verbose",
                "filters": [],
            },
        },
        "loggers": {
            "django": {"handlers": ["normal_console"], "level": "INFO"},
            "nautobot": {"handlers": ["normal_console"], "level": "INFO"},
        },
    }


class EnableOtelLogCorrelationTest(testing.TestCase):
    """Verify enable_otel_log_correlation() augments the default LOGGING dict correctly and safely.

    Regression: the correlation decision used to be baked into the LOGGING dict from env vars at
    settings-import time, so `OTEL_PYTHON_DJANGO_INSTRUMENT`/`OTEL_PYTHON_LOG_CORRELATION` set as Python
    assignments in nautobot_config.py were silently ignored for the default console output. The decision
    now happens post-load in _preprocess_settings() against the resolved settings, via this helper.
    """

    def _shipped_default_config(self):
        """A default-shaped LOGGING dict installed as `nautobot.core.settings.LOGGING` for this test.

        `enable_otel_log_correlation()` no-ops unless handed the exact dict Nautobot ships, so a test
        exercising the augmentation path must make its fixture *be* that object. Patching is undone on
        test exit, restoring the real (TESTING/NullHandler) settings value.
        """
        config = _default_logging_config()
        patcher = patch.object(core_settings, "LOGGING", config)
        patcher.start()
        self.addCleanup(patcher.stop)
        return config

    def test_correlation_on_adds_suffix_and_filter(self):
        """The helper appends the trace/span-id suffix to formatters and the filter to handlers."""
        from nautobot.core.logging import enable_otel_log_correlation

        config = self._shipped_default_config()
        enable_otel_log_correlation(config)

        for formatter in ("normal", "verbose"):
            fmt = config["formatters"][formatter]["format"]
            self.assertIn("%(otelTraceID)s", fmt, f"{formatter} formatter should carry the trace-id suffix.")
            self.assertIn("%(otelSpanID)s", fmt, f"{formatter} formatter should carry the span-id suffix.")
            # The suffix must land on the header line, before the message body.
            self.assertLess(fmt.index("%(otelTraceID)s"), fmt.index("%(message)s"))
        for handler in ("normal_console", "verbose_console"):
            self.assertIn("otel_trace_context", config["handlers"][handler]["filters"])

    def test_helper_is_idempotent(self):
        """Calling the helper twice must not double-append the suffix or duplicate the filter."""
        from nautobot.core.logging import enable_otel_log_correlation

        config = self._shipped_default_config()
        enable_otel_log_correlation(config)
        once = deepcopy(config)
        enable_otel_log_correlation(config)

        self.assertEqual(config, once, "A second call must be a no-op.")
        for formatter in ("normal", "verbose"):
            self.assertEqual(config["formatters"][formatter]["format"].count("%(otelTraceID)s"), 1)
        for handler in ("normal_console", "verbose_console"):
            self.assertEqual(config["handlers"][handler]["filters"].count("otel_trace_context"), 1)

    def test_operator_customized_default_shape_is_untouched(self):
        """An operator LOGGING dict that still uses Nautobot's names must not be mutated.

        The case the name-based guard alone missed: an operator who copies the default LOGGING and
        tweaks it (here, a level change) keeps the `normal`/`verbose` formatter and handler names, so
        matching by name would have augmented it. Reassigning LOGGING rebinds the name away from
        `nautobot.core.settings.LOGGING`, and the identity gate declines to touch it.
        """
        from nautobot.core.logging import enable_otel_log_correlation

        # The shipped default is present and augmentable...
        self._shipped_default_config()
        # ...but the operator's own near-identical copy is a different object, so it is left alone.
        operator_config = _default_logging_config()
        operator_config["handlers"]["normal_console"]["level"] = "DEBUG"
        before = deepcopy(operator_config)

        enable_otel_log_correlation(operator_config)

        self.assertEqual(operator_config, before, "A reassigned LOGGING dict must not be mutated.")
        self.assertNotIn("%(otelTraceID)s", operator_config["formatters"]["normal"]["format"])
        self.assertEqual(operator_config["handlers"]["normal_console"]["filters"], [])

    def test_custom_operator_logging_is_untouched(self):
        """A LOGGING dict with operator-named formatters/handlers must not be mutated by the helper."""
        from nautobot.core.logging import enable_otel_log_correlation

        custom = {
            "version": 1,
            "formatters": {"my_fmt": {"format": "%(levelname)s %(message)s"}},
            "handlers": {
                "my_handler": {"class": "logging.StreamHandler", "formatter": "my_fmt"},
            },
            "loggers": {"nautobot": {"handlers": ["my_handler"], "level": "INFO"}},
        }
        before = deepcopy(custom)
        enable_otel_log_correlation(custom)

        self.assertEqual(custom["formatters"], before["formatters"], "Custom formatters must be untouched.")
        self.assertEqual(custom["handlers"], before["handlers"], "Custom handlers must be untouched.")

    def test_default_fixture_has_no_suffix_before_helper(self):
        """The default LOGGING shape must be suffix-free until the helper runs.

        Guards that the correlation suffix only ever comes from enable_otel_log_correlation() (the
        env-var-driven bake-in was removed from settings.py), so an operator with correlation off gets
        plain formatters. The fixture mirrors settings.py's default block; keep them in sync.
        """
        config = _default_logging_config()
        self.assertNotIn("%(otelTraceID)s", config["formatters"]["normal"]["format"])
        self.assertNotIn("%(otelTraceID)s", config["formatters"]["verbose"]["format"])
        self.assertEqual(config["handlers"]["normal_console"]["filters"], [])
        self.assertEqual(config["handlers"]["verbose_console"]["filters"], [])

    def test_preprocess_settings_config_file_assignment_applies_suffix(self):
        """The bug case: flags set as attributes (env vars unset) must still surface the IDs.

        Simulates nautobot_config.py assigning OTEL_PYTHON_DJANGO_INSTRUMENT/OTEL_PYTHON_LOG_CORRELATION
        as Python values, then drives the exact reconciliation branch _preprocess_settings runs.
        """
        from nautobot.core.logging import enable_otel_log_correlation

        # `nautobot_config.py` does `from nautobot.core.settings import *`, so an operator who does not
        # override LOGGING holds the shipped dict itself -- which is what passes the helper's gate.
        settings_module = SimpleNamespace(
            TESTING=False,
            OTEL_PYTHON_DJANGO_INSTRUMENT=True,
            OTEL_PYTHON_LOG_CORRELATION=True,
            LOGGING=self._shipped_default_config(),
        )
        # Mirror the guard + call in nautobot.core.cli._preprocess_settings.
        if (
            not getattr(settings_module, "TESTING", False)
            and getattr(settings_module, "OTEL_PYTHON_DJANGO_INSTRUMENT", False)
            and getattr(settings_module, "OTEL_PYTHON_LOG_CORRELATION", False)
        ):
            enable_otel_log_correlation(settings_module.LOGGING)

        self.assertIn("%(otelTraceID)s", settings_module.LOGGING["formatters"]["normal"]["format"])
        self.assertIn("otel_trace_context", settings_module.LOGGING["handlers"]["normal_console"]["filters"])
