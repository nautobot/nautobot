"""Tests for the operator-overridable rate limiting complexity cost estimation function."""

from django.test import override_settings, RequestFactory, SimpleTestCase
from django.urls import reverse

from nautobot.core.rate_limiting.rest_calculator import (
    classify_rest_read_request_features,
    get_custom_rate_limiting_complexity_cost_estimation_function,
    READ_METHODS,
)
from nautobot.core.testing import APITestCase

SETTING = "NAUTOBOT_RATE_LIMITING_CUSTOM_COMPLEXITY_COST_ESTIMATION_FUNCTION"
THIS_MODULE = "nautobot.core.tests.test_rate_limiting_custom_complexity_cost_function"


def flat_cost_function(request):
    return 33


def method_aware_cost_function(request):
    cost = 33 if request.method in READ_METHODS else 77
    return cost


def feature_based_cost_function(request):
    rest_read_request_features = classify_rest_read_request_features(request)
    cost = 10 * rest_read_request_features.filter_count
    return cost


class GetCustomRateLimitingComplexityCostEstimationFunctionTestCase(SimpleTestCase):
    factory = RequestFactory()

    @override_settings(**{SETTING: ""})
    def test_returns_none_when_unset(self):
        custom_rate_limiting_cost_function = get_custom_rate_limiting_complexity_cost_estimation_function()
        self.assertIsNone(custom_rate_limiting_cost_function)

    @override_settings(**{SETTING: f"{THIS_MODULE}.flat_cost_function"})
    def test_resolves_configured_function(self):
        custom_rate_limiting_cost_function = get_custom_rate_limiting_complexity_cost_estimation_function()
        self.assertIs(custom_rate_limiting_cost_function, flat_cost_function)

    @override_settings(**{SETTING: "no_such_module.cost_function"})
    def test_raises_error_when_using_unimportable_module(self):
        with self.assertRaises(ImportError):
            get_custom_rate_limiting_complexity_cost_estimation_function()

    @override_settings(**{SETTING: f"{THIS_MODULE}.no_such_attribute"})
    def test_raises_on_missing_attribute(self):
        with self.assertRaises(ImportError):
            get_custom_rate_limiting_complexity_cost_estimation_function()

    @override_settings(**{SETTING: f"{THIS_MODULE}.feature_based_cost_function"})
    def test_default_nautobot_classification_still_supported_with_custom_estimation(self):
        """Test that default Nautobot cost classification can still be used."""
        request = self.factory.get("/api/dcim/devices/?name__ic=foo&status=active&tenant=bar")

        custom_rate_limiting_cost_function = get_custom_rate_limiting_complexity_cost_estimation_function()
        cost = custom_rate_limiting_cost_function(request)

        self.assertEqual(cost, 30)

    @override_settings(**{SETTING: f"{THIS_MODULE}.method_aware_cost_function"})
    def test_custom_estimation_function_can_price_by_http_method(self):
        custom_function = get_custom_rate_limiting_complexity_cost_estimation_function()

        get_dcim_devices_request = self.factory.get("/api/dcim/devices/")
        get_request_cost = custom_function(get_dcim_devices_request)

        post_dcim_devices_request = self.factory.post("/api/dcim/devices/")
        post_request_cost = custom_function(post_dcim_devices_request)

        self.assertEqual(get_request_cost, 33)
        self.assertEqual(post_request_cost, 77)


class CustomRateLimitingComplexityCostEstimationFunctionMiddlewareTestCase(APITestCase):
    def read_api(self):
        url = reverse("api-status")
        response = self.client.get(url, **self.header)
        return response

    def write_api(self):
        """The view rejects a POST, but the middleware prices the request before the view ever runs."""
        url = reverse("api-status")
        response = self.client.post(url, **self.header)
        return response

    @override_settings(
        NAUTOBOT_REST_RATE_LIMITING_MODE="report",
        **{SETTING: f"{THIS_MODULE}.method_aware_cost_function"},
    )
    def test_custom_function_prices_read_requests(self):
        response = self.read_api()
        complexity_cost_header = response.headers["X-Nautobot-Cost"]

        self.assertEqual(complexity_cost_header, "33")

    @override_settings(
        NAUTOBOT_REST_RATE_LIMITING_MODE="report",
        **{SETTING: f"{THIS_MODULE}.method_aware_cost_function"},
    )
    def test_custom_function_prices_write_requests(self):
        response = self.write_api()
        complexity_cost_header = response.headers["X-Nautobot-Cost"]

        self.assertEqual(complexity_cost_header, "77")

    @override_settings(
        NAUTOBOT_REST_RATE_LIMITING_MODE="report",
        NAUTOBOT_REST_RATE_LIMITING_READ_COST=1.0,
        NAUTOBOT_REST_RATE_LIMITING_PAGINATION_COST=3.0,
        **{SETTING: ""},
    )
    def test_builtin_estimate_is_used_when_unset(self):
        response = self.read_api()
        complexity_cost_header = response.headers["X-Nautobot-Cost"]

        self.assertEqual(complexity_cost_header, "4")

    @override_settings(
        NAUTOBOT_REST_RATE_LIMITING_MODE="enforce",
        NAUTOBOT_REST_RATE_LIMITING_BUDGET=1000,
        **{SETTING: f"{THIS_MODULE}.flat_cost_function"},
    )
    def test_custom_cost_is_charged_against_budget(self):
        response = self.read_api()
        rate_limit_header = response.headers["RateLimit"]

        self.assertIn("r=967;", rate_limit_header)
