from types import SimpleNamespace
from unittest import mock
import uuid

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser, Group
from django.contrib.contenttypes.models import ContentType
from django.db.models import Q
from django.test import RequestFactory
from django.test.utils import override_settings
from django.urls import reverse
from netaddr import IPNetwork
from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from rest_framework.request import Request

from nautobot.core.api.fields import SerializedPKRelatedField
from nautobot.core.api.serializers import WritableNestedSerializer
from nautobot.core.authentication import assign_permissions_to_user
from nautobot.core.models.querysets import (
    _is_natural_key_lookup,
    get_related_paths,
    restrict_queryset,
    restrict_related_lookups,
)
from nautobot.core.settings_funcs import sso_auth_enabled
from nautobot.core.testing import NautobotTestClient, TestCase
from nautobot.core.utils import lookup
from nautobot.dcim.models import Interface, Location, LocationType, Rack, RackGroup, RackReservation
from nautobot.extras.models import Note, ObjectChange, Status
from nautobot.ipam.models import Namespace, Prefix
from nautobot.tenancy.models import Tenant
from nautobot.users.models import ObjectPermission, Token
from nautobot.vpn.models import VPNTunnelEndpoint

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
        AUTHENTICATION_BACKENDS=TEST_AUTHENTICATION_BACKENDS,
        REMOTE_AUTH_AUTO_CREATE_USER=True,
        EXTERNAL_AUTH_DEFAULT_PERMISSIONS={
            "dcim.add_location": None,
            "dcim.change_location": None,
        },
    )
    def test_external_auth_default_permissions_idempotent(self):
        """Repeated requests must reuse default ObjectPermissions, not re-create them."""
        headers = {"HTTP_REMOTE_USER": "remoteuser3"}

        response = self.client.get(reverse("home"), follow=True, **headers)
        self.assertEqual(response.status_code, 200)

        response = self.client.get(reverse("home"), follow=True, **headers)
        self.assertEqual(response.status_code, 200)

        new_user = User.objects.get(username="remoteuser3")
        self.assertTrue(new_user.has_perms(["dcim.add_location", "dcim.change_location"]))
        self.assertEqual(ObjectPermission.objects.filter(name="dcim.add_location").count(), 1)
        self.assertEqual(ObjectPermission.objects.filter(name="dcim.change_location").count(), 1)

    def test_external_auth_default_permissions_preserves_divergent_existing(self):
        """An existing ObjectPermission with differing actions/constraints is warned about and not assigned."""
        user = User.objects.create(username="remoteuser4")
        location_ct = ContentType.objects.get_for_model(Location)
        existing = ObjectPermission.objects.create(
            name="dcim.add_location",
            actions=["add", "change"],
            constraints={"status": "decommissioning"},
        )
        existing.object_types.add(location_ct)

        with self.assertLogs("nautobot.core.authentication", "WARNING"):
            assign_permissions_to_user(user, {"dcim.add_location": {"status": "active"}})

        existing.refresh_from_db()
        self.assertEqual(existing.actions, ["add", "change"])
        self.assertEqual(existing.constraints, {"status": "decommissioning"})
        self.assertNotIn(user, existing.users.all())

    def test_external_auth_default_permissions_does_not_widen_object_types(self):
        """An existing ObjectPermission scoped to a different object type is warned about, not widened or assigned."""
        user = User.objects.create(username="remoteuser5")
        device_ct = ContentType.objects.get(app_label="dcim", model="device")
        existing = ObjectPermission.objects.create(name="dcim.add_location", actions=["add"], constraints=None)
        existing.object_types.add(device_ct)

        with self.assertLogs("nautobot.core.authentication", "WARNING"):
            assign_permissions_to_user(user, {"dcim.add_location": None})

        self.assertEqual(list(existing.object_types.values_list("model", flat=True)), ["device"])
        self.assertNotIn(user, existing.users.all())

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


class RelatedObjectRestrictionTestCase(TestCase):
    """The related-object fields an App may build on restrict the objects they accept to those the user may view."""

    class TenantNestedSerializer(WritableNestedSerializer):
        class Meta:
            model = Tenant
            fields = ["id"]

    class TenantsSerializer(serializers.Serializer):
        tenants = SerializedPKRelatedField(serializer=serializers.Serializer, queryset=Tenant.objects.all(), many=True)

    def setUp(self):
        super().setUp()
        self.visible_tenant = Tenant.objects.create(name="Visible Tenant")
        self.hidden_tenant = Tenant.objects.create(name="Hidden Tenant")
        obj_perm = ObjectPermission.objects.create(
            name="Tenant permission", actions=["view"], constraints={"name": "Visible Tenant"}
        )
        obj_perm.users.add(self.user)
        obj_perm.object_types.add(ContentType.objects.get_for_model(Tenant))
        self.request = RequestFactory().get("/")
        self.request.user = User.objects.get(pk=self.user.pk)  # Discard the permission cache

    def test_writable_nested_serializer(self):
        serializer = self.TenantNestedSerializer(context={"request": self.request})
        self.assertEqual(serializer.to_internal_value(self.visible_tenant.pk), self.visible_tenant)
        with self.assertRaises(ValidationError):
            serializer.to_internal_value(self.hidden_tenant.pk)

    def test_writable_nested_serializer_lookups(self):
        serializer = self.TenantNestedSerializer(context={"request": self.request})
        self.assertEqual(serializer.to_internal_value({"name": "Visible Tenant"}), self.visible_tenant)
        with self.assertRaisesRegex(ValidationError, "is not a permitted lookup"):
            serializer.to_internal_value({"name": {"startswith": "Visible"}})

    def test_serialized_pk_related_field(self):
        context = {"request": self.request}
        serializer = self.TenantsSerializer(data={"tenants": [self.visible_tenant.pk]}, context=context)
        self.assertTrue(serializer.is_valid(), serializer.errors)
        serializer = self.TenantsSerializer(data={"tenants": [self.hidden_tenant.pk]}, context=context)
        self.assertFalse(serializer.is_valid())
        self.assertIn("tenants", serializer.errors)

    def test_users_and_groups_are_unrestricted_for_a_user_who_may_view_them_all(self):
        """No filter at all is added, rather than one that happens to match everything."""
        superuser = User.objects.create(username="restriction-superuser", is_superuser=True)
        for queryset in (User.objects.all(), Group.objects.all()):
            with self.subTest(model=queryset.model):
                self.assertIs(restrict_queryset(queryset, superuser), queryset)

    def test_manager_is_restricted(self):
        """A manager, as a serializer may pass for its model, is restricted as its queryset would be."""
        for manager in (Tenant.objects, User.objects):
            with self.subTest(model=manager.model):
                self.assertQuerySetEqual(
                    restrict_queryset(manager, self.user), restrict_queryset(manager.all(), self.user), ordered=False
                )
        self.assertNotIn(self.hidden_tenant, restrict_queryset(Tenant.objects, self.user))

    def test_user_may_view_but_not_change_themselves(self):
        """The exception for a user's own record is for viewing it only."""
        other_user = User.objects.create(username="other-user")
        self.assertQuerySetEqual(
            restrict_queryset(User.objects.filter(pk__in=[self.user.pk, other_user.pk]), self.user), [self.user]
        )
        self.assertFalse(restrict_queryset(User.objects.filter(pk=self.user.pk), self.user, "change").exists())

    def test_anonymous_user_may_view_no_users_or_groups(self):
        for queryset in (User.objects.all(), Group.objects.all()):
            with self.subTest(model=queryset.model):
                self.assertFalse(restrict_queryset(queryset, AnonymousUser()).exists())


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
        self.assertIn(b"Reference it by field(s) unique in your data", response.content)
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
        self.assertIn(b"Reference it by field(s) unique in your data", response.content)

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
    def test_related_user_permission_constraints(self):
        """A related user, though `users.User` has no `restrict()`, can be referenced only if it may be viewed."""
        self.location_type.content_types.add(ContentType.objects.get_for_model(Rack))
        rack = Rack.objects.create(
            name="Permission Rack", location=self.locations[0], status=Status.objects.get_for_model(Rack).first()
        )
        other_user = User.objects.create(username="other-user")
        for model, actions in ((RackReservation, ["add"]), (Rack, ["view"])):
            obj_perm = ObjectPermission.objects.create(name=f"{model._meta.model_name} permission", actions=actions)
            obj_perm.users.add(self.user)
            obj_perm.object_types.add(ContentType.objects.get_for_model(model))
        url = reverse("dcim-api:rackreservation-list")

        # Attempt to reference a user that the requesting user may not view
        data = {"rack": rack.pk, "units": [1], "user": other_user.pk, "description": "Permission Reservation"}
        response = self.client.post(url, data, format="json", **self.header)
        self.assertEqual(response.status_code, 400)
<<<<<<< HEAD
        self.assertIn(b"No User matches", response.content)
=======
        self.assertIn(b"Related object not found using the provided attribute", response.content)
>>>>>>> develop
        self.assertFalse(RackReservation.objects.filter(description="Permission Reservation").exists())

        # Reference themselves, which a user may always do
        data["user"] = self.user.pk
        response = self.client.post(url, data, format="json", **self.header)
        self.assertEqual(response.status_code, 201)
        self.assertEqual(RackReservation.objects.get(description="Permission Reservation").user, self.user)

    @override_settings(EXEMPT_VIEW_PERMISSIONS=[])
    def test_related_group_permission_constraints(self):
        """A related group, though `auth.Group` has no `restrict()`, can be referenced only if it may be viewed."""
        # `create_user()` sets an unusable password, rather than a blank one that would fail the update's validation
        other_user = User.objects.create_user(username="other-user")
        visible_group = Group.objects.create(name="Visible Group")
        hidden_group = Group.objects.create(name="Hidden Group")
        for model, actions, constraints in (
            (User, ["change"], None),
            (Group, ["view"], {"name": visible_group.name}),
        ):
            obj_perm = ObjectPermission.objects.create(
                name=f"{model._meta.model_name} permission", actions=actions, constraints=constraints
            )
            obj_perm.users.add(self.user)
            obj_perm.object_types.add(ContentType.objects.get_for_model(model))
        url = reverse("users-api:user-detail", kwargs={"pk": other_user.pk})

        # Attempt to reference a group that the requesting user may not view
        response = self.client.patch(url, {"groups": [hidden_group.pk]}, format="json", **self.header)
        self.assertEqual(response.status_code, 400)
<<<<<<< HEAD
        self.assertIn(b"No Group matches", response.content)
=======
        self.assertIn(b"Related object not found using the provided attribute", response.content)
>>>>>>> develop
        self.assertFalse(other_user.groups.exists())

        # Reference a group that the requesting user may view
        response = self.client.patch(url, {"groups": [visible_group.pk]}, format="json", **self.header)
        self.assertEqual(response.status_code, 200, response.content)
        self.assertQuerySetEqual(other_user.groups.all(), [visible_group])

    @override_settings(EXEMPT_VIEW_PERMISSIONS=[])
    def test_related_content_types_are_not_restricted(self):
        """`ContentType` has no `restrict()` either, but any user may view content types, so may reference them."""
        self.assertQuerySetEqual(
            restrict_queryset(ContentType.objects.all(), self.user), ContentType.objects.all(), ordered=False
        )

    @override_settings(EXEMPT_VIEW_PERMISSIONS=[])
    def test_note_on_unviewable_user(self):
        """A note may be assigned only to an object the user may view, a user included."""
        other_user = User.objects.create(username="other-user")
        obj_perm = ObjectPermission.objects.create(name="Note permission", actions=["add"])
        obj_perm.users.add(self.user)
        obj_perm.object_types.add(ContentType.objects.get_for_model(Note))
        url = reverse("extras-api:note-list")

        def post_note(assigned_object_id):
            data = {"note": "A note", "assigned_object_type": "users.user", "assigned_object_id": assigned_object_id}
            return self.client.post(url, data, format="json", **self.header)

        # Attempt to assign a note to a user that the requesting user may not view, which looks like a nonexistent one
        response = post_note(other_user.pk)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json(), post_note(uuid.uuid4()).json())
        self.assertFalse(Note.objects.filter(assigned_object_id=other_user.pk).exists())

        # Assign a note to themselves, which a user may always reference
        response = post_note(self.user.pk)
        self.assertEqual(response.status_code, 201, response.content)

    @override_settings(EXEMPT_VIEW_PERMISSIONS=[])
    def test_related_object_lookup_restrictions(self):
        """A related object may be looked up only by exact matches on fields the user may see.

        Lookups such as `__startswith`, reverse relations, and sensitive fields are refused outright, as they could
        otherwise reveal data such as another user's API token one character at a time, by whether the related
        object is found. A lookup through another related object only matches through objects the user may view,
        unless it is part of the natural key that identifies the object.
        """
        self.location_type.content_types.add(
            ContentType.objects.get_for_model(Rack), ContentType.objects.get_for_model(RackGroup)
        )
        rack_group = RackGroup.objects.create(
            name="Hidden Rack Group", location=self.locations[0], description="Hidden description"
        )
        rack = Rack.objects.create(
            name="Lookup Rack",
            location=self.locations[0],
            rack_group=rack_group,
            status=Status.objects.get_for_model(Rack).first(),
        )
        other_user = User.objects.create_user(username="other-user")
        token = Token.objects.create(user=other_user)
        RackReservation.objects.create(rack=rack, units=[10], user=other_user, description="Other Reservation")
        for model, actions in ((RackReservation, ["add"]), (Rack, ["view"])):
            obj_perm = ObjectPermission.objects.create(name=f"{model._meta.model_name} permission", actions=actions)
            obj_perm.users.add(self.user)
            obj_perm.object_types.add(ContentType.objects.get_for_model(model))
        url = reverse("dcim-api:rackreservation-list")

        def reserve(rack_lookup, unit):
            data = {"rack": rack_lookup, "units": [unit], "user": self.user.pk, "description": "Lookup Reservation"}
            return self.client.post(url, data, format="json", **self.header)

        # Nested dicts and `__`-separated keys are equivalent spellings of the same lookups; both are covered.
        for _lookup in (
            {
                "pk": str(rack.pk),
                "rack_reservations": {"user": {"tokens": {"key": {"startswith": token.key[:2]}}}},
            },
            {"pk": str(rack.pk), "rack_reservations__user__tokens__key__startswith": "zz"},
            {"name": {"startswith": "Lookup"}},
            {"pk": str(rack.pk), "rack_reservations": {"description": "Other Reservation"}},
            {"pk": str(rack.pk), "rack_reservations": {"user": {"password": other_user.password}}},
        ):
            with self.subTest(lookup=_lookup):
                response = reserve(_lookup, 1)
                self.assertEqual(response.status_code, 400)
                self.assertIn(b"is not a permitted lookup", response.content)

        # A lookup through an unviewable rack group can't find the rack, whether or not the value matches
        response = reserve({"name": rack.name, "rack_group": {"description": "Hidden description"}}, 1)
        self.assertEqual(response.status_code, 400)
<<<<<<< HEAD
        self.assertIn(b"No Rack matches", response.content)
=======
        self.assertIn(b"Related object not found", response.content)
>>>>>>> develop

        # The rack group's natural key, by which exports identify the rack, still finds it
        response = reserve({"name": rack.name, "rack_group": {"name": rack_group.name}}, 2)
        self.assertEqual(response.status_code, 201, response.content)

        # As does the same lookup through the rack group, once the user may view it
        obj_perm = ObjectPermission.objects.create(name="rackgroup permission", actions=["view"])
        obj_perm.users.add(self.user)
        obj_perm.object_types.add(ContentType.objects.get_for_model(RackGroup))
        response = reserve({"name": rack.name, "rack_group": {"description": "Hidden description"}}, 3)
        self.assertEqual(response.status_code, 201, response.content)

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

        # Each user's request created two change records;
        # the constraint must limit each user to only their own records.

        # Check against 1st user's response
        self.assertEqual(response_user1.status_code, 200)
        self.assertEqual(response_user1.data["count"], 2)
        for result in response_user1.data["results"]:
            self.assertEqual(result["user"]["id"], self.user.pk)

        # Check against 2nd user's response
        self.assertEqual(response_user2.status_code, 200)
        self.assertEqual(response_user2.data["count"], 2)
        for result in response_user2.data["results"]:
            self.assertEqual(result["user"]["id"], obj_user2.pk)

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


class RestrictRelatedLookupsTestCase(TestCase):
    """`restrict_related_lookups()` adds as little cost as it can, as it runs for every related object an import names."""

    def setUp(self):
        super().setUp()
        self.superuser = User.objects.create(username="lookup-superuser", is_superuser=True)

    def test_simple_lookups_do_not_determine_the_natural_key(self):
        request = SimpleNamespace(user=self.user)
        with mock.patch.object(Rack, "csv_natural_key_field_lookups") as natural_key_lookups:
            restrict_related_lookups(Rack.objects.all(), {"pk": uuid.uuid4(), "name": "Rack"}, request)
        natural_key_lookups.assert_not_called()

    def test_natural_key_is_determined_once_per_request(self):
        request = SimpleNamespace(user=self.user)
        with mock.patch.object(
            Rack, "csv_natural_key_field_lookups", return_value=["name", "rack_group__name"]
        ) as natural_key_lookups:
            for _ in range(3):
                restrict_related_lookups(Rack.objects.all(), {"rack_group__description": "Group"}, request)
        natural_key_lookups.assert_called_once()

    def test_no_restriction_is_added_for_a_user_who_may_view_everything(self):
        queryset = Rack.objects.all()
        request = SimpleNamespace(user=self.superuser)
        self.assertIs(restrict_related_lookups(queryset, {"rack_group__description": "Group"}, request), queryset)

    def test_natural_key_is_remembered_on_a_drf_request(self):
        """The REST API passes a DRF `Request`, which proxies attributes to the Django request it wraps."""
        request = Request(RequestFactory().get("/"))
        request.user = self.user
        with mock.patch.object(
            Rack, "csv_natural_key_field_lookups", return_value=["name", "rack_group__name"]
        ) as natural_key_lookups:
            for _ in range(2):
                restrict_related_lookups(Rack.objects.all(), {"rack_group__description": "Group"}, request)
        natural_key_lookups.assert_called_once()


class RelatedLookupRulesTestCase(TestCase):
    """The shapes of lookup that may identify a related object, beyond those `test_related_object_lookup_restrictions`
    covers through the REST API."""

    def test_permitted_lookups(self):
        """Lookups that identify an object without revealing anything, which must keep working."""
        for model, lookup_, related_paths in (
            (Rack, "pk", []),
            (Rack, "name", []),
            (Rack, "location_id", []),  # A foreign key's column name
            (Rack, "rack_group__pk", [("rack_group", RackGroup)]),
            (VPNTunnelEndpoint, "source_interface__name", [("source_interface", Interface)]),  # A one-to-one
        ):
            with self.subTest(model=model, lookup=lookup_):
                self.assertEqual(get_related_paths(model, lookup_), related_paths)

    def test_natural_key_of_any_depth(self):
        """A natural key through a tree names as many ancestors as the tree is deep, however deep that is."""
        request = SimpleNamespace(user=self.user)
        deep_lookup = "location__" + "parent__" * 6 + "name"
        self.assertTrue(_is_natural_key_lookup(RackGroup, deep_lookup, request))
        self.assertTrue(_is_natural_key_lookup(Location, "parent__" * 6 + "name", request))
        self.assertFalse(_is_natural_key_lookup(RackGroup, "location__parent__description", request))

    def test_null_relation_is_not_restricted(self):
        """A lookup through a related object that is null passes through no object, so reveals nothing."""
        location_type = LocationType.objects.get(name="Campus")
        location_type.content_types.add(ContentType.objects.get_for_model(Rack))
        rack = Rack.objects.create(
            name="Groupless Rack",
            location=Location.objects.filter(location_type=location_type).first(),
            status=Status.objects.get_for_model(Rack).first(),
        )
        params = {"name": rack.name, "rack_group__description": None}
        queryset = restrict_related_lookups(Rack.objects.all(), params, SimpleNamespace(user=self.user))
        self.assertEqual(queryset.get(**params), rack)
