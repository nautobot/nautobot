import json
from unittest import mock

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.sessions.middleware import SessionMiddleware
from django.test import override_settings, RequestFactory
from django.urls import reverse
from django.utils import timezone
from social_django.utils import load_backend, load_strategy

from nautobot.core.testing import TestCase, utils, ViewTestCases
from nautobot.core.testing.context import load_event_broker_override_settings
from nautobot.core.testing.utils import post_data
from nautobot.users.models import Token
from nautobot.users.utils import serialize_user_without_config_and_views

User = get_user_model()


class PasswordUITest(TestCase):
    def test_change_password_enabled(self):
        """
        Check that a Django-authentication-based user is allowed to change their password
        """
        profile_response = self.client.get(reverse("user:profile"))
        preferences_response = self.client.get(reverse("user:preferences"))
        for response in [profile_response, preferences_response]:
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
            for response in [profile_response, preferences_response]:
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
        response = self.client.post(**request)
        response = self.client.get(url)
        self.assertEqual(timezone.get_current_timezone_name(), new_timezone_name)
        self.assertNotEqual(timezone_name, new_timezone_name)
        self.assertHttpStatus(response, 200)


class TokenUIViewSetTestCase(ViewTestCases.PrimaryObjectViewTestCase):
    model = Token

    form_data = {
        "description": "created-via-ui-test",
        "write_enabled": True,
    }

    update_data = {
        "description": "updated-via-ui-test",
        "write_enabled": False,
    }

    bulk_edit_data = {
        "description": "bulk-updated-token",
    }

    def _get_base_url(self):
        return "user:token_{}"

    def setUp(self):
        super().setUp()
        self.other_user = User.objects.create_user(username="other-user")

        Token.objects.create(user=self.user, description="seed-token-1")
        Token.objects.create(user=self.user, description="seed-token-2")
        Token.objects.create(user=self.user, description="seed-token-3")

    @override_settings(EXEMPT_VIEW_PERMISSIONS=["*"])
    def test_get_object_anonymous(self):
        self.client.logout()
        response = self.client.get(self._get_queryset().first().get_absolute_url())
        self.assertHttpStatus(response, 404)

    @override_settings(EXEMPT_VIEW_PERMISSIONS=["user:token_list"])
    def test_list_objects_anonymous_with_exempt_permission_for_one_view_only(self):
        """Ensure list view exemption alone does not allow detail access for anonymous users.

        We override default anonymous object lookup behavior to avoid a security gap: even if
        the token list endpoint is exempted from auth (for cases like public listing with
        filtering), anonymous clients still should not be allowed to view a specific token
        object via detail URL, so redirect-to-login is expected here.
        """
        self.client.logout()
        response = self.client.get(self._get_url("list"))
        self.assertHttpStatus(response, 302)
        self.assertIn("/login/", response.url)

    def test_token_add_form_shows_key_field(self):
        self.add_permissions("users.add_token", "users.view_token")
        response = self.client.get(reverse("user:token_add"))
        self.assertHttpStatus(response, 200)
        self.assertBodyContains(response, "If no key is provided")

    def test_token_edit_form_hides_key_field(self):
        self.add_permissions("users.change_token", "users.view_token")
        token = Token.objects.create(user=self.user, description="edit-me")
        response = self.client.get(reverse("user:token_edit", kwargs={"pk": token.pk}))
        self.assertHttpStatus(response, 200)
        self.assertNotIn("If no key is provided", response.content.decode(response.charset))

    def test_non_staff_list_only_shows_own_tokens(self):
        self.add_permissions("users.view_token")
        own_token = Token.objects.create(user=self.user, description="own-token-visible")
        Token.objects.create(user=self.other_user, description="other-token-hidden")

        response = self.client.get(reverse("user:token_list"), headers={"HX-Request": "true"})
        self.assertHttpStatus(response, 200)
        self.assertBodyContains(response, own_token.description)
        self.assertNotIn("other-token-hidden", response.content.decode(response.charset))

    def test_staff_list_shows_all_tokens(self):
        self.user.is_staff = True
        self.user.save()
        self.client.force_login(self.user)

        self.add_permissions("users.view_token")
        Token.objects.create(user=self.user, description="staff-own-token")
        Token.objects.create(user=self.other_user, description="staff-can-see-other")

        response = self.client.get(reverse("user:token_list"), headers={"HX-Request": "true"})
        self.assertHttpStatus(response, 200)
        self.assertBodyContains(response, "staff-own-token")
        self.assertBodyContains(response, "staff-can-see-other")

    def test_non_staff_create_cannot_assign_other_user(self):
        self.add_permissions("users.add_token", "users.view_token")
        response = self.client.post(
            reverse("user:token_add"),
            data={
                "user": str(self.other_user.pk),
                "description": "non-staff-create",
                "write_enabled": "on",
            },
        )
        self.assertHttpStatus(response, 302)

        token = Token.objects.get(description="non-staff-create")
        self.assertEqual(token.user, self.user)
        self.assertEqual(len(token.key), 40)

    def test_staff_create_can_assign_other_user(self):
        self.user.is_staff = True
        self.user.save()
        self.client.force_login(self.user)

        self.add_permissions("users.add_token", "users.view_token")
        response = self.client.post(
            reverse("user:token_add"),
            data={
                "user": str(self.other_user.pk),
                "description": "staff-create",
                "write_enabled": "on",
            },
        )
        self.assertHttpStatus(response, 302)

        token = Token.objects.get(description="staff-create")
        self.assertEqual(token.user, self.other_user)

    def test_non_staff_cannot_edit_other_users_token(self):
        self.add_permissions("users.change_token", "users.view_token")
        token = Token.objects.create(user=self.other_user, description="not-editable")
        response = self.client.get(reverse("user:token_edit", kwargs={"pk": token.pk}))
        self.assertHttpStatus(response, 404)

    def test_staff_can_edit_other_users_token(self):
        self.user.is_staff = True
        self.user.save()
        self.client.force_login(self.user)

        self.add_permissions("users.change_token", "users.view_token")
        token = Token.objects.create(user=self.other_user, description="before-edit")

        response = self.client.post(
            reverse("user:token_edit", kwargs={"pk": token.pk}),
            data={
                "user": str(self.other_user.pk),
                "description": "after-edit",
                "write_enabled": "on",
            },
        )
        self.assertHttpStatus(response, 302)

        token.refresh_from_db()
        self.assertEqual(token.user, self.other_user)
        self.assertEqual(token.description, "after-edit")
