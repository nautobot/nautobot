from unittest import mock
import uuid

from django.contrib.auth.models import AnonymousUser
from django.contrib.contenttypes.models import ContentType
from django.test import override_settings, tag
from django.urls import reverse
from django.utils.html import escape
from rest_framework import status

from nautobot.core.graphql import execute_query
from nautobot.core.testing import APITestCase, TestCase
from nautobot.core.testing.utils import post_data
from nautobot.core.testing.views import ModelViewTestCase
from nautobot.core.utils.lookup import get_changes_for_model
from nautobot.dcim.choices import InterfaceModeChoices, InterfaceTypeChoices
from nautobot.dcim.models import (
    Device,
    DeviceType,
    DeviceTypeToSoftwareImageFile,
    Interface,
    Location,
    LocationType,
    SoftwareImageFile,
)
from nautobot.extras import context_managers
from nautobot.extras.choices import (
    CustomFieldTypeChoices,
    DynamicGroupOperatorChoices,
    DynamicGroupTypeChoices,
    ObjectChangeActionChoices,
    ObjectChangeEventContextChoices,
)
from nautobot.extras.models import (
    CustomField,
    CustomFieldChoice,
    DynamicGroup,
    DynamicGroupMembership,
    ObjectChange,
    Role,
    Status,
    Tag,
)
from nautobot.ipam.models import (
    IPAddress,
    IPAddressToInterface,
    Prefix,
    PrefixLocationAssignment,
    RouteTarget,
    VLAN,
    VLANGroup,
    VRF,
)
from nautobot.virtualization.models import Cluster, ClusterType, VirtualMachine, VMInterface


class ChangeLogViewTest(ModelViewTestCase):
    model = Location

    @classmethod
    def setUpTestData(cls):
        # Create a custom field on the Location model
        ct = ContentType.objects.get_for_model(Location)
        cf = CustomField(type=CustomFieldTypeChoices.TYPE_TEXT, label="My Field", required=False)
        cf.validated_save()
        cf.content_types.set([ct])

        # Create a select custom field on the Location model
        cf_select = CustomField.objects.create(
            type=CustomFieldTypeChoices.TYPE_SELECT,
            label="My Field Select",
            required=False,
        )
        cf_select.validated_save()
        cf_select.content_types.set([ct])

        CustomFieldChoice.objects.create(custom_field=cf_select, value="Bar")
        CustomFieldChoice.objects.create(custom_field=cf_select, value="Foo")

        cls.tags = Tag.objects.get_for_model(Location)

        cls.location_status = Status.objects.get_for_model(Location).first()
        cls.location_type = LocationType.objects.create(name="Test Root")
        cls.location_type.validated_save()

    def test_create_object(self):
        form_data = {
            "location_type": self.location_type.pk,
            "name": "Test Location 1",
            "status": self.location_status.pk,
            "cf_my_field": "ABC",
            "cf_my_field_select": "Bar",
            "tags": [tag.pk for tag in self.tags],
        }

        request = {
            "path": self._get_url("add"),
            "data": post_data(form_data),
        }
        self.add_permissions(
            "dcim.add_location",
            "dcim.view_locationtype",
            "dcim.change_locationtype",
            "extras.view_tag",
            "extras.view_status",
        )
        response = self.client.post(**request)
        self.assertHttpStatus(response, 302)

        # Verify the creation of a new ObjectChange record
        location = Location.objects.get(name="Test Location 1")
        # First OC is the creation; second is the tags update
        oc = get_changes_for_model(location).first()
        self.assertEqual(oc.changed_object, location)
        self.assertEqual(oc.action, ObjectChangeActionChoices.ACTION_CREATE)
        self.assertEqual(oc.object_data["custom_fields"]["my_field"], form_data["cf_my_field"])
        self.assertEqual(oc.object_data["custom_fields"]["my_field_select"], form_data["cf_my_field_select"])
        self.assertEqual(oc.object_data["tags"], sorted([tag.name for tag in self.tags]))
        self.assertEqual(oc.user_id, self.user.pk)

    def test_update_object(self):
        location = Location(
            name="Test Location 1",
            status=self.location_status,
            location_type=self.location_type,
        )
        location.save()
        location.tags.set(self.tags[:2])

        form_data = {
            "location_type": self.location_type.pk,
            "name": "Test Location X",
            "status": self.location_status.pk,
            "cf_my_field": "DEF",
            "cf_my_field_select": "Foo",
            "tags": [self.tags[2].pk],
        }

        request = {
            "path": self._get_url("edit", instance=location),
            "data": post_data(form_data),
        }
        self.add_permissions(
            "dcim.change_location",
            "dcim.view_locationtype",
            "dcim.change_locationtype",
            "extras.view_tag",
            "extras.view_status",
        )
        response = self.client.post(**request)
        self.assertHttpStatus(response, 302)

        # Verify the creation of a new ObjectChange record
        location.refresh_from_db()
        oc = get_changes_for_model(location).first()
        self.assertEqual(oc.changed_object, location)
        self.assertEqual(oc.action, ObjectChangeActionChoices.ACTION_UPDATE)
        self.assertEqual(oc.object_data["custom_fields"]["my_field"], form_data["cf_my_field"])
        self.assertEqual(
            oc.object_data["custom_fields"]["my_field_select"],
            form_data["cf_my_field_select"],
        )
        self.assertEqual(oc.object_data["tags"], [self.tags[2].name])
        self.assertEqual(oc.user_id, self.user.pk)

    def test_delete_object(self):
        location = Location(
            name="Test Location 1",
            location_type=self.location_type,
            status=self.location_status,
            _custom_field_data={"my_field": "ABC", "my_field_select": "Bar"},
        )
        location.save()
        location.tags.set(self.tags)

        request = {
            "path": self._get_url("delete", instance=location),
            "data": post_data({"confirm": True}),
        }
        self.add_permissions("dcim.delete_location")
        response = self.client.post(**request)
        self.assertHttpStatus(response, 302)

        oc = ObjectChange.objects.first()
        self.assertEqual(oc.changed_object, None)
        self.assertEqual(oc.object_repr, location.name)
        self.assertEqual(oc.action, ObjectChangeActionChoices.ACTION_DELETE)
        self.assertEqual(oc.object_data["custom_fields"]["my_field"], "ABC")
        self.assertEqual(oc.object_data["custom_fields"]["my_field_select"], "Bar")
        self.assertEqual(oc.object_data["tags"], sorted([tag.name for tag in self.tags]))
        self.assertEqual(oc.user_id, self.user.pk)

    def test_change_context(self):
        form_data = {
            "name": "Test Location 1",
            "status": Status.objects.get_for_model(Location).first().pk,
            "location_type": self.location_type.pk,
        }

        request = {
            "path": self._get_url("add"),
            "data": post_data(form_data),
        }
        self.add_permissions(
            "dcim.add_location",
            "dcim.change_locationtype",
            "dcim.view_locationtype",
            "extras.view_tag",
            "extras.view_status",
        )
        response = self.client.post(**request)
        self.assertHttpStatus(response, 302)

        # Verify the creation of a new ObjectChange record
        location = Location.objects.get(name="Test Location 1")
        oc = get_changes_for_model(location).first()
        self.assertEqual(oc.change_context, ObjectChangeEventContextChoices.CONTEXT_WEB)
        self.assertEqual(oc.change_context_detail, "dcim:location_add")
        self.assertEqual(oc.user_id, self.user.pk)

    def test_legacy_object_data(self):
        self.add_permissions("dcim.view_location", "extras.view_objectchange")
        location_type = LocationType.objects.get(name="Campus")
        with context_managers.web_request_context(self.user):
            location = Location.objects.create(
                name="testobjectchangelocation",
                description="initial description",
                status=self.location_status,
                location_type=location_type,
            )

        # create objectchange without object_data_v2
        with context_managers.web_request_context(self.user):
            location.description = "changed description1"
            location.validated_save()
        oc_without_object_data_v2_1 = get_changes_for_model(location).first()
        oc_without_object_data_v2_1.object_data_v2 = None
        oc_without_object_data_v2_1.validated_save()
        with self.subTest("previous ObjectChange has object_data_v2, current ObjectChange does not"):
            resp = self.client.get(oc_without_object_data_v2_1.get_absolute_url())
            self.assertContains(resp, escape('"description": "initial description"'))
            self.assertContains(resp, escape('"description": "changed description1"'))

        # create second objectchange without object_data_v2
        with context_managers.web_request_context(self.user):
            location.description = "changed description2"
            location.validated_save()
        oc_without_object_data_v2_2 = get_changes_for_model(location).first()
        oc_without_object_data_v2_2.object_data_v2 = None
        oc_without_object_data_v2_2.validated_save()
        with self.subTest("previous and current ObjectChange do not have object_data_v2"):
            resp = self.client.get(oc_without_object_data_v2_2.get_absolute_url())
            self.assertContains(resp, escape('"description": "changed description1"'))
            self.assertContains(resp, escape('"description": "changed description2"'))

        # create objectchange with object_data_v2
        with context_managers.web_request_context(self.user):
            location.description = "changed description3"
            location.validated_save()
        oc_with_object_data_v2 = get_changes_for_model(location).first()
        with self.subTest("previous ObjectChange does not have object_data_v2, current ObjectChange does"):
            resp = self.client.get(oc_with_object_data_v2.get_absolute_url())
            self.assertContains(resp, escape('"description": "changed description2"'))
            self.assertContains(resp, escape('"description": "changed description3"'))

    def test_objectchange_skips_add_conditional_prefetch(self):
        """
        Test that ObjectChange.objects.all() skips prefetch_related on ContentTypes without a model class.
        """
        self.add_permissions("extras.view_objectchange")

        ct = ContentType.objects.create(app_label="nonexistent_app", model="nonexistentmodel")
        oc = ObjectChange.objects.create(
            changed_object_type=ct,
            changed_object_id=1,
            object_repr="nonexistentobject",
            action=ObjectChangeActionChoices.ACTION_CREATE,
            user=self.user,
            object_data={},
            request_id=uuid.uuid4(),
        )
        url = reverse("extras:objectchange_list")
        with self.assertLogs(level="WARNING") as cm:
            response = self.client.get(url, headers={"HX-Request": "true"})
            self.assertHttpStatus(response, 200)
            self.assertContains(response, oc.object_repr)
            self.assertIn(
                ("One or more ContentType entries in the database are invalid."),
                cm.output[0],
            )


class ChangeLogAPITest(APITestCase):
    def setUp(self):
        super().setUp()

        # Create a custom field on the Location model
        ct = ContentType.objects.get_for_model(Location)
        cf = CustomField(type=CustomFieldTypeChoices.TYPE_TEXT, label="My Field", required=False)
        cf.save()
        cf.content_types.set([ct])

        # Create a select custom field on the Location model
        cf_select = CustomField(
            type=CustomFieldTypeChoices.TYPE_SELECT,
            label="My Field Select",
            required=False,
        )
        cf_select.save()
        cf_select.content_types.set([ct])

        CustomFieldChoice.objects.create(custom_field=cf_select, value="Bar")
        CustomFieldChoice.objects.create(custom_field=cf_select, value="Foo")

        self.tags = Tag.objects.get_for_model(Location)
        self.statuses = Status.objects.get_for_model(Location)

    @tag("example_app")
    def test_create_object(self):
        from example_app.signals import EXAMPLE_APP_CUSTOM_FIELD_DEFAULT, EXAMPLE_APP_CUSTOM_FIELD_NAME

        location_type = LocationType.objects.get(name="Campus")
        data = {
            "name": "Test Location 1",
            "status": self.statuses[0].pk,
            "location_type": f"{location_type.pk}",
            "custom_fields": {
                "my_field": "ABC",
                "my_field_select": "Bar",
                EXAMPLE_APP_CUSTOM_FIELD_NAME: EXAMPLE_APP_CUSTOM_FIELD_DEFAULT,
            },
            "tags": [
                {"name": self.tags[0].name},
                {"name": self.tags[1].name},
            ],
        }
        url = reverse("dcim-api:location-list")
        self.add_permissions("dcim.add_location", "dcim.view_locationtype", "extras.view_tag", "extras.view_status")

        response = self.client.post(url, data, format="json", **self.header)
        self.assertHttpStatus(response, status.HTTP_201_CREATED)

        location = Location.objects.get(pk=response.data["id"])
        oc = get_changes_for_model(location).first()
        self.assertEqual(oc.changed_object, location)
        self.assertEqual(oc.action, ObjectChangeActionChoices.ACTION_CREATE)
        self.assertEqual(oc.object_data["custom_fields"], data["custom_fields"])
        self.assertEqual(oc.object_data["tags"], sorted([self.tags[0].name, self.tags[1].name]))
        self.assertEqual(oc.user_id, self.user.pk)

    @tag("example_app")
    def test_update_object(self):
        """Test PUT with changelogs."""
        from example_app.signals import EXAMPLE_APP_CUSTOM_FIELD_DEFAULT, EXAMPLE_APP_CUSTOM_FIELD_NAME

        location_type = LocationType.objects.get(name="Campus")
        location = Location.objects.create(
            name="Test Location 1",
            status=self.statuses[1],
            location_type=location_type,
        )

        data = {
            "name": "Test Location X",
            "status": self.statuses[0].pk,
            "location_type": f"{location_type.pk}",
            "custom_fields": {
                "my_field": "DEF",
                "my_field_select": "Foo",
                EXAMPLE_APP_CUSTOM_FIELD_NAME: EXAMPLE_APP_CUSTOM_FIELD_DEFAULT,
            },
            "tags": [{"name": self.tags[2].name}],
        }
        self.add_permissions("dcim.change_location", "extras.view_status", "dcim.view_locationtype", "extras.view_tag")
        url = reverse("dcim-api:location-detail", kwargs={"pk": location.pk})

        response = self.client.put(url, data, format="json", **self.header)
        self.assertHttpStatus(response, status.HTTP_200_OK)

        location = Location.objects.get(pk=response.data["id"])
        oc = get_changes_for_model(location).first()
        self.assertEqual(oc.changed_object, location)
        self.assertEqual(oc.action, ObjectChangeActionChoices.ACTION_UPDATE)
        self.assertEqual(oc.object_data["custom_fields"], data["custom_fields"])
        self.assertEqual(oc.object_data["tags"], [self.tags[2].name])
        self.assertEqual(oc.user_id, self.user.pk)

    def test_partial_update_object(self):
        """Test PATCH with changelogs."""
        location_type = LocationType.objects.get(name="Campus")
        location = Location.objects.create(
            name="Test Location 1",
            location_type=location_type,
            status=self.statuses[1],
            _custom_field_data={
                "my_field": "DEF",
                "my_field_select": "Foo",
            },
        )
        location.tags.add(self.tags[2])

        # We only want to update a single field.
        data = {
            "description": "new description",
        }

        self.add_permissions("dcim.change_location", "extras.view_status")
        url = reverse("dcim-api:location-detail", kwargs={"pk": location.pk})

        # Perform a PATCH (partial update)
        response = self.client.patch(url, data, format="json", **self.header)
        self.assertHttpStatus(response, status.HTTP_200_OK)
        location = Location.objects.get(pk=response.data["id"])

        # Get only the most recent OC
        oc = get_changes_for_model(location).first()
        self.assertEqual(oc.changed_object, location)
        self.assertEqual(oc.object_data["description"], data["description"])
        self.assertEqual(oc.action, ObjectChangeActionChoices.ACTION_UPDATE)
        self.assertEqual(oc.object_data["custom_fields"], location.custom_field_data)
        self.assertEqual(oc.object_data["tags"], [self.tags[2].name])
        self.assertEqual(oc.user_id, self.user.pk)

    def test_delete_object(self):
        location_type = LocationType.objects.get(name="Campus")
        location = Location(
            name="Test Location 1",
            location_type=location_type,
            status=self.statuses[0],
            _custom_field_data={"my_field": "ABC", "my_field_select": "Bar"},
        )
        location.save()
        location.tags.set(self.tags[:2])
        self.add_permissions("dcim.delete_location", "extras.view_status")
        url = reverse("dcim-api:location-detail", kwargs={"pk": location.pk})
        initial_count = Location.objects.count()

        response = self.client.delete(url, **self.header)
        self.assertHttpStatus(response, status.HTTP_204_NO_CONTENT)
        self.assertEqual(Location.objects.count(), initial_count - 1)

        oc = ObjectChange.objects.first()
        self.assertEqual(oc.changed_object, None)
        self.assertEqual(oc.object_repr, location.name)
        self.assertEqual(oc.action, ObjectChangeActionChoices.ACTION_DELETE)
        self.assertEqual(oc.object_data["custom_fields"]["my_field"], "ABC")
        self.assertEqual(oc.object_data["custom_fields"]["my_field_select"], "Bar")
        self.assertEqual(oc.object_data["tags"], sorted([tag.name for tag in self.tags[:2]]))
        self.assertEqual(oc.user_id, self.user.pk)

    @override_settings(EXEMPT_VIEW_PERMISSIONS=["*"])
    def test_get_graphql_object(self):
        """Test GET with changelogs via GraphQL."""
        location_type = LocationType.objects.get(name="Campus")
        location_payload = {
            "name": "Test Location 1",
            "status": self.statuses[0].pk,
            "location_type": location_type.pk,
        }
        self.add_permissions("dcim.add_location")

        locations_url = reverse("dcim-api:location-list")
        new_location_response = self.client.post(locations_url, location_payload, format="json", **self.header)
        self.assertHttpStatus(new_location_response, status.HTTP_201_CREATED)

        gql_payload = '{query: object_changes(q: "") { object_repr } }'
        resp = execute_query(gql_payload, user=self.user)
        self.assertIsNone(resp.errors)
        self.assertEqual(first=location_payload["name"], second=resp.data["query"][0].get("object_repr", ""))

    @override_settings(EXEMPT_VIEW_PERMISSIONS=["*"])
    def test_graphql_object_lte_filter(self):
        location_type = LocationType.objects.get(name="Campus")
        location_payload = {
            "name": "Test Location 2",
            "status": self.statuses[0].pk,
            "location_type": location_type.pk,
        }
        self.add_permissions("dcim.add_location")

        time = "2021-03-14 00:00:00"
        locations_url = reverse("dcim-api:location-list")
        new_location_response = self.client.post(locations_url, location_payload, format="json", **self.header)
        self.assertHttpStatus(new_location_response, status.HTTP_201_CREATED)

        gql_payload = f'{{query: object_changes(time__lte: "{time}") {{ object_repr }} }}'
        resp = execute_query(gql_payload, user=self.user)
        self.assertIsNone(resp.errors)
        self.assertIsInstance(resp.data.get("query"), list)
        # ObjectChangeFactory creates records with fixed dates in 2024; there shouldn't be any in this filtered response.
        self.assertEqual(len(resp.data.get("query")), 0)

    @override_settings(EXEMPT_VIEW_PERMISSIONS=["*"])
    def test_graphql_object_gte_filter(self):
        location_type = LocationType.objects.get(name="Campus")
        location_payload = {
            "name": "Test Location 1",
            "status": self.statuses[0].pk,
            "location_type": location_type.pk,
        }
        self.add_permissions("dcim.add_location")

        time = "2021-03-14 00:00:00"
        locations_url = reverse("dcim-api:location-list")
        new_location_response = self.client.post(locations_url, location_payload, format="json", **self.header)
        self.assertHttpStatus(new_location_response, status.HTTP_201_CREATED)

        gql_payload = f'{{query: object_changes(time__gte: "{time}") {{ object_repr }} }}'
        resp = execute_query(gql_payload, user=self.user)
        self.assertIsNone(resp.errors)
        self.assertIsInstance(resp.data.get("query"), list)
        self.assertEqual(first=location_payload["name"], second=resp.data["query"][0].get("object_repr", ""))

    def test_change_context(self):
        location_type = LocationType.objects.get(name="Campus")
        location_payload = {
            "name": "Test Location 1",
            "status": self.statuses[0].pk,
            "location_type": location_type.pk,
        }
        self.add_permissions("dcim.add_location", "dcim.view_locationtype", "extras.view_status")
        url = reverse("dcim-api:location-list")

        response = self.client.post(url, location_payload, format="json", **self.header)
        self.assertHttpStatus(response, status.HTTP_201_CREATED)

        location = Location.objects.get(pk=response.data["id"])
        oc = get_changes_for_model(location).first()
        self.assertEqual(oc.change_context, ObjectChangeEventContextChoices.CONTEXT_WEB)
        self.assertEqual(oc.change_context_detail, "dcim-api:location-list")
        self.assertEqual(oc.user_id, self.user.pk)

    def test_m2m_change(self):
        """Test that ManyToMany change only generates a single ObjectChange instance"""
        cluster_type = ClusterType.objects.create(name="Test Cluster Type")
        cluster = Cluster.objects.create(name="test_cluster", cluster_type=cluster_type)
        vm_statuses = Status.objects.get_for_model(VirtualMachine)
        vm = VirtualMachine.objects.create(
            name="test_vm",
            cluster=cluster,
            status=vm_statuses[0],
        )
        vminterface_statuses = Status.objects.get_for_model(VirtualMachine)
        vm_interface = VMInterface.objects.create(
            name="vm interface 1",
            virtual_machine=vm,
            status=vminterface_statuses[0],
            mode=InterfaceModeChoices.MODE_TAGGED,
        )
        vlan_statuses = Status.objects.get_for_model(VLAN)
        tagged_vlan = VLAN.objects.create(
            vid=100, name="VLAN100", status=vlan_statuses[0], vlan_group=VLANGroup.objects.first()
        )

        payload = {"tagged_vlans": [str(tagged_vlan.pk)], "description": "test vm interface m2m change"}
        self.add_permissions("virtualization.change_vminterface", "ipam.change_vlan", "ipam.view_vlan")
        url = reverse("virtualization-api:vminterface-detail", kwargs={"pk": vm_interface.pk})
        response = self.client.patch(url, payload, format="json", **self.header)
        vm_interface.refresh_from_db()
        self.assertHttpStatus(response, status.HTTP_200_OK)

        oc = get_changes_for_model(vm_interface).first()
        self.assertEqual(get_changes_for_model(vm_interface).count(), 1)
        self.assertEqual(oc.user_id, self.user.pk)
        self.assertEqual(vm_interface.description, "test vm interface m2m change")
        self.assertSequenceEqual(list(vm_interface.tagged_vlans.all()), [tagged_vlan])


class ObjectChangeModelTest(TestCase):  # TODO: change to BaseModelTestCase once we have an ObjectChangeFactory
    @classmethod
    def setUpTestData(cls):
        cls.location_status = Status.objects.get_for_model(Location).first()

    def test_m2m_fields_not_excluded(self):
        """Ensure that m2m fields are included in object changes, even if exclude_m2m is the default in the REST API."""
        with context_managers.web_request_context(self.user):
            location_type = LocationType.objects.create(name="Test m2m locationtype")

        with context_managers.web_request_context(self.user):
            location_type.content_types.set(ContentType.objects.filter(app_label="dcim"))

        object_changes = get_changes_for_model(location_type)
        self.assertEqual(object_changes.count(), 2)

        snapshots = object_changes.first().get_snapshots()
        self.assertIsNotNone(snapshots["differences"]["removed"])
        self.assertIsNotNone(snapshots["differences"]["added"])
        self.assertIn("content_types", snapshots["differences"]["removed"])
        self.assertIn("content_types", snapshots["differences"]["added"])
        self.assertEqual(
            len(snapshots["differences"]["added"]["content_types"]),
            ContentType.objects.filter(app_label="dcim").count(),
        )

    def test_opt_out(self):
        """Hidden static group associations can "opt out" of change logging."""
        dg = DynamicGroup.objects.exclude(group_type=DynamicGroupTypeChoices.TYPE_STATIC).first()
        # Force reassignment of all cached memberships:
        members = list(dg.members)
        with context_managers.web_request_context(self.user):
            dg._set_members([])
            dg._set_members(members)

        for sga in dg.static_group_associations(manager="all_objects").all():
            self.assertIsNone(get_changes_for_model(sga).first())

    def test_get_snapshots(self):
        with context_managers.web_request_context(self.user):
            location_type = LocationType.objects.get(name="Campus")
            location = Location(
                name="testobjectchangelocation",
                description="initial description",
                status=self.location_status,
                location_type=location_type,
            )
            location.validated_save()
        initial_object_change = get_changes_for_model(location).first()

        with self.subTest("test get_snapshots ObjectChange create"):
            snapshots = initial_object_change.get_snapshots()
            self.assertIsNone(snapshots["prechange"])
            self.assertEqual(snapshots["postchange"], initial_object_change.object_data_v2)
            self.assertIsNone(snapshots["differences"]["removed"])
            self.assertEqual(snapshots["differences"]["added"], initial_object_change.object_data_v2)

        # first objectchange without object_data_v2
        with context_managers.web_request_context(self.user):
            location.description = "changed description1"
            location.validated_save()
        oc_without_object_data_v2_1 = get_changes_for_model(location).first()
        oc_without_object_data_v2_1.object_data_v2 = None
        oc_without_object_data_v2_1.validated_save()
        with self.subTest("test get_snapshots previous ObjectChange has object_data_v2, current ObjectChange does not"):
            snapshots = oc_without_object_data_v2_1.get_snapshots()
            self.assertEqual(snapshots["prechange"], initial_object_change.object_data)
            self.assertEqual(snapshots["postchange"], oc_without_object_data_v2_1.object_data)
            self.assertEqual(snapshots["differences"]["removed"], {"description": "initial description"})
            self.assertEqual(snapshots["differences"]["added"], {"description": "changed description1"})

        # second objectchange without object_data_v2
        with context_managers.web_request_context(self.user):
            location.description = "changed description2"
            location.validated_save()
        oc_without_object_data_v2_2 = get_changes_for_model(location).first()
        oc_without_object_data_v2_2.object_data_v2 = None
        oc_without_object_data_v2_2.validated_save()
        with self.subTest("test get_snapshots previous and current ObjectChange do not have object_data_v2"):
            snapshots = oc_without_object_data_v2_2.get_snapshots()
            self.assertEqual(snapshots["prechange"], oc_without_object_data_v2_1.object_data)
            self.assertEqual(snapshots["postchange"], oc_without_object_data_v2_2.object_data)
            self.assertEqual(snapshots["differences"]["removed"], {"description": "changed description1"})
            self.assertEqual(snapshots["differences"]["added"], {"description": "changed description2"})

        # objectchange with object_data_v2
        with context_managers.web_request_context(self.user):
            location.description = "changed description3"
            location.validated_save()
        oc_with_object_data_v2 = get_changes_for_model(location).first()
        with self.subTest(
            "test get_snapshots previous ObjectChange does not have object_data_v2, current ObjectChange does"
        ):
            snapshots = oc_with_object_data_v2.get_snapshots()
            self.assertEqual(snapshots["prechange"], oc_without_object_data_v2_2.object_data)
            self.assertEqual(snapshots["postchange"], oc_with_object_data_v2.object_data)
            self.assertEqual(snapshots["differences"]["removed"], {"description": "changed description2"})
            self.assertEqual(snapshots["differences"]["added"], {"description": "changed description3"})

        # objectchange action delete
        location_pk = location.pk
        with context_managers.web_request_context(self.user):
            location.delete()
        oc_delete = get_changes_for_model(Location).filter(changed_object_id=location_pk).first()
        with self.subTest("test get_snapshots ObjectChange delete"):
            snapshots = oc_delete.get_snapshots()
            self.assertEqual(snapshots["prechange"], oc_with_object_data_v2.object_data_v2)
            self.assertIsNone(snapshots["postchange"])
            self.assertEqual(snapshots["differences"]["removed"], oc_with_object_data_v2.object_data_v2)
            self.assertIsNone(snapshots["differences"]["added"])


class ChangeLogM2MThroughTest(APITestCase):
    """
    Test automatic change logging of both side objects of explicit M2M through models,
    whether written via their REST API endpoints or via M2M manager methods.
    """

    def setUp(self):
        super().setUp()

        self.prefix_location_ct = ContentType.objects.get_for_model(Prefix)
        self.locations = Location.objects.filter(location_type__content_types=self.prefix_location_ct)
        # Materialized to a list because MySQL doesn't support a LIMIT-ed queryset inside an `__in` filter
        self.prefix = Prefix.objects.exclude(locations__in=list(self.locations[:2])).first()

        location = Location.objects.get_for_model(Device).first()
        devicetype = DeviceType.objects.first()
        devicerole = Role.objects.get_for_model(Device).first()
        devicestatus = Status.objects.get_for_model(Device).first()
        self.device = Device.objects.create(
            name="Change Log M2M Test Device",
            location=location,
            device_type=devicetype,
            role=devicerole,
            status=devicestatus,
        )
        int_status = Status.objects.get_for_model(Interface).first()
        self.interface = Interface.objects.create(
            device=self.device, name="eth0", status=int_status, type=InterfaceTypeChoices.TYPE_1GE_FIXED
        )
        clustertype = ClusterType.objects.create(name="Change Log M2M Test Cluster Type")
        cluster = Cluster.objects.create(cluster_type=clustertype, name="Change Log M2M Test Cluster")
        vm_status = Status.objects.get_for_model(VirtualMachine).first()
        virtual_machine = VirtualMachine.objects.create(
            name="Change Log M2M Test VM", cluster=cluster, status=vm_status
        )
        vm_int_status = Status.objects.get_for_model(VMInterface).first()
        self.vm_interface = VMInterface.objects.create(
            virtual_machine=virtual_machine, name="veth0", status=vm_int_status
        )
        self.ip_addresses = list(IPAddress.objects.all()[:6])

    def assert_single_update_change(self, instance, request_id):
        """Assert exactly one ACTION_UPDATE ObjectChange was recorded for `instance` in the given request."""
        changes = ObjectChange.objects.filter(
            changed_object_type=ContentType.objects.get_for_model(instance),
            changed_object_id=instance.pk,
            request_id=request_id,
        )
        self.assertEqual(changes.count(), 1)
        self.assertEqual(changes.first().action, ObjectChangeActionChoices.ACTION_UPDATE)
        return changes.first()

    def test_api_create_logs_both_sides(self):
        self.add_permissions("ipam.add_prefixlocationassignment", "ipam.view_prefix", "dcim.view_location")
        location = self.locations[0]

        url = reverse("ipam-api:prefixlocationassignment-list")
        response = self.client.post(
            url, {"prefix": self.prefix.pk, "location": location.pk}, format="json", **self.header
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        prefix_change = get_changes_for_model(self.prefix).first()
        self.assertIsNotNone(prefix_change)
        location_change = self.assert_single_update_change(location, prefix_change.request_id)
        self.assertEqual(prefix_change.action, ObjectChangeActionChoices.ACTION_UPDATE)
        self.assertEqual(prefix_change.user_id, self.user.pk)
        self.assertEqual(location_change.user_id, self.user.pk)

    def test_api_create_with_null_side_logs_non_null_sides(self):
        self.add_permissions("ipam.add_ipaddresstointerface", "ipam.view_ipaddress", "virtualization.view_vminterface")
        ip_address = self.ip_addresses[0]

        url = reverse("ipam-api:ipaddresstointerface-list")
        response = self.client.post(
            url,
            {"ip_address": ip_address.pk, "interface": None, "vm_interface": self.vm_interface.pk},
            format="json",
            **self.header,
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        ip_change = get_changes_for_model(ip_address).first()
        self.assertIsNotNone(ip_change)
        self.assert_single_update_change(self.vm_interface, ip_change.request_id)
        self.assertEqual(ip_change.action, ObjectChangeActionChoices.ACTION_UPDATE)

    def test_api_delete_logs_both_sides(self):
        self.add_permissions("ipam.delete_ipaddresstointerface")
        ip_address = self.ip_addresses[1]
        assignment = IPAddressToInterface.objects.create(ip_address=ip_address, interface=self.interface)

        url = reverse("ipam-api:ipaddresstointerface-detail", kwargs={"pk": assignment.pk})
        response = self.client.delete(url, **self.header)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        interface_change = get_changes_for_model(self.interface).first()
        self.assertIsNotNone(interface_change)
        self.assert_single_update_change(ip_address, interface_change.request_id)
        self.assertEqual(interface_change.action, ObjectChangeActionChoices.ACTION_UPDATE)
        # post_delete timing: the recorded snapshot must reflect the association's removal
        self.assertNotIn(str(ip_address.pk), str(interface_change.object_data_v2.get("ip_addresses", "")))

    def test_orm_add_logs_both_sides_once_each(self):
        change_id = uuid.uuid4()
        with context_managers.web_request_context(self.user, change_id=change_id):
            self.interface.ip_addresses.add(self.ip_addresses[2], self.ip_addresses[3])

        self.assert_single_update_change(self.interface, change_id)
        self.assert_single_update_change(self.ip_addresses[2], change_id)
        self.assert_single_update_change(self.ip_addresses[3], change_id)

    def test_orm_reverse_manager_add_logs_both_sides(self):
        change_id = uuid.uuid4()
        with context_managers.web_request_context(self.user, change_id=change_id):
            self.ip_addresses[4].interfaces.add(self.interface)

        self.assert_single_update_change(self.ip_addresses[4], change_id)
        self.assert_single_update_change(self.interface, change_id)

    def test_orm_set_remove_clear_log_both_sides_once_each(self):
        locations = list(self.locations[:2])

        with self.subTest("set() with additions"):
            change_id = uuid.uuid4()
            with context_managers.web_request_context(self.user, change_id=change_id):
                self.prefix.locations.set(locations)
            self.assert_single_update_change(self.prefix, change_id)
            self.assert_single_update_change(locations[0], change_id)
            self.assert_single_update_change(locations[1], change_id)

        with self.subTest("remove() does not double-log despite firing both delete and m2m signals"):
            change_id = uuid.uuid4()
            with context_managers.web_request_context(self.user, change_id=change_id):
                self.prefix.locations.remove(locations[0])
            self.assert_single_update_change(self.prefix, change_id)
            self.assert_single_update_change(locations[0], change_id)
            self.assertFalse(
                ObjectChange.objects.filter(changed_object_id=locations[1].pk, request_id=change_id).exists()
            )

        with self.subTest("clear() logs both sides via the through record deletions"):
            change_id = uuid.uuid4()
            with context_managers.web_request_context(self.user, change_id=change_id):
                self.prefix.locations.clear()
            self.assert_single_update_change(self.prefix, change_id)
            self.assert_single_update_change(locations[1], change_id)

    def test_orm_auto_created_m2m_remains_one_sided(self):
        route_target = RouteTarget.objects.create(name="65000:99999")
        vrf = VRF.objects.create(name="Change Log M2M Test VRF", namespace=self.prefix.namespace)

        change_id = uuid.uuid4()
        with context_managers.web_request_context(self.user, change_id=change_id):
            vrf.import_targets.add(route_target)

        self.assert_single_update_change(vrf, change_id)
        self.assertFalse(ObjectChange.objects.filter(changed_object_id=route_target.pk, request_id=change_id).exists())

    def test_parent_created_in_same_request_stays_create(self):
        change_id = uuid.uuid4()
        with context_managers.web_request_context(self.user, change_id=change_id):
            vrf = VRF.objects.create(name="Change Log M2M Test VRF 2", namespace=self.prefix.namespace)
            vrf.prefixes.add(self.prefix)

        vrf_changes = ObjectChange.objects.filter(changed_object_id=vrf.pk, request_id=change_id)
        self.assertEqual(vrf_changes.count(), 1)
        self.assertEqual(vrf_changes.first().action, ObjectChangeActionChoices.ACTION_CREATE)
        self.assert_single_update_change(self.prefix, change_id)

    def test_cascade_delete_does_not_log_surviving_side(self):
        vrf = VRF.objects.create(name="Change Log M2M Test VRF 3", namespace=self.prefix.namespace)
        with context_managers.web_request_context(self.user):
            vrf.prefixes.add(self.prefix)

        vrf_pk = vrf.pk
        change_id = uuid.uuid4()
        with context_managers.web_request_context(self.user, change_id=change_id):
            vrf.delete()

        vrf_changes = ObjectChange.objects.filter(changed_object_id=vrf_pk, request_id=change_id)
        self.assertEqual(vrf_changes.count(), 1)
        self.assertEqual(vrf_changes.first().action, ObjectChangeActionChoices.ACTION_DELETE)
        self.assertFalse(ObjectChange.objects.filter(changed_object_id=self.prefix.pk, request_id=change_id).exists())

    def test_queryset_delete_of_through_records_logs_both_sides(self):
        ip_address = self.ip_addresses[5]
        assignment = IPAddressToInterface.objects.create(ip_address=ip_address, interface=self.interface)

        change_id = uuid.uuid4()
        with context_managers.web_request_context(self.user, change_id=change_id):
            IPAddressToInterface.objects.filter(pk=assignment.pk).delete()

        self.assert_single_update_change(self.interface, change_id)
        self.assert_single_update_change(ip_address, change_id)

    def test_deferred_change_logging_logs_both_sides(self):
        location = self.locations[0]
        change_id = uuid.uuid4()
        with context_managers.web_request_context(self.user, change_id=change_id):
            with context_managers.deferred_change_logging_for_bulk_operation():
                PrefixLocationAssignment.objects.create(prefix=self.prefix, location=location)

        self.assert_single_update_change(self.prefix, change_id)
        self.assert_single_update_change(location, change_id)

    def test_tags_remain_unlogged(self):
        location_tag = Tag.objects.get_for_model(Location).first()
        location = self.locations[0]

        change_id = uuid.uuid4()
        with context_managers.web_request_context(self.user, change_id=change_id):
            location.tags.set([location_tag])

        self.assertTrue(ObjectChange.objects.filter(changed_object_id=location.pk, request_id=change_id).exists())
        self.assertFalse(ObjectChange.objects.filter(changed_object_id=location_tag.pk, request_id=change_id).exists())

    def test_anonymous_user_does_not_error(self):
        change_id = uuid.uuid4()
        with context_managers.web_request_context(AnonymousUser(), change_id=change_id):
            self.interface.ip_addresses.add(self.ip_addresses[2])

        changes = ObjectChange.objects.filter(changed_object_id=self.ip_addresses[2].pk, request_id=change_id)
        self.assertEqual(changes.count(), 1)
        self.assertIsNone(changes.first().user)

    def test_self_referential_through_model_logs_both_sides(self):
        device_ct = ContentType.objects.get_for_model(Device)
        parent_group = DynamicGroup.objects.create(
            name="Change Log M2M Test Parent Group",
            content_type=device_ct,
            group_type=DynamicGroupTypeChoices.TYPE_DYNAMIC_SET,
        )
        child_group = DynamicGroup.objects.create(
            name="Change Log M2M Test Child Group",
            content_type=device_ct,
            group_type=DynamicGroupTypeChoices.TYPE_DYNAMIC_FILTER,
        )

        change_id = uuid.uuid4()
        with context_managers.web_request_context(self.user, change_id=change_id):
            DynamicGroupMembership.objects.create(
                parent_group=parent_group,
                group=child_group,
                operator=DynamicGroupOperatorChoices.OPERATOR_UNION,
                weight=10,
            )

        self.assert_single_update_change(parent_group, change_id)
        self.assert_single_update_change(child_group, change_id)

    def test_change_logged_through_model_logs_itself_and_both_sides(self):
        software_image_file = SoftwareImageFile.objects.first()
        device_type = DeviceType.objects.exclude(software_image_files=software_image_file).first()

        change_id = uuid.uuid4()
        with context_managers.web_request_context(self.user, change_id=change_id):
            assignment = DeviceTypeToSoftwareImageFile.objects.create(
                device_type=device_type, software_image_file=software_image_file
            )

        assignment_changes = ObjectChange.objects.filter(changed_object_id=assignment.pk, request_id=change_id)
        self.assertEqual(assignment_changes.count(), 1)
        self.assertEqual(assignment_changes.first().action, ObjectChangeActionChoices.ACTION_CREATE)
        self.assert_single_update_change(device_type, change_id)
        self.assert_single_update_change(software_image_file, change_id)

    def test_primary_ip_nullification_on_assignment_delete(self):
        ip_address = IPAddress.objects.filter(ip_version=4).first()
        assignment = IPAddressToInterface.objects.create(ip_address=ip_address, interface=self.interface)
        self.device.primary_ip4 = ip_address
        self.device.save()

        change_id = uuid.uuid4()
        with context_managers.web_request_context(self.user, change_id=change_id):
            assignment.delete()

        self.device.refresh_from_db()
        self.assertIsNone(self.device.primary_ip4)
        self.assert_single_update_change(self.interface, change_id)
        self.assert_single_update_change(ip_address, change_id)

    @mock.patch("nautobot.extras.context_managers.publish_event")
    @mock.patch("nautobot.extras.jobs.enqueue_job_hooks", return_value=(False, None))
    @mock.patch("nautobot.extras.context_managers.enqueue_webhooks", return_value=None)
    def test_hooks_and_events_dispatched_for_both_sides(
        self, mock_enqueue_webhooks, mock_enqueue_job_hooks, mock_publish_event
    ):
        """Creating a through record dispatches job hooks, webhooks, and events for both side objects (#9270)."""
        ip_address = self.ip_addresses[0]
        with context_managers.web_request_context(self.user):
            IPAddressToInterface.objects.create(ip_address=ip_address, interface=self.interface)

        expected_changed_objects = {
            (ContentType.objects.get_for_model(Interface), self.interface.pk),
            (ContentType.objects.get_for_model(IPAddress), ip_address.pk),
        }
        webhook_changed_objects = {
            (call.args[0].changed_object_type, call.args[0].changed_object_id)
            for call in mock_enqueue_webhooks.call_args_list
        }
        self.assertEqual(webhook_changed_objects, expected_changed_objects)
        jobhook_changed_objects = {
            (call.args[0].changed_object_type, call.args[0].changed_object_id)
            for call in mock_enqueue_job_hooks.call_args_list
        }
        self.assertEqual(jobhook_changed_objects, expected_changed_objects)
        event_topics = {call.kwargs["topic"] for call in mock_publish_event.call_args_list}
        self.assertEqual(event_topics, {"nautobot.update.dcim.interface", "nautobot.update.ipam.ipaddress"})
