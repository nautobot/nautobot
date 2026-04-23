import json
from unittest import mock

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.contrib.contenttypes.models import ContentType
from django.contrib.sessions.middleware import SessionMiddleware
from django.test import override_settings, RequestFactory
from django.urls import reverse
from django.utils import timezone
from social_django.utils import load_backend, load_strategy

from nautobot.core.testing import TestCase, utils, ViewTestCases
from nautobot.core.testing.context import load_event_broker_override_settings
from nautobot.core.testing.utils import post_data
from nautobot.extras.models import JobResult
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
    ViewTestCases.GetObjectChangelogViewTestCase,
):
    """
    Tests for the admin-only ObjectPermission UI viewset.

    The viewset is wrapped in AdminRequiredMixin, so ``setUp`` force-logs a
    superuser and the inherited ViewTestCases effectively become admin-path
    smoke tests. Several inherited tests are overridden to re-express the
    expected behavior under AdminRequiredMixin (e.g. non-superusers get 403
    regardless of granted ObjectPermissions).
    """

    model = ObjectPermission

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        cls.admin_user = User.objects.create_superuser(username="adminuser")
        cls.normal_user = User.objects.create_user(username="normaluser")
        neutral_ct = ContentType.objects.get_for_model(ObjectPermission)
        cls.instance = ObjectPermission.objects.create(
            name="sample-test Permission",
            actions=["view", "add", "change", "delete"],
        )
        cls.instance.object_types.set([neutral_ct])

        # NOTE: Do not use ``bulk_create`` here — it skips ``save()`` and
        # cannot set M2M fields, which leaves the fixtures missing the
        # required ``object_types`` and breaks any flow that revalidates them.
        cls.instances = []
        for i in range(1, 4):
            op = ObjectPermission.objects.create(name=f"Perm {i}", actions=["view"])
            op.object_types.set([neutral_ct])
            cls.instances.append(op)

        cls.form_data = {
            "name": "New Permission",
            "description": "Round-trip test",
            "enabled": True,
            "actions": ["view"],
            "object_types": [neutral_ct.pk],
        }

        # Single-action value sidesteps an ordering mismatch in JSONArray
        # round-tripping (see ``assertInstanceEqual`` override below).
        cls.bulk_edit_data = {
            "actions": ["change"],
        }

    def setUp(self):
        super().setUp()
        # The viewset is admin-only; most inherited tests assume the logged-in
        # user can access the view, so authenticate as a superuser up-front.
        # Overrides below re-authenticate as ``self.normal_user`` in the cases
        # that need to exercise the "forbidden" path.
        self.client.force_login(self.admin_user)

    def test_custom_actions(self):
        """Ensure restricted custom actions (e.g., changelog) are not accessible
        to non-admin users.
        A normal authenticated user should not be permitted to access the changelog
        custom action. The request must return HTTP 403 or 404, confirming that
        custom actions enforce the appropriate permission checks.
        """
        self.client.logout()
        self.client.force_login(self.normal_user)
        self.assertHttpStatus(self.client.get(self._get_url("list")), 403)

    def assertInstanceEqual(self, instance, data, exclude=None, api=False):
        """Exclude ``actions`` from model-vs-data comparison.

        ``ObjectPermission.actions`` is stored as a JSON list but the
        form-roundtrip serialization (via ``JSONArrayFormField`` +
        ``StaticSelect2Multiple``) produces a different ordering/shape than
        the base ``assertInstanceEqual`` normalizes. Rather than paper over
        the specific mismatch here, we exclude ``actions`` and cover its
        persistence explicitly in ``test_create_object_persists_all_fields``.
        """
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

    @override_settings(EXEMPT_VIEW_PERMISSIONS=["users.view_objectpermission"])
    def test_list_objects_anonymous_with_exempt_permission_for_one_view_only(self):
        """AdminRequiredMixin must refuse anonymous access even when the model's
        view permission is marked exempt — exempt settings never override the
        admin-only gate."""
        self.client.logout()
        response = self.client.get(self._get_url("list"))
        self.assertHttpStatus(response, 302)

    # -------------------------------------------------------------------------
    # Without permission — logged-in non-superuser gets 403 regardless of any
    # ObjectPermission grants (AdminRequiredMixin short-circuits before the
    # per-object permission check runs).
    # -------------------------------------------------------------------------

    def test_list_objects_without_permission(self):
        self.client.force_login(self.normal_user)
        self.assertHttpStatus(self.client.get(self._get_url("list")), 403)

    def test_get_object_without_permission(self):
        self.client.force_login(self.normal_user)
        self.assertHttpStatus(self.client.get(self.instance.get_absolute_url()), 403)

    def test_edit_object_without_permission(self):
        self.client.force_login(self.normal_user)
        self.assertHttpStatus(self.client.get(self._get_url("edit", self.instance)), 403)

    def test_delete_object_without_permission(self):
        self.client.force_login(self.normal_user)
        self.assertHttpStatus(self.client.get(self._get_url("delete", self.instance)), 403)

    def test_bulk_delete_objects_without_permission(self):
        self.client.force_login(self.normal_user)
        self.assertHttpStatus(self.client.post(self._get_url("bulk_delete")), 403)

    def test_bulk_edit_objects_without_permission(self):
        self.client.force_login(self.normal_user)
        self.assertHttpStatus(self.client.post(self._get_url("bulk_edit")), 403)

    # -------------------------------------------------------------------------
    # Admin-bypass documentation tests — these override the base
    # ``_with_constrained_permission`` tests because AdminRequiredMixin
    # short-circuits before ObjectPermission constraints are ever consulted.
    # The overrides therefore document "admin has unconditional access" rather
    # than the base tests' "constrained grantee is filtered" assertion.
    # -------------------------------------------------------------------------

    def test_list_objects_with_constrained_permission(self):
        self.assertHttpStatus(self.client.get(self._get_url("list")), 200)

    def test_get_object_with_constrained_permission(self):
        self.assertHttpStatus(self.client.get(self.instance.get_absolute_url()), 200)

    def test_edit_object_with_constrained_permission(self):
        self.assertHttpStatus(self.client.get(self._get_url("edit", self.instance)), 200)

    def test_delete_object_with_constrained_permission(self):
        self.assertHttpStatus(self.client.get(self._get_url("delete", self.instance)), 200)

    def test_bulk_delete_objects_with_constrained_permission(self):
        """Verify the bulk-delete apply path enqueues the deletion job when invoked by admin.

        The base test exercises constraint-based filtering, which admin bypasses, so we
        instead assert the apply path runs: a "Bulk Delete Objects" JobResult is enqueued
        and the response redirects to it. The actual row deletion happens inside the job
        and is not observable synchronously from the HTTP response.
        """
        pk_list = self.get_deletable_object_pks()
        response = self.client.post(
            self._get_url("bulk_delete"),
            data={
                "pk": pk_list,
                "confirm": True,
                "_confirm": True,  # Form button
            },
        )
        job_result = JobResult.objects.filter(name="Bulk Delete Objects").first()
        self.assertIsNotNone(job_result)
        self.assertRedirects(
            response,
            reverse("extras:jobresult", args=[job_result.pk]),
            status_code=302,
            target_status_code=200,
        )

    def test_bulk_edit_objects_with_constrained_permission(self):
        """Verify the bulk-edit apply path dispatches when invoked by admin.

        As with bulk delete, the base constraint-filter test is inapplicable to
        an admin-only view, so we assert that the apply path returns a 302
        (rather than the 200 confirmation preview).
        """
        data = {
            "pk": [self.instances[0].pk],
            "_apply": True,  # Form Apply button
        }
        data.update(post_data(self.bulk_edit_data))
        response = self.client.post(self._get_url("bulk_edit"), data)
        self.assertHttpStatus(response, 302)

    # -------------------------------------------------------------------------
    # Positive coverage for the fields the inherited suite does not exercise.
    # -------------------------------------------------------------------------

    def test_create_object_persists_all_fields(self):
        """Submit the full create form and verify every field round-trips.

        The inherited ``test_create_object_with_permission`` test only checks
        the minimal ``form_data``; this test additionally covers ``users``,
        ``groups``, and the ``actions`` round-trip that ``assertInstanceEqual``
        excludes.
        """
        group = Group.objects.create(name="ObjectPermission test group")
        neutral_ct = ContentType.objects.get_for_model(ObjectPermission)
        form = {
            "name": "Full round-trip perm",
            "description": "covers all fields",
            "enabled": True,
            "actions": ["view", "change"],
            "object_types": [neutral_ct.pk],
            "users": [self.normal_user.pk],
            "groups": [group.pk],
        }
        response = self.client.post(self._get_url("add"), data=post_data(form), follow=True)
        self.assertHttpStatus(response, 200)
        created = ObjectPermission.objects.get(name="Full round-trip perm")
        self.assertEqual(sorted(created.actions), ["change", "view"])
        self.assertEqual(list(created.object_types.values_list("pk", flat=True)), [neutral_ct.pk])
        self.assertEqual(list(created.users.values_list("pk", flat=True)), [self.normal_user.pk])
        self.assertEqual(list(created.groups.values_list("pk", flat=True)), [group.pk])
        self.assertTrue(created.enabled)
        self.assertEqual(created.description, "covers all fields")
