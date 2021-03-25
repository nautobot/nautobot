import urllib.parse

from django.conf import settings
from django.test import override_settings
from django.urls import get_script_prefix, set_script_prefix, reverse

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
        FORCE_SCRIPT_NAME="/nautobot/",
    )
    def test_subdirectory_routes(self):
        # We must call `set_script_prefix()` to set the URL resolver script prefix outside of the
        # request/response cycle (e.g. in scripts/tests) to generate correct URLs when `SCRIPT_NAME`
        # is not `/`.
        #
        # We must then call it again to reset the script pefix after we're done because
        # the state is stored in the thread-local scope and will "infect" other tests.
        # with override_settings(FORCE_SCRIPT_NAME="/nautobot/"):
        try:
            original_prefix = get_script_prefix()

            set_script_prefix(settings.FORCE_SCRIPT_NAME)
            prefix = get_script_prefix()
            self.assertEqual(prefix, "/nautobot/")

            # And that routes will start w/ the prefix vs. just "/" (the default).
            routes = ("home", "login", "search", "api-root")
            for route in routes:
                url = reverse(route)
                self.assertTrue(url.startswith(prefix))

        # Reset the script prefix when we're done.
        finally:
            set_script_prefix(original_prefix)

        self.assertEqual(get_script_prefix(), original_prefix)
