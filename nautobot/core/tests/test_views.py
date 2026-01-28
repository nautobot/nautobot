import json
import os
from pathlib import Path
import re
import tempfile
from unittest import mock
import urllib.parse

from django.apps import apps
from django.contrib.contenttypes.models import ContentType
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings, RequestFactory, tag
from django.test.utils import override_script_prefix
from django.urls import get_script_prefix, reverse
from prometheus_client.parser import text_string_to_metric_families

from nautobot.circuits.models import Circuit, CircuitType, Provider
from nautobot.core.constants import GLOBAL_SEARCH_EXCLUDE_LIST
from nautobot.core.testing import TestCase
from nautobot.core.testing.api import APITestCase
from nautobot.core.testing.context import load_event_broker_override_settings
from nautobot.core.testing.utils import extract_page_body
from nautobot.core.utils.permissions import get_permission_for_model
from nautobot.core.views import NautobotMetricsView
from nautobot.core.views.mixins import GetReturnURLMixin
from nautobot.core.views.utils import METRICS_CACHE_KEY
from nautobot.dcim.models.locations import Location
from nautobot.extras.choices import CustomFieldTypeChoices
from nautobot.extras.models import FileProxy, Status
from nautobot.extras.models.customfields import CustomField, CustomFieldChoice
from nautobot.extras.registry import registry
from nautobot.users.models import ObjectPermission
from nautobot.users.utils import serialize_user_without_config_and_views


class GetReturnURLMixinTestCase(TestCase):
    """Tests for the API of GetReturnURLMixin."""

    @classmethod
    def setUpTestData(cls):
        cls.factory = RequestFactory(SERVER_NAME="nautobot.example.com")
        cls.mixin = GetReturnURLMixin()

    def test_get_return_url_explicit(self):
        request = self.factory.get("/", {"return_url": "/dcim/devices/"})
        self.assertEqual(self.mixin.get_return_url(request=request, obj=None), "/dcim/devices/")
        self.assertEqual(self.mixin.get_return_url(request=request, obj=Location.objects.first()), "/dcim/devices/")

        request = self.factory.get("/", {"return_url": "/dcim/devices/?status=Active"})
        self.assertEqual(self.mixin.get_return_url(request=request, obj=None), "/dcim/devices/?status=Active")

    def test_get_return_url_explicit_unsafe(self):
        request = self.factory.get("/", {"return_url": "http://example.com"})
        self.assertEqual(self.mixin.get_return_url(request=request, obj=None), reverse("home"))

    def test_get_return_url_explicit_punycode(self):
        """
        Replace the 'i' in '/dcim/' with a unicode dotless 'ı' and make sure we're not fooled by it.
        """  # noqa: RUF002  # ambiguous-unicode-character-docstring -- fully intentional here!
        request = self.factory.get("/", {"return_url": "/dcım/devices/"})  # noqa: RUF001  # ambiguous-unicode-character-string -- fully intentional here!
        self.assertEqual(self.mixin.get_return_url(request=request, obj=None), "/dc%C4%B1m/devices/")

    def test_get_return_url_default_with_obj(self):
        request = self.factory.get("/")
        location = Location.objects.first()
        self.assertEqual(self.mixin.get_return_url(request=request, obj=location), location.get_absolute_url())


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

    def test_appropriate_models_included_in_global_search(self):
        # Gather core app configs
        existing_models = []
        global_searchable_models = []
        for app_name in ["circuits", "dcim", "extras", "ipam", "tenancy", "virtualization"]:
            app_config = apps.get_app_config(app_name)
            existing_models += [model._meta.model_name for model in app_config.get_models()]
            global_searchable_models += app_config.searchable_models

        # Remove those models that are not searchable
        existing_models = [model for model in existing_models if model not in GLOBAL_SEARCH_EXCLUDE_LIST]
        existing_models.sort()

        # See if there are any models that are missing from global search
        difference = [model for model in existing_models if model not in global_searchable_models]
        if difference:
            self.fail(
                f"Existing model/models {','.join(difference)} are not included in the searchable_models attribute of the app config.\n"
                "If you do not want the models to be searchable, please include them in the GLOBAL_SEARCH_EXCLUDE_LIST constant in nautobot.core.constants."
            )

    def make_request(self):
        url = reverse("home")
        response = self.client.get(url)

        # Search bar in header
        header_search_bar_pattern = re.compile(
            '<header.*<form action="/search/" class="col-4 text-center" id="header_search" method="get" role="search">.*</form>.*</header>'
        )
        header_search_bar_result = header_search_bar_pattern.search(
            response.content.decode(response.charset).replace("\n", "")
        )

        return header_search_bar_result

    def test_search_bar_not_visible_if_user_not_authenticated(self):
        self.client.logout()

        header_search_bar_result = self.make_request()

        self.assertIsNone(header_search_bar_result)

    def test_search_bar_visible_if_user_authenticated(self):
        header_search_bar_result = self.make_request()

        self.assertIsNotNone(header_search_bar_result)

    @override_settings(VERSION="1.2.3")
    def test_footer_version_visible_authenticated_users_only(self):
        url = reverse("home")
        response = self.client.get(url)
        response_content = response.content.decode(response.charset).replace("\n", "")

        footer_hostname_version_pattern = re.compile(r"<span>\s+\S+\s+\(v1\.2\.3\)\s+</span>")
        self.assertRegex(response_content, footer_hostname_version_pattern)

        self.client.logout()
        response = self.client.get(url)
        response_content = response.content.decode(response.charset).replace("\n", "")
        self.assertNotRegex(response_content, footer_hostname_version_pattern)

    def test_banners_markdown(self):
        url = reverse("home")
        with override_settings(
            BANNER_TOP="# Hello world",
            BANNER_BOTTOM="[info](https://nautobot.com)",
        ):
            response = self.client.get(url)
        self.assertBodyContains(response, "<h1>Hello world</h1>", html=True)
        self.assertBodyContains(
            response, '<a href="https://nautobot.com" rel="noopener noreferrer">info</a>', html=True
        )

        with override_settings(BANNER_LOGIN="_Welcome to Nautobot!_"):
            self.client.logout()
            response = self.client.get(reverse("login"))
        self.assertBodyContains(response, "<em>Welcome to Nautobot!</em>", html=True)

    def test_banners_no_xss(self):
        url = reverse("home")
        with override_settings(
            BANNER_TOP='<script>alert("Hello from above!");</script>',
            BANNER_BOTTOM='<script>alert("Hello from below!");</script>',
        ):
            response = self.client.get(url)
        self.assertNotIn("Hello from above", response.content.decode(response.charset))
        self.assertNotIn("Hello from below", response.content.decode(response.charset))

        with override_settings(BANNER_LOGIN='<script>alert("Welcome to Nautobot!");</script>'):
            self.client.logout()
            response = self.client.get(reverse("login"))
        self.assertNotIn("Welcome to Nautobot!", response.content.decode(response.charset))


class AppDocsViewTestCase(TestCase):
    def setUp(self):
        super().setUp()
        self.test_app_label = "test_app"
        self.test_base_url = "test-app"

        # Create temp docs dir
        # I use tearDown to clean up, so this is save
        self.temp_dir = tempfile.TemporaryDirectory()  # pylint: disable=consider-using-with
        self.docs_path = Path(self.temp_dir.name) / "docs"
        self.docs_path.mkdir(parents=True)
        (self.docs_path / "index.html").write_text("<html>Test Index</html>")
        (self.docs_path / "css/style.css").parent.mkdir(parents=True, exist_ok=True)
        (self.docs_path / "css/style.css").write_text("body { background: #fff; }")

    def tearDown(self):
        self.temp_dir.cleanup()
        super().tearDown()

    def test_docs_index_redirect(self):
        """Ensure /docs/<base_url>/ redirects to /docs/<base_url>/index.html."""
        url = reverse("docs_index_redirect", kwargs={"app_base_url": self.test_base_url})
        response = self.client.get(url, follow=False)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], f"/docs/{self.test_base_url}/index.html")

    def test_docs_index_redirect_if_not_logged_in(self):
        self.client.logout()
        url = reverse("docs_index_redirect", kwargs={"app_base_url": self.test_base_url})
        response = self.client.get(url, follow=False)

        # First, the redirect to /docs/<base_url>/index.html
        self.assertEqual(response.status_code, 302)
        redirect_url = f"/docs/{self.test_base_url}/index.html"
        self.assertEqual(response["Location"], redirect_url)

        # Follow the redirect to AppDocsView, which should require login
        response = self.client.get(redirect_url)
        self.assertRedirects(
            response,
            expected_url=f"{reverse('login')}?next={redirect_url}",
            status_code=302,
            target_status_code=200,
        )

    def test_docs_file_redirect_if_not_logged_in(self):
        self.client.logout()
        url = reverse("docs_file", kwargs={"app_base_url": self.test_base_url, "path": "css/style.css"})
        response = self.client.get(url)
        # LoginRequiredMixin redirects to /accounts/login/
        self.assertRedirects(
            response,
            expected_url=f"{reverse('login')}?next={url}",
            status_code=302,
            target_status_code=200,
        )

    @mock.patch.dict("nautobot.core.views.BASE_URL_TO_APP_LABEL", {"test-app": "test_app"})
    @mock.patch("nautobot.core.views.resources.files")
    def test_access_denied_path_traversal_attempts(self, mock_resources_files):
        """Ensure ../ or similar traversal patterns are rejected."""
        mock_resources_files.return_value = Path(self.temp_dir.name)

        malicious_paths = [
            "../settings.py",
            "../../etc/passwd",
            "docs/../../secret.txt",
        ]

        for path in malicious_paths:
            with self.subTest(path=path):
                url = reverse("docs_file", kwargs={"app_base_url": self.test_base_url, "path": path})
                response = self.client.get(url)
                self.assertEqual(response.status_code, 403)

    @mock.patch.dict("nautobot.core.views.BASE_URL_TO_APP_LABEL", {"test-app": "test_app"})
    @mock.patch("nautobot.core.views.resources.files")
    def test_serve_index_html_logged_in(self, mock_resources_files):
        mock_resources_files.return_value = Path(self.temp_dir.name)
        url = reverse("docs_index_redirect", kwargs={"app_base_url": self.test_base_url, "path": "index.html"})
        response = self.client.get(url, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Test Index")
        self.assertEqual(response["Content-Type"], "text/html")

    @mock.patch.dict("nautobot.core.views.BASE_URL_TO_APP_LABEL", {"test-app": "test_app"})
    @mock.patch("nautobot.core.views.resources.files")
    def test_serve_css_logged_in(self, mock_resources_files):
        mock_resources_files.return_value = Path(self.temp_dir.name)
        url = reverse("docs_file", kwargs={"app_base_url": self.test_base_url, "path": "css/style.css"})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "background: #fff;")
        self.assertEqual(response["Content-Type"], "text/css")

    @mock.patch.dict("nautobot.core.views.BASE_URL_TO_APP_LABEL", {"test-app": "test_app"})
    @mock.patch("nautobot.core.views.resources.files")
    def test_docs_index_nonexistent_app(self, mock_resources_files):
        mock_resources_files.return_value = Path(self.temp_dir.name)
        url = reverse("docs_index_redirect", kwargs={"app_base_url": "nonexistent-app"})
        response = self.client.get(url, follow=True)
        self.assertEqual(response.status_code, 404)
        self.assertJSONEqual(response.content, {"detail": "Unknown base_url 'nonexistent-app'."})

    @mock.patch.dict("nautobot.core.views.BASE_URL_TO_APP_LABEL", {"test-app": "test_app"})
    @mock.patch("nautobot.core.views.resources.files")
    def test_docs_file_nonexistent_app(self, mock_resources_files):
        mock_resources_files.return_value = Path(self.temp_dir.name)
        url = reverse("docs_file", kwargs={"app_base_url": "nonexistent-app", "path": "css/style.css"})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)
        self.assertJSONEqual(response.content, {"detail": "Unknown base_url 'nonexistent-app'."})

    @mock.patch.dict("nautobot.core.views.BASE_URL_TO_APP_LABEL", {"test-app": "test_app"})
    @mock.patch("nautobot.core.views.resources.files")
    def test_nonexistent_file(self, mock_resources_files):
        mock_resources_files.return_value = Path(self.temp_dir.name)
        test_cases = ["/../missing.html", "//../missing.html", "missing.html", "missing_dir/missing.html"]
        for path in test_cases:
            with self.subTest(path=path):
                url = reverse("docs_file", kwargs={"app_base_url": self.test_base_url, "path": path})
                response = self.client.get(url)
                self.assertEqual(response.status_code, 404)
                self.assertIn("File", response.json()["detail"])


class MediaViewTestCase(TestCase):
    def test_media_unauthenticated(self):
        """
        Test that unauthenticated users are redirected to login when accessing media files whether they exist or not.
        """
        with tempfile.TemporaryDirectory() as temp_dir:
            with override_settings(
                MEDIA_ROOT=temp_dir,
                BRANDING_FILEPATHS={"logo": os.path.join("branding", "logo.txt")},
            ):
                file_path = os.path.join(temp_dir, "foo.txt")
                url = reverse("media", kwargs={"path": "foo.txt"})
                self.client.logout()

                # Unauthenticated request to nonexistent media file should redirect to login page
                response = self.client.get(url)
                self.assertRedirects(
                    response, expected_url=f"{reverse('login')}?next={url}", status_code=302, target_status_code=200
                )

                # Unauthenticated request to existent media file should redirect to login page as well
                with open(file_path, "w") as f:
                    f.write("Hello, world!")
                response = self.client.get(url)
                self.assertRedirects(
                    response, expected_url=f"{reverse('login')}?next={url}", status_code=302, target_status_code=200
                )

    def test_branding_media(self):
        """
        Test that users can access branding files listed in `settings.BRANDING_FILEPATHS` regardless of authentication.
        """
        with tempfile.TemporaryDirectory() as temp_dir:
            with override_settings(
                MEDIA_ROOT=temp_dir,
                BRANDING_FILEPATHS={"logo": os.path.join("branding", "logo.txt")},
            ):
                os.makedirs(os.path.join(temp_dir, "branding"))
                file_path = os.path.join(temp_dir, "branding", "logo.txt")
                with open(file_path, "w") as f:
                    f.write("Hello, world!")

                url = reverse("media", kwargs={"path": "branding/logo.txt"})

                # Authenticated request succeeds
                response = self.client.get(url)
                self.assertHttpStatus(response, 200)
                self.assertIn("Hello, world!", b"".join(response).decode(response.charset))

                # Unauthenticated request also succeeds
                self.client.logout()
                response = self.client.get(url)
                self.assertHttpStatus(response, 200)
                self.assertIn("Hello, world!", b"".join(response).decode(response.charset))

    def test_media_authenticated(self):
        """
        Test that authenticated users can access regular media files stored in the `MEDIA_ROOT`.
        """
        with tempfile.TemporaryDirectory() as temp_dir:
            with override_settings(MEDIA_ROOT=temp_dir):
                file_path = os.path.join(temp_dir, "foo.txt")
                with open(file_path, "w") as f:
                    f.write("Hello, world!")

                url = reverse("media", kwargs={"path": "foo.txt"})
                response = self.client.get(url)
                self.assertHttpStatus(response, 200)
                self.assertIn("Hello, world!", b"".join(response).decode(response.charset))


@override_settings(BRANDING_TITLE="Nautobot")
class SearchFieldsTestCase(TestCase):
    def test_search_bar_redirect_to_login(self):
        self.client.logout()
        response = self.client.get(reverse("search") + "?q=prefix")
        # Assert that if the user is not logged in
        # SearchForm will redirect the user to the login Page
        self.assertEqual(response.status_code, 302)

    def test_global_search_bar_scoped_to_model(self):
        self.add_permissions("dcim.view_location", "dcim.view_device")

        # Assert model search bar present in list UI
        response = self.client.get(reverse("dcim:location_list"))
        self.assertBodyContains(
            response,
            '<input aria-placeholder="Press Ctrl+K to search" class="form-control nb-text-transparent" name="q" type="search" value="">',
            html=True,
        )
        self.assertBodyContains(
            response,
            """
                <span class="badge border" data-nb-link="/dcim/locations/"><!--
                    -->in: Locations<!--
                    --><button tabindex="-1" type="button">
                    <span aria-hidden="true" class="mdi mdi-close"></span>
                    <span class="visually-hidden">Remove</span>
                </button>
            """,
            html=True,
        )

        response = self.client.get(reverse("dcim:device_list"))
        self.assertBodyContains(
            response,
            '<input aria-placeholder="Press Ctrl+K to search" class="form-control nb-text-transparent" name="q" type="search" value="">',
            html=True,
        )
        self.assertBodyContains(
            response,
            """
                <span class="badge border" data-nb-link="/dcim/devices/"><!--
                    -->in: Devices<!--
                    --><button tabindex="-1" type="button">
                    <span aria-hidden="true" class="mdi mdi-close"></span>
                    <span class="visually-hidden">Remove</span>
                </button>
            """,
            html=True,
        )


class FilterFormsTestCase(TestCase):
    def test_support_for_both_default_and_dynamic_filter_form_in_ui(self):
        self.add_permissions("dcim.view_location", "circuits.view_circuit")

        filter_tabs = """
        <ul class="nav nav-tabs" id="filter-tabs">
            <li class="nav-item" role="presentation">
                <a class="active nav-link" data-bs-toggle="tab" href="#default-filter" role="tab">
                    Basic
                </a>
            </li>
            <li class="nav-item" role="presentation">
                <a class="nav-link position-relative" data-bs-toggle="tab" href="#advanced-filter" role="tab">
                    Advanced
                </a>
            </li>
        </ul>
        """

        response = self.client.get(reverse("dcim:location_list"))
        self.assertBodyContains(response, filter_tabs, html=True)

        response = self.client.get(reverse("circuits:circuit_list"))
        self.assertBodyContains(response, filter_tabs, html=True)

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
        self.assertBodyContains(response, locations[0].name, html=True)
        self.assertBodyContains(response, locations[1].name, html=True)

    def test_filtering_crafted_query_params(self):
        """Test for reflected-XSS vulnerability GHSA-jxgr-gcj5-cqqg."""
        self.add_permissions("dcim.view_location")
        query_param = "?location_type=1 onmouseover=alert('hi') foo=bar"
        url = reverse("dcim:location_list") + query_param
        response = self.client.get(url)
        # The important thing here is that the data-nb-value and value are correctly quoted
        self.assertBodyContains(
            response,
            """
            <span class="badge" data-nb-value="1 onmouseover=alert(&#x27;hi&#x27;) foo=bar"><!--
                --><button class="nb-dynamic-filter-remove" type="button">
                    <span aria-hidden="true" class="mdi mdi-close"></span>
                    <span class="visually-hidden">Remove</span>
                </button><!--
                -->1 onmouseover=alert(&#x27;hi&#x27;) foo=bar<!--
                --><input name="location_type" type="hidden" value="1 onmouseover=alert(&#x27;hi&#x27;) foo=bar">
            </span>
            """,
            html=True,
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


class NavAppsUITestCase(TestCase):
    def setUp(self):
        super().setUp()

        self.apps_marketplace_url = reverse("apps:apps_marketplace")
        self.apps_marketplace_item_weight = (
            100  # TODO: not easy to introspect from the nav menu struct, so hard-code it here for now
        )

        self.apps_list_url = reverse("apps:apps_list")
        self.apps_list_item_weight = (
            200  # TODO: not easy to introspect from the nav menu struct, so hard-code it here for now
        )

    def test_apps_marketplace_visible(self):
        """The "Apps Marketplace" menu item should be available to an authenticated user regardless of permissions."""
        response = self.client.get(reverse("home"))
        self.assertContains(
            response,
            f"""
            <a class="nb-sidenav-link"
                data-item-weight="{self.apps_marketplace_item_weight}"
                href="{self.apps_marketplace_url}">
                Apps Marketplace
            </a>
            """,
            html=True,
        )

    def test_installed_apps_visible(self):
        """The "Installed Apps" menu item should be available to an authenticated user regardless of permissions."""
        response = self.client.get(reverse("home"))
        self.assertContains(
            response,
            f"""
            <a class="nb-sidenav-link"
                data-item-weight="{self.apps_list_item_weight}"
                href="{self.apps_list_url}">
                Installed Apps
            </a>
            """,
            html=True,
        )


class LoginUITestCase(TestCase):
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
        return sso_login_pattern.search(extract_page_body(response.content.decode(response.charset)))

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

    def test_graphql_redirects_back_to_login_unauthenticated(self):
        """Assert that graphql redirects to login page if user is unauthenticated."""
        self.client.logout()
        headers = {"HTTP_ACCEPT": "text/html"}
        url = reverse("graphql")
        response = self.client.get(url, follow=True, **headers)
        self.assertHttpStatus(response, 200)
        self.assertRedirects(response, f"/login/?next={url}")
        response_content = response.content.decode(response.charset).replace("\n", "")
        for footer_text in self.footer_elements:
            self.assertNotIn(footer_text, response_content)

    def test_api_docs_403_unauthenticated(self):
        """Assert that api docs return a 403 Forbidden if user is unauthenticated."""
        self.client.logout()
        urls = [
            reverse("api_docs"),
            reverse("api_redocs"),
            reverse("schema"),
            reverse("schema_json"),
            reverse("schema_yaml"),
        ]
        for url in urls:
            response = self.client.get(url)
            self.assertHttpStatus(response, 403)

    @load_event_broker_override_settings(
        EVENT_BROKERS={
            "SyslogEventBroker": {
                "CLASS": "nautobot.core.events.SyslogEventBroker",
                "TOPICS": {
                    "INCLUDE": ["*"],
                },
            }
        }
    )
    def test_login_logout(self):
        self.client.logout()
        self.user.set_password("pass")
        self.user.save()

        with self.assertLogs("nautobot.events") as cm:
            self.client.post(
                reverse("login"),
                data={
                    "username": self.user.username,
                    "password": "pass",
                },
            )
        self.user.refresh_from_db()
        payload = serialize_user_without_config_and_views(self.user)
        self.assertEqual(
            cm.output,
            [f"INFO:nautobot.events.nautobot.users.user.login:{json.dumps(payload, indent=4)}"],
        )
        self.assertTrue(self.user.is_authenticated)
        self.assertNotIn("password", cm.output)
        self.assertNotIn("pass", cm.output)

        with self.assertLogs("nautobot.events") as cm:
            self.client.get(
                reverse("logout"),
            )
        self.user.refresh_from_db()
        payload = serialize_user_without_config_and_views(self.user)
        self.assertEqual(
            cm.output,
            [f"INFO:nautobot.events.nautobot.users.user.logout:{json.dumps(payload, indent=4)}"],
        )
        self.assertNotIn("password", cm.output)
        self.assertNotIn("pass", cm.output)


class MetricsViewTestCase(TestCase):
    def query_and_parse_metrics(self):
        response = self.client.get(reverse("metrics"))
        self.assertHttpStatus(response, 200, msg="/metrics should return a 200 HTTP status code.")
        page_content = response.content.decode(response.charset)
        return text_string_to_metric_families(page_content)

    @tag("example_app")
    def test_metrics_extensibility(self):
        """Assert that the example metric from the Example App shows up _exactly_ when the app is enabled."""
        test_metric_name = "nautobot_example_metric_count"
        metrics_with_app = self.query_and_parse_metrics()
        metric_names_with_app = {metric.name for metric in metrics_with_app}
        self.assertIn(test_metric_name, metric_names_with_app)
        with override_settings(PLUGINS=[]):
            # Clear out the app metric registry because it is not updated when settings are changed but Nautobot is not
            # restarted.
            registry["app_metrics"].clear()
            metrics_without_app = self.query_and_parse_metrics()
            metric_names_without_app = {metric.name for metric in metrics_without_app}
            self.assertNotIn(test_metric_name, metric_names_without_app)
        metric_names_with_app.remove(test_metric_name)
        self.assertSetEqual(metric_names_with_app, metric_names_without_app)

    def test_enabled_metrics_cache_disabled(self):
        """Assert that when cache is disabled the cache enabled function doesn't get called."""
        with mock.patch("nautobot.core.views.utils.generate_latest_with_cache") as mock_generate_latest_with_cache:
            self.query_and_parse_metrics()
            self.assertTrue(mock_generate_latest_with_cache.call_count == 0)

    @tag("example_app")
    @override_settings(METRICS_EXPERIMENTAL_CACHING_DURATION=30)
    def test_enabled_metrics_cache_enabled(self):
        """Assert that multiple calls to metrics with caching returns expected response."""
        test_metric_name = "nautobot_example_metric_count"
        metrics_with_app = self.query_and_parse_metrics()
        metrics_with_app_cached = self.query_and_parse_metrics()
        metric_names_with_app = {metric.name for metric in metrics_with_app}
        metric_names_with_app_cached = {metric.name for metric in metrics_with_app_cached}
        self.assertIn(test_metric_name, metric_names_with_app)
        self.assertIn(test_metric_name, metric_names_with_app_cached)

        # In some circumstances (e.g. if this test is run first) metrics_with_app may not have
        # metrics from Django like total view counts. Since metrics_with_app_cached is called
        # second, it should have everything that metrics_with_app has (plus potentially more).
        # We at least want to ensure the cached version has everything the non-cached version has.
        self.assertTrue(
            metric_names_with_app.issubset(metric_names_with_app_cached),
            msg="Cached metrics should be a superset of non-cached metrics.",
        )
        with mock.patch("nautobot.core.views.generate_latest_with_cache") as mock_generate_latest_with_cache:
            self.query_and_parse_metrics()
            self.query_and_parse_metrics()
            self.assertEqual(mock_generate_latest_with_cache.call_count, 2)

        from example_app.metrics import metric_example

        cache.delete(METRICS_CACHE_KEY)  # Ensure we start with a clean cache for the next part of the test
        # Assert that the metric function only gets called once even though we scrape metrics twice

        mock_metric_function = mock.Mock(name="mock_metric_function", side_effect=metric_example)
        with mock.patch.dict("nautobot.core.views.registry", app_metrics=[mock_metric_function]):
            self.query_and_parse_metrics()
            first_call_count = mock_metric_function.call_count
            self.query_and_parse_metrics()
            second_call_count = mock_metric_function.call_count
            self.assertEqual(first_call_count, second_call_count)


class AuthenticateMetricsTestCase(APITestCase):
    def test_metrics_authentication(self):
        """Assert that if metrics require authentication, a user not logged in gets a 403."""
        self.client.logout()
        headers = {}
        response = self.client.get(reverse("metrics"), **headers)
        self.assertHttpStatus(response, 403, msg="/metrics should return a 403 HTTP status code.")

    def test_metrics(self):
        """Assert that if metrics don't require authentication, a user not logged in gets a 200."""
        self.factory = RequestFactory()
        self.client.logout()

        request = self.factory.get("/")
        response = NautobotMetricsView.as_view()(request)
        self.assertHttpStatus(response, 200, msg="/metrics should return a 200 HTTP status code.")


class ErrorPagesTestCase(TestCase):
    """Tests for 4xx and 5xx error page rendering."""

    @override_settings(DEBUG=False)
    def test_404_default_support_message(self):
        """Nautobot's custom 404 page should be used and should include a default support message."""
        with self.assertTemplateUsed("404.html"):
            response = self.client.get("/foo/bar")
        self.assertBodyContains(
            response,
            "If further assistance is required, please join the <code>#nautobot</code> channel on "
            '<a href="https://slack.networktocode.com/" rel="noopener noreferrer">Network to Code\'s '
            "Slack community</a> and post your question.",
            html=True,
            status_code=404,
        )

    @override_settings(DEBUG=False, SUPPORT_MESSAGE="Hello world!")
    def test_404_custom_support_message(self):
        """Nautobot's custom 404 page should be used and should include a custom support message if defined."""
        with self.assertTemplateUsed("404.html"):
            response = self.client.get("/foo/bar")
        self.assertNotContains(response, "Network to Code", status_code=404)
        self.assertBodyContains(response, "Hello world!", status_code=404)

    @override_settings(DEBUG=False)
    @mock.patch("nautobot.core.views.HomeView.get", side_effect=Exception)
    def test_500_default_support_message(self, mock_get):
        """Nautobot's custom 500 page should be used and should include a default support message."""
        url = reverse("home")
        self.client.raise_request_exception = False
        response = self.client.get(url)
        self.assertTemplateUsed(response, "500.html")
        self.assertBodyContains(
            response,
            "If further assistance is required, please join the <code>#nautobot</code> channel on "
            '<a href="https://slack.networktocode.com/" rel="noopener noreferrer">Network to Code\'s '
            "Slack community</a> and post your question.",
            html=True,
            status_code=500,
        )

    @override_settings(DEBUG=False, SUPPORT_MESSAGE="Hello world!")
    @mock.patch("nautobot.core.views.HomeView.get", side_effect=Exception)
    def test_500_custom_support_message(self, mock_get):
        """Nautobot's custom 500 page should be used and should include a custom support message if defined."""
        url = reverse("home")
        self.client.raise_request_exception = False
        response = self.client.get(url)
        self.assertTemplateUsed(response, "500.html")
        self.assertNotContains(response, "Network to Code", status_code=500)
        self.assertBodyContains(response, "Hello world!", status_code=500)


class DBFileStorageViewTestCase(TestCase):
    """Test authentication/permission enforcement for django_db_file_storage views."""

    def setUp(self):
        super().setUp()
        self.test_file_1 = SimpleUploadedFile(name="test_file_1.txt", content=b"I am content.\n")
        self.file_proxy_1 = FileProxy.objects.create(name=self.test_file_1.name, file=self.test_file_1)
        self.test_file_2 = SimpleUploadedFile(name="test_file_2.txt", content=b"I am content.\n")
        self.file_proxy_2 = FileProxy.objects.create(name=self.test_file_2.name, file=self.test_file_2)
        self.url = f"{reverse('db_file_storage.download_file')}?name={self.file_proxy_1.file.name}"

    def test_get_file_anonymous(self):
        self.client.logout()
        response = self.client.get(self.url)
        self.assertHttpStatus(response, 403)

    def test_get_file_without_permission(self):
        response = self.client.get(self.url)
        self.assertHttpStatus(response, 403)

    def test_get_object_with_permission(self):
        self.add_permissions(get_permission_for_model(FileProxy, "view"))
        response = self.client.get(self.url)
        self.assertHttpStatus(response, 200)

    def test_get_object_with_constrained_permission(self):
        obj_perm = ObjectPermission(
            name="Test permission",
            constraints={"pk": self.file_proxy_1.pk},
            actions=["view"],
        )
        obj_perm.save()
        obj_perm.users.add(self.user)
        obj_perm.object_types.add(ContentType.objects.get_for_model(FileProxy))
        response = self.client.get(self.url)
        self.assertHttpStatus(response, 200)
        url = f"{reverse('db_file_storage.download_file')}?name={self.file_proxy_2.file.name}"
        response = self.client.get(url)
        self.assertHttpStatus(response, 404)


class SilkUIAccessTestCase(TestCase):
    """Test access control related to the django-silk UI"""

    def test_access_for_non_superuser(self):
        # Login as non-superuser
        self.user.is_superuser = False
        self.user.save()
        self.client.force_login(self.user)

        # Attempt to access the view
        response = self.client.get(reverse("silk:summary"))

        # Check for redirect or forbidden status code (302 or 403)
        self.assertIn(response.status_code, [302, 403])

    def test_access_for_superuser(self):
        # Login as superuser
        self.user.is_superuser = True
        self.user.save()
        self.client.force_login(self.user)

        # Attempt to access the view
        response = self.client.get(reverse("silk:summary"))

        # Check for success status code (e.g., 200)
        self.assertEqual(response.status_code, 200)


class ExampleViewWithCustomPermissionsTest(TestCase):
    @tag("example_app")
    @override_settings(EXEMPT_VIEW_PERMISSIONS=[])
    def test_permission_classes_attribute_is_enforced(self):
        """
        If example app is installed, check if the ViewWithCustomPermissions
        is enforcing the permissions specified in its `permission_classes` attribute.
        """
        # Test IsAuthenticated permission
        self.add_permissions("example_app.view_examplemodel")
        self.client.logout()
        url = reverse("plugins:example_app:view_with_custom_permissions")
        response = self.client.get(url, follow=True)
        # check if the user is redirected to the login page
        self.assertBodyContains(response, f'<input type="hidden" name="next" value="{url}" />', html=True)

        # Test IsAdmin permission
        self.client.force_login(self.user)
        response = self.client.get(url, follow=True)
        # check if the users have to have the permission to access the page
        self.assertBodyContains(response, "You do not have permission to access this page", status_code=403)

        # View should be successfully accessed
        self.user.is_staff = True
        self.user.save()
        response = self.client.get(url)
        self.assertBodyContains(response, "You are viewing a table of example models")


class TestObjectDetailView(TestCase):
    @override_settings(PAGINATE_COUNT=5)
    def test_object_table_panel(self):
        provider = Provider.objects.create(name="A Test Provider 1")
        circuit_type = CircuitType.objects.create(
            name="A Test Circuit Type",
        )
        circuit_status = Status.objects.get_for_model(Circuit).first()

        circuits = [
            Circuit(
                provider=provider,
                cid=f"00121{x}",
                circuit_type=circuit_type,
                status=circuit_status,
            )
            for x in range(10)
        ]
        Circuit.objects.bulk_create(circuits)

        self.add_permissions("circuits.view_provider", "circuits.view_circuit")
        url = reverse("circuits:provider", args=(provider.pk,))
        response = self.client.get(url)
        self.assertHttpStatus(response, 200)
        response_data = extract_page_body(response.content.decode(response.charset))
        view_move_url = reverse("circuits:circuit_list") + f"?provider={provider.id}"

        # Assert Badge Count in table panel header
        panel_header = f"""<strong>Circuits</strong> <a href="{view_move_url}" class="badge bg-primary">10</a>"""
        self.assertInHTML(panel_header, response_data)

        # Assert view X more btn
        view_more_btn = f"""<a href="{view_move_url}"><span class="mdi mdi-dots-horizontal" aria-hidden="true"></span>View 5 more circuits</a>"""
        self.assertInHTML(view_more_btn, response_data)

        # Validate Copy btn on all rows excluding empty rows
        name_copy = f"""
        <span>
            <span id="_value_name">{provider.name}</span>
            <button class="btn btn-secondary nb-btn-inline-hover" data-clipboard-target="#_value_name">
                <span aria-hidden="true" class="mdi mdi-content-copy"></span>
                <span class="visually-hidden">Copy</span>
            </button>
        </span>"""
        self.assertInHTML(name_copy, response_data)
        # ASN do not have a value, therefore no copy btn
        self.assertNotIn("#asn_copy", response_data)


class SearchRobotsTestCase(TestCase):
    def test_robots_disallowed(self):
        """
        Test that the robots.txt file is accessible to all users and defaults to disallowing all bots.
        """
        url = reverse("robots_txt")
        response = self.client.get(url)
        self.assertHttpStatus(response, 200)
        self.assertBodyContains(response, "User-Agent: *")
        self.assertBodyContains(response, "Disallow: /")

        url = reverse("home")
        response = self.client.get(url)
        self.assertContains(response, '<meta name="robots" content="noindex, nofollow">', html=True)

    @override_settings(PUBLISH_ROBOTS_TXT=False)
    def test_robots_allowed(self):
        """
        Test that the robots.txt file is not published if PUBLISH_ROBOTS_TXT is set to False.
        """
        url = reverse("robots_txt")
        response = self.client.get(url)
        self.assertHttpStatus(response, 404)

        url = reverse("home")
        response = self.client.get(url)
        self.assertNotContains(response, '<meta name="robots" content="noindex, nofollow">', html=True)


@tag("example_app")
class ViewSetCustomActionsTestCase(TestCase):
    """Tests for NautobotUIViewSet custom actions."""

    def test_custom_view_base_action(self):
        """Assert that all of the permissions in a custom action's custom_view_base_action are enforced."""
        from example_app.models import AnotherExampleModel

        self.add_permissions("example_app.view_anotherexamplemodel", "dcim.view_location")
        self.remove_permissions("dcim.add_location", "dcim.change_location")

        example_model = AnotherExampleModel.objects.create(name="test")
        url = reverse(
            "plugins:example_app:anotherexamplemodel_custom-action-permissions-test",
            kwargs={"pk": example_model.pk},
        )
        response = self.client.get(url)
        self.assertEqual(response.status_code, 403)

        self.add_permissions("dcim.add_location", "dcim.change_location")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
