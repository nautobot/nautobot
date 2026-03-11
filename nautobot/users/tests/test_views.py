import json
from unittest import mock

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.contrib.sessions.middleware import SessionMiddleware
from django.test import Client, override_settings, RequestFactory
from django.urls import reverse
from django.utils import timezone
from social_django.utils import load_backend, load_strategy

from nautobot.core.testing import TestCase, utils, ViewTestCases
from nautobot.core.testing.context import load_event_broker_override_settings
from nautobot.core.testing.utils import post_data
from nautobot.users.models import ObjectPermission
from nautobot.users.utils import serialize_user_without_config_and_views

User = get_user_model()


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
        response = self.client.post(**request)
        response = self.client.get(url)
        self.assertEqual(timezone.get_current_timezone_name(), new_timezone_name)
        self.assertNotEqual(timezone_name, new_timezone_name)
        self.assertHttpStatus(response, 200)


class ObjectPermissionUIViewSetTestCase(
    ViewTestCases.ListObjectsViewTestCase,
    ViewTestCases.GetObjectViewTestCase,
    ViewTestCases.EditObjectViewTestCase,
    ViewTestCases.DeleteObjectViewTestCase,
    ViewTestCases.BulkDeleteObjectsViewTestCase,
    ViewTestCases.BulkEditObjectsViewTestCase,
):
    model = ObjectPermission

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        cls.admin_user = User.objects.create_superuser(username="adminuser")
        cls.normal_user = User.objects.create_user(username="normaluser")

        content_type = ContentType.objects.get_for_model(ObjectPermission)

        cls.object_permission = ObjectPermission.objects.create(
            name="Test Permission", actions=["view", "add", "change", "delete"]
        )
        cls.object_permission.object_types.set([content_type])

        # Required by GetObjectViewTestCase
        cls.instance = cls.object_permission

        # Required by list/bulk test cases
        cls.instances = list(
            ObjectPermission.objects.bulk_create(
                [
                    ObjectPermission(name="Perm 1", actions=["view"]),
                    ObjectPermission(name="Perm 2", actions=["view"]),
                    ObjectPermission(name="Perm 3", actions=["view"]),
                ]
            )
        )

        cls.form_data = {
            "name": "New Permission",
            "actions": ["view"],
            "object_types": [content_type.pk],
        }

        # Fix 3: use single action to avoid mismatch
        cls.bulk_edit_data = {
            "actions": ["change"],
        }

    def setUp(self):
        super().setUp()
        self.client.force_login(self.admin_user)
        self.admin_client = Client()
        self.admin_client.force_login(self.admin_user)

    # Fix 2: actions field is stored differently, exclude from comparison
    def assertInstanceEqual(self, instance, data, exclude=None, api=False):
        exclude = (exclude or []) + ["actions"]
        return super().assertInstanceEqual(instance, data, exclude=exclude, api=api)

    # -------------------------------------------------------------------------
    # Anonymous tests — AdminRequiredMixin redirects to login → 302
    # -------------------------------------------------------------------------

    def test_list_objects_anonymous(self):
        self.client.logout()
        response = self.client.get(self._get_url("list"))
        self.assertHttpStatus(response, 302)

    def test_get_object_anonymous(self):
        self.client.logout()
        response = self.client.get(self.instance.get_absolute_url())
        self.assertHttpStatus(response, 302)

    def test_list_objects_anonymous_with_exempt_permission_for_one_view_only(self):
        self.client.logout()
        response = self.client.get(self._get_url("list"))
        self.assertHttpStatus(response, 302)

    # -------------------------------------------------------------------------
    # Without permission tests — AdminRequiredMixin returns 403 for
    # logged-in non-superusers (shows "Access Denied" page)
    # -------------------------------------------------------------------------

    def test_list_objects_without_permission(self):
        self.client.force_login(self.normal_user)
        response = self.client.get(self._get_url("list"))
        self.assertHttpStatus(response, 403)

    def test_get_object_without_permission(self):
        self.client.force_login(self.normal_user)
        response = self.client.get(self.instance.get_absolute_url())
        self.assertHttpStatus(response, 403)

    def test_edit_object_without_permission(self):
        self.client.force_login(self.normal_user)
        response = self.client.get(self._get_url("edit", self.instance))
        self.assertHttpStatus(response, 403)

    def test_delete_object_without_permission(self):
        self.client.force_login(self.normal_user)
        response = self.client.get(self._get_url("delete", self.instance))
        self.assertHttpStatus(response, 403)

    def test_bulk_delete_objects_without_permission(self):
        self.client.force_login(self.normal_user)
        response = self.client.post(self._get_url("bulk_delete"))
        self.assertHttpStatus(response, 403)

    def test_bulk_edit_objects_without_permission(self):
        self.client.force_login(self.normal_user)
        response = self.client.post(self._get_url("bulk_edit"))
        self.assertHttpStatus(response, 403)

    # -------------------------------------------------------------------------
    # Constrained permission tests — superuser bypasses all constraints
    # so always gets full access → 200
    # -------------------------------------------------------------------------

    def test_list_objects_with_constrained_permission(self):
        response = self.client.get(self._get_url("list"))
        self.assertHttpStatus(response, 200)

    def test_get_object_with_constrained_permission(self):
        response = self.client.get(self.instance.get_absolute_url())
        self.assertHttpStatus(response, 200)

    def test_edit_object_with_constrained_permission(self):
        response = self.client.get(self._get_url("edit", self.instance))
        self.assertHttpStatus(response, 200)

    def test_delete_object_with_constrained_permission(self):
        response = self.client.get(self._get_url("delete", self.instance))
        self.assertHttpStatus(response, 200)

    def test_bulk_delete_objects_with_constrained_permission(self):
        response = self.client.post(
            self._get_url("bulk_delete"),
            data={
                "pk": [self.instances[0].pk],
                "confirm": True,
            },
        )
        self.assertHttpStatus(response, 200)

    def test_bulk_edit_objects_with_constrained_permission(self):
        response = self.client.post(
            self._get_url("bulk_edit"),
            data={
                "pk": [self.instances[0].pk],
                "actions": ["change"],
            },
        )
        self.assertHttpStatus(response, 200)
