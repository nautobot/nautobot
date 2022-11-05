import re
import urllib.parse

from django.test import override_settings
from django.test.utils import override_script_prefix
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

        response = self.client.get(f"{url}?{urllib.parse.urlencode(params)}")
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

    @override_settings(VERSION="1.2.3")
    def test_footer_version_visible_authenticated_users_only(self):
        url = reverse("home")
        response = self.client.get(url)
        response_content = response.content.decode(response.charset).replace("\n", "")

        footer_hostname_version_pattern = re.compile(r'<p class="text-muted">\s+\S+\s+\(v1\.2\.3\)\s+</p>')
        self.assertRegex(response_content, footer_hostname_version_pattern)

        self.client.logout()
        response = self.client.get(url)
        response_content = response.content.decode(response.charset).replace("\n", "")
        self.assertNotRegex(response_content, footer_hostname_version_pattern)


@override_settings(BRANDING_TITLE="Nautobot")
class SearchFieldsTestCase(TestCase):
    def test_global_and_model_search_bar(self):
        self.add_permissions("dcim.view_site", "dcim.view_device")

        # Assert model search bar present in list UI
        response = self.client.get(reverse("dcim:site_list"))
        self.assertInHTML(
            '<input type="text" name="q" class="form-control" required placeholder="Search Sites" id="id_q">',
            response.content.decode(response.charset),
        )

        response = self.client.get(reverse("dcim:device_list"))
        self.assertInHTML(
            '<input type="text" name="q" class="form-control" required placeholder="Search Devices" id="id_q">',
            response.content.decode(response.charset),
        )

        # Assert global search bar present in UI
        self.assertInHTML(
            '<input type="text" name="q" class="form-control" placeholder="Search Nautobot">',
            response.content.decode(response.charset),
        )


class FilterFormsTestCase(TestCase):
    def test_support_for_both_default_and_dynamic_filter_form_in_ui(self):
        self.add_permissions("dcim.view_site", "circuits.view_circuit")

        filter_tabs = """
            <ul id="tabs" class="nav nav-tabs">
                <li role="presentation" class="active">
                    <a href="#default-filter" role="tab" data-toggle="tab">
                        Default
                    </a>
                </li>
                <li role="presentation" class="">
                    <a href="#advanced-filter" role="tab" data-toggle="tab">
                        Advanced
                    </a>
                </li>
            </ul>
            """

        response = self.client.get(reverse("dcim:site_list"))
        self.assertInHTML(
            filter_tabs,
            response.content.decode(response.charset),
        )

        response = self.client.get(reverse("circuits:circuit_list"))
        self.assertInHTML(
            filter_tabs,
            response.content.decode(response.charset),
        )


class ForceScriptNameTestcase(TestCase):
    """Basic test to assert that `settings.FORCE_SCRIPT_NAME` works as intended."""

    @override_settings(
        FORCE_SCRIPT_NAME="/nautobot/",
    )
    @override_script_prefix("/nautobot/")
    def test_subdirectory_routes(self):
        # We must call `set_script_prefix()` to set the URL resolver script prefix outside of the
        # request/response cycle (e.g. in scripts/tests) to generate correct URLs when `SCRIPT_NAME`
        # is not `/`.
        #
        # We must then call it again to reset the script pefix after we're done because
        # the state is stored in the thread-local scope and will "infect" other tests.
        prefix = get_script_prefix()
        self.assertEqual(prefix, "/nautobot/")

        # And that routes will start w/ the prefix vs. just "/" (the default).
        routes = ("home", "login", "search", "api-root")
        for route in routes:
            url = reverse(route)
            self.assertTrue(url.startswith(prefix))


class NavRestrictedUI(TestCase):
    def setUp(self):
        super().setUp()

        self.url = reverse("plugins:plugins_list")
        self.item_weight = 100  # TODO: not easy to introspect from the nav menu struct, so hard-code it here for now

    def make_request(self):
        response = self.client.get(reverse("home"))
        return response.content.decode(response.charset)

    @override_settings(HIDE_RESTRICTED_UI=True)
    def test_installed_plugins_visible_to_staff_with_hide_restricted_ui_true(self):
        """The "Installed Plugins" menu item should be available to is_staff user regardless of HIDE_RESTRICTED_UI."""
        # Make user admin
        self.user.is_staff = True
        self.user.save()

        response_content = self.make_request()
        self.assertInHTML(
            f"""
            <li>
              <div class="buttons pull-right"></div>
              <a href="{self.url}" data-item-weight="{self.item_weight}">Installed Plugins</a>
            </li>
            """,
            response_content,
        )

    @override_settings(HIDE_RESTRICTED_UI=False)
    def test_installed_plugins_visible_to_staff_with_hide_restricted_ui_false(self):
        """The "Installed Plugins" menu item should be available to is_staff user regardless of HIDE_RESTRICTED_UI."""
        # Make user admin
        self.user.is_staff = True
        self.user.save()

        response_content = self.make_request()
        self.assertInHTML(
            f"""
            <li>
              <div class="buttons pull-right"></div>
              <a href="{self.url}" data-item-weight="{self.item_weight}">Installed Plugins</a>
            </li>
            """,
            response_content,
        )

    @override_settings(HIDE_RESTRICTED_UI=True)
    def test_installed_plugins_not_visible_to_non_staff_user_with_hide_restricted_ui_true(self):
        """The "Installed Plugins" menu item should be hidden from a non-staff user when HIDE_RESTRICTED_UI=True."""
        response_content = self.make_request()

        self.assertNotRegex(response_content, r"Installed\s+Plugins")

    @override_settings(HIDE_RESTRICTED_UI=False)
    def test_installed_plugins_disabled_to_non_staff_user_with_hide_restricted_ui_false(self):
        """The "Installed Plugins" menu item should be disabled for a non-staff user when HIDE_RESTRICTED_UI=False."""
        response_content = self.make_request()

        self.assertInHTML(
            f"""
            <li class="disabled">
              <div class="buttons pull-right"></div>
              <a href="{self.url}" data-item-weight="{self.item_weight}">Installed Plugins</a>
            </li>
            """,
            response_content,
        )


class LoginUI(TestCase):
    def make_request(self):
        response = self.client.get(reverse("login"))
        sso_login_pattern = re.compile('<a href=".*">Continue with SSO</a>')
        return sso_login_pattern.search(response.content.decode(response.charset))

    def test_sso_login_button_not_visible(self):
        """Test Continue with SSO button not visible if SSO is enabled"""
        self.client.logout()

        sso_login_search_result = self.make_request()
        self.assertIsNone(sso_login_search_result)

    @override_settings(
        AUTHENTICATION_BACKENDS=[
            "social_core.backends.google.GoogleOAuth2",
            "nautobot.core.authentication.ObjectPermissionBackend",
        ]
    )
    def test_sso_login_button_visible(self):
        self.client.logout()
        sso_login_search_result = self.make_request()
        self.assertIsNotNone(sso_login_search_result)
