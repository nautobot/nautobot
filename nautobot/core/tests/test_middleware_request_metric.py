import time

from django.db import connections, DEFAULT_DB_ALIAS

from nautobot.core.middleware import (
    BaseRequestMetric,
    DatabaseDurationRequestMetric,
    TotalDurationRequestMetric,
)
from nautobot.core.testing import TestCase
from nautobot.extras.models import Status


class BaseRequestMetricTestCase(TestCase):
    """Tests for the abstract contract declared by `BaseRequestMetric`."""

    def test_the_abstract_base_cannot_be_instantiated(self):
        with self.assertRaises(TypeError):
            BaseRequestMetric()  # pylint: disable=abstract-class-instantiated

    def test_a_subclass_missing_part_of_the_contract_cannot_be_instantiated(self):
        """An incomplete metric must fail when it is constructed, naming the member it is missing."""

        class MetricWithoutName(BaseRequestMetric):
            @property
            def description(self):
                return "no name"

            def __enter__(self):
                return self

            def __exit__(self, *exception_info):
                return False

        with self.assertRaisesRegex(TypeError, "name"):
            MetricWithoutName()  # pylint: disable=abstract-class-instantiated

        class MetricWithoutDescription(BaseRequestMetric):
            @property
            def name(self):
                return "no description"

            def __enter__(self):
                return self

            def __exit__(self, *exception_info):
                return False

        with self.assertRaisesRegex(TypeError, "description"):
            MetricWithoutDescription()  # pylint: disable=abstract-class-instantiated

        class MetricWithoutEnter(BaseRequestMetric):
            @property
            def name(self):
                return "no enter"

            @property
            def description(self):
                return "no enter"

            def __exit__(self, *exception_info):
                return False

        with self.assertRaisesRegex(TypeError, "__enter__"):
            MetricWithoutEnter()  # pylint: disable=abstract-class-instantiated

        class MetricWithoutExit(BaseRequestMetric):
            @property
            def name(self):
                return "no exit"

            @property
            def description(self):
                return "no exit"

            def __enter__(self):
                return self

        with self.assertRaisesRegex(TypeError, "__exit__"):
            MetricWithoutExit()  # pylint: disable=abstract-class-instantiated


class TotalDurationRequestMetricTestCase(TestCase):
    """Tests for `TotalDurationRequestMetric`."""

    def test_duration_is_reported_in_milliseconds(self):
        """A known amount of work must be reported in milliseconds, not seconds or nanoseconds."""
        metric = TotalDurationRequestMetric()

        # Trigger __enter__/__exit___
        with metric:
            time.sleep(0.05)

        self.assertGreater(metric.duration_in_milliseconds, 10)
        self.assertLess(metric.duration_in_milliseconds, 1000)

    def test_duration_is_recorded_even_on_error(self):
        metric = TotalDurationRequestMetric()

        with self.assertRaises(ValueError):
            with metric:
                time.sleep(0.05)
                raise ValueError("Intentional error")

        self.assertGreater(metric.duration_in_milliseconds, 10)
        self.assertLess(metric.duration_in_milliseconds, 1000)

    def test_total_duration_name_is_correct(self):
        metric = TotalDurationRequestMetric()
        self.assertEqual(metric.name, "total")

    def test_total_duration_description_is_correct(self):
        metric = TotalDurationRequestMetric()
        self.assertEqual(metric.description, "Total request duration")


class DatabaseDurationRequestMetricTestCase(TestCase):
    """Tests for `DatabaseDurationRequestMetric`."""

    def test_duration_is_reported_in_milliseconds(self):
        """Best effort made to trigger delay in database query so that duration can be confirmed."""
        metric = DatabaseDurationRequestMetric()

        # Trigger __enter__/__exit__
        with metric:
            Status.objects.count()
            Status.objects.count()

        self.assertGreater(metric.duration_in_milliseconds, 0)
        self.assertLess(metric.duration_in_milliseconds, 1000)

    def test_duration_is_recorded_even_on_error(self):
        metric = DatabaseDurationRequestMetric()

        with self.assertRaises(ValueError):
            with metric:
                Status.objects.count()
                Status.objects.count()
                raise ValueError("Intentional error")

        self.assertGreater(metric.duration_in_milliseconds, 0)
        self.assertLess(metric.duration_in_milliseconds, 1000)

    def test_database_duration_name_is_correct(self):
        metric = DatabaseDurationRequestMetric()
        self.assertEqual(metric.name, "db")

    def test_database_duration_description_is_correct(self):
        metric = DatabaseDurationRequestMetric()
        self.assertEqual(metric.query_count, 0)
        self.assertEqual(metric.description, "0 database queries")

        with metric:
            Status.objects.count()
            Status.objects.count()

        self.assertEqual(metric.query_count, 2)
        self.assertEqual(metric.description, "2 database queries")

    def test_a_request_without_queries_reports_a_zero_duration(self):
        metric = DatabaseDurationRequestMetric()

        with metric:
            pass

        self.assertEqual(metric.query_count, 0)
        self.assertEqual(metric.description, "0 database queries")
        self.assertEqual(metric.duration_in_milliseconds, 0.0)

    def test_the_query_wrapper_is_removed_after_measuring(self):
        """The `execute_wrapper` hook must not leak past the block it was registered for."""
        metric = DatabaseDurationRequestMetric()

        with metric:
            self.assertIn(metric, connections[DEFAULT_DB_ALIAS].execute_wrappers)

        self.assertNotIn(metric, connections[DEFAULT_DB_ALIAS].execute_wrappers)
