"""Tests for API rate limiting (nautobot.core.rate_limiting)."""

from django.test import RequestFactory, SimpleTestCase

from nautobot.core.rate_limiting.rest_calculator import classify_rest_read_request_features, RestReadRequestFeatures


class RestRequestFeaturesTestCase(SimpleTestCase):
    # TODO: Add unit tests
    pass


class ClassifyRestRequestFeaturesTestCase(SimpleTestCase):
    """REST cost calculator: classification and estimation, no Django stack involved."""

    factory = RequestFactory()

    def test_debug(self):
        # The FLAT_WEIGHTS preset turns the budget into a plain requests-per-window limit —
        # no dedicated code path, just configuration.
        test_path = "/api/dcim/devices/?limit=1000&depth=3&name__ic=foo"
        wsgi_request = self.factory.get(test_path)
        features = classify_rest_read_request_features(wsgi_request)
        # import pdb
        # pdb.set_trace()
        # cost, _ = costing.cost(self.factory.get(path))

    def test_features_default_instantion_has_correct_estimation(self):
        features = RestReadRequestFeatures()
        # TODO: Confirm default features
