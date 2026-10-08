import json
import re
from unittest import mock

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.sessions.middleware import SessionMiddleware
from django.template.loader import render_to_string
from django.test import override_settings, RequestFactory
from django.urls import reverse
from django.utils import timezone
from social_django.utils import load_backend, load_strategy

from nautobot.core.testing import TestCase, utils
from nautobot.core.testing.context import load_event_broker_override_settings
from nautobot.core.testing.utils import post_data
from nautobot.users.utils import serialize_user_without_config_and_views

User = get_user_model()

SAMPLE_FAVORITES = [
    {"link": "/dcim/devices/", "name": "Devices", "tab_name": "Devices"},
    {"link": "/dcim/locations/", "name": "Locations", "tab_name": "Organization"},
    {"link": "/ipam/prefixes/", "name": "Prefixes", "tab_name": "IPAM"},
]


class PasswordUITest(TestCase):
    def test_change_password_enabled(self):
        """
        Check that a Django-authentication-based user is allowed to change their password
        """
        profile_response = self.client.get(reverse("user:profile"))
        preferences_response = self.client.get(reverse("user:preferences"))
        api_tokens_response = self.client.get(reverse("user:token_list"))
        for response in [profile_response, preferences_response, api_tokens_response]:
            self.assertBodyContains(response, "Change Password")

        # Check GET change_password functionality
        get_response = self.client.get(reverse("user:change_password"))
        self.assertBodyContains(get_response, "New password confirmation")

        # Check POST change_password functionality
        post_response = self.client.post(
            reverse("user:change_password"),
            data={
                "old_password": "foo",
                "new_password1": "bar",
                "new_password2": "baz",
            },
        )
        self.assertBodyContains(post_response, "The two password fields")

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
    def test_change_password(self):
        self.user.set_password("foo")
        self.user.save()
        self.client.force_login(self.user)
        with self.assertLogs("nautobot.events") as cm:
            self.client.post(
                reverse("user:change_password"),
                data={
                    "old_password": "foo",
                    "new_password1": "bar",
                    "new_password2": "bar",
                },
            )
        payload = serialize_user_without_config_and_views(self.user)
        self.assertEqual(
            cm.output,
            [f"INFO:nautobot.events.nautobot.users.user.change_password:{json.dumps(payload, indent=4)}"],
        )
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("bar"))

    @override_settings(
        AUTHENTICATION_BACKENDS=[
            "social_core.backends.google.GoogleOAuth2",
            "nautobot.core.authentication.ObjectPermissionBackend",
        ]
    )
    def test_change_password_disabled(self):
        """
        Mock an SSO-authenticated user, log them in by force and check that the change
        password functionality isn't visible in the UI or available server-side
        """
        # Logout the non-SSO user
        self.client.logout()

        sso_user = User.objects.create_user(username="sso_user", is_superuser=True)

        self.request_factory = RequestFactory(SERVER_NAME="nautobot.example.com")
        self.request = self.request_factory.get("/")
        SessionMiddleware(lambda: None).process_request(self.request)

        # load 'social_django.strategy.DjangoStrategy' from social_core into the fake request
        django_strategy = load_strategy(request=self.request)

        # Load GoogleOAuth2 authentication backend to test against in the mock
        google_auth_backend = load_backend(strategy=django_strategy, name="google-oauth2", redirect_uri="/")

        # Mock an authenticated SSO pipeline
        with mock.patch("social_core.backends.base.BaseAuth.pipeline", return_value=sso_user):
            result = django_strategy.authenticate(backend=google_auth_backend, response=mock.Mock())
            self.assertEqual(result, sso_user)
            self.assertEqual(result.backend, "social_core.backends.google.GoogleOAuth2")
            self.assertTrue(sso_user.is_authenticated)
            self.client.force_login(sso_user, backend=settings.AUTHENTICATION_BACKENDS[0])

            # Check UI
            profile_response = self.client.get(reverse("user:profile"))
            preferences_response = self.client.get(reverse("user:preferences"))
            api_tokens_response = self.client.get(reverse("user:token_list"))
            for response in [profile_response, preferences_response, api_tokens_response]:
                self.assertNotIn("Change Password", utils.extract_page_body(response.content.decode(response.charset)))

            # Check GET and POST change_password functionality
            get_response = self.client.get(reverse("user:change_password"), follow=True)
            post_response = self.client.post(reverse("user:change_password"), follow=True)
            for response in [get_response, post_response]:
                content = utils.extract_page_body(response.content.decode(response.charset))
                self.assertNotIn("New password confirmation", content)
                # Check redirect
                self.assertIn("User Profile", content)
                # Check warning message
                self.assertIn("Remotely authenticated user credentials cannot be changed within Nautobot.", content)


class AdvancedProfileSettingsViewTest(TestCase):
    """
    Tests for the user's advanced settings profile edit view
    """

    @override_settings(ALLOW_REQUEST_PROFILING=True)
    def test_enable_request_profiling(self):
        """
        Check that a user can enable request profling on their session
        """
        # Simulate form submission with checkbox checked
        response = self.client.post(reverse("user:advanced_settings_edit"), {"request_profiling": True})
        self.assertEqual(response.status_code, 200)
        # Check if the session has the correct value
        self.assertTrue(self.client.session["silk_record_requests"])

    @override_settings(ALLOW_REQUEST_PROFILING=True)
    def test_disable_request_profiling(self):
        """
        Check that a user can disable request profling on their session
        """
        # Simulate form submission with checkbox unchecked
        response = self.client.post(reverse("user:advanced_settings_edit"), {"request_profiling": False})
        self.assertEqual(response.status_code, 200)
        # Check if the session has the correct value
        self.assertFalse(self.client.session["silk_record_requests"])

    @override_settings(ALLOW_REQUEST_PROFILING=False)
    def test_disable_allow_request_profiling_rejects_user_enable(self):
        """
        Check that a user cannot enable request profiling if ALLOW_REQUEST_PROFILING=False
        """
        # Simulate form submission with checkbox unchecked
        response = self.client.post(reverse("user:advanced_settings_edit"), {"request_profiling": True})

        # Check if the form is in the response context and has errors
        self.assertTrue("form" in response.context)
        form = response.context["form"]
        self.assertFalse(form.cleaned_data["request_profiling"])

        # Check if the session has the correct value
        self.assertFalse(self.client.session.get("silk_record_requests"))


class PreferenceTestCase(TestCase):
    def test_timezone_change(self):
        self.user.is_superuser = True
        self.user.save()
        self.client.force_login(self.user)

        timezone_name = timezone.get_current_timezone_name()
        new_timezone_name = "US/Eastern"
        form_data = {"timezone": new_timezone_name, "_update_preference_form": [""]}
        url = reverse("user:preferences")
        request = {
            "path": url,
            "data": post_data(form_data),
        }
        response = self.client.post(**request, follow=True)
        self.assertHttpStatus(response, 200)
        response = self.client.get(url)
        self.assertEqual(timezone.get_current_timezone_name(), new_timezone_name)
        self.assertNotEqual(timezone_name, new_timezone_name)
        self.assertHttpStatus(response, 200)


class NavbarFavoritesAddViewTest(TestCase):
    """Tests for the UserNavbarFavoritesAddView."""

    def test_add_favorite(self):
        """A submitted favorite is appended verbatim, query string and all."""
        response = self.client.post(
            reverse("user:navbar_favorites_add"),
            data={"link": "/dcim/devices/?status=active", "name": "Active Devices", "tab_name": "Devices"},
            headers={"HX-Request": "true"},
        )
        self.assertHttpStatus(response, 201)

        self.user.refresh_from_db()
        self.assertEqual(
            self.user.navbar_favorites,
            [{"link": "/dcim/devices/?status=active", "name": "Active Devices", "tab_name": "Devices"}],
        )


class NavbarFavoritesDeleteViewTest(TestCase):
    """Tests for the UserNavbarFavoritesDeleteView."""

    def test_delete_favorite(self):
        """Removal matches the whole link, so a query string makes a distinct favorite."""
        self.user.set_config(
            "navbar_favorites",
            [
                {"link": "/dcim/devices/", "name": "Devices", "tab_name": "Devices"},
                {"link": "/dcim/devices/?status=active", "name": "Active Devices", "tab_name": ""},
            ],
            commit=True,
        )

        response = self.client.post(
            reverse("user:navbar_favorites_delete"),
            data={"link": "/dcim/devices/"},
            headers={"HX-Request": "true"},
        )
        self.assertHttpStatus(response, 200)

        self.user.refresh_from_db()
        self.assertEqual([item["link"] for item in self.user.navbar_favorites], ["/dcim/devices/?status=active"])


class NavbarFavoritesReorderViewTest(TestCase):
    """Tests for the UserNavbarFavoritesReorderView."""

    def setUp(self):
        super().setUp()
        self.url = reverse("user:navbar_favorites_reorder")
        self.user.set_config("navbar_favorites", list(SAMPLE_FAVORITES), commit=True)

    def _post_reorder(self, ordered_links):
        return self.client.post(self.url, data={"ordered_links": ordered_links}, headers={"HX-Request": "true"})

    def test_reorder_favorites(self):
        """Reordering should persist the new order and preserve each favorite's full metadata."""
        reversed_links = [favorite["link"] for favorite in reversed(SAMPLE_FAVORITES)]
        response = self._post_reorder(reversed_links)
        self.assertHttpStatus(response, 204)

        self.user.refresh_from_db()
        result = self.user.get_config("navbar_favorites", [])
        self.assertEqual(result, list(reversed(SAMPLE_FAVORITES)))

    def test_partial_list_appends_missing(self):
        """Favorites not included in ordered_links should be appended at the end, in their existing order."""
        response = self._post_reorder(["/ipam/prefixes/"])
        self.assertHttpStatus(response, 204)

        self.user.refresh_from_db()
        links = [favorite["link"] for favorite in self.user.get_config("navbar_favorites", [])]
        self.assertEqual(links, ["/ipam/prefixes/", "/dcim/devices/", "/dcim/locations/"])

    def test_duplicate_and_unknown_links(self):
        """Duplicate links should appear once; unknown links should be ignored."""
        response = self._post_reorder(["/nonexistent/", "/dcim/devices/", "/dcim/devices/", "/ipam/prefixes/"])
        self.assertHttpStatus(response, 204)

        self.user.refresh_from_db()
        links = [favorite["link"] for favorite in self.user.get_config("navbar_favorites", [])]
        self.assertEqual(links, ["/dcim/devices/", "/ipam/prefixes/", "/dcim/locations/"])

    def test_non_htmx_request_redirects(self):
        """Requests that do not come from htmx should be redirected without touching the saved order."""
        response = self.client.post(self.url, data={"ordered_links": ["/ipam/prefixes/"]})
        self.assertHttpStatus(response, 302)

        self.user.refresh_from_db()
        self.assertEqual(self.user.get_config("navbar_favorites", []), list(SAMPLE_FAVORITES))

    def test_unauthenticated_returns_redirect(self):
        """Unauthenticated requests should be redirected to the login page."""
        self.client.logout()
        response = self._post_reorder(["/dcim/devices/"])
        self.assertHttpStatus(response, 204)
        self.assertIn("login", response.headers["HX-Redirect"])
        self.user.refresh_from_db()
        self.assertEqual(self.user.get_config("navbar_favorites", []), list(SAMPLE_FAVORITES))


class NavbarFavoritesDuplicateNameTest(TestCase):
    """Tests for the name uniqueness constraint on UserNavbarFavoritesAddView."""

    def setUp(self):
        super().setUp()
        self.url = reverse("user:navbar_favorites_add")
        self.user.set_config(
            "navbar_favorites",
            [{"link": "/dcim/devices/", "name": "Devices", "tab_name": "Devices"}],
            commit=True,
        )

    def test_duplicate_name_and_tab_name_is_rejected(self):
        """A favorite is refused when both its name and tab name are already taken."""
        response = self.client.post(
            self.url,
            data={"link": "/dcim/racks/", "name": "Devices", "tab_name": "Devices"},
            headers={"HX-Request": "true"},
        )
        self.assertHttpStatus(response, 400)
        self.assertEqual(response.headers["HX-Retarget"], "#modal-content-container")
        self.assertEqual(response.headers["HX-Reselect"], "unset")

        self.user.refresh_from_db()
        self.assertEqual(len(self.user.navbar_favorites), 1)

    def test_same_name_under_a_different_tab_name_is_allowed(self):
        """Name and tab name are unique together, so the same name may be reused under another tab."""
        response = self.client.post(
            self.url,
            data={"link": "/dcim/racks/", "name": "Devices"},
            headers={"HX-Request": "true"},
        )
        self.assertHttpStatus(response, 201)

        self.user.refresh_from_db()
        self.assertEqual(len(self.user.navbar_favorites), 2)


class NavbarFavoriteButtonTest(TestCase):
    """Tests for the `data-nb-flip` configuration of the page title favorite button."""

    LINK = "/dcim/locations/"

    def _render_button(self, navbar_favorites):
        """Render the button for a user with the given favorites, and return its flip configuration."""
        self.user.set_config("navbar_favorites", navbar_favorites, commit=True)
        request = RequestFactory().get(self.LINK)
        request.user = self.user

        attributes = dict(
            re.findall(r'([\w:.-]+)="([^"]*)"', render_to_string("buttons/favorite.html", {"request": request}))
        )
        flipped = attributes["data-nb-flip"].split()
        live = {name: attributes[name] for name in flipped if name in attributes}
        parked = {name: attributes[f"data-nb-flip-{name}"] for name in flipped if f"data-nb-flip-{name}" in attributes}

        return flipped, live, parked

    def test_every_flipped_attribute_is_defined(self):
        """A name listed in `data-nb-flip` is meaningless unless one of the two states defines it."""
        for navbar_favorites in ([], [{"link": self.LINK, "name": "Locations", "tab_name": ""}]):
            with self.subTest(navbar_favorites=navbar_favorites):
                flipped, live, parked = self._render_button(navbar_favorites)
                self.assertEqual(sorted(flipped), sorted(set(live) | set(parked)))

    def test_flip_configuration_is_symmetric(self):
        """What one state has in effect, the other has parked, so flipping either way restores the opposite state."""
        _, inactive_live, inactive_parked = self._render_button([])
        _, active_live, active_parked = self._render_button([{"link": self.LINK, "name": "Locations", "tab_name": ""}])

        self.assertEqual(inactive_live, active_parked)
        self.assertEqual(inactive_parked, active_live)
