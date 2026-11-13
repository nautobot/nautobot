from unittest import mock

from django.db import connection, OperationalError
from django.test import override_settings
from django.test.utils import CaptureQueriesContext
from health_check.exceptions import ServiceUnavailable

from nautobot.core.testing import TestCase
from nautobot.extras.health_checks import DatabaseBackend
from nautobot.extras.models import HealthCheckTestModel


class DatabaseBackendTestCase(TestCase):
    """Tests for the `DatabaseBackend` health check."""

    def run_database_check(self):
        backend = DatabaseBackend()
        with CaptureQueriesContext(connection) as ctx:
            backend.run_check()
        return backend, [query["sql"] for query in ctx.captured_queries]

    @override_settings(MAINTENANCE_MODE=False, DATABASE_HEALTH_CHECK_READ_ONLY=False)
    def test_default_check_writes_a_test_row(self):
        backend, queries = self.run_database_check()

        self.assertEqual(backend.errors, [])
        self.assertTrue(any(sql.startswith("INSERT") for sql in queries), queries)
        self.assertFalse(HealthCheckTestModel.objects.exists())

    def test_read_only_check_runs_select_1_without_writing(self):
        for settings_override in (
            {"MAINTENANCE_MODE": True, "DATABASE_HEALTH_CHECK_READ_ONLY": False},
            {"MAINTENANCE_MODE": False, "DATABASE_HEALTH_CHECK_READ_ONLY": True},
        ):
            with self.subTest(**settings_override), override_settings(**settings_override):
                backend, queries = self.run_database_check()

                self.assertEqual(backend.errors, [])
                self.assertEqual(queries, ["SELECT 1"])

    @override_settings(DATABASE_HEALTH_CHECK_READ_ONLY=True)
    def test_read_only_check_reports_database_errors(self):
        backend = DatabaseBackend()
        with mock.patch.object(connection, "cursor", side_effect=OperationalError("server closed the connection")):
            backend.run_check()

        self.assertEqual(len(backend.errors), 1)
        self.assertIsInstance(backend.errors[0], ServiceUnavailable)
        self.assertIn("Database error", str(backend.errors[0]))
