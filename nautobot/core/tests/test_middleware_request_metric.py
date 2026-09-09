import re
import time

from django.db import connections
from django.http import HttpResponse
from django.test import override_settings, RequestFactory
from django.urls import reverse

from nautobot.core.middleware import (
    BaseRequestMetric,
    DatabaseDurationRequestMetric,
    RequestMetricMiddleware,
    TotalDurationRequestMetric,
)
from nautobot.core.testing import APITestCase, TestCase
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
            default_database_execution_wrappers = connections["default"].execute_wrappers
            self.assertIn(metric, default_database_execution_wrappers)

        default_database_execution_wrappers = connections["default"].execute_wrappers
        self.assertNotIn(metric, default_database_execution_wrappers)


class RequestMetricMiddlewareTestCase(APITestCase):
    """Tests for the `Server-Timing` response header written by `RequestMetricMiddleware`."""

    header_name = "Server-Timing"
    # Example:
    # name=EXAMPLE;dur:00:00:00;desc=Test Example
    metric_pattern = re.compile(r'(?P<name>[\w-]+);dur=(?P<duration>\d+(?:\.\d+)?);desc="(?P<description>[^"]*)"')

    def parse_metrics(self, header_value):
        """Return `{name: {"duration": duration_in_milliseconds, "description": description}}` parsed from a `Server-Timing` value."""
        request_metrics = {
            match.group("name"): {
                "duration": float(match.group("duration")),
                "description": match.group("description"),
            }
            for match in self.metric_pattern.finditer(header_value)
        }
        return request_metrics

    @staticmethod
    def call_middleware(get_response):
        """Run the middleware around `get_response` and return the resulting response."""
        return RequestMetricMiddleware(get_response)(RequestFactory().get("/"))

    @staticmethod
    def empty_response(request):
        return HttpResponse()

    def call_api(self):
        """Request a REST API endpoint as a token authenticated client and return the response."""
        url = reverse("api-status")
        return self.client.get(url, **self.header)

    @override_settings(REQUEST_TOTAL_DURATION_HEADER_ENABLED=False, REQUEST_DB_DURATION_HEADER_ENABLED=False)
    def test_header_is_omitted_when_all_metrics_are_disabled(self):
        response = self.call_api()

        self.assertNotIn(self.header_name, response.headers)

    @override_settings(REQUEST_TOTAL_DURATION_HEADER_ENABLED=True, REQUEST_DB_DURATION_HEADER_ENABLED=False)
    def test_total_metric_exists_when_only_metric_enabled(self):
        response = self.call_api()

        raw_server_timing_header = response.headers[self.header_name]
        request_metrics = self.parse_metrics(raw_server_timing_header)
        response_header_metric_names = list(request_metrics.keys())

        self.assertEqual(response_header_metric_names, ["total"])

    @override_settings(REQUEST_TOTAL_DURATION_HEADER_ENABLED=False, REQUEST_DB_DURATION_HEADER_ENABLED=True)
    def test_database_metric_exists_when_only_metric_enabled(self):
        response = self.call_api()

        raw_server_timing_header = response.headers[self.header_name]
        request_metrics = self.parse_metrics(raw_server_timing_header)
        response_header_metric_names = list(request_metrics.keys())

        self.assertEqual(response_header_metric_names, ["db"])

    @override_settings(REQUEST_TOTAL_DURATION_HEADER_ENABLED=True, REQUEST_DB_DURATION_HEADER_ENABLED=True)
    def test_total_and_db_metrics_exist_when_enabled(self):
        response = self.call_api()

        raw_server_timing_header = response.headers[self.header_name]
        request_metrics = self.parse_metrics(raw_server_timing_header)
        response_header_metric_names = list(request_metrics.keys())

        self.assertEqual(response_header_metric_names, ["total", "db"])

    @override_settings(REQUEST_TOTAL_DURATION_HEADER_ENABLED=True, REQUEST_DB_DURATION_HEADER_ENABLED=True)
    def test_an_error_from_the_view_is_not_swallowed(self):
        """The middleware must not hide a view failure behind its metric reporting."""

        def get_response(request):
            raise ValueError("Intentional error")

        with self.assertRaises(ValueError):
            self.call_middleware(get_response)

    @override_settings(REQUEST_TOTAL_DURATION_HEADER_ENABLED=True, REQUEST_DB_DURATION_HEADER_ENABLED=True)
    def test_server_timing_header_does_not_override_other_headers(self):
        """`Server-Timing` addition does not override other settings."""

        # Cache doesn't get used. It's placeholder to smoke-test that state is
        # persisting between responses and not clobbering other middleware
        def existing_headers_response(request):
            response = HttpResponse()
            response.headers["Server-Timing"] = 'cache;dur=1.5;desc="Cache lookup"'
            return response

        current_response = self.call_middleware(existing_headers_response)

        raw_server_timing_header = current_response.headers[self.header_name]
        request_metrics = self.parse_metrics(raw_server_timing_header)
        response_header_metric_names = list(request_metrics.keys())

        self.assertEqual(response_header_metric_names, ["cache", "total", "db"])

    @override_settings(REQUEST_TOTAL_DURATION_HEADER_ENABLED=True, REQUEST_DB_DURATION_HEADER_ENABLED=True)
    def test_durations_are_reported_in_milliseconds(self):
        response = self.call_api()

        raw_server_timing_header = response.headers[self.header_name]
        request_metrics = self.parse_metrics(raw_server_timing_header)
        total_duration = request_metrics["total"]["duration"]

        self.assertGreater(total_duration, 0)
        self.assertLess(total_duration, 10_000)

    @override_settings(REQUEST_TOTAL_DURATION_HEADER_ENABLED=True, REQUEST_DB_DURATION_HEADER_ENABLED=True)
    def test_durations_are_rounded_to_two_decimal_places(self):
        response = self.call_api()

        raw_server_timing_header = response.headers[self.header_name]

        raw_durations = re.findall(r";dur=([\d.]+)", raw_server_timing_header)

        for raw_duration in raw_durations:
            with self.subTest(duration=raw_duration):
                _, _, decimal_places = raw_duration.partition(".")
                self.assertLessEqual(len(decimal_places), 2)

    @override_settings(REQUEST_TOTAL_DURATION_HEADER_ENABLED=True, REQUEST_DB_DURATION_HEADER_ENABLED=True)
    def test_database_queries_are_counted_and_timed(self):
        response = self.call_api()

        raw_server_timing_header = response.headers[self.header_name]
        request_metrics = self.parse_metrics(raw_server_timing_header)

        total_duration = request_metrics["total"]["duration"]
        database_duration = request_metrics["db"]["duration"]
        database_description = request_metrics["db"]["description"]

        self.assertGreaterEqual(total_duration, database_duration)
        self.assertRegex(database_description, r"^\d+ database queries$")
        self.assertGreater(database_duration, 0)

    @override_settings(REQUEST_TOTAL_DURATION_HEADER_ENABLED=True, REQUEST_DB_DURATION_HEADER_ENABLED=False)
    def test_no_database_query_wrapper_used_when_database_metric_is_disabled(self):
        """Confirm that server runtime isn't penalized with a database wrapper when the database metric is disabled."""
        wrappers_during_request = []

        def get_response(request):
            default_database_execution_wrappers = connections["default"].execute_wrappers
            wrappers_during_request.extend(default_database_execution_wrappers)
            return HttpResponse()

        self.call_middleware(get_response)

        database_metric_wrappers = [
            wrapper for wrapper in wrappers_during_request if isinstance(wrapper, DatabaseDurationRequestMetric)
        ]

        self.assertEqual(database_metric_wrappers, [])

    @override_settings(REQUEST_TOTAL_DURATION_HEADER_ENABLED=False, REQUEST_DB_DURATION_HEADER_ENABLED=True)
    def test_database_query_wrapper_used_when_the_database_metric_is_enabled(self):
        wrappers_during_request = []

        def get_response(request):
            default_database_execution_wrappers = connections["default"].execute_wrappers
            wrappers_during_request.extend(default_database_execution_wrappers)
            return HttpResponse()

        self.call_middleware(get_response)

        database_metric_wrappers = [
            wrapper for wrapper in wrappers_during_request if isinstance(wrapper, DatabaseDurationRequestMetric)
        ]

        self.assertEqual(len(database_metric_wrappers), 1)

    @override_settings(REQUEST_TOTAL_DURATION_HEADER_ENABLED=True, REQUEST_DB_DURATION_HEADER_ENABLED=True)
    def test_metrics_exist_when_using_the_configured_middleware_stack(self):
        """Exercise the middleware from its real position in `settings.MIDDLEWARE`."""
        response = self.call_api()

        raw_server_timing_header = response.headers[self.header_name]
        request_metrics = self.parse_metrics(raw_server_timing_header)
        response_header_metric_names = list(request_metrics.keys())

        self.assertEqual(response_header_metric_names, ["total", "db"])
