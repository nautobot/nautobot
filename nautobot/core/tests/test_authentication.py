import uuid

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.contrib.contenttypes.models import ContentType
from django.test import Client
from django.test.utils import override_settings
from django.urls import reverse
from netaddr import IPNetwork
from rest_framework.test import APIClient

from nautobot.core.settings_funcs import sso_auth_enabled
from nautobot.dcim.models import Site
from nautobot.extras.models import Status
from nautobot.ipam.models import Prefix
from nautobot.users.models import ObjectPermission, Token
from nautobot.utilities.testing import TestCase


# Use the proper swappable User model
User = get_user_model()


# Authentication backends required for remote authentication to work
TEST_AUTHENTICATION_BACKENDS = [
    "nautobot.core.authentication.RemoteUserBackend",
    "nautobot.core.authentication.ObjectPermissionBackend",
]


class ExternalAuthenticationTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create(username="remoteuser1")

    def setUp(self):
        self.client = Client()

    def test_remote_auth_disabled(self):
        """
        Test enabling remote authentication with the default configuration.
        """
        headers = {
            "HTTP_REMOTE_USER": "remoteuser1",
        }

        self.assertFalse("nautobot.core.authentication.RemoteUserBackend" in settings.AUTHENTICATION_BACKENDS)
        self.assertEqual(settings.REMOTE_AUTH_HEADER, "HTTP_REMOTE_USER")

        # Client should not be authenticated
        self.client.get(reverse("home"), follow=True, **headers)  # noqa
        self.assertNotIn("_auth_user_id", self.client.session)

    @override_settings(AUTHENTICATION_BACKENDS=TEST_AUTHENTICATION_BACKENDS)
    def test_remote_auth_enabled(self):
        """
        Test enabling remote authentication with the default configuration.
        """
        headers = {
            "HTTP_REMOTE_USER": "remoteuser1",
        }

        self.assertTrue("nautobot.core.authentication.RemoteUserBackend" in settings.AUTHENTICATION_BACKENDS)
        self.assertEqual(settings.REMOTE_AUTH_HEADER, "HTTP_REMOTE_USER")

        response = self.client.get(reverse("home"), follow=True, **headers)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            uuid.UUID(self.client.session.get("_auth_user_id")),
            self.user.pk,
            msg="Authentication failed",
        )

    @override_settings(AUTHENTICATION_BACKENDS=TEST_AUTHENTICATION_BACKENDS, REMOTE_AUTH_HEADER="HTTP_FOO")
    def test_remote_auth_custom_header(self):
        """
        Test enabling remote authentication with a custom HTTP header.
        """
        headers = {
            "HTTP_FOO": "remoteuser1",
        }

        self.assertTrue("nautobot.core.authentication.RemoteUserBackend" in settings.AUTHENTICATION_BACKENDS)
        self.assertEqual(settings.REMOTE_AUTH_HEADER, "HTTP_FOO")

        response = self.client.get(reverse("home"), follow=True, **headers)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            uuid.UUID(self.client.session.get("_auth_user_id")),
            self.user.pk,
            msg="Authentication failed",
        )

    @override_settings(
        AUTHENTICATION_BACKENDS=TEST_AUTHENTICATION_BACKENDS,
        REMOTE_AUTH_AUTO_CREATE_USER=True,
    )
    def test_remote_auth_auto_create(self):
        """
        Test enabling remote authentication with automatic user creation disabled.
        """
        headers = {
            "HTTP_REMOTE_USER": "remoteuser2",
        }

        self.assertTrue("nautobot.core.authentication.RemoteUserBackend" in settings.AUTHENTICATION_BACKENDS)
        self.assertTrue(settings.REMOTE_AUTH_AUTO_CREATE_USER)
        self.assertEqual(settings.REMOTE_AUTH_HEADER, "HTTP_REMOTE_USER")

        response = self.client.get(reverse("home"), follow=True, **headers)
        self.assertEqual(response.status_code, 200)

        # Local user should have been automatically created
        new_user = User.objects.get(username="remoteuser2")
        self.assertEqual(
            uuid.UUID(self.client.session.get("_auth_user_id")),
            new_user.pk,
            msg="Authentication failed",
        )

    @override_settings(
        AUTHENTICATION_BACKENDS=TEST_AUTHENTICATION_BACKENDS,
        REMOTE_AUTH_AUTO_CREATE_USER=True,
        EXTERNAL_AUTH_DEFAULT_GROUPS=["Group 1", "Group 2"],
    )
    def test_EXTERNAL_AUTH_DEFAULT_groups(self):
        """
        Test enabling remote authentication with the default configuration.
        """
        headers = {
            "HTTP_REMOTE_USER": "remoteuser2",
        }

        self.assertTrue("nautobot.core.authentication.RemoteUserBackend" in settings.AUTHENTICATION_BACKENDS)
        self.assertTrue(settings.REMOTE_AUTH_AUTO_CREATE_USER)
        self.assertEqual(settings.REMOTE_AUTH_HEADER, "HTTP_REMOTE_USER")
        self.assertEqual(settings.EXTERNAL_AUTH_DEFAULT_GROUPS, ["Group 1", "Group 2"])

        # Create required groups
        groups = (
            Group.objects.create(name="Group 1"),
            Group.objects.create(name="Group 2"),
            Group.objects.create(name="Group 3"),
        )

        response = self.client.get(reverse("home"), follow=True, **headers)
        self.assertEqual(response.status_code, 200)

        new_user = User.objects.get(username="remoteuser2")
        self.assertEqual(
            uuid.UUID(self.client.session.get("_auth_user_id")),
            new_user.pk,
            msg="Authentication failed",
        )
        self.assertSetEqual({groups[0], groups[1]}, set(new_user.groups.all()))

    @override_settings(
        AUTHENTICATION_BACKENDS=TEST_AUTHENTICATION_BACKENDS,
        REMOTE_AUTH_AUTO_CREATE_USER=True,
        EXTERNAL_AUTH_DEFAULT_PERMISSIONS={
            "dcim.add_site": None,
            "dcim.change_site": None,
        },
    )
    def test_external_auth_default_permissions(self):
        """
        Test enabling remote authentication with the default configuration.
        """
        headers = {
            "HTTP_REMOTE_USER": "remoteuser2",
        }

        self.assertTrue("nautobot.core.authentication.RemoteUserBackend" in settings.AUTHENTICATION_BACKENDS)
        self.assertTrue(settings.REMOTE_AUTH_AUTO_CREATE_USER)
        self.assertEqual(settings.REMOTE_AUTH_HEADER, "HTTP_REMOTE_USER")
        self.assertEqual(
            settings.EXTERNAL_AUTH_DEFAULT_PERMISSIONS,
            {"dcim.add_site": None, "dcim.change_site": None},
        )

        response = self.client.get(reverse("home"), follow=True, **headers)
        self.assertEqual(response.status_code, 200)

        new_user = User.objects.get(username="remoteuser2")
        self.assertEqual(
            uuid.UUID(self.client.session.get("_auth_user_id")),
            new_user.pk,
            msg="Authentication failed",
        )
        self.assertTrue(new_user.has_perms(["dcim.add_site", "dcim.change_site"]))

    @override_settings(
        SOCIAL_AUTH_BACKEND_PREFIX="custom_auth.backend",
    )
    def test_custom_social_auth_backend_prefix_sso_enabled_true(self):
        """
        Test specifying custom social auth backend prefix for custom auth plugins return True with matching backend prefix.
        """

        self.assertEqual(settings.SOCIAL_AUTH_BACKEND_PREFIX, "custom_auth.backend")
        self.assertTrue(
            sso_auth_enabled(("custom_auth.backend.pingid", "nautobot.core.authentication.ObjectPermissionBackend"))
        )

    @override_settings(
        SOCIAL_AUTH_BACKEND_PREFIX="custom_auth.backend",
    )
    def test_custom_social_auth_backend_prefix_sso_enabled_false(self):
        """
        Test specifying custom social auth backend prefix for custom auth plugins with no matching custom backend.
        """

        self.assertEqual(settings.SOCIAL_AUTH_BACKEND_PREFIX, "custom_auth.backend")
        self.assertFalse(sso_auth_enabled(tuple(TEST_AUTHENTICATION_BACKENDS)))

    def test_default_social_auth_backend_prefix_sso_enabled_true(self):
        """
        Test default check for 'social_core.backends' with backend specified that starts with default backend prefix.
        """

        self.assertTrue(
            sso_auth_enabled(
                ("social_core.backends.google.GoogleOauth2", "nautobot.core.authentication.ObjectPermissionBackend")
            )
        )

    def test_default_social_auth_backend_prefix_sso_enabled_false(self):
        """
        Test default check for 'social_core.backends' with no backends specified that startswith prefix.
        """

        self.assertFalse(sso_auth_enabled(tuple(TEST_AUTHENTICATION_BACKENDS)))


class ObjectPermissionAPIViewTestCase(TestCase):
    client_class = APIClient

    @classmethod
    def setUpTestData(cls):

        cls.sites = Site.objects.all()[:3]

        statuses = Status.objects.get_for_model(Prefix)

        cls.prefixes = [
            Prefix.objects.create(prefix=IPNetwork("10.0.0.0/24"), site=cls.sites[0], status=statuses[0]),
            Prefix.objects.create(prefix=IPNetwork("10.0.1.0/24"), site=cls.sites[0], status=statuses[0]),
            Prefix.objects.create(prefix=IPNetwork("10.0.2.0/24"), site=cls.sites[0], status=statuses[0]),
            Prefix.objects.create(prefix=IPNetwork("10.0.3.0/24"), site=cls.sites[1], status=statuses[0]),
            Prefix.objects.create(prefix=IPNetwork("10.0.4.0/24"), site=cls.sites[1], status=statuses[0]),
            Prefix.objects.create(prefix=IPNetwork("10.0.5.0/24"), site=cls.sites[1], status=statuses[0]),
            Prefix.objects.create(prefix=IPNetwork("10.0.6.0/24"), site=cls.sites[2], status=statuses[0]),
            Prefix.objects.create(prefix=IPNetwork("10.0.7.0/24"), site=cls.sites[2], status=statuses[0]),
            Prefix.objects.create(prefix=IPNetwork("10.0.8.0/24"), site=cls.sites[2], status=statuses[0]),
        ]

    def setUp(self):
        """
        Create a test user and token for API calls.
        """
        self.user = User.objects.create(username="testuser")
        self.token = Token.objects.create(user=self.user)
        self.header = {"HTTP_AUTHORIZATION": f"Token {self.token.key}"}

    @override_settings(EXEMPT_VIEW_PERMISSIONS=[])
    def test_get_object(self):

        # Attempt to retrieve object without permission
        url = reverse("ipam-api:prefix-detail", kwargs={"pk": self.prefixes[0].pk})
        response = self.client.get(url, **self.header)
        self.assertEqual(response.status_code, 403)

        # Assign object permission
        obj_perm = ObjectPermission.objects.create(
            name="Test permission",
            constraints={"site__name": self.sites[0].name},
            actions=["view"],
        )
        obj_perm.users.add(self.user)
        obj_perm.object_types.add(ContentType.objects.get_for_model(Prefix))

        # Retrieve permitted object
        url = reverse("ipam-api:prefix-detail", kwargs={"pk": self.prefixes[0].pk})
        response = self.client.get(url, **self.header)
        self.assertEqual(response.status_code, 200)

        # Attempt to retrieve non-permitted object
        url = reverse("ipam-api:prefix-detail", kwargs={"pk": self.prefixes[3].pk})
        response = self.client.get(url, **self.header)
        self.assertEqual(response.status_code, 404)

    @override_settings(EXEMPT_VIEW_PERMISSIONS=[])
    def test_list_objects(self):
        url = reverse("ipam-api:prefix-list")

        # Attempt to list objects without permission
        response = self.client.get(url, **self.header)
        self.assertEqual(response.status_code, 403)

        # Assign object permission
        obj_perm = ObjectPermission.objects.create(
            name="Test permission",
            constraints={"site__name": self.sites[0].name},
            actions=["view"],
        )
        obj_perm.users.add(self.user)
        obj_perm.object_types.add(ContentType.objects.get_for_model(Prefix))

        # Retrieve all objects. Only permitted objects should be returned.
        response = self.client.get(url, **self.header)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], Prefix.objects.filter(site=self.sites[0]).count())

    @override_settings(EXEMPT_VIEW_PERMISSIONS=[])
    def test_create_object(self):
        url = reverse("ipam-api:prefix-list")
        data = {
            "prefix": "10.0.9.0/24",
            "site": self.sites[1].pk,
            "status": "active",
        }
        initial_count = Prefix.objects.count()

        # Attempt to create an object without permission
        response = self.client.post(url, data, format="json", **self.header)
        self.assertEqual(response.status_code, 403)

        # Assign object permission
        obj_perm = ObjectPermission.objects.create(
            name="Test permission",
            constraints={"site__name": self.sites[0].name},
            actions=["add"],
        )
        obj_perm.users.add(self.user)
        obj_perm.object_types.add(ContentType.objects.get_for_model(Prefix))

        # Attempt to create a non-permitted object
        response = self.client.post(url, data, format="json", **self.header)
        self.assertEqual(response.status_code, 403)
        self.assertEqual(Prefix.objects.count(), initial_count)

        # Create a permitted object
        data["site"] = self.sites[0].pk
        response = self.client.post(url, data, format="json", **self.header)
        self.assertEqual(response.status_code, 201)
        self.assertEqual(Prefix.objects.count(), initial_count + 1)

    @override_settings(EXEMPT_VIEW_PERMISSIONS=[])
    def test_edit_object(self):

        # Attempt to edit an object without permission
        data = {"site": self.sites[0].pk}
        url = reverse("ipam-api:prefix-detail", kwargs={"pk": self.prefixes[0].pk})
        response = self.client.patch(url, data, format="json", **self.header)
        self.assertEqual(response.status_code, 403)

        # Assign object permission
        obj_perm = ObjectPermission.objects.create(
            name="Test permission",
            constraints={"site__name": f"{self.sites[0].name}"},
            actions=["change"],
        )
        obj_perm.users.add(self.user)
        obj_perm.object_types.add(ContentType.objects.get_for_model(Prefix))

        # Attempt to edit a non-permitted object
        data = {"site": self.sites[0].pk}
        url = reverse("ipam-api:prefix-detail", kwargs={"pk": self.prefixes[3].pk})
        response = self.client.patch(url, data, format="json", **self.header)
        self.assertEqual(response.status_code, 404)

        # Edit a permitted object
        data["status"] = "reserved"
        url = reverse("ipam-api:prefix-detail", kwargs={"pk": self.prefixes[0].pk})
        response = self.client.patch(url, data, format="json", **self.header)
        self.assertEqual(response.status_code, 200)

        # Attempt to modify a permitted object to a non-permitted object
        data["site"] = self.sites[1].pk
        url = reverse("ipam-api:prefix-detail", kwargs={"pk": self.prefixes[0].pk})
        response = self.client.patch(url, data, format="json", **self.header)
        self.assertEqual(response.status_code, 403)

    @override_settings(EXEMPT_VIEW_PERMISSIONS=[])
    def test_delete_object(self):

        # Attempt to delete an object without permission
        url = reverse("ipam-api:prefix-detail", kwargs={"pk": self.prefixes[0].pk})
        response = self.client.delete(url, format="json", **self.header)
        self.assertEqual(response.status_code, 403)

        # Assign object permission
        obj_perm = ObjectPermission.objects.create(
            name="Test permission",
            constraints={"site__name": self.sites[0].name},
            actions=["delete"],
        )
        obj_perm.users.add(self.user)
        obj_perm.object_types.add(ContentType.objects.get_for_model(Prefix))

        # Attempt to delete a non-permitted object
        url = reverse("ipam-api:prefix-detail", kwargs={"pk": self.prefixes[3].pk})
        response = self.client.delete(url, format="json", **self.header)
        self.assertEqual(response.status_code, 404)

        # Delete a permitted object
        url = reverse("ipam-api:prefix-detail", kwargs={"pk": self.prefixes[0].pk})
        response = self.client.delete(url, format="json", **self.header)
        self.assertEqual(response.status_code, 204)
