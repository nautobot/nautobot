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

    The viewset is wrapped in AdminRequiredMixin, so `setUp` force-logs a
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
        # `object_types` is required by the form, but this view is admin-only
        # (AdminRequiredMixin bypasses the ObjectPermission constraint system
        # entirely), so the specific model chosen is arbitrary — `Group` is
        # used as a stable, non-self-referential placeholder.
        cls.group_content_type = ContentType.objects.get_for_model(Group)
        cls.instance = ObjectPermission.objects.create(
            name="sample-test Permission",
            actions=["view", "add", "change", "delete"],
        )
        cls.instance.object_types.set([cls.group_content_type])

        # NOTE: Do not use `bulk_create` here — it skips `save()` and
        # cannot set M2M fields, which leaves the fixtures missing the
        # required `object_types` and breaks any flow that revalidates them.
        cls.instances = []
        for i in range(1, 4):
            op = ObjectPermission.objects.create(name=f"Perm {i}", actions=["view"])
            op.object_types.set([cls.group_content_type])
            cls.instances.append(op)

        cls.form_data = {
            "name": "New Permission",
            "description": "Round-trip test",
            "enabled": True,
            "object_types": [cls.group_content_type.pk],
            "can_view": True,
        }

        # `ObjectPermissionBulkEditForm` currently exposes only `enabled`;
        # The inherited `test_bulk_edit_objects_with_permission` test calls
        # `field.clean(value)` directly (bypassing the widget), so the value
        # has to parse to False through both `NullBooleanSelect.value_from_datadict`
        # (widget path) and `NullBooleanField.clean` (direct field path).
        # The intersection for False is the literal string "False".
        cls.bulk_edit_data = {
            "enabled": "False",
        }

    def setUp(self):
        super().setUp()
        # The viewset is admin-only; most inherited tests assume the logged-in
        # user can access the view, so authenticate as a superuser up-front.
        # Overrides below re-authenticate as `self.normal_user` in the cases
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
    # Admin-gate short-circuit tests — these override the inherited
    # `*_without_permission` tests with a stronger assertion: grant the
    # non-admin user an ObjectPermission that would *normally* allow every
    # action on ObjectPermission records, then verify each surface still
    # returns 403. A bare "user with no permissions → 403" test is ambiguous
    # about whether `AdminRequiredMixin` actually fired or whether the normal
    # permission backend would have rejected the request anyway; granting a
    # spurious permission first makes 403 attributable to the admin gate.
    # -------------------------------------------------------------------------

    def _grant_full_objectpermission_to_normal_user(self):
        """Give `normal_user` an ObjectPermission that would normally allow
        every action on ObjectPermission records."""
        grant = ObjectPermission.objects.create(
            name="spurious admin-bypass attempt",
            actions=["view", "add", "change", "delete"],
        )
        grant.object_types.add(ContentType.objects.get_for_model(ObjectPermission))
        grant.users.add(self.normal_user)

    def test_list_objects_without_permission(self):
        self._grant_full_objectpermission_to_normal_user()
        self.client.force_login(self.normal_user)
        self.assertHttpStatus(self.client.get(self._get_url("list")), 403)

    def test_get_object_without_permission(self):
        self._grant_full_objectpermission_to_normal_user()
        self.client.force_login(self.normal_user)
        self.assertHttpStatus(self.client.get(self.instance.get_absolute_url()), 403)

    def test_edit_object_without_permission(self):
        self._grant_full_objectpermission_to_normal_user()
        self.client.force_login(self.normal_user)
        self.assertHttpStatus(self.client.get(self._get_url("edit", self.instance)), 403)

    def test_delete_object_without_permission(self):
        self._grant_full_objectpermission_to_normal_user()
        self.client.force_login(self.normal_user)
        self.assertHttpStatus(self.client.get(self._get_url("delete", self.instance)), 403)

    def test_bulk_delete_objects_without_permission(self):
        self._grant_full_objectpermission_to_normal_user()
        self.client.force_login(self.normal_user)
        self.assertHttpStatus(self.client.post(self._get_url("bulk_delete")), 403)

    def test_bulk_edit_objects_without_permission(self):
        self._grant_full_objectpermission_to_normal_user()
        self.client.force_login(self.normal_user)
        self.assertHttpStatus(self.client.post(self._get_url("bulk_edit")), 403)

    # -------------------------------------------------------------------------
    # Admin-bypass documentation tests — these override the base
    # `_with_constrained_permission` tests because AdminRequiredMixin
    # short-circuits before ObjectPermission constraints are ever consulted.
    # The overrides therefore document "admin has unconditional access" rather
    # than the base tests' "constrained grantee is filtered" assertion.
    # -------------------------------------------------------------------------

    def test_list_objects_with_constrained_permission(self):
        """Admin bypasses ObjectPermission constraints; verify the list view shows all rows."""
        response = self.client.get(self._get_url("list"), headers={"HX-Request": "true"})
        self.assertHttpStatus(response, 200)
        for op in [self.instance, *self.instances]:
            self.assertBodyContains(response, op.name)

    def test_get_object_with_constrained_permission(self):
        """Admin bypasses ObjectPermission constraints; verify the detail view renders for any instance."""
        response = self.client.get(self.instance.get_absolute_url())
        self.assertHttpStatus(response, 200)
        self.assertBodyContains(response, self.instance.name)

    def test_edit_object_with_constrained_permission(self):
        """Admin bypasses ObjectPermission constraints; verify the edit POST actually persists changes."""
        # GET the edit form
        self.assertHttpStatus(self.client.get(self._get_url("edit", self.instance)), 200)

        # POST the form data and confirm the instance round-trips
        response = self.client.post(
            self._get_url("edit", self.instance),
            data=post_data(self.form_data),
        )
        self.assertHttpStatus(response, 302)
        self.assertInstanceEqual(self._get_queryset().get(pk=self.instance.pk), self.form_data)

    def test_delete_object_with_constrained_permission(self):
        """Admin bypasses ObjectPermission constraints; verify the delete POST actually removes the record."""
        instance = self.instances[0]
        # GET the delete confirmation page
        self.assertHttpStatus(self.client.get(self._get_url("delete", instance)), 200)

        # POST confirm=True and verify the row is gone
        response = self.client.post(
            self._get_url("delete", instance),
            data=post_data({"confirm": True}),
        )
        self.assertHttpStatus(response, 302)
        self.assertFalse(self._get_queryset().filter(pk=instance.pk).exists())

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
        """Verify the bulk-edit apply path dispatches the async job when invoked by admin.

        Nautobot's bulk-edit UI hands off to a `Bulk Edit Objects` system Job
        rather than mutating rows inline (same pattern as bulk-delete), so the
        actual `enabled` flip happens asynchronously inside the Job and is not
        observable from the HTTP response. Assert the Job was enqueued and the
        response redirects to its detail page; the base constraint-filter test
        is inapplicable to an admin-only view.
        """
        target = self.instances[0]
        target.enabled = True
        target.save()

        data = {
            "pk": [target.pk],
            "_apply": True,  # Form Apply button
        }
        data.update(post_data(self.bulk_edit_data))
        response = self.client.post(self._get_url("bulk_edit"), data)

        job_result = JobResult.objects.filter(name="Bulk Edit Objects").first()
        self.assertIsNotNone(job_result)
        self.assertRedirects(
            response,
            reverse("extras:jobresult", args=[job_result.pk]),
            status_code=302,
            target_status_code=200,
        )

    # -------------------------------------------------------------------------
    # Positive coverage for the fields the inherited suite does not exercise.
    # -------------------------------------------------------------------------

    def test_create_object_persists_all_fields(self):
        """Submit the full create form and verify every field round-trips.

        The inherited `test_create_object_with_permission` test only checks
        the minimal `form_data`; this test additionally covers `users` and
        `groups`, which the shared `form_data` does not populate.
        """
        group = Group.objects.create(name="ObjectPermission test group")
        form = {
            "name": "Full round-trip perm",
            "description": "covers all fields",
            "enabled": True,
            "object_types": [self.group_content_type.pk],
            "users": [self.normal_user.pk],
            "groups": [group.pk],
            # Canonical actions via the new `can_*` checkboxes; no additional actions.
            "can_view": True,
            "can_change": True,
            "actions": [],
        }
        response = self.client.post(self._get_url("add"), data=post_data(form), follow=True)
        self.assertHttpStatus(response, 200)
        created = ObjectPermission.objects.get(name="Full round-trip perm")
        self.assertEqual(sorted(created.actions), ["change", "view"])
        self.assertEqual(list(created.object_types.values_list("pk", flat=True)), [self.group_content_type.pk])
        self.assertEqual(list(created.users.values_list("pk", flat=True)), [self.normal_user.pk])
        self.assertEqual(list(created.groups.values_list("pk", flat=True)), [group.pk])
        self.assertTrue(created.enabled)
        self.assertEqual(created.description, "covers all fields")

    def test_create_object_merges_canonical_checkboxes(self):
        """Verify the form's `can_*` checkboxes merge into `instance.actions`.

        `ObjectPermissionForm` exposes the four canonical CRUD actions as
        `can_view`/`can_add`/`can_change`/`can_delete` boolean fields and
        keeps a separate `actions` JSONField for any non-canonical extras.
        `clean()` unions any checked boxes into `cleaned_data["actions"]`
        before save, so the persisted `instance.actions` list reflects
        every checked box.

        Note: the *additional* (non-canonical) actions branch isn't exercised
        here. The `actions` JSONField expects a JSON-parseable string in the
        POST body, and `post_data` does not serialize Python lists into valid
        JSON — so driving additional actions through the test client needs a
        separate fixture shape and is left for a follow-up.
        """
        form = {
            "name": "Merged actions perm",
            "enabled": True,
            "object_types": [self.group_content_type.pk],
            "can_view": True,
            "can_change": True,
            "actions": [],
        }
        response = self.client.post(self._get_url("add"), data=post_data(form), follow=True)
        self.assertHttpStatus(response, 200)
        created = ObjectPermission.objects.get(name="Merged actions perm")
        self.assertEqual(sorted(created.actions), ["change", "view"])
