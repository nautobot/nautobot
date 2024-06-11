from unittest import mock

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.contrib.sessions.middleware import SessionMiddleware
from django.test import override_settings, RequestFactory
from django.urls import reverse
from django.utils.html import escape
from social_django.utils import load_backend, load_strategy

from nautobot.core.testing import ModelViewTestCase, post_data, TestCase
from nautobot.core.testing.utils import extract_page_body
from nautobot.users.models import ObjectPermission, SavedView

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
            self.assertIn("Change Password", str(response.content))

        # Check GET change_password functionality
        get_response = self.client.get(reverse("user:change_password"))
        self.assertIn("New password confirmation", str(get_response.content))

        # Check POST change_password functionality
        post_response = self.client.post(
            reverse("user:change_password"),
            data={
                "old_password": "foo",
                "new_password1": "bar",
                "new_password2": "baz",
            },
        )
        self.assertIn("The two password fields", str(post_response.content))

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
                self.assertNotIn("Change Password", str(response.content))

            # Check GET and POST change_password functionality
            get_response = self.client.get(reverse("user:change_password"), follow=True)
            post_response = self.client.post(reverse("user:change_password"), follow=True)
            for response in [get_response, post_response]:
                self.assertNotIn("New password confirmation", str(response.content))
                # Check redirect
                self.assertIn("User Profile", str(response.content))
                # Check warning message
                self.assertIn(
                    "Remotely authenticated user credentials cannot be changed within Nautobot.",
                    str(response.content),
                )


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


class SavedViewTest(ModelViewTestCase):
    """
    Tests for Saved Views
    """

    model = SavedView

    def get_view_url_for_saved_view(self, saved_view, action="detail"):
        """
        Since saved view detail url redirects, we need to manually construct its detail url
        to test the content of its response.
        """
        view = saved_view.view
        pk = saved_view.pk

        if action == "detail":
            url = reverse(view) + f"?saved_view={pk}"
        elif action == "edit":
            url = saved_view.get_absolute_url() + "edit/"
        else:
            url = reverse("users:savedview_add")

        return url

    @override_settings(EXEMPT_VIEW_PERMISSIONS=["*"])
    def test_get_object_anonymous(self):
        # Make the request as an unauthenticated user
        self.client.logout()
        instance = self._get_queryset().first()
        response = self.client.get(instance.get_absolute_url(), follow=True)
        self.assertHttpStatus(response, 200)
        # This view should redirect to /login/?next={saved_view's absolute url}
        self.assertRedirects(response, f"/login/?next={instance.get_absolute_url()}")

    @override_settings(EXEMPT_VIEW_PERMISSIONS=[])
    def test_get_object_without_permission(self):
        instance = self._get_queryset().first()
        view = instance.view
        app_label = view.split(":")[0]
        model_name = view.split(":")[1].split("_")[0]
        # SavedView detail view should only require the model's view permission
        self.add_permissions(f"{app_label}.view_{model_name}")

        # Try GET with model-level permission
        response = self.client.get(instance.get_absolute_url(), follow=True)
        self.assertHttpStatus(response, 200)

    @override_settings(EXEMPT_VIEW_PERMISSIONS=[])
    def test_get_object_with_permission(self):
        instance = self._get_queryset().first()
        view = instance.view
        app_label = view.split(":")[0]
        model_name = view.split(":")[1].split("_")[0]
        # Add model-level permission
        self.add_permissions("users.view_savedview")
        self.add_permissions(f"{app_label}.view_{model_name}")

        # Try GET with model-level permission
        # SavedView detail view should redirect to the View from which it is derived
        response = self.client.get(instance.get_absolute_url(), follow=True)
        self.assertHttpStatus(response, 200)
        response_body = extract_page_body(response.content.decode(response.charset))
        self.assertIn(escape(instance.name), response_body, msg=response_body)

        query_strings = ["&table_changes_pending=true", "&per_page=1234", "&status=active", "&sort=name"]
        for string in query_strings:
            view_url = self.get_view_url_for_saved_view(instance) + string
            response = self.client.get(view_url)
            self.assertHttpStatus(response, 200)
            response_body = extract_page_body(response.content.decode(response.charset))
            # Assert that the star sign is rendered on the page since there are unsaved changes
            self.assertIn('<i title="Pending changes not saved">', response_body, msg=response_body)

    @override_settings(EXEMPT_VIEW_PERMISSIONS=[])
    def test_get_object_with_constrained_permission(self):
        instance1, instance2 = self._get_queryset().all()[:2]

        # Add object-level permission
        obj_perm = ObjectPermission(
            name="Test permission",
            constraints={"pk": instance1.pk},
            actions=["view", "add", "change", "delete"],
        )
        obj_perm.save()
        obj_perm.users.add(self.user)
        obj_perm.object_types.add(ContentType.objects.get_for_model(self.model))
        app_label = instance1.view.split(":")[0]
        model_name = instance1.view.split(":")[1].split("_")[0]
        self.add_permissions(f"{app_label}.view_{model_name}")

        # Try GET to permitted object
        self.assertHttpStatus(self.client.get(instance1.get_absolute_url()), 302)

        # Try GET to non-permitted object
        # Should be able to get to any SavedView instance as long as the user has "{app_label}.view_{model_name}" permission
        app_label = instance2.view.split(":")[0]
        model_name = instance2.view.split(":")[1].split("_")[0]
        self.add_permissions(f"{app_label}.view_{model_name}")
        self.assertHttpStatus(self.client.get(instance2.get_absolute_url()), 302)

    @override_settings(EXEMPT_VIEW_PERMISSIONS=["*"])
    def test_update_saved_view_as_different_user(self):
        instance = self._get_queryset().first()
        update_query_strings = ["per_page=12", "&status=active", "&name=new_name_filter", "&sort=name"]
        update_url = self.get_view_url_for_saved_view(instance, "edit") + "?" + "".join(update_query_strings)
        different_user = User.objects.create(username="User 1", is_active=True)
        # Try update the saved view with a different user from the owner of the saved view
        self.client.force_login(different_user)
        response = self.client.get(update_url, follow=True)
        self.assertHttpStatus(response, 200)
        response_body = extract_page_body(response.content.decode(response.charset))
        self.assertIn(
            f"You do not have the required permission to modify this Saved View owned by {instance.owner}",
            response_body,
            msg=response_body,
        )

    @override_settings(EXEMPT_VIEW_PERMISSIONS=["*"])
    def test_update_saved_view_as_owner(self):
        instance = self._get_queryset().first()
        update_query_strings = ["per_page=12", "&status=active", "&name=new_name_filter", "&sort=name"]
        update_url = self.get_view_url_for_saved_view(instance, "edit") + "?" + "".join(update_query_strings)
        # Try update the saved view with the same user as the owner of the saved view
        instance.owner.is_active = True
        instance.owner.save()
        self.client.force_login(instance.owner)
        response = self.client.get(update_url)
        self.assertHttpStatus(response, 302)
        instance.refresh_from_db()
        self.assertEqual(instance.config["pagination_count"], 12)
        self.assertEqual(instance.config["filter_params"]["status"], ["active"])
        self.assertEqual(instance.config["filter_params"]["name"], ["new_name_filter"])
        self.assertEqual(instance.config["sort_order"], ["name"])

    @override_settings(EXEMPT_VIEW_PERMISSIONS=["*"])
    def test_delete_saved_view_as_different_user(self):
        instance = self._get_queryset().first()
        instance.config = {
            "filter_params": {
                "location_type": ["Campus", "Building", "Floor", "Elevator"],
                "tenant": ["Krause, Welch and Fuentes"],
            },
            "table_config": {"LocationTable": {"columns": ["name", "status", "location_type", "tags"]}},
        }
        instance.validated_save()
        delete_url = reverse("users:savedview_delete", kwargs={"pk": instance.pk})
        different_user = User.objects.create(username="User 2", is_active=True)
        # Try delete the saved view with a different user from the owner of the saved view
        self.client.force_login(different_user)
        response = self.client.post(delete_url, follow=True)
        self.assertHttpStatus(response, 200)
        response_body = extract_page_body(response.content.decode(response.charset))
        self.assertIn(
            f"You do not have the required permission to delete this Saved View owned by {instance.owner}",
            response_body,
            msg=response_body,
        )

    @override_settings(EXEMPT_VIEW_PERMISSIONS=["*"])
    def test_delete_saved_view_as_owner(self):
        instance = self._get_queryset().first()
        instance.config = {
            "filter_params": {
                "location_type": ["Campus", "Building", "Floor", "Elevator"],
                "tenant": ["Krause, Welch and Fuentes"],
            },
            "table_config": {"LocationTable": {"columns": ["name", "status", "location_type", "tags"]}},
        }
        instance.validated_save()
        delete_url = reverse("users:savedview_delete", kwargs={"pk": instance.pk})
        # Delete functionality should work even without "users.delete_savedview" permissions
        # if the saved view belongs to the user.
        instance.owner.is_active = True
        instance.owner.save()
        self.client.force_login(instance.owner)
        response = self.client.post(delete_url, follow=True)
        self.assertHttpStatus(response, 200)
        response_body = extract_page_body(response.content.decode(response.charset))
        self.assertIn(
            "Are you sure you want to delete saved view",
            response_body,
            msg=response_body,
        )

    @override_settings(EXEMPT_VIEW_PERMISSIONS=["*"])
    def test_create_saved_view(self):
        instance = self._get_queryset().first()
        # User should be able to create saved view with only "{app_label}.view_{model_name}" permission
        # self.add_permissions("users.add_savedview")
        view = instance.view
        app_label = view.split(":")[0]
        model_name = view.split(":")[1].split("_")[0]
        self.add_permissions(f"{app_label}.view_{model_name}")
        create_query_strings = [
            f"saved_view={instance.pk}",
            "&per_page=12",
            "&status=active",
            "&name=new_name_filter",
            "&sort=name",
        ]
        create_url = self.get_view_url_for_saved_view(instance, "create")
        request = {
            "path": create_url,
            "data": post_data(
                {"name": "New Test View", "view": f"{instance.view}", "params": "".join(create_query_strings)}
            ),
        }
        self.assertHttpStatus(self.client.post(**request), 302)
        instance = SavedView.objects.get(name="New Test View")
        self.assertEqual(instance.config["pagination_count"], 12)
        self.assertEqual(instance.config["filter_params"]["status"], ["active"])
        self.assertEqual(instance.config["filter_params"]["name"], ["new_name_filter"])
        self.assertEqual(instance.config["sort_order"], ["name"])
