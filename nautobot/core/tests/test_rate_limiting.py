"""Tests for API rate limiting (nautobot.core.rate_limiting)."""

from django.test import RequestFactory, SimpleTestCase

from nautobot.core.rate_limiting.rest_calculator import classify_rest_read_request_features, RestReadRequestFeatures


class RestReadRequestFeaturesTestCase(SimpleTestCase):
    pass


class ClassifyRestReadRequestFeaturesTestCase(SimpleTestCase):
    """REST cost calculator: classification and estimation, no Django stack involved."""

    # factory = RequestFactory()

    def test_features_default_instantion_has_correct_estimation(self):
        # test_path = "/api/dcim/devices/?limit=1000&depth=3&name__ic=foo"
        # wsgi_request = self.factory.get(test_path)

        # features = RestReadRequestFeatures()
        # TODO: Confirm default features
