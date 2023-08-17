import re
import urllib.parse

from django.contrib.contenttypes.models import ContentType
from django.test import override_settings
from django.test.utils import override_script_prefix
from django.urls import get_script_prefix, reverse
from prometheus_client.parser import text_string_to_metric_families

from nautobot.core.testing import TestCase
from nautobot.dcim.models.locations import Location
from nautobot.extras.choices import CustomFieldTypeChoices
from nautobot.extras.models.customfields import CustomField, CustomFieldChoice
from nautobot.extras.registry import registry


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
    def test_search_bar_redirect_to_login(self):
        self.client.logout()
        response = self.client.get(reverse("search") + "?q=prefix")
        # Assert that if the user is not logged in
        # SearchForm will redirect the user to the login Page
        self.assertEqual(response.status_code, 302)

    def test_global_and_model_search_bar(self):
        self.add_permissions("dcim.view_location", "dcim.view_device")

        # Assert model search bar present in list UI
        response = self.client.get(reverse("dcim:location_list"))
        self.assertInHTML(
            '<input type="text" name="q" class="form-control" required placeholder="Search Locations" id="id_q">',
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
        self.add_permissions("dcim.view_location", "circuits.view_circuit")

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

        response = self.client.get(reverse("dcim:location_list"))
        self.assertInHTML(
            filter_tabs,
            response.content.decode(response.charset),
        )

        response = self.client.get(reverse("circuits:circuit_list"))
        self.assertInHTML(
            filter_tabs,
            response.content.decode(response.charset),
        )

    def test_filtering_on_custom_select_filter_field(self):
        """Assert CustomField select and multiple select fields can be filtered using multiple entries"""
        self.add_permissions("dcim.view_location")

        multi_select_cf = CustomField.objects.create(
            type=CustomFieldTypeChoices.TYPE_MULTISELECT, label="Multiple Choice"
        )
        select_cf = CustomField.objects.create(type=CustomFieldTypeChoices.TYPE_SELECT, label="choice")
        choices = ["Foo", "Bar", "FooBar"]
        for cf in [multi_select_cf, select_cf]:
            cf.content_types.set([ContentType.objects.get_for_model(Location)])
            CustomFieldChoice.objects.create(custom_field=cf, value=choices[0])
            CustomFieldChoice.objects.create(custom_field=cf, value=choices[1])
            CustomFieldChoice.objects.create(custom_field=cf, value=choices[2])

        locations = Location.objects.all()[:3]
        for idx, location in enumerate(locations):
            location.cf[multi_select_cf.key] = choices[:2]
            location.cf[select_cf.key] = choices[idx]
            location.save()

        query_param = (
            f"?cf_{multi_select_cf.key}={choices[0]}&cf_{multi_select_cf.key}={choices[1]}"
            f"&cf_{select_cf.key}={choices[0]}&cf_{select_cf.key}={choices[1]}"
        )
        url = reverse("dcim:location_list") + query_param
        response = self.client.get(url)
        response_content = response.content.decode(response.charset).replace("\n", "")
        self.assertInHTML(locations[0].name, response_content)
        self.assertInHTML(locations[1].name, response_content)


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
    def test_installed_apps_visible_to_staff_with_hide_restricted_ui_true(self):
        """The "Installed Apps" menu item should be available to is_staff user regardless of HIDE_RESTRICTED_UI."""
        # Make user admin
        self.user.is_staff = True
        self.user.save()

        response_content = self.make_request()
        self.assertInHTML(
            f"""
            <a href="{self.url}"
                data-item-weight="{self.item_weight}">
                Installed Plugins
            </a>
            """,
            response_content,
        )

    @override_settings(HIDE_RESTRICTED_UI=False)
    def test_installed_apps_visible_to_staff_with_hide_restricted_ui_false(self):
        """The "Installed Apps" menu item should be available to is_staff user regardless of HIDE_RESTRICTED_UI."""
        # Make user admin
        self.user.is_staff = True
        self.user.save()

        response_content = self.make_request()
        self.assertInHTML(
            f"""
            <a href="{self.url}"
                data-item-weight="{self.item_weight}">
                Installed Plugins
            </a>
            """,
            response_content,
        )

    @override_settings(HIDE_RESTRICTED_UI=True)
    def test_installed_apps_not_visible_to_non_staff_user_with_hide_restricted_ui_true(self):
        """The "Installed Apps" menu item should be hidden from a non-staff user when HIDE_RESTRICTED_UI=True."""
        response_content = self.make_request()

        self.assertNotRegex(response_content, r"Installed\s+Apps")

    @override_settings(HIDE_RESTRICTED_UI=False)
    def test_installed_apps_disabled_to_non_staff_user_with_hide_restricted_ui_false(self):
        """The "Installed Apps" menu item should be disabled for a non-staff user when HIDE_RESTRICTED_UI=False."""
        response_content = self.make_request()

        # print(response_content)

        self.assertInHTML(
            f"""
            <a href="{self.url}"
                data-item-weight="{self.item_weight}">
                Installed Plugins
            </a>
            """,
            response_content,
        )


class LoginUI(TestCase):
    def setUp(self):
        super().setUp()

        self.footer_elements = [
            '<a href="#theme_modal" data-toggle="modal" data-target="#theme_modal" id="btn-theme-modal"><i class="mdi mdi-theme-light-dark text-primary"></i>Theme</a>',
            '<a href="/static/docs/index.html">Docs</a>',
            '<i class="mdi mdi-cloud-braces text-primary"></i> <a href="/api/docs/">API</a>',
            '<i class="mdi mdi-graphql text-primary"></i> <a href="/graphql/">GraphQL</a>',
            '<i class="mdi mdi-xml text-primary"></i> <a href="https://github.com/nautobot/nautobot">Code</a>',
            '<i class="mdi mdi-lifebuoy text-primary"></i> <a href="https://github.com/nautobot/nautobot/wiki">Help</a>',
        ]

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

    @override_settings(HIDE_RESTRICTED_UI=True, BANNER_TOP="Hello, Banner Top", BANNER_BOTTOM="Hello, Banner Bottom")
    def test_routes_redirect_back_to_login_if_hide_restricted_ui_true(self):
        """Assert that api docs and graphql redirects to login page if user is unauthenticated and HIDE_RESTRICTED_UI=True."""
        self.client.logout()
        headers = {"HTTP_ACCEPT": "text/html"}
        urls = [reverse("api_docs"), reverse("graphql")]
        for url in urls:
            response = self.client.get(url, follow=True, **headers)
            self.assertHttpStatus(response, 200)
            redirect_chain = [(f"/login/?next={url}", 302)]
            self.assertEqual(response.redirect_chain, redirect_chain)
            response_content = response.content.decode(response.charset).replace("\n", "")
            # Assert Footer items(`self.footer_elements`), Banner and Banner Top is hidden
            for footer_text in self.footer_elements:
                self.assertNotIn(footer_text, response_content)
            # Only API Docs implements BANNERS
            if url == urls[0]:
                self.assertNotIn("Hello, Banner Top", response_content)
                self.assertNotIn("Hello, Banner Bottom", response_content)

    @override_settings(HIDE_RESTRICTED_UI=False, BANNER_TOP="Hello, Banner Top", BANNER_BOTTOM="Hello, Banner Bottom")
    def test_routes_no_redirect_back_to_login_if_hide_restricted_ui_false(self):
        """Assert that api docs and graphql do not redirects to login page if user is unauthenticated and HIDE_RESTRICTED_UI=False."""
        self.client.logout()
        headers = {"HTTP_ACCEPT": "text/html"}
        urls = [reverse("api_docs"), reverse("graphql")]
        for url in urls:
            response = self.client.get(url, **headers)
            self.assertHttpStatus(response, 200)
            self.assertEqual(response.request["PATH_INFO"], url)
            response_content = response.content.decode(response.charset).replace("\n", "")
            # Assert Footer items(`self.footer_elements`), Banner and Banner Top is not hidden
            for footer_text in self.footer_elements:
                self.assertInHTML(footer_text, response_content)

            # Only API Docs implements BANNERS
            if url == urls[0]:
                self.assertInHTML("Hello, Banner Top", response_content)
                self.assertInHTML("Hello, Banner Bottom", response_content)


class MetricsViewTestCase(TestCase):
    def query_and_parse_metrics(self):
        response = self.client.get(reverse("metrics"))
        self.assertHttpStatus(response, 200, msg="/metrics should return a 200 HTTP status code.")
        page_content = response.content.decode(response.charset)
        return text_string_to_metric_families(page_content)

    def test_metrics_extensibility(self):
        """Assert that the example metric from the example plugin shows up _exactly_ when the plugin is enabled."""
        test_metric_name = "nautobot_example_metric_count"
        metrics_with_plugin = self.query_and_parse_metrics()
        metric_names_with_plugin = {metric.name for metric in metrics_with_plugin}
        self.assertIn(test_metric_name, metric_names_with_plugin)
        with override_settings(PLUGINS=[]):
            # Clear out the app metric registry because it is not updated when settings are changed but Nautobot is not
            # restarted.
            registry["app_metrics"].clear()
            metrics_without_plugin = self.query_and_parse_metrics()
            metric_names_without_plugin = {metric.name for metric in metrics_without_plugin}
            self.assertNotIn(test_metric_name, metric_names_without_plugin)
        metric_names_with_plugin.remove(test_metric_name)
        self.assertSetEqual(metric_names_with_plugin, metric_names_without_plugin)
