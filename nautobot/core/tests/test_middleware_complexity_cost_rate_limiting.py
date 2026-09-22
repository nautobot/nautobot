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


class ComplexityCostRateLimitingMiddlewareTestCase(APITestCase):
    """Tests `ComplexityCostRateLimitingMiddleware`'s plumbing.

    Makes sure that it runs, and aligns with internal settings.
    Does not validate any cost metrics. Purely focused code path traversal.
    """

    rate_limit_policy_header_name = "RateLimit-Policy"
    rate_limit_header_name = "RateLimit"
    nautobot_cost_header_name = "X-Nautobot-Cost"
    # Example: TODO
    # TODO
    # rate_limit_policy_pattern = re.compile()
    # Example: TODO
    # TODO
    # rate_limit_pattern = re.compile()
    # TODO: Test ratelimit pattern is correct
    # TODO: Test ratelimit policy pattern is correct
    # TODO: Test nautobot pattern is correct

    # TODO
    def parse_rate_limit_policy_header(self, header_value):
        pass

    # TODO
    def parse_rate_limit_header(self, header_value):
        pass

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

        self.assertNotIn(self.rate_limit_policy_header_name, response.headers)
        self.assertNotIn(self.rate_limit_header_name, response.headers)
        self.assertNotIn(self.nautobot_cost_header_name, response.headers)

    @override_settings(NAUTOBOT_REST_RATE_LIMITING_MODE="report")
    def test_header_is_added_when_rest_complexity_cost_rate_limiting_is_set_to_report(self):
        response = self.call_api()

        self.assertIn(self.rate_limit_policy_header_name, response.headers)
        self.assertIn(self.rate_limit_header_name, response.headers)
        self.assertIn(self.nautobot_cost_header_name, response.headers)

    @override_settings(NAUTOBOT_REST_RATE_LIMITING_MODE="enforce")
    def test_header_is_added_when_rest_complexity_cost_rate_limiting_is_set_to_enforce(self):
        response = self.call_api()

        self.assertIn(self.rate_limit_policy_header_name, response.headers)
        self.assertIn(self.rate_limit_header_name, response.headers)
        self.assertIn(self.nautobot_cost_header_name, response.headers)

    # TODO
    @override_settings(NAUTOBOT_REST_RATE_LIMITING_MODE="off")
    def test_api_request_is_allowed_when_rest_complexity_cost_rate_limiting_is_set_to_off(self):
        pass

    # TODO
    @override_settings(NAUTOBOT_REST_RATE_LIMITING_MODE="report")
    def test_api_request_is_allowed_when_rest_complexity_cost_rate_limiting_is_set_to_report(self):
        pass

    # TODO
    # - html request doesn't include headers in response?


class ComplexityCostRateLimitingBudgetTestCase(APITestCase):
    """Tests the complexity cost budget behavior."""

    rate_limit_policy_header_name = "RateLimit-Policy"
    rate_limit_header_name = "RateLimit"
    nautobot_cost_header_name = "X-Nautobot-Cost"

    @staticmethod
    def parse_rate_limit_header(header_value):
        """Parse `"policy-name";r=0;t=5` into `{"r": "0", "t": "5"}`."""
        parameters = {}
        for element in header_value.split(";"):
            name, separator, value = element.partition("=")
            if separator:
                parameters[name.strip()] = value.strip()
        return parameters

    def get_remaining_budget(self, response):
        """Return the `r` parameter of the RateLimit header as an integer."""
        rate_limit = self.parse_rate_limit_header(response.headers[self.rate_limit_header_name])
        return int(rate_limit["r"])

    def call_api(self):
        """Request a REST API endpoint as a token authenticated client and return the response."""
        api_status_response = self.client.get(reverse("api-status"), **self.header)
        return api_status_response

    def call_api_until_throttled(self):
        """Call the API repeatedly, returning `(first_response, throttled_response_or_None)`."""
        first_response = self.call_api()
        if first_response.status_code == 429:
            return first_response, first_response

        for _ in range(50):
            response = self.call_api()
            if response.status_code == 429:
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
        self.assertIn(self.rate_limit_policy_header_name, first_response.headers)
        self.assertIn(self.rate_limit_header_name, first_response.headers)
        self.assertIn(self.nautobot_cost_header_name, first_response.headers)

        self.assertIsNotNone(second_response)
        self.assertEqual(second_response.status_code, status.HTTP_200_OK)
        self.assertIn(self.rate_limit_policy_header_name, second_response.headers)
        self.assertIn(self.rate_limit_header_name, second_response.headers)
        self.assertIn(self.nautobot_cost_header_name, second_response.headers)

        first_response_remaining_budget = self.get_remaining_budget(first_response)
        second_response_remaining_budget = self.get_remaining_budget(second_response)

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
        self.assertIn(self.rate_limit_policy_header_name, api_response.headers)
        self.assertIn(self.rate_limit_header_name, api_response.headers)
        self.assertIn(self.nautobot_cost_header_name, api_response.headers)

        remaining_budget = self.get_remaining_budget(api_response)
        self.assertEqual(settings.NAUTOBOT_REST_RATE_LIMITING_BUDGET, remaining_budget)


    @override_settings(
        NAUTOBOT_REST_RATE_LIMITING_MODE="enforce",
        NAUTOBOT_REST_RATE_LIMITING_WINDOW_IN_SECONDS=3600,
        NAUTOBOT_REST_RATE_LIMITING_BUDGET=10,
    )
    def test_consumed_budget_accumulates_across_requests_until_the_budget_is_exhausted(self):
        first_response, throttled_response = self.call_api_until_throttled()

        self.assertIsNotNone(first_response)
        self.assertEqual(first_response.status_code, status.HTTP_200_OK)
        self.assertIn(self.rate_limit_policy_header_name, first_response.headers)
        self.assertIn(self.rate_limit_header_name, first_response.headers)
        self.assertIn(self.nautobot_cost_header_name, first_response.headers)

        self.assertIsNotNone(throttled_response)
        self.assertEqual(throttled_response.status_code, status.HTTP_429_TOO_MANY_REQUESTS)
        self.assertIn(self.rate_limit_policy_header_name, throttled_response.headers)
        self.assertIn(self.rate_limit_header_name, throttled_response.headers)
        self.assertIn(self.nautobot_cost_header_name, throttled_response.headers)

    @override_settings(NAUTOBOT_REST_RATE_LIMITING_MODE="enforce")
    def test_remaining_budget_decreases_between_requests(self):
        first_response = self.call_api()
        second_response = self.call_api()

        self.assertIsNotNone(first_response)
        self.assertEqual(first_response.status_code, status.HTTP_200_OK)
        self.assertIn(self.rate_limit_policy_header_name, first_response.headers)
        self.assertIn(self.rate_limit_header_name, first_response.headers)
        self.assertIn(self.nautobot_cost_header_name, first_response.headers)

        self.assertIsNotNone(second_response)
        self.assertEqual(second_response.status_code, status.HTTP_200_OK)
        self.assertIn(self.rate_limit_policy_header_name, second_response.headers)
        self.assertIn(self.rate_limit_header_name, second_response.headers)
        self.assertIn(self.nautobot_cost_header_name, second_response.headers)

        first_response_remaining_budget = self.get_remaining_budget(first_response)
        second_response_remaining_budget = self.get_remaining_budget(second_response)

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
        self.assertGreaterEqual(initial_retry_after, 3500)
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
        self.assertEqual(self.get_remaining_budget(first_throttled_response), 0)

        self.assertIsNotNone(second_throttled_response)
        self.assertEqual(self.get_remaining_budget(second_throttled_response), 0)

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

        remaining_budget = self.get_remaining_budget(api_response)

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
        first_response_cost = int(first_response.headers[self.nautobot_cost_header_name])
        first_response_remaining_budget = self.get_remaining_budget(first_response)

        self.assertEqual(first_response.status_code, status.HTTP_200_OK)
        self.assertGreater(first_response_cost, 1)
        self.assertEqual(first_response_remaining_budget, 0)

        second_response = self.client.get(device_list_url, **self.header)
        second_response_remaining_budget = self.get_remaining_budget(second_response)

        self.assertEqual(second_response.status_code, status.HTTP_429_TOO_MANY_REQUESTS)
        self.assertEqual(second_response_remaining_budget, 0)
        self.assertIn("Retry-After", second_response.headers)

    @override_settings(
        NAUTOBOT_REST_RATE_LIMITING_MODE="enforce",
        NAUTOBOT_REST_RATE_LIMITING_WINDOW_IN_SECONDS=3600,
        NAUTOBOT_REST_RATE_LIMITING_BUDGET=10,
    )
    def test_budget_resets_after_window_expires(self):
        _, throttled_response = self.call_api_until_throttled()
        self.assertIsNotNone(throttled_response)
        self.assertEqual(throttled_response.status_code, status.HTTP_429_TOO_MANY_REQUESTS)

        # Expiring the window is Redis dropping the bucket entirely, so deleting the key is what
        # actually reproduces it. `expire()` would only re-arm the TTL and leave the spend behind.
        bucket_id = get_rate_limit_bucket_id(self.header["HTTP_AUTHORIZATION"])
        get_redis_connection("default").delete(bucket_id)

        api_response = self.call_api()
        remaining_budget = self.get_remaining_budget(api_response)

        self.assertEqual(api_response.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(remaining_budget, 1)
