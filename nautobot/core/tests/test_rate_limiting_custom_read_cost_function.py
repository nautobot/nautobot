"""Tests for the operator-overridable REST read complexity cost function."""

from django.test import override_settings, SimpleTestCase
from django.urls import reverse

from nautobot.core.rate_limiting.rest_calculator import (
    get_custom_rest_request_read_complexity_cost_estimation_function,
    RestReadRequestFeatures,
)
from nautobot.core.testing import APITestCase

SETTING = "NAUTOBOT_REST_RATE_LIMITING_CUSTOM_READ_COMPLEXITY_COST_ESTIMATION_FUNCTION"
THIS_MODULE = "nautobot.core.tests.test_rate_limiting_custom_read_cost_function"


def flat_cost_function(read_request_features):
    return 33


def rest_request_filter_count_cost_function(read_request_features):
    return 10 * read_request_features.filter_count


class GetCustomRestRequestReadComplexityCostEstimationFunctionTestCase(SimpleTestCase):
    @override_settings(**{SETTING: ""})
    def test_returns_none_when_unset(self):
        custom_rest_request_cost_estimation = get_custom_rest_request_read_complexity_cost_estimation_function()
        self.assertIsNone(custom_rest_request_cost_estimation)

    @override_settings(**{SETTING: f"{THIS_MODULE}.flat_cost_function"})
    def test_resolves_configured_function(self):
        custom_rest_request_cost_estimation = get_custom_rest_request_read_complexity_cost_estimation_function()
        self.assertIs(custom_rest_request_cost_estimation, flat_cost_function)

    @override_settings(**{SETTING: "no_such_module.cost_function"})
    def test_raises_error_when_using_unimportable_module(self):
        with self.assertRaises(ImportError):
            get_custom_rest_request_read_complexity_cost_estimation_function()

    @override_settings(**{SETTING: f"{THIS_MODULE}.no_such_attribute"})
    def test_raises_on_missing_attribute(self):
        with self.assertRaises(ImportError):
            get_custom_rest_request_read_complexity_cost_estimation_function()


class CustomRestRequestReadComplexityCostEstimationFunctionTestCase(APITestCase):
    @override_settings(**{SETTING: f"{THIS_MODULE}.rest_request_filter_count_cost_function"})
    def test_custom_function_calls_successfully_with_correct_calculation(self):
        custom_rest_request_cost_estimation = get_custom_rest_request_read_complexity_cost_estimation_function()
        read_request_with_filter_cost = custom_rest_request_cost_estimation(RestReadRequestFeatures(filter_count=3))

        self.assertEqual(read_request_with_filter_cost, 30)


class CustomCostFunctionMiddlewareTestCase(APITestCase):
    def call_api(self):
        return self.client.get(reverse("api-status"), **self.header)

    @override_settings(
        NAUTOBOT_REST_RATE_LIMITING_MODE="report",
        **{SETTING: f"{THIS_MODULE}.flat_cost_function"},
    )
    def test_custom_cost_is_reported_in_header(self):
        response = self.call_api()

        self.assertEqual(response.headers["X-Nautobot-Cost"], "33")

    @override_settings(NAUTOBOT_REST_RATE_LIMITING_MODE="report", **{SETTING: ""})
    def test_builtin_cost_is_used_when_unset(self):
        response = self.call_api()

        self.assertNotEqual(response.headers["X-Nautobot-Cost"], "33")

    @override_settings(
        NAUTOBOT_REST_RATE_LIMITING_MODE="enforce",
        NAUTOBOT_REST_RATE_LIMITING_BUDGET=1000,
        **{SETTING: f"{THIS_MODULE}.flat_cost_function"},
    )
    def test_custom_cost_is_charged_against_budget(self):
        response = self.call_api()

        self.assertIn("r=967;", response.headers["RateLimit"])
