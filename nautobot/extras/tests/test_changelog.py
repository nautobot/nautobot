from django.contrib.contenttypes.models import ContentType
from django.test import override_settings
from django.urls import reverse
from django.utils.html import escape
from rest_framework import status

from example_plugin.signals import EXAMPLE_PLUGIN_CUSTOM_FIELD_DEFAULT, EXAMPLE_PLUGIN_CUSTOM_FIELD_NAME
from nautobot.core.graphql import execute_query
from nautobot.core.testing import APITestCase, TestCase
from nautobot.core.testing.utils import post_data
from nautobot.core.testing.views import ModelViewTestCase
from nautobot.core.utils.lookup import get_changes_for_model
from nautobot.dcim.choices import InterfaceModeChoices
from nautobot.dcim.models import Location, LocationType
from nautobot.extras import context_managers
from nautobot.extras.choices import CustomFieldTypeChoices, ObjectChangeActionChoices, ObjectChangeEventContextChoices
from nautobot.extras.models import CustomField, CustomFieldChoice, ObjectChange, Status, Tag
from nautobot.ipam.models import VLAN, VLANGroup
from nautobot.virtualization.models import Cluster, ClusterType, VMInterface, VirtualMachine


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

    def test_create_object(self):
        location_type = LocationType.objects.get(name="Campus")
        data = {
            "name": "Test Location 1",
            "status": self.statuses[0].pk,
            "location_type": f"{location_type.pk}",
            "custom_fields": {
                "my_field": "ABC",
                "my_field_select": "Bar",
                EXAMPLE_PLUGIN_CUSTOM_FIELD_NAME: EXAMPLE_PLUGIN_CUSTOM_FIELD_DEFAULT,
            },
            "tags": [
                {"name": self.tags[0].name},
                {"name": self.tags[1].name},
            ],
        }
        self.assertEqual(ObjectChange.objects.count(), 0)
        url = reverse("dcim-api:location-list")
        self.add_permissions("dcim.add_location", "extras.view_status")

        response = self.client.post(url, data, format="json", **self.header)
        self.assertHttpStatus(response, status.HTTP_201_CREATED)

        location = Location.objects.get(pk=response.data["id"])
        oc = get_changes_for_model(location).first()
        self.assertEqual(oc.changed_object, location)
        self.assertEqual(oc.action, ObjectChangeActionChoices.ACTION_CREATE)
        self.assertEqual(oc.object_data["custom_fields"], data["custom_fields"])
        self.assertEqual(oc.object_data["tags"], sorted([self.tags[0].name, self.tags[1].name]))
        self.assertEqual(oc.user_id, self.user.pk)

    def test_update_object(self):
        """Test PUT with changelogs."""
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
                EXAMPLE_PLUGIN_CUSTOM_FIELD_NAME: EXAMPLE_PLUGIN_CUSTOM_FIELD_DEFAULT,
            },
            "tags": [{"name": self.tags[2].name}],
        }
        self.assertEqual(ObjectChange.objects.count(), 0)
        self.add_permissions("dcim.change_location", "extras.view_status")
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

        self.assertEqual(ObjectChange.objects.count(), 0)
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
        self.assertEqual(ObjectChange.objects.count(), 0)
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
        resp = execute_query(gql_payload, user=self.user).to_dict()
        self.assertFalse(resp["data"].get("error"))
        self.assertEqual(first=location_payload["name"], second=resp["data"]["query"][0].get("object_repr", ""))

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
        resp = execute_query(gql_payload, user=self.user).to_dict()
        self.assertFalse(resp["data"].get("error"))
        self.assertIsInstance(resp["data"].get("query"), list)
        self.assertEqual(len(resp["data"].get("query")), 0)

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
        resp = execute_query(gql_payload, user=self.user).to_dict()
        self.assertFalse(resp["data"].get("error"))
        self.assertIsInstance(resp["data"].get("query"), list)
        self.assertEqual(first=location_payload["name"], second=resp["data"]["query"][0].get("object_repr", ""))

    def test_change_context(self):
        location_type = LocationType.objects.get(name="Campus")
        location_payload = {
            "name": "Test Location 1",
            "status": self.statuses[0].pk,
            "location_type": location_type.pk,
        }
        self.assertEqual(ObjectChange.objects.count(), 0)
        self.add_permissions("dcim.add_location")
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
        self.assertEqual(ObjectChange.objects.count(), 0)
        self.add_permissions("virtualization.change_vminterface", "ipam.change_vlan")
        url = reverse("virtualization-api:vminterface-detail", kwargs={"pk": vm_interface.pk})
        response = self.client.patch(url, payload, format="json", **self.header)
        vm_interface.refresh_from_db()
        self.assertHttpStatus(response, status.HTTP_200_OK)

        oc = get_changes_for_model(vm_interface).first()
        self.assertEqual(ObjectChange.objects.count(), 1)
        self.assertEqual(oc.user_id, self.user.pk)
        self.assertEqual(vm_interface.description, "test vm interface m2m change")
        self.assertSequenceEqual(list(vm_interface.tagged_vlans.all()), [tagged_vlan])


class ObjectChangeModelTest(TestCase):  # TODO: change to BaseModelTestCase once we have an ObjectChangeFactory
    @classmethod
    def setUpTestData(cls):
        cls.location_status = Status.objects.get_for_model(Location).first()

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
