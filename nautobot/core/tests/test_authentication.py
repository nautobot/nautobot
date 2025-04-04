import uuid

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.contrib.contenttypes.models import ContentType
from django.db.models import Q
from django.test.utils import override_settings
from django.urls import reverse
from netaddr import IPNetwork

from nautobot.core.settings_funcs import sso_auth_enabled
from nautobot.core.testing import NautobotTestClient, TestCase
from nautobot.core.utils import lookup
from nautobot.dcim.models import Location, LocationType
from nautobot.extras.models import ObjectChange, Status
from nautobot.ipam.models import Namespace, Prefix
from nautobot.users.models import ObjectPermission, Token

# Use the proper swappable User model
User = get_user_model()


# Authentication backends required for remote authentication to work
TEST_AUTHENTICATION_BACKENDS = [
    "nautobot.core.authentication.RemoteUserBackend",
    "nautobot.core.authentication.ObjectPermissionBackend",
]


class ExternalAuthenticationTestCase(TestCase):
    client_class = NautobotTestClient

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create(username="remoteuser1")

    def setUp(self):
        """
        Override nautobot.core.testing.TestCase.setUp() so that it doesn't automatically log in the test client.
        """

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
        self.client.get(reverse("home"), follow=True, **headers)
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
            "dcim.add_location": None,
            "dcim.change_location": None,
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
            {"dcim.add_location": None, "dcim.change_location": None},
        )

        response = self.client.get(reverse("home"), follow=True, **headers)
        self.assertEqual(response.status_code, 200)

        new_user = User.objects.get(username="remoteuser2")
        self.assertEqual(
            uuid.UUID(self.client.session.get("_auth_user_id")),
            new_user.pk,
            msg="Authentication failed",
        )
        self.assertTrue(new_user.has_perms(["dcim.add_location", "dcim.change_location"]))

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
    client_class = NautobotTestClient

    @classmethod
    def setUpTestData(cls):
        cls.location_type = LocationType.objects.get(name="Campus")
        cls.locations = Location.objects.filter(location_type=cls.location_type)[:3]
        cls.namespace = Namespace.objects.first()

        cls.statuses = Status.objects.get_for_model(Prefix)

        cls.prefixes = [
            Prefix.objects.create(
                prefix=IPNetwork("10.0.0.0/24"),
                namespace=cls.namespace,
                location=cls.locations[0],
                status=cls.statuses[0],
            ),
            Prefix.objects.create(
                prefix=IPNetwork("10.0.1.0/24"),
                namespace=cls.namespace,
                location=cls.locations[0],
                status=cls.statuses[0],
            ),
            Prefix.objects.create(
                prefix=IPNetwork("10.0.2.0/24"),
                namespace=cls.namespace,
                location=cls.locations[0],
                status=cls.statuses[0],
            ),
            Prefix.objects.create(
                prefix=IPNetwork("10.0.3.0/24"),
                namespace=cls.namespace,
                location=cls.locations[1],
                status=cls.statuses[0],
            ),
            Prefix.objects.create(
                prefix=IPNetwork("10.0.4.0/24"),
                namespace=cls.namespace,
                location=cls.locations[1],
                status=cls.statuses[0],
            ),
            Prefix.objects.create(
                prefix=IPNetwork("10.0.5.0/24"),
                namespace=cls.namespace,
                location=cls.locations[1],
                status=cls.statuses[0],
            ),
            Prefix.objects.create(
                prefix=IPNetwork("10.0.6.0/24"),
                namespace=cls.namespace,
                location=cls.locations[2],
                status=cls.statuses[0],
            ),
            Prefix.objects.create(
                prefix=IPNetwork("10.0.7.0/24"),
                namespace=cls.namespace,
                location=cls.locations[2],
                status=cls.statuses[0],
            ),
            Prefix.objects.create(
                prefix=IPNetwork("10.0.8.0/24"),
                namespace=cls.namespace,
                location=cls.locations[2],
                status=cls.statuses[0],
            ),
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
            constraints={"locations__name__in": [self.locations[0].name]},
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
            constraints={"locations__name__in": [self.locations[0].name]},
            actions=["view"],
        )
        obj_perm.users.add(self.user)
        obj_perm.object_types.add(ContentType.objects.get_for_model(Prefix))

        # Retrieve all objects. Only permitted objects should be returned.
        response = self.client.get(url, **self.header)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], Prefix.objects.filter(locations__in=[self.locations[0]]).count())

    @override_settings(EXEMPT_VIEW_PERMISSIONS=[])
    def test_create_object(self):
        url = reverse("ipam-api:prefix-list")
        data = {
            "prefix": "10.0.9.0/24",
            "namespace": self.namespace.pk,
            "location": self.locations[1].pk,
            "status": self.statuses[1].pk,
        }
        initial_count = Prefix.objects.count()

        # Attempt to create an object without permission
        response = self.client.post(url, data, format="json", **self.header)
        self.assertEqual(response.status_code, 403)

        # Assign object permission
        obj_perm = ObjectPermission.objects.create(
            name="Test permission",
            constraints={"locations__name__in": [self.locations[0].name]},
            actions=["add"],
        )
        obj_perm.users.add(self.user)
        obj_perm.object_types.add(ContentType.objects.get_for_model(Prefix))
        related_obj_perm = ObjectPermission.objects.create(
            name="Related object permission",
            actions=["view"],
        )
        related_obj_perm.users.add(self.user)
        related_obj_perm.object_types.add(
            ContentType.objects.get_for_model(Namespace),
            ContentType.objects.get_for_model(Status),
            ContentType.objects.get_for_model(Location),
        )
        # Attempt to create a non-permitted object
        response = self.client.post(url, data, format="json", **self.header)
        self.assertEqual(response.status_code, 403)
        self.assertEqual(Prefix.objects.count(), initial_count)

        # Attempt to create a permitted object without related object permissions
        data["location"] = self.locations[0].pk
        related_obj_perm.users.remove(self.user)
        response = self.client.post(url, data, format="json", **self.header)
        self.assertEqual(response.status_code, 400)
        self.assertIn(b"Related object not found using the provided attribute", response.content)
        self.assertEqual(Prefix.objects.count(), initial_count)

        # Create a permitted object with related object permissions
        related_obj_perm.users.add(self.user)
        response = self.client.post(url, data, format="json", **self.header)
        self.assertEqual(response.status_code, 201)
        self.assertEqual(Prefix.objects.count(), initial_count + 1)

    @override_settings(EXEMPT_VIEW_PERMISSIONS=[])
    def test_edit_object(self):
        # Attempt to edit an object without permission
        data = {"location": self.locations[0].pk}
        url = reverse("ipam-api:prefix-detail", kwargs={"pk": self.prefixes[0].pk})
        response = self.client.patch(url, data, format="json", **self.header)
        self.assertEqual(response.status_code, 403)

        # Assign object permission
        obj_perm = ObjectPermission.objects.create(
            name="Test permission",
            constraints={"locations__name__in": [self.locations[0].name]},
            actions=["change"],
        )
        obj_perm.users.add(self.user)
        obj_perm.object_types.add(ContentType.objects.get_for_model(Prefix))
        related_obj_perm = ObjectPermission.objects.create(
            name="Related object permission",
            actions=["view"],
        )
        related_obj_perm.users.add(self.user)
        related_obj_perm.object_types.add(
            ContentType.objects.get_for_model(Namespace),
            ContentType.objects.get_for_model(Status),
            ContentType.objects.get_for_model(Location),
        )
        # Attempt to edit a non-permitted object
        data = {"location": self.locations[0].pk}
        url = reverse("ipam-api:prefix-detail", kwargs={"pk": self.prefixes[3].pk})
        response = self.client.patch(url, data, format="json", **self.header)
        self.assertEqual(response.status_code, 404)

        # Attempt to edit a permitted object without related object permissions
        related_obj_perm.users.remove(self.user)
        data["status"] = self.statuses[1].pk
        url = reverse("ipam-api:prefix-detail", kwargs={"pk": self.prefixes[0].pk})
        response = self.client.patch(url, data, format="json", **self.header)
        self.assertEqual(response.status_code, 400)
        self.assertIn(b"Related object not found using the provided attribute", response.content)

        # Edit a permitted object with related object permissions
        related_obj_perm.users.add(self.user)
        response = self.client.patch(url, data, format="json", **self.header)
        self.assertEqual(response.status_code, 200)

        # Attempt to modify a permitted object to a non-permitted object
        data["location"] = self.locations[1].pk
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
            constraints={"locations__name__in": [self.locations[0].name]},
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

    @override_settings(EXEMPT_VIEW_PERMISSIONS=[])
    def test_related_object_permission_constraints_on_get_requests(self):
        """
        Users who have permission to view Location objects, but not LocationType and Status objects
        should still be able to view Location objects from the API.
        """
        self.add_permissions("dcim.view_location")
        response = self.client.get(reverse("dcim-api:location-list"), **self.header)
        self.assertEqual(response.status_code, 200)
        # we should be able to get all the locations
        self.assertEqual(len(response.data["results"]), Location.objects.count())

    @override_settings(EXEMPT_VIEW_PERMISSIONS=[])
    def test_related_object_permission_constraints_on_patch_requests(self):
        """
        Users who have permission to view and change Location objects, but not LocationType and Status objects
        should still be able to change a Location object's name from the API.
        """
        self.add_permissions("dcim.view_location", "dcim.change_location")
        location = Location.objects.first()
        data = {"name": "New Location Name"}
        url = reverse("dcim-api:location-detail", kwargs={"pk": location.pk})
        response = self.client.patch(url, data, format="json", **self.header)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["name"], "New Location Name")

    @override_settings(EXEMPT_VIEW_PERMISSIONS=[])
    def test_user_token_constraints(self):
        """
        Test user token as permission constraints.
        """
        url = reverse("ipam-api:prefix-list")
        data = [
            {
                "prefix": "10.0.9.0/24",
                "namespace": self.namespace.pk,
                "location": self.locations[1].pk,
                "status": self.statuses[1].pk,
            },
            {
                "prefix": "10.0.10.0/24",
                "namespace": self.namespace.pk,
                "location": self.locations[1].pk,
                "status": self.statuses[1].pk,
            },
        ]

        obj_user2 = User.objects.create(username="new-user")
        token_user2 = Token.objects.create(user=obj_user2)
        header_user2 = {"HTTP_AUTHORIZATION": f"Token {token_user2.key}"}
        # Assign object permission to both users to create Prefixes
        obj_perm = ObjectPermission.objects.create(
            name="Test ipam permission",
            actions=["add"],
        )
        obj_perm.users.add(self.user, obj_user2)
        obj_perm.object_types.add(ContentType.objects.get_for_model(Prefix))
        related_obj_perm = ObjectPermission.objects.create(
            name="Related object permission",
            actions=["view"],
        )
        related_obj_perm.users.add(self.user, obj_user2)
        related_obj_perm.object_types.add(
            ContentType.objects.get_for_model(Namespace),
            ContentType.objects.get_for_model(Status),
            ContentType.objects.get_for_model(Location),
        )
        # Create one Prefix object per user
        self.client.post(url, data[0], format="json", **self.header)
        self.client.post(url, data[1], format="json", **header_user2)

        # Assign object permission to both users to view Change Logs, based on user token constraint
        obj_perm = ObjectPermission.objects.create(
            name="Test change log permission",
            constraints={"user": "$user"},
            actions=["view", "list"],
        )
        obj_perm.users.add(self.user, obj_user2)
        obj_perm.object_types.add(ContentType.objects.get_for_model(ObjectChange))

        # Retrieve all ObjectChange Log entries for every user
        url = reverse(lookup.get_route_for_model(ObjectChange, "list", api=True))
        response_user1 = self.client.get(url, **self.header)
        response_user2 = self.client.get(url, **header_user2)

        # Assert every user has permissions to view Change Logs
        self.assertTrue(self.user.has_perms(["extras.view_objectchange", "extras.list_objectchange"]))
        self.assertTrue(obj_user2.has_perms(["extras.view_objectchange", "extras.list_objectchange"]))

        # Check against 1st user's response
        self.assertEqual(response_user1.status_code, 200)
        self.assertEqual(response_user1.data["count"], 1)
        self.assertEqual(response_user1.data["results"][0]["user"]["id"], self.user.pk)

        # Check against 2nd user's response
        self.assertEqual(response_user2.status_code, 200)
        self.assertEqual(response_user2.data["count"], 1)
        self.assertEqual(response_user2.data["results"][0]["user"]["id"], obj_user2.pk)

    @override_settings(EXEMPT_VIEW_PERMISSIONS=[])
    def test_user_token_list_constraints(self):
        """
        Test user token as permission of a list of constraints.
        """
        url = reverse("ipam-api:prefix-list")
        data = [
            {
                "prefix": "10.0.9.0/24",
                "namespace": self.namespace.pk,
                "location": self.locations[1].pk,
                "status": self.statuses[1].pk,
            },
            {
                "prefix": "10.0.10.0/24",
                "namespace": self.namespace.pk,
                "location": self.locations[1].pk,
                "status": self.statuses[1].pk,
            },
        ]

        obj_user2 = User.objects.create(username="new-user")
        token_user2 = Token.objects.create(user=obj_user2)
        header_user2 = {"HTTP_AUTHORIZATION": f"Token {token_user2.key}"}
        # Assign object permission to both users to create Prefixes
        obj_perm = ObjectPermission.objects.create(
            name="Test ipam permission",
            actions=["add"],
        )
        obj_perm.users.add(self.user, obj_user2)
        obj_perm.object_types.add(ContentType.objects.get_for_model(Prefix))
        related_obj_perm = ObjectPermission.objects.create(
            name="Related object permission",
            actions=["view"],
        )
        related_obj_perm.users.add(self.user, obj_user2)
        related_obj_perm.object_types.add(
            ContentType.objects.get_for_model(Namespace),
            ContentType.objects.get_for_model(Status),
            ContentType.objects.get_for_model(Location),
        )
        # Create one Prefix object per user
        self.client.post(url, data[0], format="json", **self.header)
        self.client.post(url, data[1], format="json", **header_user2)

        # Assign object permission to both users to view Change Logs, based on user token constraint
        obj_perm = ObjectPermission.objects.create(
            name="Test change log permission",
            constraints=[{"user": "$user"}, {"action": "delete"}],
            actions=["view", "list"],
        )
        obj_perm.users.add(self.user, obj_user2)
        obj_perm.object_types.add(ContentType.objects.get_for_model(ObjectChange))

        # Retrieve all ObjectChange Log entries for every user
        url = reverse(lookup.get_route_for_model(ObjectChange, "list", api=True))
        response_user1 = self.client.get(url, **self.header)
        response_user2 = self.client.get(url, **header_user2)

        # Assert every user has permissions to view Change Logs
        self.assertTrue(self.user.has_perms(["extras.view_objectchange", "extras.list_objectchange"]))
        self.assertTrue(obj_user2.has_perms(["extras.view_objectchange", "extras.list_objectchange"]))

        # Check against 1st user's response
        self.assertEqual(response_user1.status_code, 200)
        self.assertEqual(
            response_user1.data["count"], ObjectChange.objects.filter(Q(user=self.user) | Q(action="delete")).count()
        )
        self.assertEqual(response_user1.data["results"][0]["user"]["id"], self.user.pk)

        # Check against 2nd user's response
        self.assertEqual(response_user2.status_code, 200)
        self.assertEqual(
            response_user2.data["count"], ObjectChange.objects.filter(Q(user=obj_user2) | Q(action="delete")).count()
        )
        self.assertEqual(response_user2.data["results"][0]["user"]["id"], obj_user2.pk)
