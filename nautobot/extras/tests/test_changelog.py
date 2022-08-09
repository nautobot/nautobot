from django.contrib.contenttypes.models import ContentType
from django.urls import reverse
from django.test import override_settings
from rest_framework import status

from nautobot.core.graphql import execute_query
from nautobot.dcim.models import Site
from nautobot.extras.choices import CustomFieldTypeChoices, ObjectChangeActionChoices, ObjectChangeEventContextChoices
from nautobot.extras.models import CustomField, CustomFieldChoice, ObjectChange, Status, Tag
from nautobot.ipam.models import VLAN
from nautobot.utilities.testing import APITestCase
from nautobot.utilities.testing.utils import post_data
from nautobot.utilities.testing.views import ModelViewTestCase
from nautobot.utilities.utils import get_changes_for_model
from nautobot.virtualization.models import Cluster, ClusterType, VMInterface, VirtualMachine


class ChangeLogViewTest(ModelViewTestCase):
    model = Site

    @classmethod
    def setUpTestData(cls):

        # Create a custom field on the Site model
        ct = ContentType.objects.get_for_model(Site)
        cf = CustomField(type=CustomFieldTypeChoices.TYPE_TEXT, name="my_field", required=False)
        cf.validated_save()
        cf.content_types.set([ct])

        # Create a select custom field on the Site model
        cf_select = CustomField(
            type=CustomFieldTypeChoices.TYPE_SELECT,
            name="my_field_select",
            required=False,
        )
        cf_select.validated_save()
        cf_select.content_types.set([ct])

        CustomFieldChoice.objects.create(field=cf_select, value="Bar")
        CustomFieldChoice.objects.create(field=cf_select, value="Foo")

    def test_create_object(self):
        tags = self.create_tags("Tag 1", "Tag 2")
        form_data = {
            "name": "Test Site 1",
            "slug": "test-site-1",
            "status": Status.objects.get(slug="active").pk,
            "cf_my_field": "ABC",
            "cf_my_field_select": "Bar",
            "tags": [tag.pk for tag in tags],
        }

        request = {
            "path": self._get_url("add"),
            "data": post_data(form_data),
        }
        self.add_permissions("dcim.add_site", "extras.view_tag", "extras.view_status")
        response = self.client.post(**request)
        self.assertHttpStatus(response, 302)

        # Verify the creation of a new ObjectChange record
        site = Site.objects.get(name="Test Site 1")
        # First OC is the creation; second is the tags update
        oc = get_changes_for_model(site).first()
        self.assertEqual(oc.changed_object, site)
        self.assertEqual(oc.action, ObjectChangeActionChoices.ACTION_CREATE)
        self.assertEqual(oc.object_data["custom_fields"]["my_field"], form_data["cf_my_field"])
        self.assertEqual(oc.object_data["custom_fields"]["my_field_select"], form_data["cf_my_field_select"])
        self.assertEqual(oc.object_data["tags"], ["Tag 1", "Tag 2"])
        self.assertEqual(oc.user_id, self.user.pk)

    def test_update_object(self):
        site = Site(
            name="Test Site 1",
            slug="test-site-1",
            status=Status.objects.get(slug="active"),
        )
        site.save()
        tags = self.create_tags("Tag 1", "Tag 2", "Tag 3")
        site.tags.set("Tag 1", "Tag 2")

        form_data = {
            "name": "Test Site X",
            "slug": "test-site-x",
            "status": Status.objects.get(slug="planned").pk,
            "cf_my_field": "DEF",
            "cf_my_field_select": "Foo",
            "tags": [tags[2].pk],
        }

        request = {
            "path": self._get_url("edit", instance=site),
            "data": post_data(form_data),
        }
        self.add_permissions("dcim.change_site", "extras.view_tag", "extras.view_status")
        response = self.client.post(**request)
        self.assertHttpStatus(response, 302)

        # Verify the creation of a new ObjectChange record
        site.refresh_from_db()
        oc = get_changes_for_model(site).first()
        self.assertEqual(oc.changed_object, site)
        self.assertEqual(oc.action, ObjectChangeActionChoices.ACTION_UPDATE)
        self.assertEqual(oc.object_data["custom_fields"]["my_field"], form_data["cf_my_field"])
        self.assertEqual(
            oc.object_data["custom_fields"]["my_field_select"],
            form_data["cf_my_field_select"],
        )
        self.assertEqual(oc.object_data["tags"], ["Tag 3"])
        self.assertEqual(oc.user_id, self.user.pk)

    def test_delete_object(self):
        site = Site(
            name="Test Site 1",
            slug="test-site-1",
            _custom_field_data={"my_field": "ABC", "my_field_select": "Bar"},
        )
        site.save()
        self.create_tags("Tag 1", "Tag 2")
        site.tags.set("Tag 1", "Tag 2")

        request = {
            "path": self._get_url("delete", instance=site),
            "data": post_data({"confirm": True}),
        }
        self.add_permissions("dcim.delete_site")
        response = self.client.post(**request)
        self.assertHttpStatus(response, 302)

        oc = ObjectChange.objects.first()
        self.assertEqual(oc.changed_object, None)
        self.assertEqual(oc.object_repr, site.name)
        self.assertEqual(oc.action, ObjectChangeActionChoices.ACTION_DELETE)
        self.assertEqual(oc.object_data["custom_fields"]["my_field"], "ABC")
        self.assertEqual(oc.object_data["custom_fields"]["my_field_select"], "Bar")
        self.assertEqual(oc.object_data["tags"], ["Tag 1", "Tag 2"])
        self.assertEqual(oc.user_id, self.user.pk)

    def test_change_context(self):
        form_data = {
            "name": "Test Site 1",
            "slug": "test-site-1",
            "status": Status.objects.get(slug="active").pk,
        }

        request = {
            "path": self._get_url("add"),
            "data": post_data(form_data),
        }
        self.add_permissions("dcim.add_site", "extras.view_tag", "extras.view_status")
        response = self.client.post(**request)
        self.assertHttpStatus(response, 302)

        # Verify the creation of a new ObjectChange record
        site = Site.objects.get(name="Test Site 1")
        oc = get_changes_for_model(site).first()
        self.assertEqual(oc.change_context, ObjectChangeEventContextChoices.CONTEXT_WEB)
        self.assertEqual(oc.change_context_detail, "dcim:site_add")
        self.assertEqual(oc.user_id, self.user.pk)


class ChangeLogAPITest(APITestCase):
    def setUp(self):
        super().setUp()

        # Create a custom field on the Site model
        ct = ContentType.objects.get_for_model(Site)
        cf = CustomField(type=CustomFieldTypeChoices.TYPE_TEXT, name="my_field", required=False)
        cf.save()
        cf.content_types.set([ct])

        # Create a select custom field on the Site model
        cf_select = CustomField(
            type=CustomFieldTypeChoices.TYPE_SELECT,
            name="my_field_select",
            required=False,
        )
        cf_select.save()
        cf_select.content_types.set([ct])

        CustomFieldChoice.objects.create(field=cf_select, value="Bar")
        CustomFieldChoice.objects.create(field=cf_select, value="Foo")

        # Create some tags
        tags = (
            Tag.objects.create(name="Tag 1", slug="tag-1"),
            Tag.objects.create(name="Tag 2", slug="tag-2"),
            Tag.objects.create(name="Tag 3", slug="tag-3"),
        )
        for tag in tags:
            tag.content_types.add(ContentType.objects.get_for_model(Site))

        self.statuses = Status.objects.get_for_model(Site)

    def test_create_object(self):
        data = {
            "name": "Test Site 1",
            "slug": "test-site-1",
            "status": "active",
            "custom_fields": {
                "my_field": "ABC",
                "my_field_select": "Bar",
            },
            "tags": [
                {"name": "Tag 1"},
                {"name": "Tag 2"},
            ],
        }
        self.assertEqual(ObjectChange.objects.count(), 0)
        url = reverse("dcim-api:site-list")
        self.add_permissions("dcim.add_site", "extras.view_status")

        response = self.client.post(url, data, format="json", **self.header)
        self.assertHttpStatus(response, status.HTTP_201_CREATED)

        site = Site.objects.get(pk=response.data["id"])
        oc = get_changes_for_model(site).first()
        self.assertEqual(oc.changed_object, site)
        self.assertEqual(oc.action, ObjectChangeActionChoices.ACTION_CREATE)
        self.assertEqual(oc.object_data["custom_fields"], data["custom_fields"])
        self.assertEqual(oc.object_data["tags"], ["Tag 1", "Tag 2"])
        self.assertEqual(oc.user_id, self.user.pk)

    def test_update_object(self):
        """Test PUT with changelogs."""
        site = Site.objects.create(
            name="Test Site 1",
            slug="test-site-1",
            status=self.statuses.get(slug="planned"),
        )

        data = {
            "name": "Test Site X",
            "slug": "test-site-x",
            "status": "active",
            "custom_fields": {
                "my_field": "DEF",
                "my_field_select": "Foo",
            },
            "tags": [{"name": "Tag 3"}],
        }
        self.assertEqual(ObjectChange.objects.count(), 0)
        self.add_permissions("dcim.change_site", "extras.view_status")
        url = reverse("dcim-api:site-detail", kwargs={"pk": site.pk})

        response = self.client.put(url, data, format="json", **self.header)
        self.assertHttpStatus(response, status.HTTP_200_OK)

        site = Site.objects.get(pk=response.data["id"])
        oc = get_changes_for_model(site).first()
        self.assertEqual(oc.changed_object, site)
        self.assertEqual(oc.action, ObjectChangeActionChoices.ACTION_UPDATE)
        self.assertEqual(oc.object_data["custom_fields"], data["custom_fields"])
        self.assertEqual(oc.object_data["tags"], ["Tag 3"])
        self.assertEqual(oc.user_id, self.user.pk)

    def test_partial_update_object(self):
        """Test PATCH with changelogs."""
        site = Site.objects.create(
            name="Test Site 1",
            slug="test-site-1",
            status=self.statuses.get(slug="planned"),
            _custom_field_data={
                "my_field": "DEF",
                "my_field_select": "Foo",
            },
        )
        site.tags.add(Tag.objects.get(name="Tag 3"))

        # We only want to update a single field.
        data = {
            "description": "new description",
        }

        self.assertEqual(ObjectChange.objects.count(), 0)
        self.add_permissions("dcim.change_site", "extras.view_status")
        url = reverse("dcim-api:site-detail", kwargs={"pk": site.pk})

        # Perform a PATCH (partial update)
        response = self.client.patch(url, data, format="json", **self.header)
        self.assertHttpStatus(response, status.HTTP_200_OK)
        site = Site.objects.get(pk=response.data["id"])

        # Get only the most recent OC
        oc = get_changes_for_model(site).first()
        self.assertEqual(oc.changed_object, site)
        self.assertEqual(oc.object_data["description"], data["description"])
        self.assertEqual(oc.action, ObjectChangeActionChoices.ACTION_UPDATE)
        self.assertEqual(oc.object_data["custom_fields"], site.custom_field_data)
        self.assertEqual(oc.object_data["tags"], ["Tag 3"])
        self.assertEqual(oc.user_id, self.user.pk)

    def test_delete_object(self):
        site = Site(
            name="Test Site 1",
            slug="test-site-1",
            status=self.statuses.get(slug="active"),
            _custom_field_data={"my_field": "ABC", "my_field_select": "Bar"},
        )
        site.save()
        site.tags.set(*Tag.objects.all()[:2])
        self.assertEqual(ObjectChange.objects.count(), 0)
        self.add_permissions("dcim.delete_site", "extras.view_status")
        url = reverse("dcim-api:site-detail", kwargs={"pk": site.pk})

        response = self.client.delete(url, **self.header)
        self.assertHttpStatus(response, status.HTTP_204_NO_CONTENT)
        self.assertEqual(Site.objects.count(), 0)

        oc = ObjectChange.objects.first()
        self.assertEqual(oc.changed_object, None)
        self.assertEqual(oc.object_repr, site.name)
        self.assertEqual(oc.action, ObjectChangeActionChoices.ACTION_DELETE)
        self.assertEqual(oc.object_data["custom_fields"]["my_field"], "ABC")
        self.assertEqual(oc.object_data["custom_fields"]["my_field_select"], "Bar")
        self.assertEqual(oc.object_data["tags"], ["Tag 1", "Tag 2"])
        self.assertEqual(oc.user_id, self.user.pk)

    @override_settings(EXEMPT_VIEW_PERMISSIONS=["*"])
    def test_get_graphql_object(self):
        """Test GET with changelogs via GraphQL."""
        site_payload = {
            "name": "Test Site 1",
            "slug": "test-site-1",
            "status": "active",
        }
        self.add_permissions("dcim.add_site")

        sites_url = reverse("dcim-api:site-list")
        new_site_response = self.client.post(sites_url, site_payload, format="json", **self.header)
        self.assertHttpStatus(new_site_response, status.HTTP_201_CREATED)

        gql_payload = '{query: object_changes(q: "") { object_repr } }'
        resp = execute_query(gql_payload, user=self.user).to_dict()
        self.assertFalse(resp["data"].get("error"))
        self.assertEqual(first=site_payload["name"], second=resp["data"]["query"][0].get("object_repr", ""))

    @override_settings(EXEMPT_VIEW_PERMISSIONS=["*"])
    def test_graphql_object_lte_filter(self):
        site_payload = {
            "name": "Test Site 2",
            "slug": "test-site-2",
            "status": "active",
        }
        self.add_permissions("dcim.add_site")

        time = "2021-03-14 00:00:00"
        sites_url = reverse("dcim-api:site-list")
        new_site_response = self.client.post(sites_url, site_payload, format="json", **self.header)
        self.assertHttpStatus(new_site_response, status.HTTP_201_CREATED)

        gql_payload = f'{{query: object_changes(time__lte: "{time}") {{ object_repr }} }}'
        resp = execute_query(gql_payload, user=self.user).to_dict()
        self.assertFalse(resp["data"].get("error"))
        self.assertIsInstance(resp["data"].get("query"), list)
        self.assertEqual(len(resp["data"].get("query")), 0)

    @override_settings(EXEMPT_VIEW_PERMISSIONS=["*"])
    def test_graphql_object_gte_filter(self):
        site_payload = {
            "name": "Test Site 1",
            "slug": "test-site-1",
            "status": "active",
        }
        self.add_permissions("dcim.add_site")

        time = "2021-03-14 00:00:00"
        sites_url = reverse("dcim-api:site-list")
        new_site_response = self.client.post(sites_url, site_payload, format="json", **self.header)
        self.assertHttpStatus(new_site_response, status.HTTP_201_CREATED)

        gql_payload = f'{{query: object_changes(time__gte: "{time}") {{ object_repr }} }}'
        resp = execute_query(gql_payload, user=self.user).to_dict()
        self.assertFalse(resp["data"].get("error"))
        self.assertIsInstance(resp["data"].get("query"), list)
        self.assertEqual(first=site_payload["name"], second=resp["data"]["query"][0].get("object_repr", ""))

    def test_change_context(self):
        site_payload = {
            "name": "Test Site 1",
            "slug": "test-site-1",
            "status": "active",
        }
        self.assertEqual(ObjectChange.objects.count(), 0)
        self.add_permissions("dcim.add_site")
        url = reverse("dcim-api:site-list")

        response = self.client.post(url, site_payload, format="json", **self.header)
        self.assertHttpStatus(response, status.HTTP_201_CREATED)

        site = Site.objects.get(pk=response.data["id"])
        oc = get_changes_for_model(site).first()
        self.assertEqual(oc.change_context, ObjectChangeEventContextChoices.CONTEXT_WEB)
        self.assertEqual(oc.change_context_detail, "dcim-api:site-list")
        self.assertEqual(oc.user_id, self.user.pk)

    def test_m2m_change(self):
        """Test that ManyToMany change only generates a single ObjectChange instance"""
        cluster_type = ClusterType.objects.create(name="test_cluster_type")
        cluster = Cluster.objects.create(name="test_cluster", type=cluster_type)
        vm_statuses = Status.objects.get_for_model(VirtualMachine)
        vm = VirtualMachine.objects.create(
            name="test_vm",
            cluster=cluster,
            status=vm_statuses.get(slug="active"),
        )
        vminterface_statuses = Status.objects.get_for_model(VirtualMachine)
        vm_interface = VMInterface.objects.create(
            name="vm interface 1",
            virtual_machine=vm,
            status=vminterface_statuses.get(slug="active"),
        )
        vlan_statuses = Status.objects.get_for_model(VLAN)
        tagged_vlan = VLAN.objects.create(vid=100, name="Vlan100", status=vlan_statuses.get(slug="active"))

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
