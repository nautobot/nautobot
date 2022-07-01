import re
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

    def make_request(self):
        url = reverse("home")
        response = self.client.get(url)

        # Search bar in nav
        nav_search_bar_pattern = re.compile(
            '<nav.*<form action="/search/" method="get" class="navbar-form navbar-right" id="navbar_search" role="search">.*</form>.*</nav>'
        )
        nav_search_bar_result = nav_search_bar_pattern.search(
            response.content.decode(response.charset).replace("\n", "")
        )

        # Global search bar in body/container-fluid wrapper
        body_search_bar_pattern = re.compile(
            '<div class="container-fluid wrapper">.*<form action="/search/" method="get" class="form-inline">.*</form>.*</div>'
        )
        body_search_bar_result = body_search_bar_pattern.search(
            response.content.decode(response.charset).replace("\n", "")
        )

        return nav_search_bar_result, body_search_bar_result

    @override_settings(HIDE_RESTRICTED_UI=True)
    def test_search_bar_not_visible_if_user_not_authenticated_and_hide_restricted_ui_True(self):
        self.client.logout()

        nav_search_bar_result, body_search_bar_result = self.make_request()

        self.assertIsNone(nav_search_bar_result)
        self.assertIsNone(body_search_bar_result)

    @override_settings(HIDE_RESTRICTED_UI=False)
    def test_search_bar_visible_if_user_authenticated_and_hide_restricted_ui_True(self):
        nav_search_bar_result, body_search_bar_result = self.make_request()

        self.assertIsNotNone(nav_search_bar_result)
        self.assertIsNotNone(body_search_bar_result)

    @override_settings(HIDE_RESTRICTED_UI=False)
    def test_search_bar_visible_if_hide_restricted_ui_False(self):
        # Assert if user is authenticated
        nav_search_bar_result, body_search_bar_result = self.make_request()

        self.assertIsNotNone(nav_search_bar_result)
        self.assertIsNotNone(body_search_bar_result)

        # Assert if user is logout
        self.client.logout()
        nav_search_bar_result, body_search_bar_result = self.make_request()

        self.assertIsNotNone(nav_search_bar_result)
        self.assertIsNotNone(body_search_bar_result)


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


class NavRestrictedUI(TestCase):
    def make_request(self):
        response = self.client.get(reverse("home"))
        response_body = response.content.decode(response.charset).replace("\n", "")
        return re.compile(r'<nav.*<li class="dropdown-header".*General</li>.*Installed Plugins.*</nav>').search(
            response_body
        )

    @override_settings(HIDE_RESTRICTED_UI=True)
    def test_installed_plugins_visible_to_admin_with_hide_restricted_ui_True(self):
        # Make user admin
        self.user.is_staff = True
        self.user.is_superuser = True
        self.user.save()

        search_result = self.make_request()

        self.assertIsNotNone(search_result)

    @override_settings(HIDE_RESTRICTED_UI=False)
    def test_installed_plugins_visible_to_admin_with_hide_restricted_ui_False(self):
        # Make user admin
        self.user.is_staff = True
        self.user.is_superuser = True
        self.user.save()

        search_result = self.make_request()

        self.assertIsNotNone(search_result)

    @override_settings(HIDE_RESTRICTED_UI=True)
    def test_installed_plugins_not_visible_to_user_with_hide_restricted_ui_True(self):
        search_result = self.make_request()

        self.assertIsNone(search_result)

    @override_settings(HIDE_RESTRICTED_UI=False)
    def test_installed_plugins_not_visible_to_user_with_hide_restricted_ui_False(self):
        search_result = self.make_request()

        self.assertIsNone(search_result)
