import re
import time
from unittest.mock import patch

from django.conf import settings
from django.test import override_settings, RequestFactory
from django.urls import reverse
from django_redis import get_redis_connection
import redis.exceptions
from rest_framework import status

from nautobot.core.middleware import (
    ComplexityCostRateLimitingMiddleware,
)
from nautobot.core.rate_limiting.budget_helpers import get_rate_limit_bucket_id
from nautobot.core.testing import APITestCase
from nautobot.users.models import Token

rate_limit_policy_header_name = "RateLimit-Policy"
# Example: "rest-complexity-cost";q=1000;w=60
rate_limit_policy_pattern = re.compile(r'^"(?P<policy_name>[^"]+)";q=(?P<budget>\d+);w=(?P<window_in_seconds>\d+)$')
# ----------------------------------------
rate_limit_header_name = "RateLimit"
# Example: "rest-complexity-cost";r=996;t=60
rate_limit_pattern = re.compile(
    r'^"(?P<policy_name>[^"]+)";r=(?P<remaining_budget>\d+);t=(?P<remaining_window_in_seconds>\d+)$'
)
# ----------------------------------------
nautobot_cost_header_name = "X-Nautobot-Cost"
# Example: 4
nautobot_cost_pattern = re.compile(r"^(?P<cost>\d+)$")


def parse_rate_limit_policy_header(header_value):
    match = rate_limit_policy_pattern.fullmatch(header_value)

    if match is None:
        return None

    rate_limit_policy_data = {
        "policy_name": match.group("policy_name"),
        "budget": int(match.group("budget")),
        "window_in_seconds": int(match.group("window_in_seconds")),
    }

    return rate_limit_policy_data


def parse_rate_limit_header(header_value):
    match = rate_limit_pattern.fullmatch(header_value)

    if match is None:
        return None

    rate_limit_data = {
        "policy_name": match.group("policy_name"),
        "remaining_budget": int(match.group("remaining_budget")),
        "remaining_window_in_seconds": int(match.group("remaining_window_in_seconds")),
    }

    return rate_limit_data


def parse_nautobot_cost_header(header_value):
    match = nautobot_cost_pattern.fullmatch(header_value)
    if match is None:
        return None

    nautobot_cost = int(match.group("cost"))

    return nautobot_cost


def get_rate_limit_policy_header_policy_name(response):
    """Return the policy name of the RateLimit-Policy header."""
    rate_limit_policy_data = parse_rate_limit_policy_header(response.headers[rate_limit_policy_header_name])
    rate_limit_policy_name = rate_limit_policy_data["policy_name"]
    return rate_limit_policy_name


def get_rate_limit_policy_header_budget(response):
    """Return the `q` parameter of the RateLimit-Policy header as an integer."""
    rate_limit_policy_data = parse_rate_limit_policy_header(response.headers[rate_limit_policy_header_name])
    total_budget = rate_limit_policy_data["budget"]
    return total_budget


def get_rate_limit_policy_header_window_in_seconds(response):
    """Return the `w` parameter of the RateLimit-Policy header as an integer."""
    rate_limit_policy_data = parse_rate_limit_policy_header(response.headers[rate_limit_policy_header_name])
    window_in_seconds = rate_limit_policy_data["window_in_seconds"]
    return window_in_seconds


def get_rate_limit_header_policy_name(response):
    """Return the policy name of the RateLimit header."""
    rate_limit_data = parse_rate_limit_header(response.headers[rate_limit_header_name])
    rate_limit_name = rate_limit_data["policy_name"]
    return rate_limit_name


def get_rate_limit_header_remaining_budget(response):
    """Return the `r` parameter of the RateLimit header as an integer."""
    rate_limit_data = parse_rate_limit_header(response.headers[rate_limit_header_name])
    remaining_budget = rate_limit_data["remaining_budget"]
    return remaining_budget


def get_rate_limit_header_remaining_window_in_seconds(response):
    """Return the `t` parameter of the RateLimit header as an integer."""
    rate_limit_data = parse_rate_limit_header(response.headers[rate_limit_header_name])
    remaining_window_in_seconds = rate_limit_data["remaining_window_in_seconds"]
    return remaining_window_in_seconds


def get_nautobot_header_cost(response):
    nautobot_cost = parse_nautobot_cost_header(response.headers[nautobot_cost_header_name])
    return nautobot_cost


class ComplexityCostRateLimitingMiddlewareTestCase(APITestCase):
    """Tests `ComplexityCostRateLimitingMiddleware`'s plumbing.

    Makes sure that it runs, and aligns with internal settings.
    Does not validate any cost metrics. Purely focused code path traversal.
    """

    @staticmethod
    def call_middleware(get_response):
        """Run the middleware around `get_response` and return the resulting response."""
        return ComplexityCostRateLimitingMiddleware(get_response)(RequestFactory().get("/"))

    def call_api(self):
        """Request a REST API endpoint as a token authenticated client and return the response."""
        url = reverse("api-status")
        return self.client.get(url, **self.header)

    @override_settings(NAUTOBOT_REST_RATE_LIMITING_MODE="off")
    def test_header_is_omitted_when_rest_complexity_cost_rate_limiting_mode_is_set_to_off(self):
        response = self.call_api()

        self.assertNotIn(rate_limit_policy_header_name, response.headers)
        self.assertNotIn(rate_limit_header_name, response.headers)
        self.assertNotIn(nautobot_cost_header_name, response.headers)

    @override_settings(NAUTOBOT_REST_RATE_LIMITING_MODE="report")
    def test_header_is_added_when_rest_complexity_cost_rate_limiting_is_set_to_report(self):
        response = self.call_api()

        self.assertIn(rate_limit_policy_header_name, response.headers)
        self.assertIn(rate_limit_header_name, response.headers)
        self.assertIn(nautobot_cost_header_name, response.headers)

    @override_settings(NAUTOBOT_REST_RATE_LIMITING_MODE="enforce")
    def test_header_is_added_when_rest_complexity_cost_rate_limiting_is_set_to_enforce(self):
        response = self.call_api()

        self.assertIn(rate_limit_policy_header_name, response.headers)
        self.assertIn(rate_limit_header_name, response.headers)
        self.assertIn(nautobot_cost_header_name, response.headers)

    @override_settings(NAUTOBOT_REST_RATE_LIMITING_MODE="report")
    def test_rate_limit_policy_header_matches_expected_format(self):
        response = self.call_api()

        raw_rate_limit_policy_header = response.headers[rate_limit_policy_header_name]
        rate_limit_policy = parse_rate_limit_policy_header(raw_rate_limit_policy_header)

        # Checks the fields exists and that they were correctly parsed out
        self.assertIsNotNone(rate_limit_policy)
        self.assertIn("policy_name", rate_limit_policy)
        self.assertEqual(rate_limit_policy["policy_name"], "rest-complexity-cost")
        self.assertIn("budget", rate_limit_policy)
        self.assertEqual(rate_limit_policy["budget"], settings.NAUTOBOT_REST_RATE_LIMITING_BUDGET)
        self.assertIn("window_in_seconds", rate_limit_policy)
        self.assertEqual(rate_limit_policy["window_in_seconds"], settings.NAUTOBOT_REST_RATE_LIMITING_WINDOW_IN_SECONDS)

    @override_settings(
        NAUTOBOT_REST_RATE_LIMITING_MODE="report",
        NAUTOBOT_REST_RATE_LIMITING_WINDOW_IN_SECONDS=3600,
    )
    def test_rate_limit_header_matches_expected_format(self):
        response = self.call_api()

        raw_rate_limit_header = response.headers[rate_limit_header_name]
        rate_limit = parse_rate_limit_header(raw_rate_limit_header)

        # Checks the fields exists and that they were correctly parsed out
        self.assertIsNotNone(rate_limit)
        self.assertIn("policy_name", rate_limit)
        self.assertEqual(rate_limit["policy_name"], "rest-complexity-cost")
        self.assertIn("remaining_budget", rate_limit)
        self.assertEqual(rate_limit["remaining_budget"], settings.NAUTOBOT_REST_RATE_LIMITING_BUDGET)
        self.assertIn("remaining_window_in_seconds", rate_limit)
        self.assertEqual(
            rate_limit["remaining_window_in_seconds"], settings.NAUTOBOT_REST_RATE_LIMITING_WINDOW_IN_SECONDS
        )

    @override_settings(NAUTOBOT_REST_RATE_LIMITING_MODE="enforce")
    def test_nautobot_cost_header_matches_expected_format(self):
        response = self.call_api()

        raw_nautobot_cost_header = response.headers[nautobot_cost_header_name]
        nautobot_cost = parse_nautobot_cost_header(raw_nautobot_cost_header)

        self.assertIsNotNone(nautobot_cost)
        self.assertIsInstance(nautobot_cost, int)

    # TODO
    # - html request doesn't include headers in response?


class ComplexityCostRateLimitingBudgetTestCase(APITestCase):
    """Tests the complexity cost budget behavior."""

    def call_api(self):
        """Request a REST API endpoint as a token authenticated client and return the response."""
        api_status_response = self.client.get(reverse("api-status"), **self.header)
        return api_status_response

    def call_api_until_throttled(self):
        """Call the API repeatedly, returning `(first_response, throttled_response_or_None)`."""
        first_response = self.call_api()
        if first_response.status_code == status.HTTP_429_TOO_MANY_REQUESTS:
            return first_response, first_response

        for _ in range(50):
            response = self.call_api()
            if response.status_code == status.HTTP_429_TOO_MANY_REQUESTS:
                return first_response, response

        return first_response, None

    # --------------------------------------------------------------------------
    # Rate Limiting Reported
    # --------------------------------------------------------------------------
    @override_settings(NAUTOBOT_REST_RATE_LIMITING_MODE="report")
    def test_budget_is_not_consumed_when_set_to_report(self):
        first_response = self.call_api()
        second_response = self.call_api()

        self.assertIsNotNone(first_response)
        self.assertEqual(first_response.status_code, status.HTTP_200_OK)
        self.assertIn(rate_limit_policy_header_name, first_response.headers)
        self.assertIn(rate_limit_header_name, first_response.headers)
        self.assertIn(nautobot_cost_header_name, first_response.headers)

        self.assertIsNotNone(second_response)
        self.assertEqual(second_response.status_code, status.HTTP_200_OK)
        self.assertIn(rate_limit_policy_header_name, second_response.headers)
        self.assertIn(rate_limit_header_name, second_response.headers)
        self.assertIn(nautobot_cost_header_name, second_response.headers)

        first_response_remaining_budget = get_rate_limit_header_remaining_budget(first_response)
        second_response_remaining_budget = get_rate_limit_header_remaining_budget(second_response)

        self.assertEqual(first_response_remaining_budget, second_response_remaining_budget)

    # --------------------------------------------------------------------------
    # Rate Limiting Enforced
    # --------------------------------------------------------------------------
    @override_settings(
        NAUTOBOT_REST_RATE_LIMITING_MODE="enforce",
        NAUTOBOT_REST_RATE_LIMITING_WINDOW_IN_SECONDS=3600,
        NAUTOBOT_REST_RATE_LIMITING_BUDGET=10,
    )
    def test_unauthenticated_request_returns_a_full_budget_when_enforcement_enabled(self):
        api_response = self.client.get(reverse("api-status"))

        self.assertIsNotNone(api_response)
        self.assertEqual(api_response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertIn(rate_limit_policy_header_name, api_response.headers)
        self.assertIn(rate_limit_header_name, api_response.headers)
        self.assertIn(nautobot_cost_header_name, api_response.headers)

        remaining_budget = get_rate_limit_header_remaining_budget(api_response)
        self.assertEqual(settings.NAUTOBOT_REST_RATE_LIMITING_BUDGET, remaining_budget)

    @override_settings(
        NAUTOBOT_REST_RATE_LIMITING_MODE="enforce",
        NAUTOBOT_REST_RATE_LIMITING_WINDOW_IN_SECONDS=3600,
        NAUTOBOT_REST_RATE_LIMITING_BUDGET=10,
    )
    def test_consumed_budget_accumulates_across_requests_until_the_budget_is_exhausted(self):
        _, throttled_response = self.call_api_until_throttled()

        self.assertIsNotNone(throttled_response)
        self.assertEqual(throttled_response.status_code, status.HTTP_429_TOO_MANY_REQUESTS)

        # The policy header advertises the configured allowance, so it never moves as budget is spent.
        self.assertIn(rate_limit_policy_header_name, throttled_response.headers)
        throttled_response_rate_limit_policy_name = get_rate_limit_policy_header_policy_name(throttled_response)
        throttled_response_rate_limit_policy_budget = get_rate_limit_policy_header_budget(throttled_response)
        throttled_response_rate_limiting_window_in_seconds = get_rate_limit_policy_header_window_in_seconds(
            throttled_response
        )
        self.assertEqual(throttled_response_rate_limit_policy_name, "rest-complexity-cost")
        self.assertEqual(throttled_response_rate_limit_policy_budget, settings.NAUTOBOT_REST_RATE_LIMITING_BUDGET)
        self.assertEqual(
            throttled_response_rate_limiting_window_in_seconds, settings.NAUTOBOT_REST_RATE_LIMITING_WINDOW_IN_SECONDS
        )

        # The RateLimit header reports what is left, which is floored at zero once overspent.
        self.assertIn(rate_limit_header_name, throttled_response.headers)
        throttled_response_rate_limit_name = get_rate_limit_header_policy_name(throttled_response)
        throttled_response_rate_limit_budget_remaining = get_rate_limit_header_remaining_budget(throttled_response)
        throttled_response_rate_limit_remaining_window_in_seconds = get_rate_limit_header_remaining_window_in_seconds(
            throttled_response
        )
        self.assertEqual(throttled_response_rate_limit_name, "rest-complexity-cost")
        self.assertEqual(throttled_response_rate_limit_budget_remaining, 0)
        self.assertGreater(throttled_response_rate_limit_remaining_window_in_seconds, 0)

        # A throttled request is still priced, and it tells the caller when to come back.
        self.assertIn(nautobot_cost_header_name, throttled_response.headers)
        throttled_response_cost = get_nautobot_header_cost(throttled_response)
        self.assertGreater(throttled_response_cost, 0)
        self.assertIn("Retry-After", throttled_response.headers)

    @override_settings(NAUTOBOT_REST_RATE_LIMITING_MODE="enforce")
    def test_remaining_budget_decreases_between_requests(self):
        first_response = self.call_api()
        second_response = self.call_api()

        self.assertIsNotNone(first_response)
        self.assertEqual(first_response.status_code, status.HTTP_200_OK)
        self.assertIn(rate_limit_policy_header_name, first_response.headers)
        self.assertIn(rate_limit_header_name, first_response.headers)
        self.assertIn(nautobot_cost_header_name, first_response.headers)

        self.assertIsNotNone(second_response)
        self.assertEqual(second_response.status_code, status.HTTP_200_OK)
        self.assertIn(rate_limit_policy_header_name, second_response.headers)
        self.assertIn(rate_limit_header_name, second_response.headers)
        self.assertIn(nautobot_cost_header_name, second_response.headers)

        first_response_remaining_budget = get_rate_limit_header_remaining_budget(first_response)
        second_response_remaining_budget = get_rate_limit_header_remaining_budget(second_response)

        self.assertLess(second_response_remaining_budget, first_response_remaining_budget)

    @override_settings(
        NAUTOBOT_REST_RATE_LIMITING_MODE="enforce",
        NAUTOBOT_REST_RATE_LIMITING_WINDOW_IN_SECONDS=3600,
        NAUTOBOT_REST_RATE_LIMITING_BUDGET=10,
    )
    def test_throttled_response_advertises_when_to_retry(self):
        window_in_seconds = 3600
        one_minute_in_seconds = 60

        _, throttled_response = self.call_api_until_throttled()

        self.assertIsNotNone(throttled_response)
        self.assertIn("Retry-After", throttled_response.headers)

        initial_retry_after = int(throttled_response.headers["Retry-After"])
        initial_retry_after_window_fudge_factor = 3500
        self.assertGreaterEqual(initial_retry_after, initial_retry_after_window_fudge_factor)
        self.assertLessEqual(initial_retry_after, window_in_seconds)

        remaining_window_after_a_minute = window_in_seconds - one_minute_in_seconds
        bucket_id = get_rate_limit_bucket_id(self.header["HTTP_AUTHORIZATION"])
        get_redis_connection("default").expire(bucket_id, remaining_window_after_a_minute)

        throttled_response_after_a_minute = self.call_api()

        self.assertEqual(throttled_response_after_a_minute.status_code, status.HTTP_429_TOO_MANY_REQUESTS)
        self.assertIn("Retry-After", throttled_response_after_a_minute.headers)

        retry_after_a_minute = int(throttled_response_after_a_minute.headers["Retry-After"])
        self.assertLessEqual(retry_after_a_minute, remaining_window_after_a_minute)
        self.assertGreater(retry_after_a_minute, remaining_window_after_a_minute - 5)

    @override_settings(
        NAUTOBOT_REST_RATE_LIMITING_MODE="enforce",
        NAUTOBOT_REST_RATE_LIMITING_WINDOW_IN_SECONDS=3600,
        NAUTOBOT_REST_RATE_LIMITING_BUDGET=10,
    )
    def test_remaining_budget_is_never_advertised_as_negative(self):
        _, first_throttled_response = self.call_api_until_throttled()
        _, second_throttled_response = self.call_api_until_throttled()

        self.assertIsNotNone(first_throttled_response)
        self.assertEqual(get_rate_limit_header_remaining_budget(first_throttled_response), 0)

        self.assertIsNotNone(second_throttled_response)
        self.assertEqual(get_rate_limit_header_remaining_budget(second_throttled_response), 0)

    @override_settings(
        NAUTOBOT_REST_RATE_LIMITING_MODE="enforce",
        NAUTOBOT_REST_RATE_LIMITING_WINDOW_IN_SECONDS=3600,
        NAUTOBOT_REST_RATE_LIMITING_BUDGET=10,
    )
    def test_budget_is_tracked_per_token_rather_than_per_user(self):
        _, throttled_response = self.call_api_until_throttled()
        self.assertIsNotNone(throttled_response)
        self.assertEqual(throttled_response.status_code, status.HTTP_429_TOO_MANY_REQUESTS)

        second_token = Token.objects.create(user=self.user)
        self.header = {"HTTP_AUTHORIZATION": f"Token {second_token.key}"}

        api_response = self.call_api()
        self.assertEqual(api_response.status_code, status.HTTP_200_OK)

    @override_settings(NAUTOBOT_REST_RATE_LIMITING_MODE="enforce")
    def test_unreachable_caching_service_reports_a_full_budget(self):
        with patch(
            "nautobot.core.rate_limiting.budget_helpers.get_redis_connection",
            side_effect=redis.exceptions.ConnectionError,
        ):
            api_response = self.call_api()

        remaining_budget = get_rate_limit_header_remaining_budget(api_response)

        self.assertEqual(api_response.status_code, status.HTTP_200_OK)
        self.assertEqual(remaining_budget, settings.NAUTOBOT_REST_RATE_LIMITING_BUDGET)

    @override_settings(
        NAUTOBOT_REST_RATE_LIMITING_MODE="enforce",
        NAUTOBOT_REST_RATE_LIMITING_WINDOW_IN_SECONDS=3600,
        NAUTOBOT_REST_RATE_LIMITING_BUDGET=1,
    )
    def test_request_that_consumes_entire_budget_is_allowed_and_next_request_fails(self):
        self.add_permissions("dcim.view_device")
        device_list_url = f"{reverse('dcim-api:device-list')}?depth=3&limit=100&name=test-device"

        first_response = self.client.get(device_list_url, **self.header)
        first_response_cost = get_nautobot_header_cost(first_response)
        first_response_remaining_budget = get_rate_limit_header_remaining_budget(first_response)

        self.assertEqual(first_response.status_code, status.HTTP_200_OK)
        self.assertGreater(first_response_cost, 1)
        self.assertEqual(first_response_remaining_budget, 0)

        second_response = self.client.get(device_list_url, **self.header)
        second_response_remaining_budget = get_rate_limit_header_remaining_budget(second_response)

        self.assertEqual(second_response.status_code, status.HTTP_429_TOO_MANY_REQUESTS)
        self.assertEqual(second_response_remaining_budget, 0)
        self.assertIn("Retry-After", second_response.headers)

    @override_settings(
        NAUTOBOT_REST_RATE_LIMITING_MODE="enforce",
        # The window has to outlast the time it takes to spend the budget, or the bucket expires
        # mid-loop and consumption resets before anything is ever throttled. At this budget the
        # third request trips the limit, and a reset window still leaves budget for one more.
        NAUTOBOT_REST_RATE_LIMITING_WINDOW_IN_SECONDS=6,
        NAUTOBOT_REST_RATE_LIMITING_BUDGET=8,
    )
    def test_budget_resets_after_window_expires(self):
        _, throttled_response = self.call_api_until_throttled()
        self.assertIsNotNone(throttled_response)
        self.assertEqual(throttled_response.status_code, status.HTTP_429_TOO_MANY_REQUESTS)

        # Sleeping the full window always outlasts whatever is left of the bucket's TTL, which was
        # set when the first request opened the window and has been counting down ever since.
        time.sleep(settings.NAUTOBOT_REST_RATE_LIMITING_WINDOW_IN_SECONDS)
        api_response = self.call_api()
        remaining_budget = get_rate_limit_header_remaining_budget(api_response)

        self.assertEqual(api_response.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(remaining_budget, 1)
