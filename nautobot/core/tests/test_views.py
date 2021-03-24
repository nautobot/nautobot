import urllib.parse

from django.test import override_settings
from django.urls import get_script_prefix, reverse

from nautobot.utilities.testing import TestCase


class HomeViewTestCase(TestCase):
    def test_home(self):

        url = reverse("home")

        response = self.client.get(url)
        self.assertHttpStatus(response, 200)

    def test_search(self):

        url = reverse("search")
        params = {
            "q": "foo",
        }

        response = self.client.get("{}?{}".format(url, urllib.parse.urlencode(params)))
        self.assertHttpStatus(response, 200)


class ForceScriptNameTestcase(TestCase):
    """Basic test to assert that `settings.FORCE_SCRIPT_NAME` works as intended."""

    @override_settings(
        FORCE_SCRIPT_NAME="/nautobot",
    )
    def test_subdirectory_routes(self):
        prefix = get_script_prefix()
        routes = ("home", "login", "search", "api-root")
        for route in routes:
            url = reverse(route)
            self.assertTrue(url.startswith(prefix))
