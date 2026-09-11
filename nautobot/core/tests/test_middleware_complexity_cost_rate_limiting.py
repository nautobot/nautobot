from django.test import override_settings, RequestFactory
from django.urls import reverse

from nautobot.core.middleware import (
    ComplexityCostRateLimitingMiddleware,
)
from nautobot.core.testing import APITestCase


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
