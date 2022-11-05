from datetime import datetime, timedelta
import uuid
from unittest import mock

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.test import override_settings
from django.urls import reverse
from django.utils.timezone import make_aware, now
from rest_framework import status

from nautobot.dcim.models import (
    Device,
    DeviceRole,
    DeviceType,
    Manufacturer,
    Rack,
    RackGroup,
    RackRole,
    Site,
)
from nautobot.extras.api.nested_serializers import NestedJobResultSerializer
from nautobot.extras.choices import (
    DynamicGroupOperatorChoices,
    JobExecutionType,
    JobResultStatusChoices,
    RelationshipTypeChoices,
    SecretsGroupAccessTypeChoices,
    SecretsGroupSecretTypeChoices,
)
from nautobot.extras.jobs import get_job
from nautobot.extras.models import (
    ComputedField,
    ConfigContext,
    ConfigContextSchema,
    CustomField,
    CustomLink,
    DynamicGroup,
    DynamicGroupMembership,
    ExportTemplate,
    GitRepository,
    GraphQLQuery,
    ImageAttachment,
    Job,
    JobLogEntry,
    JobResult,
    Note,
    Relationship,
    RelationshipAssociation,
    ScheduledJob,
    Secret,
    SecretsGroup,
    SecretsGroupAssociation,
    Status,
    Tag,
    Webhook,
)
from nautobot.extras.models.jobs import JobHook
from nautobot.extras.tests.test_relationships import RequiredRelationshipTestMixin
from nautobot.extras.utils import TaggableClassesQuery
from nautobot.ipam.models import VLANGroup
from nautobot.users.models import ObjectPermission
from nautobot.utilities.choices import ColorChoices
from nautobot.utilities.testing import APITestCase, APIViewTestCases
from nautobot.utilities.testing.utils import disable_warnings
from nautobot.utilities.utils import get_route_for_model, slugify_dashes_to_underscores


User = get_user_model()


class AppTest(APITestCase):
    def test_root(self):
        url = reverse("extras-api:api-root")
        response = self.client.get(f"{url}?format=api", **self.header)

        self.assertEqual(response.status_code, 200)


#
#  Computed Fields
#


class ComputedFieldTest(APIViewTestCases.APIViewTestCase):
    model = ComputedField
    brief_fields = [
        "content_type",
        "display",
        "id",
        "label",
        "url",
    ]
    create_data = [
        {
            "content_type": "dcim.site",
            "slug": "cf4",
            "label": "Computed Field 4",
            "template": "{{ obj.name }}",
            "fallback_value": "error",
        },
        {
            "content_type": "dcim.site",
            "slug": "cf5",
            "label": "Computed Field 5",
            "template": "{{ obj.name }}",
            "fallback_value": "error",
        },
        {
            "content_type": "dcim.site",
            "slug": "cf6",
            "label": "Computed Field 6",
            "template": "{{ obj.name }}",
        },
        {
            "content_type": "dcim.site",
            "label": "Computed Field 7",
            "template": "{{ obj.name }}",
            "fallback_value": "error",
        },
    ]
    update_data = {
        "content_type": "dcim.site",
        "slug": "cf1",
        "label": "My Computed Field",
    }
    bulk_update_data = {
        "description": "New description",
    }
    slug_source = "label"
    slugify_function = staticmethod(slugify_dashes_to_underscores)

    @classmethod
    def setUpTestData(cls):
        site_ct = ContentType.objects.get_for_model(Site)

        ComputedField.objects.create(
            slug="cf1",
            label="Computed Field One",
            template="{{ obj.name }}",
            fallback_value="error",
            content_type=site_ct,
        )
        ComputedField.objects.create(
            slug="cf2",
            label="Computed Field Two",
            template="{{ obj.name }}",
            fallback_value="error",
            content_type=site_ct,
        )
        ComputedField.objects.create(
            slug="cf3",
            label="Computed Field Three",
            template="{{ obj.name }}",
            fallback_value="error",
            content_type=site_ct,
        )

        cls.site = Site.objects.create(name="Site 1", slug="site-1")

    def test_computed_field_include(self):
        """Test that explicitly including a computed field behaves as expected."""
        self.add_permissions("dcim.view_site")
        url = reverse("dcim-api:site-detail", kwargs={"pk": self.site.pk})

        # First get the object without computed fields.
        response = self.client.get(url, **self.header)
        self.assertNotIn("computed_fields", response.json())

        # Now get it with computed fields.
        params = {"include": "computed_fields"}
        response = self.client.get(url, data=params, **self.header)
        self.assertIn("computed_fields", response.json())


class ConfigContextTest(APIViewTestCases.APIViewTestCase):
    model = ConfigContext
    brief_fields = ["display", "id", "name", "url"]
    create_data = [
        {
            "name": "Config Context 4",
            "data": {"more_foo": True},
        },
        {
            "name": "Config Context 5",
            "data": {"more_bar": False},
        },
        {
            "name": "Config Context 6",
            "data": {"more_baz": None},
        },
    ]
    bulk_update_data = {
        "description": "New description",
    }

    @classmethod
    def setUpTestData(cls):
        ConfigContext.objects.create(name="Config Context 1", weight=100, data={"foo": 123})
        ConfigContext.objects.create(name="Config Context 2", weight=200, data={"bar": 456})
        ConfigContext.objects.create(name="Config Context 3", weight=300, data={"baz": 789})

    def test_render_configcontext_for_object(self):
        """
        Test rendering config context data for a device.
        """
        manufacturer = Manufacturer.objects.create(name="Manufacturer 1", slug="manufacturer-1")
        devicetype = DeviceType.objects.create(manufacturer=manufacturer, model="Device Type 1", slug="device-type-1")
        devicerole = DeviceRole.objects.create(name="Device Role 1", slug="device-role-1")
        site = Site.objects.create(name="Site-1", slug="site-1")
        device = Device.objects.create(name="Device 1", device_type=devicetype, device_role=devicerole, site=site)

        # Test default config contexts (created at test setup)
        rendered_context = device.get_config_context()
        self.assertEqual(rendered_context["foo"], 123)
        self.assertEqual(rendered_context["bar"], 456)
        self.assertEqual(rendered_context["baz"], 789)

        # Test API response as well
        self.add_permissions("dcim.view_device")
        device_url = reverse("dcim-api:device-detail", kwargs={"pk": device.pk})
        response = self.client.get(device_url, **self.header)
        self.assertHttpStatus(response, status.HTTP_200_OK)
        self.assertIn("config_context", response.data)
        self.assertEqual(response.data["config_context"], {"foo": 123, "bar": 456, "baz": 789}, response.data)

        # Add another context specific to the site
        configcontext4 = ConfigContext(name="Config Context 4", data={"site_data": "ABC"})
        configcontext4.save()
        configcontext4.sites.add(site)
        rendered_context = device.get_config_context()
        self.assertEqual(rendered_context["site_data"], "ABC")
        response = self.client.get(device_url, **self.header)
        self.assertHttpStatus(response, status.HTTP_200_OK)
        self.assertIn("config_context", response.data)
        self.assertEqual(response.data["config_context"]["site_data"], "ABC", response.data["config_context"])

        # Override one of the default contexts
        configcontext5 = ConfigContext(name="Config Context 5", weight=2000, data={"foo": 999})
        configcontext5.save()
        configcontext5.sites.add(site)
        rendered_context = device.get_config_context()
        self.assertEqual(rendered_context["foo"], 999)
        response = self.client.get(device_url, **self.header)
        self.assertHttpStatus(response, status.HTTP_200_OK)
        self.assertIn("config_context", response.data)
        self.assertEqual(response.data["config_context"]["foo"], 999, response.data["config_context"])

        # Add a context which does NOT match our device and ensure it does not apply
        site2 = Site.objects.create(name="Site 2", slug="site-2")
        configcontext6 = ConfigContext(name="Config Context 6", weight=2000, data={"bar": 999})
        configcontext6.save()
        configcontext6.sites.add(site2)
        rendered_context = device.get_config_context()
        self.assertEqual(rendered_context["bar"], 456)
        response = self.client.get(device_url, **self.header)
        self.assertHttpStatus(response, status.HTTP_200_OK)
        self.assertIn("config_context", response.data)
        self.assertEqual(response.data["config_context"]["bar"], 456, response.data["config_context"])

    def test_schema_validation_pass(self):
        """
        Given a config context schema
        And a config context that conforms to that schema
        Assert that the config context passes schema validation via full_clean()
        """
        schema = ConfigContextSchema.objects.create(
            name="Schema 1", slug="schema-1", data_schema={"type": "object", "properties": {"foo": {"type": "string"}}}
        )
        self.add_permissions("extras.add_configcontext")

        data = {"name": "Config Context with schema", "weight": 100, "data": {"foo": "bar"}, "schema": str(schema.pk)}
        response = self.client.post(self._get_list_url(), data, format="json", **self.header)
        self.assertHttpStatus(response, status.HTTP_201_CREATED)
        self.assertEqual(response.data["schema"]["id"], str(schema.pk))

    def test_schema_validation_fails(self):
        """
        Given a config context schema
        And a config context that *does not* conform to that schema
        Assert that the config context fails schema validation via full_clean()
        """
        schema = ConfigContextSchema.objects.create(
            name="Schema 1", slug="schema-1", data_schema={"type": "object", "properties": {"foo": {"type": "integer"}}}
        )
        self.add_permissions("extras.add_configcontext")

        data = {
            "name": "Config Context with bad schema",
            "weight": 100,
            "data": {"foo": "bar"},
            "schema": str(schema.pk),
        }
        response = self.client.post(self._get_list_url(), data, format="json", **self.header)
        self.assertHttpStatus(response, status.HTTP_400_BAD_REQUEST)


class ConfigContextSchemaTest(APIViewTestCases.APIViewTestCase):
    model = ConfigContextSchema
    brief_fields = ["display", "id", "name", "slug", "url"]
    create_data = [
        {
            "name": "Schema 4",
            "slug": "schema-4",
            "data_schema": {"type": "object", "properties": {"foo": {"type": "string"}}},
        },
        {
            "name": "Schema 5",
            "slug": "schema-5",
            "data_schema": {"type": "object", "properties": {"bar": {"type": "string"}}},
        },
        {
            "name": "Schema 6",
            "slug": "schema-6",
            "data_schema": {"type": "object", "properties": {"buz": {"type": "string"}}},
        },
        {
            "name": "Schema 7",
            "data_schema": {"type": "object", "properties": {"buz": {"type": "string"}}},
        },
    ]
    bulk_update_data = {
        "description": "New description",
    }
    choices_fields = []
    slug_source = "name"

    @classmethod
    def setUpTestData(cls):
        ConfigContextSchema.objects.create(
            name="Schema 1", slug="schema-1", data_schema={"type": "object", "properties": {"foo": {"type": "string"}}}
        )
        ConfigContextSchema.objects.create(
            name="Schema 2", slug="schema-2", data_schema={"type": "object", "properties": {"bar": {"type": "string"}}}
        )
        ConfigContextSchema.objects.create(
            name="Schema 3", slug="schema-3", data_schema={"type": "object", "properties": {"baz": {"type": "string"}}}
        )


class ContentTypeTest(APITestCase):
    @override_settings(EXEMPT_VIEW_PERMISSIONS=["contenttypes.contenttype"])
    def test_list_objects(self):
        contenttype_count = ContentType.objects.count()

        response = self.client.get(reverse("extras-api:contenttype-list"), **self.header)
        self.assertHttpStatus(response, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], contenttype_count)

    @override_settings(EXEMPT_VIEW_PERMISSIONS=["contenttypes.contenttype"])
    def test_get_object(self):
        contenttype = ContentType.objects.first()

        url = reverse("extras-api:contenttype-detail", kwargs={"pk": contenttype.pk})
        self.assertHttpStatus(self.client.get(url, **self.header), status.HTTP_200_OK)


class CreatedUpdatedFilterTest(APITestCase):
    def setUp(self):
        super().setUp()

        self.site1 = Site.objects.create(name="Test Site 1", slug="test-site-1")
        self.rackgroup1 = RackGroup.objects.create(site=self.site1, name="Test Rack Group 1", slug="test-rack-group-1")
        self.rackrole1 = RackRole.objects.create(name="Test Rack Role 1", slug="test-rack-role-1", color="ff0000")
        self.rack1 = Rack.objects.create(
            site=self.site1,
            group=self.rackgroup1,
            role=self.rackrole1,
            name="Test Rack 1",
            u_height=42,
        )
        self.rack2 = Rack.objects.create(
            site=self.site1,
            group=self.rackgroup1,
            role=self.rackrole1,
            name="Test Rack 2",
            u_height=42,
        )

        # change the created and last_updated of one
        Rack.objects.filter(pk=self.rack2.pk).update(
            last_updated=make_aware(datetime(2001, 2, 3, 1, 2, 3, 4)),
            created=make_aware(datetime(2001, 2, 3)),
        )

    def test_get_rack_created(self):
        self.add_permissions("dcim.view_rack")
        url = reverse("dcim-api:rack-list")
        response = self.client.get(f"{url}?created=2001-02-03", **self.header)

        self.assertHttpStatus(response, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["id"], str(self.rack2.pk))

    def test_get_rack_created_gte(self):
        self.add_permissions("dcim.view_rack")
        url = reverse("dcim-api:rack-list")
        response = self.client.get(f"{url}?created__gte=2001-02-04", **self.header)

        self.assertHttpStatus(response, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["id"], str(self.rack1.pk))

    def test_get_rack_created_lte(self):
        self.add_permissions("dcim.view_rack")
        url = reverse("dcim-api:rack-list")
        response = self.client.get(f"{url}?created__lte=2001-02-04", **self.header)

        self.assertHttpStatus(response, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["id"], str(self.rack2.pk))

    def test_get_rack_last_updated(self):
        self.add_permissions("dcim.view_rack")
        url = reverse("dcim-api:rack-list")
        response = self.client.get(f"{url}?last_updated=2001-02-03%2001:02:03.000004", **self.header)

        self.assertHttpStatus(response, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["id"], str(self.rack2.pk))

    def test_get_rack_last_updated_gte(self):
        self.add_permissions("dcim.view_rack")
        url = reverse("dcim-api:rack-list")
        response = self.client.get(f"{url}?last_updated__gte=2001-02-04%2001:02:03.000004", **self.header)

        self.assertHttpStatus(response, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["id"], str(self.rack1.pk))

    def test_get_rack_last_updated_lte(self):
        self.add_permissions("dcim.view_rack")
        url = reverse("dcim-api:rack-list")
        response = self.client.get(f"{url}?last_updated__lte=2001-02-04%2001:02:03.000004", **self.header)

        self.assertHttpStatus(response, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["id"], str(self.rack2.pk))


class CustomFieldTestVersion12(APIViewTestCases.APIViewTestCase):
    """Tests for the API version 1.2/1.3 CustomField REST API."""

    model = CustomField
    api_version = "1.2"
    brief_fields = ["display", "id", "name", "url"]
    create_data = [
        {
            "content_types": ["dcim.site"],
            "name": "cf4",
            "type": "date",
        },
        {
            "content_types": ["dcim.site"],
            "name": "cf5",
            "type": "url",
        },
        {
            "content_types": ["dcim.site"],
            "name": "cf6",
            "type": "select",
            "label": "Custom Field 6",
        },
    ]
    update_data = {
        "content_types": ["dcim.site"],
        "name": "cf1",
        "label": "foo",
    }
    bulk_update_data = {
        "description": "New description",
    }
    choices_fields = ["filter_logic", "type"]
    slug_source = "label"
    slugify_function = staticmethod(slugify_dashes_to_underscores)

    @classmethod
    def setUpTestData(cls):
        site_ct = ContentType.objects.get_for_model(Site)

        custom_fields = (
            CustomField(name="cf1", type="text"),
            CustomField(name="cf2", type="integer"),
            CustomField(name="cf3", type="boolean"),
        )
        for cf in custom_fields:
            cf.validated_save()
            cf.content_types.add(site_ct)

    def test_create_object(self):
        super(APIViewTestCases.APIViewTestCase, self).test_create_object()
        # Verify that label is auto-populated when not specified
        for create_data in self.create_data:
            instance = self._get_queryset().get(name=create_data["name"])
            self.assertEqual(instance.label, create_data.get("label", instance.name))


class CustomFieldTestVersion14(CustomFieldTestVersion12):
    """Tests for the API version 1.4+ CustomField REST API."""

    api_version = "1.4"
    create_data = [
        {
            "content_types": ["dcim.site"],
            "label": "Custom Field 4",
            "slug": "cf4",
            "type": "date",
            "weight": 100,
        },
        {
            "content_types": ["dcim.site", "dcim.device"],
            "label": "Custom Field 5",
            "slug": "cf5",
            "type": "url",
            "default": "http://example.com",
            "weight": 200,
        },
        {
            "content_types": ["dcim.site"],
            "label": "Custom Field 6",
            "slug": "cf6",
            "type": "select",
            "description": "A select custom field",
            "weight": 300,
        },
    ]
    update_data = {
        "content_types": ["dcim.site"],
        "description": "New description",
        "label": "Non-unique label",
    }

    @classmethod
    def setUpTestData(cls):
        site_ct = ContentType.objects.get_for_model(Site)

        custom_fields = (
            CustomField(slug="cf1", label="Custom Field 1", type="text"),
            CustomField(slug="cf2", label="Custom Field 2", type="integer"),
            CustomField(slug="cf3", label="Custom Field 3", type="boolean"),
        )
        for cf in custom_fields:
            cf.validated_save()
            cf.content_types.add(site_ct)

    def test_create_object(self):
        super(APIViewTestCases.APIViewTestCase, self).test_create_object()
        # 2.0 TODO: #824 remove name entirely
        # For now, check that name is correctly populated in the model even though it's not an API field.
        for create_data in self.create_data:
            instance = self._get_queryset().get(slug=create_data["slug"])
            self.assertEqual(instance.name, instance.slug)

    def test_create_object_required_fields(self):
        """For this API version, `label` and `slug` are required fields."""
        self.add_permissions("extras.add_customfield")

        incomplete_data = {
            "content_types": ["dcim.site"],
            "type": "date",
        }

        response = self.client.post(self._get_list_url(), incomplete_data, format="json", **self.header)
        self.assertHttpStatus(response, status.HTTP_400_BAD_REQUEST)
        self.maxDiff = None
        self.assertEqual(
            response.data,
            {"slug": ["This field is required."], "label": ["This field is required."]},
        )


class CustomLinkTest(APIViewTestCases.APIViewTestCase):
    model = CustomLink
    brief_fields = ["content_type", "display", "id", "name", "url"]
    create_data = [
        {
            "content_type": "dcim.site",
            "name": "api-test-4",
            "text": "API customlink text 4",
            "target_url": "http://api-test-4.com/test4",
            "weight": 100,
            "new_window": False,
        },
        {
            "content_type": "dcim.site",
            "name": "api-test-5",
            "text": "API customlink text 5",
            "target_url": "http://api-test-5.com/test5",
            "weight": 100,
            "new_window": False,
        },
        {
            "content_type": "dcim.site",
            "name": "api-test-6",
            "text": "API customlink text 6",
            "target_url": "http://api-test-6.com/test6",
            "weight": 100,
            "new_window": False,
        },
    ]
    choices_fields = ["button_class"]

    @classmethod
    def setUpTestData(cls):
        obj_type = ContentType.objects.get_for_model(Site)

        CustomLink.objects.create(
            content_type=obj_type,
            name="api-test-1",
            text="API customlink text 1",
            target_url="http://api-test-1.com/test1",
            weight=100,
            new_window=False,
        )
        CustomLink.objects.create(
            content_type=obj_type,
            name="api-test-2",
            text="API customlink text 2",
            target_url="http://api-test-2.com/test2",
            weight=100,
            new_window=False,
        )
        CustomLink.objects.create(
            content_type=obj_type,
            name="api-test-3",
            text="API customlink text 3",
            target_url="http://api-test-3.com/test3",
            weight=100,
            new_window=False,
        )


class DynamicGroupTestMixin:
    """Mixin for Dynamic Group test cases to re-use the same set of common fixtures."""

    @classmethod
    def setUpTestData(cls):
        # Create the objects required for devices.
        sites = [
            Site.objects.create(name="Site 1", slug="site-1"),
            Site.objects.create(name="Site 2", slug="site-2"),
            Site.objects.create(name="Site 3", slug="site-3"),
        ]

        manufacturer = Manufacturer.objects.create(name="Manufacturer 1", slug="manufacturer-1")
        device_type = DeviceType.objects.create(
            manufacturer=manufacturer,
            model="device Type 1",
            slug="device-type-1",
        )
        device_role = DeviceRole.objects.create(name="Device Role 1", slug="device-role-1", color="ff0000")
        status_active = Status.objects.get(slug="active")
        status_planned = Status.objects.get(slug="planned")
        Device.objects.create(
            name="device-site-1",
            status=status_active,
            device_role=device_role,
            device_type=device_type,
            site=sites[0],
        )
        Device.objects.create(
            name="device-site-2",
            status=status_active,
            device_role=device_role,
            device_type=device_type,
            site=sites[1],
        )
        Device.objects.create(
            name="device-site-3",
            status=status_planned,
            device_role=device_role,
            device_type=device_type,
            site=sites[2],
        )

        # Then the DynamicGroups.
        cls.content_type = ContentType.objects.get_for_model(Device)
        cls.groups = [
            DynamicGroup.objects.create(
                name="API DynamicGroup 1",
                slug="api-dynamicgroup-1",
                content_type=cls.content_type,
                filter={"status": ["active"]},
            ),
            DynamicGroup.objects.create(
                name="API DynamicGroup 2",
                slug="api-dynamicgroup-2",
                content_type=cls.content_type,
                filter={"status": ["planned"]},
            ),
            DynamicGroup.objects.create(
                name="API DynamicGroup 3",
                slug="api-dynamicgroup-3",
                content_type=cls.content_type,
                filter={"site": ["site-3"]},
            ),
        ]


class DynamicGroupTest(DynamicGroupTestMixin, APIViewTestCases.APIViewTestCase):
    model = DynamicGroup
    brief_fields = ["content_type", "display", "id", "name", "slug", "url"]
    create_data = [
        {
            "name": "API DynamicGroup 4",
            "slug": "api-dynamicgroup-4",
            "content_type": "dcim.device",
            "filter": {"site": ["site-1"]},
        },
        {
            "name": "API DynamicGroup 5",
            "slug": "api-dynamicgroup-5",
            "content_type": "dcim.device",
            "filter": {"has_interfaces": False},
        },
        {
            "name": "API DynamicGroup 6",
            "slug": "api-dynamicgroup-6",
            "content_type": "dcim.device",
            "filter": {"site": ["site-2"]},
        },
    ]

    def test_get_members(self):
        """Test that the `/members/` API endpoint returns what is expected."""
        self.add_permissions("extras.view_dynamicgroup")
        instance = DynamicGroup.objects.first()
        member_count = instance.members.count()
        url = reverse("extras-api:dynamicgroup-members", kwargs={"pk": instance.pk})
        response = self.client.get(url, **self.header)
        self.assertHttpStatus(response, status.HTTP_200_OK)
        self.assertEqual(member_count, len(response.json()["results"]))


class DynamicGroupMembershipTest(DynamicGroupTestMixin, APIViewTestCases.APIViewTestCase):
    model = DynamicGroupMembership
    brief_fields = ["display", "group", "id", "operator", "parent_group", "url", "weight"]
    choices_fields = ["operator"]

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        parent = DynamicGroup.objects.create(
            name="parent",
            slug="parent",
            content_type=cls.content_type,
            filter={},
        )
        parent2 = DynamicGroup.objects.create(
            name="parent2",
            slug="parent2",
            content_type=cls.content_type,
            filter={},
        )
        group1, group2, group3 = cls.groups

        DynamicGroupMembership.objects.create(
            parent_group=parent,
            group=group1,
            operator=DynamicGroupOperatorChoices.OPERATOR_INTERSECTION,
            weight=10,
        )
        DynamicGroupMembership.objects.create(
            parent_group=parent,
            group=group2,
            operator=DynamicGroupOperatorChoices.OPERATOR_UNION,
            weight=20,
        )
        DynamicGroupMembership.objects.create(
            parent_group=parent,
            group=group3,
            operator=DynamicGroupOperatorChoices.OPERATOR_DIFFERENCE,
            weight=30,
        )

        cls.create_data = [
            {
                "parent_group": parent2.pk,
                "group": group1.pk,
                "operator": DynamicGroupOperatorChoices.OPERATOR_INTERSECTION,
                "weight": 10,
            },
            {
                "parent_group": parent2.pk,
                "group": group2.pk,
                "operator": DynamicGroupOperatorChoices.OPERATOR_UNION,
                "weight": 20,
            },
            {
                "parent_group": parent2.pk,
                "group": group3.pk,
                "operator": DynamicGroupOperatorChoices.OPERATOR_DIFFERENCE,
                "weight": 30,
            },
        ]


class ExportTemplateTest(APIViewTestCases.APIViewTestCase):
    model = ExportTemplate
    brief_fields = ["display", "id", "name", "url"]
    create_data = [
        {
            "content_type": "dcim.device",
            "name": "Test Export Template 4",
            "template_code": "{% for obj in queryset %}{{ obj.name }}\n{% endfor %}",
        },
        {
            "content_type": "dcim.device",
            "name": "Test Export Template 5",
            "template_code": "{% for obj in queryset %}{{ obj.name }}\n{% endfor %}",
        },
        {
            "content_type": "dcim.device",
            "name": "Test Export Template 6",
            "template_code": "{% for obj in queryset %}{{ obj.name }}\n{% endfor %}",
        },
    ]
    bulk_update_data = {
        "description": "New description",
    }
    choices_fields = ["owner_content_type", "content_type"]

    @classmethod
    def setUpTestData(cls):
        ct = ContentType.objects.get_for_model(Device)

        ExportTemplate.objects.create(
            content_type=ct,
            name="Export Template 1",
            template_code="{% for obj in queryset %}{{ obj.name }}\n{% endfor %}",
        )
        ExportTemplate.objects.create(
            content_type=ct,
            name="Export Template 2",
            template_code="{% for obj in queryset %}{{ obj.name }}\n{% endfor %}",
        )
        ExportTemplate.objects.create(
            content_type=ct,
            name="Export Template 3",
            template_code="{% for obj in queryset %}{{ obj.name }}\n{% endfor %}",
        )


class GitRepositoryTest(APIViewTestCases.APIViewTestCase):
    model = GitRepository
    brief_fields = ["display", "id", "name", "url"]
    bulk_update_data = {
        "branch": "develop",
    }
    choices_fields = ["provided_contents"]
    slug_source = "name"

    @classmethod
    def setUpTestData(cls):
        secrets_groups = (
            SecretsGroup.objects.create(name="Secrets Group 1", slug="secrets-group-1"),
            SecretsGroup.objects.create(name="Secrets Group 2", slug="secrets-group-2"),
        )

        cls.repos = (
            GitRepository(
                name="Repo 1",
                slug="repo-1",
                remote_url="https://example.com/repo1.git",
                secrets_group=secrets_groups[0],
            ),
            GitRepository(
                name="Repo 2",
                slug="repo-2",
                remote_url="https://example.com/repo2.git",
                secrets_group=secrets_groups[0],
            ),
            GitRepository(name="Repo 3", slug="repo-3", remote_url="https://example.com/repo3.git"),
        )
        for repo in cls.repos:
            repo.save(trigger_resync=False)

        cls.create_data = [
            {
                "name": "New Git Repository 1",
                "slug": "new-git-repository-1",
                "remote_url": "https://example.com/newrepo1.git",
                "secrets_group": secrets_groups[1].pk,
            },
            {
                "name": "New Git Repository 2",
                "slug": "new-git-repository-2",
                "remote_url": "https://example.com/newrepo2.git",
                "secrets_group": secrets_groups[1].pk,
            },
            {
                "name": "New Git Repository 3",
                "slug": "new-git-repository-3",
                "remote_url": "https://example.com/newrepo3.git",
                "secrets_group": secrets_groups[1].pk,
            },
            {
                "name": "New Git Repository 4",
                "remote_url": "https://example.com/newrepo3.git",
                "secrets_group": secrets_groups[1].pk,
            },
        ]

    @override_settings(EXEMPT_VIEW_PERMISSIONS=[])
    @mock.patch("nautobot.extras.api.views.get_worker_count")
    def test_run_git_sync_no_celery_worker(self, mock_get_worker_count):
        """Git sync cannot be triggered if Celery is not running."""
        mock_get_worker_count.return_value = 0
        self.add_permissions("extras.add_gitrepository")
        self.add_permissions("extras.change_gitrepository")
        url = reverse("extras-api:gitrepository-sync", kwargs={"pk": self.repos[0].id})
        response = self.client.post(url, format="json", **self.header)
        self.assertHttpStatus(response, status.HTTP_503_SERVICE_UNAVAILABLE)
        self.assertEqual(
            response.data["detail"], "Unable to process request: No celery workers running on queue default."
        )

    @override_settings(EXEMPT_VIEW_PERMISSIONS=[])
    @mock.patch("nautobot.extras.api.views.get_worker_count")
    def test_run_git_sync_nonexistent_repo(self, mock_get_worker_count):
        """Git sync request handles case of a nonexistent repository."""
        mock_get_worker_count.return_value = 1
        self.add_permissions("extras.add_gitrepository")
        self.add_permissions("extras.change_gitrepository")
        url = reverse("extras-api:gitrepository-sync", kwargs={"pk": "11111111-1111-1111-1111-111111111111"})
        response = self.client.post(url, format="json", **self.header)
        self.assertHttpStatus(response, status.HTTP_404_NOT_FOUND)

    @override_settings(EXEMPT_VIEW_PERMISSIONS=[])
    @mock.patch("nautobot.extras.api.views.get_worker_count")
    def test_run_git_sync_without_permissions(self, mock_get_worker_count):
        """Git sync request verifies user permissions."""
        mock_get_worker_count.return_value = 1
        url = reverse("extras-api:gitrepository-sync", kwargs={"pk": self.repos[0].id})
        response = self.client.post(url, format="json", **self.header)
        self.assertHttpStatus(response, status.HTTP_403_FORBIDDEN)

    @override_settings(EXEMPT_VIEW_PERMISSIONS=[])
    @mock.patch("nautobot.extras.api.views.get_worker_count")
    def test_run_git_sync_with_permissions(self, mock_get_worker_count):
        """Git sync request can be submitted successfully."""
        mock_get_worker_count.return_value = 1
        self.add_permissions("extras.add_gitrepository")
        self.add_permissions("extras.change_gitrepository")
        url = reverse("extras-api:gitrepository-sync", kwargs={"pk": self.repos[0].id})
        response = self.client.post(url, format="json", **self.header)
        self.assertHttpStatus(response, status.HTTP_200_OK)

    def test_create_with_plugin_provided_contents(self):
        """Test that `provided_contents` published by a plugin works."""
        self.add_permissions("extras.add_gitrepository")
        self.add_permissions("extras.change_gitrepository")
        url = self._get_list_url()
        data = {
            "name": "plugin_test",
            "slug": "plugin-test",
            "remote_url": "https://localhost/plugin-test",
            "provided_contents": ["example_plugin.textfile"],
        }
        response = self.client.post(url, data, format="json", **self.header)
        self.assertHttpStatus(response, status.HTTP_201_CREATED)
        self.assertEqual(list(response.data["provided_contents"]), data["provided_contents"])


class GraphQLQueryTest(APIViewTestCases.APIViewTestCase):
    model = GraphQLQuery
    brief_fields = ["display", "id", "name", "url"]

    create_data = [
        {
            "name": "graphql-query-4",
            "slug": "graphql-query-4",
            "query": "{ query: sites {name} }",
        },
        {
            "name": "graphql-query-5",
            "slug": "graphql-query-5",
            "query": '{ devices(role: "edge") { id, name, device_role { name slug } } }',
        },
        {
            "name": "Graphql Query 6",
            "query": '{ devices(role: "edge") { id, name, device_role { name slug } } }',
        },
    ]
    slug_source = "name"

    @classmethod
    def setUpTestData(cls):
        cls.graphqlqueries = (
            GraphQLQuery(
                name="graphql-query-1",
                slug="graphql-query-1",
                query="{ sites {name} }",
            ),
            GraphQLQuery(
                name="graphql-query-2",
                slug="graphql-query-2",
                query='{ devices(role: "edge") { id, name, device_role { name slug } } }',
            ),
            GraphQLQuery(
                name="graphql-query-3",
                slug="graphql-query-3",
                query="""
query ($device: [String!]) {
  devices(name: $device) {
    config_context
    name
    position
    serial
    primary_ip4 {
      id
      primary_ip4_for {
        id
        name
      }
    }
    tenant {
      name
    }
    tags {
      name
      slug
    }
    device_role {
      name
    }
    platform {
      name
      slug
      manufacturer {
        name
      }
      napalm_driver
    }
    site {
      name
      slug
      vlans {
        id
        name
        vid
      }
      vlan_groups {
        id
      }
    }
    interfaces {
      description
      mac_address
      enabled
      name
      ip_addresses {
        address
        tags {
          id
        }
      }
      connected_circuit_termination {
        circuit {
          cid
          commit_rate
          provider {
            name
          }
        }
      }
      tagged_vlans {
        id
      }
      untagged_vlan {
        id
      }
      cable {
        termination_a_type
        status {
          name
        }
        color
      }
      tagged_vlans {
        site {
          name
        }
        id
      }
      tags {
        id
      }
    }
  }
}""",
            ),
        )

        for query in cls.graphqlqueries:
            query.full_clean()
            query.save()

    def test_run_saved_query(self):
        """Exercise the /run/ API endpoint."""
        self.add_permissions("extras.add_graphqlquery")
        self.add_permissions("extras.change_graphqlquery")
        self.add_permissions("extras.view_graphqlquery")

        url = reverse("extras-api:graphqlquery-run", kwargs={"pk": self.graphqlqueries[0].pk})
        response = self.client.post(url, **self.header)
        self.assertHttpStatus(response, status.HTTP_200_OK)
        self.assertEqual({"data": {"sites": []}}, response.data)

        url = reverse("extras-api:graphqlquery-run", kwargs={"pk": self.graphqlqueries[2].pk})
        response = self.client.post(url, **self.header)
        self.assertHttpStatus(response, status.HTTP_200_OK)
        self.assertEqual({"data": {"devices": []}}, response.data)


# TODO: Standardize to APIViewTestCase (needs create & update tests)
class ImageAttachmentTest(
    APIViewTestCases.GetObjectViewTestCase,
    APIViewTestCases.ListObjectsViewTestCase,
    APIViewTestCases.DeleteObjectViewTestCase,
):
    model = ImageAttachment
    brief_fields = ["display", "id", "image", "name", "url"]
    choices_fields = ["content_type"]

    @classmethod
    def setUpTestData(cls):
        ct = ContentType.objects.get_for_model(Site)

        site = Site.objects.create(name="Site 1", slug="site-1")

        ImageAttachment.objects.create(
            content_type=ct,
            object_id=site.pk,
            name="Image Attachment 1",
            image="http://example.com/image1.png",
            image_height=100,
            image_width=100,
        )
        ImageAttachment.objects.create(
            content_type=ct,
            object_id=site.pk,
            name="Image Attachment 2",
            image="http://example.com/image2.png",
            image_height=100,
            image_width=100,
        )
        ImageAttachment.objects.create(
            content_type=ct,
            object_id=site.pk,
            name="Image Attachment 3",
            image="http://example.com/image3.png",
            image_height=100,
            image_width=100,
        )


class JobAPIRunTestMixin:
    """
    Mixin providing test cases for the "run" API endpoint, shared between the different versions of Job API testing.
    """

    def setUp(self):
        super().setUp()
        self.job_model = Job.objects.get_for_class_path("local/api_test_job/APITestJob")
        self.job_model.enabled = True
        self.job_model.validated_save()

    def get_run_url(self, class_path="local/api_test_job/APITestJob"):
        """To be implemented by classes using this mixin."""
        raise NotImplementedError

    # Status code for successful submission of a job or schedule - to be set by subclasses
    run_success_response_status = None

    @override_settings(EXEMPT_VIEW_PERMISSIONS=["*"])
    def test_run_job_anonymous_not_permitted(self):
        """The run_job endpoint should NOT allow anonymous users to submit jobs."""
        url = self.get_run_url()
        with disable_warnings("django.request"):
            response = self.client.post(url)
        self.assertHttpStatus(response, status.HTTP_403_FORBIDDEN)

    @override_settings(EXEMPT_VIEW_PERMISSIONS=[])
    @mock.patch("nautobot.extras.api.views.get_worker_count")
    def test_run_job_without_permission(self, mock_get_worker_count):
        """Job run request enforces user permissions."""
        mock_get_worker_count.return_value = 1
        url = self.get_run_url()
        with disable_warnings("django.request"):
            response = self.client.post(url, {}, format="json", **self.header)
        self.assertHttpStatus(response, status.HTTP_403_FORBIDDEN)

    @override_settings(EXEMPT_VIEW_PERMISSIONS=[])
    @mock.patch("nautobot.extras.api.views.get_worker_count")
    def test_run_job_object_permissions(self, mock_get_worker_count):
        """The run_job endpoint should enforce object-level permissions."""
        mock_get_worker_count.return_value = 1
        obj_perm = ObjectPermission(
            name="Test permission",
            constraints={"module_name__in": ["test_pass", "test_fail"]},
            actions=["run"],
        )
        obj_perm.save()
        obj_perm.users.add(self.user)
        obj_perm.object_types.add(ContentType.objects.get_for_model(Job))

        # Try post to unpermitted job
        url = self.get_run_url()
        with disable_warnings("django.request"):
            response = self.client.post(url, **self.header)
        self.assertHttpStatus(response, status.HTTP_404_NOT_FOUND)

        # Try post to permitted job
        job_model = Job.objects.get_for_class_path("local/test_pass/TestPass")
        job_model.enabled = True
        job_model.validated_save()
        url = self.get_run_url("local/test_pass/TestPass")
        response = self.client.post(url, **self.header)
        self.assertHttpStatus(response, self.run_success_response_status)

    @override_settings(EXEMPT_VIEW_PERMISSIONS=[])
    @mock.patch("nautobot.extras.api.views.get_worker_count")
    def test_run_job_not_enabled(self, mock_get_worker_count):
        """Job run request enforces the Job.enabled flag."""
        mock_get_worker_count.return_value = 1
        self.add_permissions("extras.run_job")

        job_model = Job.objects.get_for_class_path("local/api_test_job/APITestJob")
        job_model.enabled = False
        job_model.save()

        url = self.get_run_url()
        with disable_warnings("django.request"):
            response = self.client.post(url, {}, format="json", **self.header)
        self.assertHttpStatus(response, status.HTTP_403_FORBIDDEN)

    @override_settings(EXEMPT_VIEW_PERMISSIONS=[])
    @mock.patch("nautobot.extras.api.views.get_worker_count")
    def test_run_job_not_installed(self, mock_get_worker_count):
        """Job run request enforces the Job.installed flag."""
        mock_get_worker_count.return_value = 1
        self.add_permissions("extras.run_job")

        job_model = Job(
            source="local",
            module_name="uninstalled_module",
            job_class_name="NoSuchJob",
            grouping="Uninstalled Module",
            name="No such job",
            installed=False,
            enabled=True,
        )
        job_model.validated_save()

        url = self.get_run_url("local/uninstalled_module/NoSuchJob")
        with disable_warnings("django.request"):
            response = self.client.post(url, {}, format="json", **self.header)
        self.assertHttpStatus(response, status.HTTP_405_METHOD_NOT_ALLOWED)

    @override_settings(EXEMPT_VIEW_PERMISSIONS=[])
    @mock.patch("nautobot.extras.api.views.get_worker_count")
    def test_run_job_no_worker(self, mock_get_worker_count):
        """Job run cannot be requested if Celery is not running."""
        mock_get_worker_count.return_value = 0
        self.add_permissions("extras.run_job")
        device_role = DeviceRole.objects.create(name="role", slug="role")
        job_data = {
            "var1": "FooBar",
            "var2": 123,
            "var3": False,
            "var4": device_role.pk,
        }

        data = {
            "data": job_data,
            "commit": True,
        }

        url = self.get_run_url()
        response = self.client.post(url, data, format="json", **self.header)
        self.assertHttpStatus(response, status.HTTP_503_SERVICE_UNAVAILABLE)
        self.assertEqual(
            response.data["detail"], "Unable to process request: No celery workers running on queue default."
        )

    @override_settings(EXEMPT_VIEW_PERMISSIONS=["*"])
    @mock.patch("nautobot.extras.api.views.get_worker_count")
    def test_run_job_object_var(self, mock_get_worker_count):
        """Job run requests can reference objects by their primary keys."""
        mock_get_worker_count.return_value = 1
        self.add_permissions("extras.run_job")
        device_role = DeviceRole.objects.create(name="role", slug="role")
        job_data = {
            "var1": "FooBar",
            "var2": 123,
            "var3": False,
            "var4": device_role.pk,
        }

        data = {
            "data": job_data,
            "commit": True,
            "schedule": {
                "name": "test",
                "interval": "future",
                "start_time": str(datetime.now() + timedelta(minutes=1)),
            },
        }

        url = self.get_run_url()
        response = self.client.post(url, data, format="json", **self.header)
        self.assertHttpStatus(response, self.run_success_response_status)

        schedule = ScheduledJob.objects.last()
        self.assertEqual(schedule.kwargs["data"]["var4"], str(device_role.pk))

        return (response, schedule)  # so subclasses can do additional testing

    @override_settings(EXEMPT_VIEW_PERMISSIONS=["*"])
    @mock.patch("nautobot.extras.api.views.get_worker_count")
    def test_run_job_object_var_no_schedule(self, mock_get_worker_count):
        """
        Run a job with `approval_required` without providing a schedule.

        Assert an immediate schedule that enforces it.
        """
        # Set approval_required=True
        self.job_model.approval_required = True
        self.job_model.save()

        # Do the stuff.
        mock_get_worker_count.return_value = 1
        self.add_permissions("extras.run_job")
        device_role = DeviceRole.objects.create(name="role", slug="role")
        job_data = {
            "var1": "FooBar",
            "var2": 123,
            "var3": False,
            "var4": device_role.pk,
        }

        data = {
            "data": job_data,
            "commit": True,
            # schedule is omitted
        }

        url = self.get_run_url()
        response = self.client.post(url, data, format="json", **self.header)
        self.assertHttpStatus(response, self.run_success_response_status)

        # Assert that a JobResult was NOT created.
        self.assertFalse(JobResult.objects.exists())

        # Assert that we have an immediate ScheduledJob and that it matches the job_model.
        schedule = ScheduledJob.objects.last()
        self.assertIsNotNone(schedule)
        self.assertEqual(schedule.interval, JobExecutionType.TYPE_IMMEDIATELY)
        self.assertEqual(schedule.approval_required, self.job_model.approval_required)
        self.assertEqual(schedule.kwargs["data"]["var4"], str(device_role.pk))

        return (response, schedule)  # so subclasses can do additional testing

    @override_settings(EXEMPT_VIEW_PERMISSIONS=["*"])
    @mock.patch("nautobot.extras.api.views.get_worker_count")
    def test_run_job_object_var_lookup(self, mock_get_worker_count):
        """Job run requests can reference objects by their attributes."""
        mock_get_worker_count.return_value = 1
        self.add_permissions("extras.run_job")
        device_role = DeviceRole.objects.create(name="role", slug="role")
        job_data = {
            "var1": "FooBar",
            "var2": 123,
            "var3": False,
            "var4": {"name": "role"},
        }

        self.assertEqual(
            get_job("local/api_test_job/APITestJob").deserialize_data(job_data),
            {"var1": "FooBar", "var2": 123, "var3": False, "var4": device_role},
        )

        url = self.get_run_url()
        response = self.client.post(url, {"data": job_data}, format="json", **self.header)
        self.assertHttpStatus(response, self.run_success_response_status)

        job_result = JobResult.objects.last()
        self.assertIn("data", job_result.job_kwargs)
        self.assertEqual(job_result.job_kwargs["data"], job_data)

        return (response, job_result)  # so subclasses can do additional testing

    @override_settings(EXEMPT_VIEW_PERMISSIONS=["*"])
    @mock.patch("nautobot.extras.api.views.get_worker_count")
    def test_run_job_future(self, mock_get_worker_count):
        mock_get_worker_count.return_value = 1
        self.add_permissions("extras.run_job")
        d = DeviceRole.objects.create(name="role", slug="role")
        data = {
            "data": {"var1": "x", "var2": 1, "var3": False, "var4": d.pk},
            "commit": True,
            "schedule": {
                "start_time": str(datetime.now() + timedelta(minutes=1)),
                "interval": "future",
                "name": "test",
            },
        }

        url = self.get_run_url()
        response = self.client.post(url, data, format="json", **self.header)
        self.assertHttpStatus(response, self.run_success_response_status)

        schedule = ScheduledJob.objects.last()

        return (response, schedule)  # so subclasses can do additional testing

    @override_settings(EXEMPT_VIEW_PERMISSIONS=["*"])
    @mock.patch("nautobot.extras.api.views.get_worker_count")
    def test_run_a_job_with_sensitive_variables_for_future(self, mock_get_worker_count):
        mock_get_worker_count.return_value = 1
        self.add_permissions("extras.run_job")

        job_model = Job.objects.get(job_class_name="ExampleJob")
        job_model.enabled = True
        job_model.validated_save()

        url = reverse("extras-api:job-run", kwargs={"pk": job_model.pk})
        data = {
            "data": {},
            "commit": True,
            "schedule": {
                "start_time": str(datetime.now() + timedelta(minutes=1)),
                "interval": "future",
                "name": "test",
            },
        }

        # url = self.get_run_url()
        response = self.client.post(url, data, format="json", **self.header)
        self.assertHttpStatus(response, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            response.data["schedule"]["interval"][0],
            "Unable to schedule job: Job may have sensitive input variables",
        )

    @override_settings(EXEMPT_VIEW_PERMISSIONS=["*"])
    @mock.patch("nautobot.extras.api.views.get_worker_count")
    def test_run_a_job_with_sensitive_variables_and_requires_approval(self, mock_get_worker_count):
        mock_get_worker_count.return_value = 1
        self.add_permissions("extras.run_job")

        job_model = Job.objects.get(job_class_name="ExampleJob")
        job_model.enabled = True
        job_model.has_sensitive_variables = True
        job_model.approval_required = True
        job_model.save()

        url = reverse("extras-api:job-run", kwargs={"pk": job_model.pk})
        data = {
            "data": {},
            "commit": True,
            "schedule": {
                "interval": "immediately",
                "name": "test",
            },
        }

        response = self.client.post(url, data, format="json", **self.header)
        self.assertHttpStatus(response, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            response.data[0],
            "Unable to run or schedule job: "
            "This job is flagged as possibly having sensitive variables but is also flagged as requiring approval."
            "One of these two flags must be removed before this job can be scheduled or run.",
        )

    @override_settings(EXEMPT_VIEW_PERMISSIONS=["*"])
    @mock.patch("nautobot.extras.api.views.get_worker_count")
    def test_run_a_job_with_sensitive_variables_immediately(self, mock_get_worker_count):
        mock_get_worker_count.return_value = 1
        self.add_permissions("extras.run_job")
        d = DeviceRole.objects.create(name="role", slug="role")
        data = {
            "data": {"var1": "x", "var2": 1, "var3": False, "var4": d.pk},
            "commit": True,
            "schedule": {
                "interval": "immediately",
                "name": "test",
            },
        }
        job = Job.objects.get_for_class_path("local/api_test_job/APITestJob")
        job.has_sensitive_variables = True
        job.has_sensitive_variables_override = True
        job.validated_save()

        url = self.get_run_url()
        response = self.client.post(url, data, format="json", **self.header)
        self.assertHttpStatus(response, self.run_success_response_status)

        job_result = JobResult.objects.last()
        self.assertEqual(job_result.job_kwargs, None)

    @override_settings(EXEMPT_VIEW_PERMISSIONS=["*"])
    @mock.patch("nautobot.extras.api.views.get_worker_count")
    def test_run_job_future_past(self, mock_get_worker_count):
        mock_get_worker_count.return_value = 1
        self.add_permissions("extras.run_job")
        d = DeviceRole.objects.create(name="role", slug="role")
        data = {
            "data": {"var1": "x", "var2": 1, "var3": False, "var4": d.pk},
            "commit": True,
            "schedule": {
                "start_time": str(datetime.now() - timedelta(minutes=1)),
                "interval": "future",
                "name": "test",
            },
        }

        url = self.get_run_url()
        response = self.client.post(url, data, format="json", **self.header)
        self.assertHttpStatus(response, status.HTTP_400_BAD_REQUEST)

    @override_settings(EXEMPT_VIEW_PERMISSIONS=["*"])
    @mock.patch("nautobot.extras.api.views.get_worker_count")
    def test_run_job_interval(self, mock_get_worker_count):
        mock_get_worker_count.return_value = 1
        self.add_permissions("extras.run_job")
        d = DeviceRole.objects.create(name="role", slug="role")
        data = {
            "data": {"var1": "x", "var2": 1, "var3": False, "var4": d.pk},
            "commit": True,
            "schedule": {
                "start_time": str(datetime.now() + timedelta(minutes=1)),
                "interval": "hourly",
                "name": "test",
            },
        }

        url = self.get_run_url()
        response = self.client.post(url, data, format="json", **self.header)
        self.assertHttpStatus(response, self.run_success_response_status)

        schedule = ScheduledJob.objects.last()

        return (response, schedule)  # so subclasses can do additional testing

    @override_settings(EXEMPT_VIEW_PERMISSIONS=[])
    def test_run_job_with_invalid_data(self):
        self.add_permissions("extras.run_job")

        data = {
            "data": "invalid",
            "commit": True,
        }

        url = self.get_run_url()
        response = self.client.post(url, data, format="json", **self.header)
        self.assertHttpStatus(response, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data, {"errors": ["Job data needs to be a dict"]})

    @override_settings(EXEMPT_VIEW_PERMISSIONS=[])
    def test_run_job_with_wrong_data(self):
        self.add_permissions("extras.run_job")
        job_data = {
            "var1": "FooBar",
            "var2": 123,
            "var3": False,
            "var5": "wrong",
        }

        data = {
            "data": job_data,
            "commit": True,
        }

        url = self.get_run_url()
        response = self.client.post(url, data, format="json", **self.header)
        self.assertHttpStatus(response, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data, {"errors": {"var5": ["Job data contained an unknown property"]}})

    @override_settings(EXEMPT_VIEW_PERMISSIONS=[])
    def test_run_job_with_missing_data(self):
        self.add_permissions("extras.run_job")

        job_data = {
            "var1": "FooBar",
            "var3": False,
        }

        data = {
            "data": job_data,
            "commit": True,
        }

        url = self.get_run_url()
        response = self.client.post(url, data, format="json", **self.header)
        self.assertHttpStatus(response, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            response.data, {"errors": {"var2": ["This field is required."], "var4": ["This field is required."]}}
        )

    @override_settings(EXEMPT_VIEW_PERMISSIONS=[])
    def test_run_job_with_invalid_task_queue(self):
        self.add_permissions("extras.run_job")
        d = DeviceRole.objects.create(name="role", slug="role")
        data = {
            "data": {"var1": "x", "var2": 1, "var3": False, "var4": d.pk},
            "commit": True,
            "task_queue": "invalid",
        }

        url = self.get_run_url()
        response = self.client.post(url, data, format="json", **self.header)
        self.assertHttpStatus(response, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            response.data,
            {"task_queue": ['"invalid" is not a valid choice.']},
        )

    @override_settings(EXEMPT_VIEW_PERMISSIONS=[])
    @mock.patch("nautobot.extras.api.views.get_worker_count", return_value=1)
    def test_run_job_with_valid_task_queue(self, _):
        self.add_permissions("extras.run_job")
        d = DeviceRole.objects.create(name="role", slug="role")
        data = {
            "data": {"var1": "x", "var2": 1, "var3": False, "var4": d.pk},
            "commit": True,
            "task_queue": settings.CELERY_TASK_DEFAULT_QUEUE,
        }

        url = self.get_run_url()
        response = self.client.post(url, data, format="json", **self.header)
        self.assertHttpStatus(response, self.run_success_response_status)

    @override_settings(EXEMPT_VIEW_PERMISSIONS=[])
    @mock.patch("nautobot.extras.api.views.get_worker_count", return_value=1)
    def test_run_job_with_default_queue_with_empty_job_model_task_queues(self, _):
        self.add_permissions("extras.run_job")
        data = {
            "commit": True,
            "task_queue": settings.CELERY_TASK_DEFAULT_QUEUE,
        }

        job_model = Job.objects.get_for_class_path("local/test_pass/TestPass")
        job_model.enabled = True
        job_model.validated_save()
        url = self.get_run_url("local/test_pass/TestPass")
        response = self.client.post(url, data, format="json", **self.header)
        self.assertHttpStatus(response, self.run_success_response_status)


class JobHookTest(APIViewTestCases.APIViewTestCase):

    model = JobHook
    brief_fields = ["display", "id", "name", "url"]
    choices_fields = []
    update_data = {
        "name": "Overridden name",
        "enabled": False,
        "type_create": True,
        "type_update": True,
        "type_delete": False,
    }
    bulk_update_data = {
        "enabled": False,
        "type_create": True,
        "type_update": True,
        "type_delete": False,
    }
    validation_excluded_fields = []
    api_version = "1.3"

    @classmethod
    def setUpTestData(cls):
        cls.create_data = [
            {
                "name": "JobHook4",
                "content_types": ["dcim.consoleport"],
                "type_delete": True,
                "job": Job.objects.get(job_class_name="TestJobHookReceiverLog").pk,
                "enabled": False,
            },
            {
                "name": "JobHook5",
                "content_types": ["dcim.consoleport"],
                "type_delete": True,
                "job": Job.objects.get(job_class_name="TestJobHookReceiverChange").pk,
                "enabled": False,
            },
            {
                "name": "JobHook6",
                "content_types": ["dcim.consoleport"],
                "type_delete": True,
                "job": Job.objects.get(job_class_name="TestJobHookReceiverFail").pk,
                "enabled": False,
            },
        ]
        cls.job_hooks = (
            JobHook(
                name="JobHook1",
                type_create=True,
                job=Job.objects.get(job_class_name="TestJobHookReceiverLog"),
                type_delete=True,
            ),
            JobHook(
                name="JobHook2",
                type_create=True,
                job=Job.objects.get(job_class_name="TestJobHookReceiverChange"),
                type_delete=True,
            ),
            JobHook(
                name="JobHook3",
                type_create=True,
                job=Job.objects.get(job_class_name="TestJobHookReceiverFail"),
                type_delete=True,
            ),
        )

        obj_type = ContentType.objects.get_for_model(DeviceType)

        for job_hook in cls.job_hooks:
            job_hook.save()
            job_hook.content_types.set([obj_type])

    def test_validate_post(self):
        """POST a job hook with values that duplicate another job hook"""

        data = {
            "name": "JobHook4",
            "content_types": ["dcim.devicetype"],
            "job": Job.objects.get(job_class_name="TestJobHookReceiverLog").pk,
            "type_create": False,
            "type_delete": True,
        }

        self.add_permissions("extras.add_jobhook")
        response = self.client.post(self._get_list_url(), data, format="json", **self.header)
        self.assertContains(
            response,
            "A job hook already exists for delete on dcim | device type to job TestJobHookReceiverLog",
            status_code=400,
        )

    def test_validate_patch(self):
        """PATCH an existing job hook with values that duplicate another job hook"""

        data = {
            "job": Job.objects.get(job_class_name="TestJobHookReceiverLog").pk,
            "type_delete": True,
        }

        self.add_permissions("extras.change_jobhook")
        job_hook2 = JobHook.objects.get(name="JobHook2")
        response = self.client.patch(self._get_detail_url(job_hook2), data, format="json", **self.header)
        self.assertContains(
            response,
            "A job hook already exists for delete on dcim | device type to job TestJobHookReceiverLog",
            status_code=400,
        )


class JobTestVersion13(
    JobAPIRunTestMixin,
    # note no CreateObjectViewTestCase - we do not support user creation of Job records
    APIViewTestCases.GetObjectViewTestCase,
    APIViewTestCases.ListObjectsViewTestCase,
    APIViewTestCases.UpdateObjectViewTestCase,
    APIViewTestCases.DeleteObjectViewTestCase,
):
    """Test cases for the Jobs REST API under API version 1.3 - first version introducing JobModel-based APIs."""

    model = Job
    brief_fields = ["display", "grouping", "id", "job_class_name", "module_name", "name", "slug", "source", "url"]
    choices_fields = None
    update_data = {
        # source, module_name, job_class_name, installed are NOT editable
        "grouping_override": True,
        "grouping": "Overridden grouping",
        "name_override": True,
        "name": "Overridden name",
        "slug": "overridden-slug",
        "description_override": True,
        "description": "This is an overridden description.",
        "enabled": True,
        "approval_required_override": True,
        "approval_required": True,
        "commit_default_override": True,
        "commit_default": False,
        "hidden_override": True,
        "hidden": True,
        "read_only_override": True,
        "read_only": True,
        "soft_time_limit_override": True,
        "soft_time_limit": 350.1,
        "time_limit_override": True,
        "time_limit": 650,
        "has_sensitive_variables": False,
        "has_sensitive_variables_override": True,
        "task_queues": ["default", "priority"],
        "task_queues_override": True,
    }
    bulk_update_data = {
        "enabled": True,
        "approval_required_override": True,
        "approval_required": True,
        "has_sensitive_variables": False,
        "has_sensitive_variables_override": True,
    }
    validation_excluded_fields = []

    run_success_response_status = status.HTTP_201_CREATED
    api_version = "1.3"

    def get_run_url(self, class_path="local/api_test_job/APITestJob"):
        job_model = Job.objects.get_for_class_path(class_path)
        return reverse("extras-api:job-run", kwargs={"pk": job_model.pk})

    def test_get_job_variables(self):
        """Test the job/<pk>/variables API endpoint."""
        self.add_permissions("extras.view_job")
        route = get_route_for_model(self.model, "variables", api=True)
        response = self.client.get(reverse(route, kwargs={"pk": self.job_model.pk}), **self.header)
        self.assertEqual(4, len(response.data))  # 4 variables, in order
        self.assertEqual(response.data[0], {"name": "var1", "type": "StringVar", "required": True})
        self.assertEqual(response.data[1], {"name": "var2", "type": "IntegerVar", "required": True})
        self.assertEqual(response.data[2], {"name": "var3", "type": "BooleanVar", "required": False})
        self.assertEqual(
            response.data[3],
            {"name": "var4", "type": "ObjectVar", "required": True, "model": "dcim.devicerole"},
        )

    @override_settings(EXEMPT_VIEW_PERMISSIONS=["*"])
    def test_update_job_with_sensitive_variables_set_approval_required_to_true(self):
        job_model = Job.objects.get_for_class_path("local/api_test_job/APITestJob")
        job_model.has_sensitive_variables = True
        job_model.has_sensitive_variables_override = True
        job_model.validated_save()

        url = self._get_detail_url(job_model)
        data = {
            "approval_required_override": True,
            "approval_required": True,
        }

        self.add_permissions("extras.change_job")

        response = self.client.patch(url, data, format="json", **self.header)
        self.assertHttpStatus(response, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            response.data["approval_required"][0],
            "A job with sensitive variables cannot also be marked as requiring approval",
        )

    @override_settings(EXEMPT_VIEW_PERMISSIONS=["*"])
    def test_update_approval_required_job_set_has_sensitive_variables_to_true(self):
        job_model = Job.objects.get_for_class_path("local/api_test_job/APITestJob")
        job_model.approval_required = True
        job_model.approval_required_override = True
        job_model.validated_save()

        url = self._get_detail_url(job_model)
        data = {
            "has_sensitive_variables": True,
            "has_sensitive_variables_override": True,
        }

        self.add_permissions("extras.change_job")

        response = self.client.patch(url, data, format="json", **self.header)
        self.assertHttpStatus(response, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            response.data["has_sensitive_variables"][0],
            "A job with sensitive variables cannot also be marked as requiring approval",
        )

    @override_settings(EXEMPT_VIEW_PERMISSIONS=["*"])
    def test_run_job_object_var(self):  # pylint: disable=arguments-differ
        """In addition to the base test case provided by JobAPIRunTestMixin, also verify the JSON response data."""
        response, schedule = super().test_run_job_object_var()

        self.assertIn("schedule", response.data)
        self.assertIn("job_result", response.data)
        self.assertEqual(response.data["schedule"]["id"], str(schedule.pk))
        self.assertEqual(
            response.data["schedule"]["url"],
            "http://testserver" + reverse("extras-api:scheduledjob-detail", kwargs={"pk": schedule.pk}),
        )
        self.assertEqual(response.data["schedule"]["name"], schedule.name)
        self.assertEqual(response.data["schedule"]["start_time"], schedule.start_time)
        self.assertEqual(response.data["schedule"]["interval"], schedule.interval)
        self.assertIsNone(response.data["job_result"])

    @override_settings(EXEMPT_VIEW_PERMISSIONS=["*"])
    def test_run_job_object_var_lookup(self):  # pylint: disable=arguments-differ
        """In addition to the base test case provided by JobAPIRunTestMixin, also verify the JSON response data."""
        response, job_result = super().test_run_job_object_var_lookup()

        self.assertIn("schedule", response.data)
        self.assertIn("job_result", response.data)
        self.assertIsNone(response.data["schedule"])
        # The urls in a NestedJobResultSerializer depends on the request context, which we don't have
        data_job_result = response.data["job_result"]
        del data_job_result["url"]
        del data_job_result["user"]["url"]
        expected_data_job_result = NestedJobResultSerializer(job_result, context={"request": None}).data
        del expected_data_job_result["url"]
        del expected_data_job_result["user"]["url"]
        self.assertEqual(data_job_result, expected_data_job_result)

    @override_settings(EXEMPT_VIEW_PERMISSIONS=["*"])
    def test_run_job_future(self):  # pylint: disable=arguments-differ
        """In addition to the base test case provided by JobAPIRunTestMixin, also verify the JSON response data."""
        response, schedule = super().test_run_job_future()

        self.assertIn("schedule", response.data)
        self.assertIn("job_result", response.data)
        self.assertEqual(response.data["schedule"]["id"], str(schedule.pk))
        self.assertEqual(
            response.data["schedule"]["url"],
            "http://testserver" + reverse("extras-api:scheduledjob-detail", kwargs={"pk": schedule.pk}),
        )
        self.assertEqual(response.data["schedule"]["name"], schedule.name)
        self.assertEqual(response.data["schedule"]["start_time"], schedule.start_time)
        self.assertEqual(response.data["schedule"]["interval"], schedule.interval)
        self.assertIsNone(response.data["job_result"])

    @override_settings(EXEMPT_VIEW_PERMISSIONS=["*"])
    def test_run_job_future_schedule_kwargs_pk(self):
        """In addition to the base test case provided by JobAPIRunTestMixin, also verify that kwargs['scheduled_job_pk'] was set in the scheduled job."""
        _, schedule = super().test_run_job_future()

        self.assertEqual(schedule.kwargs["scheduled_job_pk"], str(schedule.pk))

    @override_settings(EXEMPT_VIEW_PERMISSIONS=["*"])
    def test_run_job_interval(self):  # pylint: disable=arguments-differ
        """In addition to the base test case provided by JobAPIRunTestMixin, also verify the JSON response data."""
        response, schedule = super().test_run_job_interval()

        self.assertIn("schedule", response.data)
        self.assertIn("job_result", response.data)
        self.assertEqual(response.data["schedule"]["id"], str(schedule.pk))
        self.assertEqual(
            response.data["schedule"]["url"],
            "http://testserver" + reverse("extras-api:scheduledjob-detail", kwargs={"pk": schedule.pk}),
        )
        self.assertEqual(response.data["schedule"]["name"], schedule.name)
        self.assertEqual(response.data["schedule"]["start_time"], schedule.start_time)
        self.assertEqual(response.data["schedule"]["interval"], schedule.interval)
        self.assertIsNone(response.data["job_result"])


class JobTestVersion12(
    JobAPIRunTestMixin,
    APITestCase,
):
    """Test cases for the Jobs REST API under API version 1.2 - deprecated JobClass-based API pattern."""

    run_success_response_status = status.HTTP_200_OK
    api_version = "1.2"

    def get_run_url(self, class_path="local/api_test_job/APITestJob"):
        return reverse("extras-api:job-run", kwargs={"class_path": class_path})

    @override_settings(EXEMPT_VIEW_PERMISSIONS=["*"])
    def test_list_jobs_anonymous(self):
        url = reverse("extras-api:job-list")
        response = self.client.get(url, **self.header)
        self.assertHttpStatus(response, status.HTTP_200_OK)

    @override_settings(EXEMPT_VIEW_PERMISSIONS=[])
    def test_list_jobs_without_permission(self):
        url = reverse("extras-api:job-list")
        with disable_warnings("django.request"):
            response = self.client.get(url, **self.header)
        self.assertHttpStatus(response, status.HTTP_403_FORBIDDEN)

    @override_settings(EXEMPT_VIEW_PERMISSIONS=[])
    def test_list_jobs_with_permission(self):
        self.add_permissions("extras.view_job")
        url = reverse("extras-api:job-list")
        response = self.client.get(url, **self.header)

        self.assertHttpStatus(response, status.HTTP_200_OK)
        # At a minimum, the job provided by the example plugin should be present
        self.assertNotEqual(response.data, [])
        self.assertIn(
            "plugins/example_plugin.jobs/ExampleJob",
            [job["id"] for job in response.data],
        )

    @override_settings(EXEMPT_VIEW_PERMISSIONS=["*"])
    def test_get_job_anonymous(self):
        url = reverse("extras-api:job-detail", kwargs={"class_path": "local/api_test_job/APITestJob"})
        response = self.client.get(url, **self.header)
        self.assertHttpStatus(response, status.HTTP_200_OK)

    @override_settings(EXEMPT_VIEW_PERMISSIONS=[])
    def test_get_job_without_permission(self):
        url = reverse("extras-api:job-detail", kwargs={"class_path": "local/api_test_job/APITestJob"})
        with disable_warnings("django.request"):
            response = self.client.get(url, **self.header)
        self.assertHttpStatus(response, status.HTTP_403_FORBIDDEN)

    @override_settings(EXEMPT_VIEW_PERMISSIONS=[])
    def test_get_job_with_permission(self):
        self.add_permissions("extras.view_job")
        # Try GET to permitted object
        url = reverse("extras-api:job-detail", kwargs={"class_path": "local/api_test_job/APITestJob"})
        response = self.client.get(url, **self.header)

        self.assertHttpStatus(response, status.HTTP_200_OK)
        self.assertEqual(response.data["name"], "Job for API Tests")
        self.assertEqual(response.data["vars"]["var1"], "StringVar")
        self.assertEqual(response.data["vars"]["var2"], "IntegerVar")
        self.assertEqual(response.data["vars"]["var3"], "BooleanVar")

        # Try GET to non-existent object
        url = reverse("extras-api:job-detail", kwargs={"class_path": "local/api_test_job/NoSuchJob"})
        response = self.client.get(url, **self.header)
        self.assertHttpStatus(response, status.HTTP_404_NOT_FOUND)


class JobTestVersionDefault(JobTestVersion12):
    """
    Test cases for the Jobs REST API when not explicitly requesting a specific API version.

    Currently we default to version 1.2, but this may change in a future major release.
    """

    api_version = None


class JobResultTest(
    APIViewTestCases.GetObjectViewTestCase,
    APIViewTestCases.ListObjectsViewTestCase,
    APIViewTestCases.DeleteObjectViewTestCase,
):
    model = JobResult
    brief_fields = ["completed", "created", "display", "id", "name", "status", "url", "user"]

    @classmethod
    def setUpTestData(cls):
        jobs = Job.objects.all()[:2]
        job_ct = ContentType.objects.get_for_model(Job)
        git_ct = ContentType.objects.get_for_model(GitRepository)

        JobResult.objects.create(
            job_model=jobs[0],
            name=jobs[0].class_path,
            obj_type=job_ct,
            completed=datetime.now(),
            user=None,
            status=JobResultStatusChoices.STATUS_COMPLETED,
            data={"output": "\nRan for 3 seconds"},
            job_kwargs=None,
            schedule=None,
            job_id=uuid.uuid4(),
        )
        JobResult.objects.create(
            job_model=None,
            name="Git Repository",
            obj_type=git_ct,
            completed=datetime.now(),
            user=None,
            status=JobResultStatusChoices.STATUS_COMPLETED,
            data=None,
            job_kwargs={"repository_pk": uuid.uuid4()},
            schedule=None,
            job_id=uuid.uuid4(),
        )
        JobResult.objects.create(
            job_model=jobs[1],
            name=jobs[1].class_path,
            obj_type=job_ct,
            completed=None,
            user=None,
            status=JobResultStatusChoices.STATUS_PENDING,
            data=None,
            job_kwargs={"data": {"device": uuid.uuid4(), "multichoices": ["red", "green"], "checkbox": False}},
            schedule=None,
            job_id=uuid.uuid4(),
        )


class JobLogEntryTest(
    APIViewTestCases.GetObjectViewTestCase,
    APIViewTestCases.ListObjectsViewTestCase,
):
    model = JobLogEntry
    brief_fields = [
        "absolute_url",
        "created",
        "display",
        "grouping",
        "id",
        "job_result",
        "log_level",
        "log_object",
        "message",
        "url",
    ]
    choices_fields = []

    @classmethod
    def setUpTestData(cls):
        cls.job_result = JobResult.objects.create(
            name="test",
            job_id=uuid.uuid4(),
            obj_type=ContentType.objects.get_for_model(GitRepository),
        )

        for log_level in ("debug", "info", "success", "warning"):
            JobLogEntry.objects.create(
                log_level=log_level,
                grouping="run",
                job_result=cls.job_result,
                message=f"I am a {log_level} log.",
            )

    def test_list_job_logs_from_job_results_detail(self):
        """Test `logs` endpoint from `JobResult` detail."""
        self.add_permissions("extras.view_jobresult")
        url = reverse("extras-api:jobresult-logs", kwargs={"pk": self.job_result.pk})
        response = self.client.get(url, **self.header)
        self.assertEqual(len(response.json()), JobLogEntry.objects.count())


class ScheduledJobTest(
    APIViewTestCases.GetObjectViewTestCase,
    APIViewTestCases.ListObjectsViewTestCase,
):
    model = ScheduledJob
    brief_fields = ["crontab", "display", "id", "interval", "name", "start_time", "url"]
    choices_fields = []

    @classmethod
    def setUpTestData(cls):
        user = User.objects.create(username="user1", is_active=True)
        job_model = Job.objects.get_for_class_path("local/test_pass/TestPass")
        ScheduledJob.objects.create(
            name="test1",
            task="nautobot.extras.jobs.scheduled_job_handler",
            job_class=job_model.class_path,
            job_model=job_model,
            interval=JobExecutionType.TYPE_IMMEDIATELY,
            user=user,
            approval_required=True,
            start_time=now(),
        )
        ScheduledJob.objects.create(
            name="test2",
            task="nautobot.extras.jobs.scheduled_job_handler",
            job_class=job_model.class_path,
            job_model=job_model,
            interval=JobExecutionType.TYPE_IMMEDIATELY,
            user=user,
            approval_required=True,
            start_time=now(),
        )
        ScheduledJob.objects.create(
            name="test3",
            task="nautobot.extras.jobs.scheduled_job_handler",
            job_class=job_model.class_path,
            job_model=job_model,
            interval=JobExecutionType.TYPE_IMMEDIATELY,
            user=user,
            approval_required=True,
            start_time=now(),
        )


class JobApprovalTest(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.additional_user = User.objects.create(username="user1", is_active=True)
        cls.job_model = Job.objects.get_for_class_path("local/test_pass/TestPass")
        cls.job_model.enabled = True
        cls.job_model.save()
        cls.scheduled_job = ScheduledJob.objects.create(
            name="test",
            task="nautobot.extras.jobs.scheduled_job_handler",
            job_class=cls.job_model.class_path,
            job_model=cls.job_model,
            interval=JobExecutionType.TYPE_IMMEDIATELY,
            user=cls.additional_user,
            approval_required=True,
            start_time=now(),
        )

    @override_settings(EXEMPT_VIEW_PERMISSIONS=["*"])
    def test_approve_job_anonymous(self):
        url = reverse("extras-api:scheduledjob-approve", kwargs={"pk": self.scheduled_job.pk})
        response = self.client.post(url)
        self.assertHttpStatus(response, status.HTTP_403_FORBIDDEN)

    @override_settings(EXEMPT_VIEW_PERMISSIONS=["*"])
    def test_approve_job_without_permission(self):
        url = reverse("extras-api:scheduledjob-approve", kwargs={"pk": self.scheduled_job.pk})
        with disable_warnings("django.request"):
            response = self.client.post(url, **self.header)
        self.assertHttpStatus(response, status.HTTP_403_FORBIDDEN)

    @override_settings(EXEMPT_VIEW_PERMISSIONS=["*"])
    def test_approve_job_without_approve_job_permission(self):
        self.add_permissions("extras.view_scheduledjob", "extras.change_scheduledjob")
        url = reverse("extras-api:scheduledjob-approve", kwargs={"pk": self.scheduled_job.pk})
        response = self.client.post(url, **self.header)
        self.assertHttpStatus(response, status.HTTP_403_FORBIDDEN)

    @override_settings(EXEMPT_VIEW_PERMISSIONS=["*"])
    def test_approve_job_without_change_scheduledjob_permission(self):
        self.add_permissions("extras.approve_job", "extras.view_scheduledjob")
        url = reverse("extras-api:scheduledjob-approve", kwargs={"pk": self.scheduled_job.pk})
        response = self.client.post(url, **self.header)
        self.assertHttpStatus(response, status.HTTP_403_FORBIDDEN)

    @override_settings(EXEMPT_VIEW_PERMISSIONS=["*"])
    def test_approve_job_same_user(self):
        self.add_permissions("extras.approve_job", "extras.view_scheduledjob", "extras.change_scheduledjob")
        scheduled_job = ScheduledJob.objects.create(
            name="test",
            task="nautobot.extras.jobs.scheduled_job_handler",
            job_class=self.job_model.class_path,
            job_model=self.job_model,
            interval=JobExecutionType.TYPE_IMMEDIATELY,
            user=self.user,
            approval_required=True,
            start_time=now(),
        )
        url = reverse("extras-api:scheduledjob-approve", kwargs={"pk": scheduled_job.pk})
        response = self.client.post(url, **self.header)
        self.assertHttpStatus(response, status.HTTP_403_FORBIDDEN)

    @override_settings(EXEMPT_VIEW_PERMISSIONS=["*"])
    def test_approve_job(self):
        self.add_permissions("extras.approve_job", "extras.view_scheduledjob", "extras.change_scheduledjob")
        url = reverse("extras-api:scheduledjob-approve", kwargs={"pk": self.scheduled_job.pk})
        response = self.client.post(url, **self.header)
        self.assertHttpStatus(response, status.HTTP_200_OK)

    @override_settings(EXEMPT_VIEW_PERMISSIONS=["*"])
    def test_approve_job_in_past(self):
        self.add_permissions("extras.approve_job", "extras.view_scheduledjob", "extras.change_scheduledjob")
        scheduled_job = ScheduledJob.objects.create(
            name="test",
            task="nautobot.extras.jobs.scheduled_job_handler",
            job_class=self.job_model.class_path,
            job_model=self.job_model,
            interval=JobExecutionType.TYPE_FUTURE,
            one_off=True,
            user=self.additional_user,
            approval_required=True,
            start_time=now(),
        )
        url = reverse("extras-api:scheduledjob-approve", kwargs={"pk": scheduled_job.pk})
        response = self.client.post(url, **self.header)
        self.assertHttpStatus(response, status.HTTP_400_BAD_REQUEST)

    @override_settings(EXEMPT_VIEW_PERMISSIONS=["*"])
    def test_approve_job_in_past_force(self):
        self.add_permissions("extras.approve_job", "extras.view_scheduledjob", "extras.change_scheduledjob")
        scheduled_job = ScheduledJob.objects.create(
            name="test",
            task="nautobot.extras.jobs.scheduled_job_handler",
            job_class=self.job_model.class_path,
            job_model=self.job_model,
            interval=JobExecutionType.TYPE_FUTURE,
            one_off=True,
            user=self.additional_user,
            approval_required=True,
            start_time=now(),
        )
        url = reverse("extras-api:scheduledjob-approve", kwargs={"pk": scheduled_job.pk})
        response = self.client.post(url + "?force=true", **self.header)
        self.assertHttpStatus(response, status.HTTP_200_OK)

    @override_settings(EXEMPT_VIEW_PERMISSIONS=["*"])
    def test_deny_job_without_permission(self):
        url = reverse("extras-api:scheduledjob-deny", kwargs={"pk": self.scheduled_job.pk})
        with disable_warnings("django.request"):
            response = self.client.post(url, **self.header)
        self.assertHttpStatus(response, status.HTTP_403_FORBIDDEN)

    @override_settings(EXEMPT_VIEW_PERMISSIONS=["*"])
    def test_deny_job_without_approve_job_permission(self):
        self.add_permissions("extras.view_scheduledjob", "extras.delete_scheduledjob")
        url = reverse("extras-api:scheduledjob-deny", kwargs={"pk": self.scheduled_job.pk})
        response = self.client.post(url, **self.header)
        self.assertHttpStatus(response, status.HTTP_403_FORBIDDEN)

    @override_settings(EXEMPT_VIEW_PERMISSIONS=["*"])
    def test_deny_job_without_delete_scheduledjob_permission(self):
        self.add_permissions("extras.approve_job", "extras.view_scheduledjob")
        url = reverse("extras-api:scheduledjob-deny", kwargs={"pk": self.scheduled_job.pk})
        response = self.client.post(url, **self.header)
        self.assertHttpStatus(response, status.HTTP_403_FORBIDDEN)

    @override_settings(EXEMPT_VIEW_PERMISSIONS=["*"])
    def test_deny_job(self):
        self.add_permissions("extras.approve_job", "extras.view_scheduledjob", "extras.delete_scheduledjob")
        url = reverse("extras-api:scheduledjob-deny", kwargs={"pk": self.scheduled_job.pk})
        response = self.client.post(url, **self.header)
        self.assertHttpStatus(response, status.HTTP_200_OK)
        self.assertIsNone(ScheduledJob.objects.filter(pk=self.scheduled_job.pk).first())

    @override_settings(EXEMPT_VIEW_PERMISSIONS=[])
    def test_dry_run_job_without_permission(self):
        url = reverse("extras-api:scheduledjob-dry-run", kwargs={"pk": self.scheduled_job.pk})
        with disable_warnings("django.request"):
            response = self.client.post(url, **self.header)
        self.assertHttpStatus(response, status.HTTP_403_FORBIDDEN)

    @override_settings(EXEMPT_VIEW_PERMISSIONS=["*"])
    def test_dry_run_job_without_run_job_permission(self):
        self.add_permissions("extras.view_scheduledjob")
        url = reverse("extras-api:scheduledjob-dry-run", kwargs={"pk": self.scheduled_job.pk})
        response = self.client.post(url, **self.header)
        self.assertHttpStatus(response, status.HTTP_403_FORBIDDEN)

    @override_settings(EXEMPT_VIEW_PERMISSIONS=["*"])
    def test_dry_run_job(self):
        self.add_permissions("extras.run_job", "extras.view_scheduledjob")
        url = reverse("extras-api:scheduledjob-dry-run", kwargs={"pk": self.scheduled_job.pk})
        response = self.client.post(url, **self.header)
        self.assertHttpStatus(response, status.HTTP_200_OK)


class NoteTest(APIViewTestCases.APIViewTestCase):
    model = Note
    brief_fields = [
        "assigned_object",
        "display",
        "id",
        "note",
        "slug",
        "url",
        "user",
    ]
    choices_fields = ["assigned_object_type"]

    @classmethod
    def setUpTestData(cls):
        site1 = Site.objects.create(name="Site 1", slug="site-1")
        site2 = Site.objects.create(name="Site 2", slug="site-2")
        ct = ContentType.objects.get_for_model(Site)
        user1 = User.objects.create(username="user1", is_active=True)
        user2 = User.objects.create(username="user2", is_active=True)

        cls.create_data = [
            {
                "note": "This is a test.",
                "assigned_object_id": site1.pk,
                "assigned_object_type": f"{ct._meta.app_label}.{ct._meta.model_name}",
            },
            {
                "note": "This is a test.",
                "assigned_object_id": site2.pk,
                "assigned_object_type": f"{ct._meta.app_label}.{ct._meta.model_name}",
            },
            {
                "note": "This is a note on Site 1.",
                "assigned_object_id": site1.pk,
                "assigned_object_type": f"{ct._meta.app_label}.{ct._meta.model_name}",
            },
        ]
        cls.bulk_update_data = {
            "note": "Bulk change.",
        }
        Note.objects.create(
            note="Site has been placed on maintenance.",
            user=user1,
            assigned_object_type=ct,
            assigned_object_id=site1.pk,
        )
        Note.objects.create(
            note="Site maintenance has ended.",
            user=user1,
            assigned_object_type=ct,
            assigned_object_id=site1.pk,
        )
        Note.objects.create(
            note="Site is under duress.",
            user=user2,
            assigned_object_type=ct,
            assigned_object_id=site2.pk,
        )


class RelationshipTest(APIViewTestCases.APIViewTestCase, RequiredRelationshipTestMixin):
    model = Relationship
    brief_fields = ["display", "id", "name", "slug", "url"]

    create_data = [
        {
            "name": "Device VLANs",
            "slug": "device-vlans",
            "type": "many-to-many",
            "source_type": "ipam.vlan",
            "destination_type": "dcim.device",
        },
        {
            "name": "Primary VLAN",
            "slug": "primary-vlan",
            "type": "one-to-many",
            "source_type": "ipam.vlan",
            "destination_type": "dcim.device",
        },
        {
            "name": "Primary Interface",
            "slug": "primary-interface",
            "type": "one-to-one",
            "source_type": "dcim.device",
            "source_label": "primary interface",
            "destination_type": "dcim.interface",
            "destination_hidden": True,
        },
        {
            "name": "Relationship 1",
            "type": "one-to-one",
            "source_type": "dcim.device",
            "source_label": "primary interface",
            "destination_type": "dcim.interface",
            "destination_hidden": True,
        },
    ]

    bulk_update_data = {
        "source_filter": {"slug": ["some-slug"]},
    }
    choices_fields = ["destination_type", "source_type", "type", "required_on"]
    slug_source = "name"
    slugify_function = staticmethod(slugify_dashes_to_underscores)

    @classmethod
    def setUpTestData(cls):
        site_type = ContentType.objects.get_for_model(Site)
        device_type = ContentType.objects.get_for_model(Device)

        cls.relationships = (
            Relationship(
                name="Related Sites",
                slug="related-sites",
                type="symmetric-many-to-many",
                source_type=site_type,
                destination_type=site_type,
            ),
            Relationship(
                name="Unrelated Sites",
                slug="unrelated-sites",
                type="many-to-many",
                source_type=site_type,
                source_label="Other sites (from source side)",
                destination_type=site_type,
                destination_label="Other sites (from destination side)",
            ),
            Relationship(
                name="Devices found elsewhere",
                slug="devices-elsewhere",
                type="many-to-many",
                source_type=site_type,
                destination_type=device_type,
            ),
        )
        for relationship in cls.relationships:
            relationship.validated_save()

        cls.site = Site.objects.create(name="Site 1", status=Status.objects.get(slug="active"))

    def test_get_all_relationships_on_site(self):
        """Verify that all relationships are accurately represented when requested."""
        self.add_permissions("dcim.view_site")
        response = self.client.get(
            reverse("dcim-api:site-detail", kwargs={"pk": self.site.pk}) + "?include=relationships", **self.header
        )
        self.assertHttpStatus(response, status.HTTP_200_OK)
        self.assertIn("relationships", response.data)
        self.assertIsInstance(response.data["relationships"], dict)
        self.maxDiff = None
        self.assertEqual(
            {
                self.relationships[0].slug: {
                    "id": str(self.relationships[0].pk),
                    "url": (
                        "http://testserver"
                        + reverse("extras-api:relationship-detail", kwargs={"pk": self.relationships[0].pk})
                    ),
                    "name": self.relationships[0].name,
                    "type": self.relationships[0].type,
                    "peer": {
                        "label": "sites",
                        "object_type": "dcim.site",
                        "objects": [],
                    },
                },
                self.relationships[1].slug: {
                    "id": str(self.relationships[1].pk),
                    "url": (
                        "http://testserver"
                        + reverse("extras-api:relationship-detail", kwargs={"pk": self.relationships[1].pk})
                    ),
                    "name": self.relationships[1].name,
                    "type": self.relationships[1].type,
                    "destination": {
                        "label": self.relationships[1].source_label,  # yes -- it's a bit confusing
                        "object_type": "dcim.site",
                        "objects": [],
                    },
                    "source": {
                        "label": self.relationships[1].destination_label,  # yes -- it's a bit confusing
                        "object_type": "dcim.site",
                        "objects": [],
                    },
                },
                self.relationships[2].slug: {
                    "id": str(self.relationships[2].pk),
                    "url": (
                        "http://testserver"
                        + reverse("extras-api:relationship-detail", kwargs={"pk": self.relationships[2].pk})
                    ),
                    "name": self.relationships[2].name,
                    "type": self.relationships[2].type,
                    "destination": {
                        "label": "devices",
                        "object_type": "dcim.device",
                        "objects": [],
                    },
                },
            },
            response.data["relationships"],
        )

    def test_populate_relationship_associations_on_site_create(self):
        """Verify that relationship associations can be populated at instance creation time."""
        existing_site_1 = Site.objects.create(name="Existing Site 1", status=Status.objects.get(slug="active"))
        existing_site_2 = Site.objects.create(name="Existing Site 2", status=Status.objects.get(slug="active"))
        manufacturer = Manufacturer.objects.create(name="Manufacturer 1", slug="manufacturer-1")
        device_type = DeviceType.objects.create(
            manufacturer=manufacturer,
            model="device Type 1",
            slug="device-type-1",
        )
        device_role = DeviceRole.objects.create(name="Device Role 1", slug="device-role-1", color="ff0000")
        existing_device_1 = Device.objects.create(
            name="existing-device-site-1",
            status=Status.objects.get(slug="active"),
            device_role=device_role,
            device_type=device_type,
            site=existing_site_1,
        )
        existing_device_2 = Device.objects.create(
            name="existing-device-site-2",
            status=Status.objects.get(slug="active"),
            device_role=device_role,
            device_type=device_type,
            site=existing_site_2,
        )

        self.add_permissions("dcim.view_site", "dcim.add_site", "extras.add_relationshipassociation")
        response = self.client.post(
            reverse("dcim-api:site-list"),
            data={
                "name": "New Site",
                "status": "active",
                "relationships": {
                    self.relationships[0].slug: {
                        "peer": {
                            "objects": [str(existing_site_1.pk)],
                        },
                    },
                    self.relationships[1].slug: {
                        "source": {
                            "objects": [str(existing_site_2.pk)],
                        },
                    },
                    self.relationships[2].slug: {
                        "destination": {
                            "objects": [
                                {"name": "existing-device-site-1"},
                                {"name": "existing-device-site-2"},
                            ],
                        },
                    },
                },
            },
            format="json",
            **self.header,
        )
        self.assertHttpStatus(response, status.HTTP_201_CREATED)
        new_site_id = response.data["id"]
        # Peer case - don't distinguish source/destination
        self.assertTrue(
            RelationshipAssociation.objects.filter(
                relationship=self.relationships[0],
                source_type=self.relationships[0].source_type,
                source_id__in=[existing_site_1.pk, new_site_id],
                destination_type=self.relationships[0].destination_type,
                destination_id__in=[existing_site_1.pk, new_site_id],
            ).exists()
        )
        self.assertTrue(
            RelationshipAssociation.objects.filter(
                relationship=self.relationships[1],
                source_type=self.relationships[1].source_type,
                source_id=existing_site_2.pk,
                destination_type=self.relationships[1].destination_type,
                destination_id=new_site_id,
            ).exists()
        )
        self.assertTrue(
            RelationshipAssociation.objects.filter(
                relationship=self.relationships[2],
                source_type=self.relationships[2].source_type,
                source_id=new_site_id,
                destination_type=self.relationships[2].destination_type,
                destination_id=existing_device_1.pk,
            ).exists()
        )
        self.assertTrue(
            RelationshipAssociation.objects.filter(
                relationship=self.relationships[2],
                source_type=self.relationships[2].source_type,
                source_id=new_site_id,
                destination_type=self.relationships[2].destination_type,
                destination_id=existing_device_2.pk,
            ).exists()
        )

    def test_required_relationships(self):
        """
        1. Try creating an object when no required target object exists
        2. Try creating an object without specifying required target object(s)
        3. Try creating an object when all required data is present
        """
        # Parameterized test:
        self.required_relationships_test(interact_with="api")


class RelationshipAssociationTest(APIViewTestCases.APIViewTestCase):
    model = RelationshipAssociation
    brief_fields = ["destination_id", "display", "id", "relationship", "source_id", "url"]
    choices_fields = ["destination_type", "source_type"]

    @classmethod
    def setUpTestData(cls):
        cls.site_type = ContentType.objects.get_for_model(Site)
        cls.device_type = ContentType.objects.get_for_model(Device)
        cls.status_active = Status.objects.get(slug="active")

        cls.relationship = Relationship(
            name="Devices found elsewhere",
            slug="elsewhere-devices",
            type="many-to-many",
            source_type=cls.site_type,
            destination_type=cls.device_type,
        )
        cls.relationship.validated_save()
        cls.sites = (
            Site.objects.create(name="Empty Site", slug="empty", status=cls.status_active),
            Site.objects.create(name="Occupied Site", slug="occupied", status=cls.status_active),
            Site.objects.create(name="Another Empty Site", slug="another-empty", status=cls.status_active),
        )
        manufacturer = Manufacturer.objects.create(name="Manufacturer 1", slug="manufacturer-1")
        devicetype = DeviceType.objects.create(manufacturer=manufacturer, model="Device Type 1", slug="device-type-1")
        devicerole = DeviceRole.objects.create(name="Device Role 1", slug="device-role-1")
        cls.devices = (
            Device.objects.create(
                name="Device 1",
                device_type=devicetype,
                device_role=devicerole,
                site=cls.sites[1],
                status=cls.status_active,
            ),
            Device.objects.create(
                name="Device 2",
                device_type=devicetype,
                device_role=devicerole,
                site=cls.sites[1],
                status=cls.status_active,
            ),
            Device.objects.create(
                name="Device 3",
                device_type=devicetype,
                device_role=devicerole,
                site=cls.sites[1],
                status=cls.status_active,
            ),
            Device.objects.create(
                name="Device 4",
                device_type=devicetype,
                device_role=devicerole,
                site=cls.sites[1],
                status=cls.status_active,
            ),
        )

        cls.associations = (
            RelationshipAssociation(
                relationship=cls.relationship,
                source_type=cls.site_type,
                source_id=cls.sites[0].pk,
                destination_type=cls.device_type,
                destination_id=cls.devices[0].pk,
            ),
            RelationshipAssociation(
                relationship=cls.relationship,
                source_type=cls.site_type,
                source_id=cls.sites[0].pk,
                destination_type=cls.device_type,
                destination_id=cls.devices[1].pk,
            ),
            RelationshipAssociation(
                relationship=cls.relationship,
                source_type=cls.site_type,
                source_id=cls.sites[0].pk,
                destination_type=cls.device_type,
                destination_id=cls.devices[2].pk,
            ),
        )
        for association in cls.associations:
            association.validated_save()

        cls.create_data = [
            {
                "relationship": cls.relationship.pk,
                "source_type": "dcim.site",
                "source_id": cls.sites[2].pk,
                "destination_type": "dcim.device",
                "destination_id": cls.devices[0].pk,
            },
            {
                "relationship": cls.relationship.pk,
                "source_type": "dcim.site",
                "source_id": cls.sites[2].pk,
                "destination_type": "dcim.device",
                "destination_id": cls.devices[1].pk,
            },
            {
                "relationship": cls.relationship.pk,
                "source_type": "dcim.site",
                "source_id": cls.sites[2].pk,
                "destination_type": "dcim.device",
                "destination_id": cls.devices[2].pk,
            },
        ]

    def test_create_invalid_relationship_association(self):
        """Test creation of invalid relationship association restricted by destination/source filter."""

        relationship = Relationship.objects.create(
            name="Device to Site Rel 1",
            slug="device-to-site-rel-1",
            source_type=self.device_type,
            source_filter={"name": [self.devices[0].name]},
            destination_type=self.site_type,
            destination_label="Primary Rack",
            type=RelationshipTypeChoices.TYPE_ONE_TO_ONE,
            destination_filter={"name": [self.sites[0].name]},
        )

        associations = [
            (
                "destination",  # side
                self.sites[2].name,  # field name with an error
                {
                    "relationship": relationship.pk,
                    "source_type": "dcim.device",
                    "source_id": self.devices[0].pk,
                    "destination_type": "dcim.site",
                    "destination_id": self.sites[2].pk,
                },
            ),
            (
                "source",  # side
                self.devices[1].name,  # field name with an error
                {
                    "relationship": relationship.pk,
                    "source_type": "dcim.device",
                    "source_id": self.devices[1].pk,
                    "destination_type": "dcim.site",
                    "destination_id": self.sites[0].pk,
                },
            ),
        ]

        self.add_permissions("extras.add_relationshipassociation")

        for side, field_error_name, data in associations:
            response = self.client.post(self._get_list_url(), data, format="json", **self.header)
            self.assertHttpStatus(response, status.HTTP_400_BAD_REQUEST)
            self.assertEqual(
                response.data[side],
                [f"{field_error_name} violates {relationship.name} {side}_filter restriction"],
            )

    def test_model_clean_method_is_called(self):
        """Validate RelationshipAssociation clean method is called"""

        data = {
            "relationship": self.relationship.pk,
            "source_type": "dcim.device",
            "source_id": self.sites[2].pk,
            "destination_type": "dcim.device",
            "destination_id": self.devices[2].pk,
        }

        self.add_permissions("extras.add_relationshipassociation")

        response = self.client.post(self._get_list_url(), data, format="json", **self.header)
        self.assertHttpStatus(response, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            response.data["source_type"], [f"source_type has a different value than defined in {self.relationship}"]
        )

    def test_get_association_data_on_site(self):
        """
        Check that `include=relationships` query parameter on a model endpoint includes relationships/associations.
        """
        self.add_permissions("dcim.view_site")
        response = self.client.get(
            reverse("dcim-api:site-detail", kwargs={"pk": self.sites[0].pk}) + "?include=relationships", **self.header
        )
        self.assertHttpStatus(response, status.HTTP_200_OK)
        self.assertIn("relationships", response.data)
        self.assertIsInstance(response.data["relationships"], dict)
        # Ensure consistent ordering
        response.data["relationships"][self.relationship.slug]["destination"]["objects"].sort(key=lambda v: v["name"])
        self.maxDiff = None
        self.assertEqual(
            {
                self.relationship.slug: {
                    "id": str(self.relationship.pk),
                    "url": (
                        "http://testserver"
                        + reverse("extras-api:relationship-detail", kwargs={"pk": self.relationship.pk})
                    ),
                    "name": self.relationship.name,
                    "type": "many-to-many",
                    "destination": {
                        "label": "devices",
                        "object_type": "dcim.device",
                        "objects": [
                            {
                                "id": str(self.devices[0].pk),
                                "url": (
                                    "http://testserver"
                                    + reverse("dcim-api:device-detail", kwargs={"pk": self.devices[0].pk})
                                ),
                                "display": self.devices[0].display,
                                "name": self.devices[0].name,
                            },
                            {
                                "id": str(self.devices[1].pk),
                                "url": (
                                    "http://testserver"
                                    + reverse("dcim-api:device-detail", kwargs={"pk": self.devices[1].pk})
                                ),
                                "display": self.devices[1].display,
                                "name": self.devices[1].name,
                            },
                            {
                                "id": str(self.devices[2].pk),
                                "url": (
                                    "http://testserver"
                                    + reverse("dcim-api:device-detail", kwargs={"pk": self.devices[2].pk})
                                ),
                                "display": self.devices[2].display,
                                "name": self.devices[2].name,
                            },
                        ],
                    },
                },
            },
            response.data["relationships"],
        )

    def test_update_association_data_on_site(self):
        """
        Check that relationship-associations can be updated via the 'relationships' field.
        """
        self.add_permissions(
            "dcim.view_site",
            "dcim.change_site",
            "extras.add_relationshipassociation",
            "extras.delete_relationshipassociation",
        )
        initial_response = self.client.get(
            reverse("dcim-api:site-detail", kwargs={"pk": self.sites[0].pk}) + "?include=relationships", **self.header
        )
        self.assertHttpStatus(initial_response, status.HTTP_200_OK)

        url = reverse("dcim-api:site-detail", kwargs={"pk": self.sites[0].pk})

        with self.subTest("Round-trip of same relationships data is a no-op"):
            response = self.client.patch(
                url,
                {"relationships": initial_response.data["relationships"]},
                format="json",
                **self.header,
            )
            self.assertHttpStatus(response, status.HTTP_200_OK)
            self.assertEqual(3, RelationshipAssociation.objects.filter(relationship=self.relationship).count())
            for association in self.associations:
                self.assertTrue(RelationshipAssociation.objects.filter(pk=association.pk).exists())

        with self.subTest("Omitting relationships data entirely is valid"):
            response = self.client.patch(
                url,
                {},
                format="json",
                **self.header,
            )
            self.assertHttpStatus(response, status.HTTP_200_OK)
            self.assertEqual(3, RelationshipAssociation.objects.filter(relationship=self.relationship).count())
            for association in self.associations:
                self.assertTrue(RelationshipAssociation.objects.filter(pk=association.pk).exists())

        with self.subTest("Error handling: nonexistent relationship"):
            response = self.client.patch(
                url,
                {"relationships": {"nonexistent-relationship": {"peer": {"objects": []}}}},
                format="json",
                **self.header,
            )
            self.assertHttpStatus(response, status.HTTP_400_BAD_REQUEST)
            self.assertEqual(
                str(response.data["relationships"][0]), '"nonexistent-relationship" is not a relationship on dcim.Site'
            )
            self.assertEqual(3, RelationshipAssociation.objects.filter(relationship=self.relationship).count())
            for association in self.associations:
                self.assertTrue(RelationshipAssociation.objects.filter(pk=association.pk).exists())

        with self.subTest("Error handling: wrong relationship"):
            Relationship.objects.create(
                name="Device-to-Device",
                slug="device-to-device",
                source_type=self.device_type,
                destination_type=self.device_type,
                type=RelationshipTypeChoices.TYPE_ONE_TO_ONE,
            )
            response = self.client.patch(
                url,
                {"relationships": {"device-to-device": {"peer": {"objects": []}}}},
                format="json",
                **self.header,
            )
            self.assertHttpStatus(response, status.HTTP_400_BAD_REQUEST)
            self.assertEqual(
                str(response.data["relationships"][0]), '"device-to-device" is not a relationship on dcim.Site'
            )
            self.assertEqual(3, RelationshipAssociation.objects.filter(relationship=self.relationship).count())
            for association in self.associations:
                self.assertTrue(RelationshipAssociation.objects.filter(pk=association.pk).exists())

        with self.subTest("Error handling: wrong relationship side"):
            response = self.client.patch(
                url,
                {"relationships": {self.relationship.slug: {"source": {"objects": []}}}},
                format="json",
                **self.header,
            )
            self.assertHttpStatus(response, status.HTTP_400_BAD_REQUEST)
            self.assertEqual(
                str(response.data["relationships"][0]),
                '"source" is not a valid side for "Devices found elsewhere" on dcim.Site',
            )
            self.assertEqual(3, RelationshipAssociation.objects.filter(relationship=self.relationship).count())
            for association in self.associations:
                self.assertTrue(RelationshipAssociation.objects.filter(pk=association.pk).exists())

        with self.subTest("Valid data: create/no-op/delete on RelationshipAssociations"):
            response = self.client.patch(
                url,
                {
                    "relationships": {
                        self.relationship.slug: {
                            "destination": {
                                "objects": [
                                    # remove devices[0] by omission
                                    str(self.devices[1].pk),  # existing device identified by PK
                                    {"name": self.devices[2].name},  # existing device identified by attributes
                                    {"id": self.devices[3].pk},  # new device association
                                ]
                            }
                        }
                    },
                },
                format="json",
                **self.header,
            )
            self.assertHttpStatus(response, status.HTTP_200_OK)
            # Removed association
            self.assertFalse(RelationshipAssociation.objects.filter(pk=self.associations[0].pk).exists())
            # Unchanged associations
            self.assertTrue(RelationshipAssociation.objects.filter(pk=self.associations[1].pk).exists())
            self.assertTrue(RelationshipAssociation.objects.filter(pk=self.associations[2].pk).exists())
            # Created association
            self.assertTrue(RelationshipAssociation.objects.filter(destination_id=self.devices[3].pk).exists())


class SecretTest(APIViewTestCases.APIViewTestCase):
    model = Secret
    brief_fields = ["display", "id", "name", "slug", "url"]
    bulk_update_data = {}

    create_data = [
        {
            "name": "NAPALM Username",
            "provider": "environment-variable",
            "description": "Username for all NAPALM devices",
            "parameters": {
                "variable": "NAPALM_USERNAME",
            },
        },
        {
            "name": "NAPALM Password",
            "provider": "environment-variable",
            "parameters": {
                "variable": "NAPALM_PASSWORD",
            },
        },
        {
            "name": "GitHub Token for My Repository",
            "slug": "github-token-my-repository",
            "provider": "text-file",
            "parameters": {
                "path": "/github-tokens/user/myusername.txt",
            },
        },
    ]
    slug_source = "name"

    @classmethod
    def setUpTestData(cls):
        secrets = (
            Secret(
                name="api-test-1",
                provider="environment-variable",
                parameters={"variable": "API_TEST_1"},
            ),
            Secret(
                name="api-test-2",
                provider="environment-variable",
                parameters={"variable": "API_TEST_2"},
            ),
            Secret(
                name="api-test-3",
                provider="environment-variable",
                parameters={"variable": "API_TEST_3"},
            ),
        )

        for secret in secrets:
            secret.validated_save()


class SecretsGroupTest(APIViewTestCases.APIViewTestCase):
    model = SecretsGroup
    brief_fields = ["display", "id", "name", "slug", "url"]
    bulk_update_data = {}

    slug_source = "name"

    @classmethod
    def setUpTestData(cls):
        secrets = (
            Secret.objects.create(
                name="secret-1", provider="environment-variable", parameters={"variable": "SOME_VAR"}
            ),
            Secret.objects.create(
                name="secret-2", provider="environment-variable", parameters={"variable": "ANOTHER_VAR"}
            ),
        )

        secrets_groups = (
            SecretsGroup.objects.create(name="Group A", slug="group-a"),
            SecretsGroup.objects.create(name="Group B", slug="group-b"),
            SecretsGroup.objects.create(name="Group C", slug="group-c", description="Some group"),
        )

        SecretsGroupAssociation.objects.create(
            secret=secrets[0],
            group=secrets_groups[0],
            access_type=SecretsGroupAccessTypeChoices.TYPE_GENERIC,
            secret_type=SecretsGroupSecretTypeChoices.TYPE_SECRET,
        )
        SecretsGroupAssociation.objects.create(
            secret=secrets[1],
            group=secrets_groups[1],
            access_type=SecretsGroupAccessTypeChoices.TYPE_GENERIC,
            secret_type=SecretsGroupSecretTypeChoices.TYPE_SECRET,
        )

        cls.create_data = [
            {
                "name": "Secrets Group 1",
                "slug": "secrets-group-1",
                "description": "First Secrets Group",
            },
            {
                "name": "Secrets Group 2",
                "description": "Second Secrets Group",
            },
            {
                "name": "Secrets Group 3",
                "description": "Third Secrets Group",
            },
        ]


class SecretsGroupAssociationTest(APIViewTestCases.APIViewTestCase):
    model = SecretsGroupAssociation
    brief_fields = ["access_type", "display", "id", "secret", "secret_type", "url"]
    bulk_update_data = {}
    choices_fields = ["access_type", "secret_type"]

    @classmethod
    def setUpTestData(cls):
        secrets = (
            Secret.objects.create(
                name="secret-1", provider="environment-variable", parameters={"variable": "SOME_VAR"}
            ),
            Secret.objects.create(
                name="secret-2", provider="environment-variable", parameters={"variable": "ANOTHER_VAR"}
            ),
            Secret.objects.create(
                name="secret-3", provider="environment-variable", parameters={"variable": "YET_ANOTHER"}
            ),
        )

        secrets_groups = (
            SecretsGroup.objects.create(name="Group A", slug="group-a"),
            SecretsGroup.objects.create(name="Group B", slug="group-b"),
            SecretsGroup.objects.create(name="Group C", slug="group-c", description="Some group"),
        )

        SecretsGroupAssociation.objects.create(
            secret=secrets[0],
            group=secrets_groups[0],
            access_type=SecretsGroupAccessTypeChoices.TYPE_GENERIC,
            secret_type=SecretsGroupSecretTypeChoices.TYPE_SECRET,
        )
        SecretsGroupAssociation.objects.create(
            secret=secrets[1],
            group=secrets_groups[1],
            access_type=SecretsGroupAccessTypeChoices.TYPE_GENERIC,
            secret_type=SecretsGroupSecretTypeChoices.TYPE_SECRET,
        )
        SecretsGroupAssociation.objects.create(
            secret=secrets[2],
            group=secrets_groups[2],
            access_type=SecretsGroupAccessTypeChoices.TYPE_GENERIC,
            secret_type=SecretsGroupSecretTypeChoices.TYPE_SECRET,
        )

        cls.create_data = [
            {
                "group": secrets_groups[0].pk,
                "access_type": SecretsGroupAccessTypeChoices.TYPE_SSH,
                "secret_type": SecretsGroupSecretTypeChoices.TYPE_USERNAME,
                "secret": secrets[0].pk,
            },
            {
                "group": secrets_groups[1].pk,
                "access_type": SecretsGroupAccessTypeChoices.TYPE_SSH,
                "secret_type": SecretsGroupSecretTypeChoices.TYPE_USERNAME,
                "secret": secrets[1].pk,
            },
            {
                "group": secrets_groups[2].pk,
                "access_type": SecretsGroupAccessTypeChoices.TYPE_SSH,
                "secret_type": SecretsGroupSecretTypeChoices.TYPE_USERNAME,
                "secret": secrets[2].pk,
            },
        ]


class StatusTest(APIViewTestCases.APIViewTestCase):
    model = Status
    brief_fields = ["display", "id", "name", "slug", "url"]
    bulk_update_data = {
        "color": "000000",
    }

    create_data = [
        {
            "name": "Pizza",
            "slug": "pizza",
            "color": "0000ff",
            "content_types": ["dcim.device", "dcim.rack"],
        },
        {
            "name": "Oysters",
            "slug": "oysters",
            "color": "00ff00",
            "content_types": ["ipam.ipaddress", "ipam.prefix"],
        },
        {
            "name": "Bad combinations",
            "slug": "bad-combinations",
            "color": "ff0000",
            "content_types": ["dcim.device"],
        },
        {
            "name": "Status 1",
            "color": "ff0000",
            "content_types": ["dcim.device"],
        },
    ]
    slug_source = "name"


class TagTestVersion12(APIViewTestCases.APIViewTestCase):
    model = Tag
    brief_fields = ["color", "display", "id", "name", "slug", "url"]
    create_data = [
        {
            "name": "Tag 4",
            "slug": "tag-4",
        },
        {
            "name": "Tag 5",
            "slug": "tag-5",
        },
        {
            "name": "Tag 6",
            "slug": "tag-6",
        },
    ]
    bulk_update_data = {
        "description": "New description",
    }

    def test_all_relevant_content_types_assigned_to_tags_with_empty_content_types(self):
        self.add_permissions("extras.add_tag")

        self.client.post(self._get_list_url(), self.create_data[0], format="json", **self.header)

        tag = Tag.objects.get(slug=self.create_data[0]["slug"])
        self.assertEqual(
            tag.content_types.count(),
            TaggableClassesQuery().as_queryset().count(),
        )


class TagTestVersion13(
    APIViewTestCases.CreateObjectViewTestCase,
    APIViewTestCases.UpdateObjectViewTestCase,
):
    model = Tag
    brief_fields = ["color", "display", "id", "name", "slug", "url"]
    api_version = "1.3"
    create_data = [
        {"name": "Tag 4", "slug": "tag-4", "content_types": [Site._meta.label_lower]},
        {"name": "Tag 5", "slug": "tag-5", "content_types": [Site._meta.label_lower]},
        {"name": "Tag 6", "slug": "tag-6", "content_types": [Site._meta.label_lower]},
    ]
    choices_fields = []

    @classmethod
    def setUpTestData(cls):
        cls.update_data = {
            "name": "A new tag name",
            "slug": "a-new-tag-name",
            "content_types": [f"{ct.app_label}.{ct.model}" for ct in TaggableClassesQuery().as_queryset()],
        }
        cls.bulk_update_data = {
            "content_types": [f"{ct.app_label}.{ct.model}" for ct in TaggableClassesQuery().as_queryset()]
        }

    def test_create_tags_with_invalid_content_types(self):
        self.add_permissions("extras.add_tag")

        # VLANGroup is an OrganizationalModel, not a PrimaryModel, and therefore does not support tags
        data = {**self.create_data[0], "content_types": [VLANGroup._meta.label_lower]}
        response = self.client.post(self._get_list_url(), data, format="json", **self.header)

        tag = Tag.objects.filter(slug=data["slug"])
        self.assertHttpStatus(response, 400)
        self.assertFalse(tag.exists())
        self.assertIn(f"Invalid content type: {VLANGroup._meta.label_lower}", response.data["content_types"])

    def test_create_tags_without_content_types(self):
        self.add_permissions("extras.add_tag")
        data = {
            "name": "Tag 8",
            "slug": "tag-8",
        }

        response = self.client.post(self._get_list_url(), data, format="json", **self.header)
        self.assertHttpStatus(response, 400)
        self.assertEqual(str(response.data["content_types"][0]), "This field is required.")

    def test_update_tags_remove_content_type(self):
        """Test removing a tag content_type that is been tagged to a model"""
        self.add_permissions("extras.change_tag")

        tag_1 = Tag.objects.filter(content_types=ContentType.objects.get_for_model(Site)).first()
        site = Site.objects.create(name="site 1", slug="site-1")
        site.tags.add(tag_1)

        tag_content_types = list(tag_1.content_types.all())
        tag_content_types.remove(ContentType.objects.get_for_model(Site))

        url = self._get_detail_url(tag_1)
        data = {"content_types": [f"{ct.app_label}.{ct.model}" for ct in tag_content_types]}

        response = self.client.patch(url, data, format="json", **self.header)
        self.assertHttpStatus(response, 400)
        self.assertEqual(
            str(response.data["content_types"][0]), "Unable to remove dcim.site. Dependent objects were found."
        )

    def test_update_tag_content_type_unchanged(self):
        """Test updating a tag without changing its content-types."""
        self.add_permissions("extras.change_tag")

        tag = Tag.objects.exclude(content_types=ContentType.objects.get_for_model(Site)).first()
        tag_content_types = list(tag.content_types.all())
        url = self._get_detail_url(tag)
        data = {"color": ColorChoices.COLOR_LIME}

        response = self.client.patch(url, data, format="json", **self.header)
        self.assertHttpStatus(response, status.HTTP_200_OK)
        self.assertEqual(response.data["color"], ColorChoices.COLOR_LIME)
        self.assertEqual(
            sorted(response.data["content_types"]), sorted([f"{ct.app_label}.{ct.model}" for ct in tag_content_types])
        )

        tag.refresh_from_db()
        self.assertEqual(tag.color, ColorChoices.COLOR_LIME)
        self.assertEqual(list(tag.content_types.all()), tag_content_types)


class WebhookTest(APIViewTestCases.APIViewTestCase):
    model = Webhook
    brief_fields = ["display", "id", "name", "url"]
    create_data = [
        {
            "content_types": ["dcim.consoleport"],
            "name": "api-test-4",
            "type_create": True,
            "payload_url": "http://example.com/test4",
            "http_method": "POST",
            "http_content_type": "application/json",
            "ssl_verification": True,
        },
        {
            "content_types": ["dcim.consoleport"],
            "name": "api-test-5",
            "type_update": True,
            "payload_url": "http://example.com/test5",
            "http_method": "POST",
            "http_content_type": "application/json",
            "ssl_verification": True,
        },
        {
            "content_types": ["dcim.consoleport"],
            "name": "api-test-6",
            "type_delete": True,
            "payload_url": "http://example.com/test6",
            "http_method": "POST",
            "http_content_type": "application/json",
            "ssl_verification": True,
        },
    ]
    choices_fields = ["http_method"]

    @classmethod
    def setUpTestData(cls):
        cls.webhooks = (
            Webhook(
                name="api-test-1",
                type_create=True,
                payload_url="http://example.com/test1",
                http_method="POST",
                http_content_type="application/json",
                ssl_verification=True,
            ),
            Webhook(
                name="api-test-2",
                type_update=True,
                payload_url="http://example.com/test2",
                http_method="POST",
                http_content_type="application/json",
                ssl_verification=True,
            ),
            Webhook(
                name="api-test-3",
                type_delete=True,
                payload_url="http://example.com/test3",
                http_method="POST",
                http_content_type="application/json",
                ssl_verification=True,
            ),
        )

        obj_type = ContentType.objects.get_for_model(DeviceType)

        for webhook in cls.webhooks:
            webhook.save()
            webhook.content_types.set([obj_type])

    def test_create_webhooks_with_diff_content_type_same_url_same_action(self):
        """
        Create a new webhook with diffrent content_types, same url and same action with a webhook that exists

        Example:
            Webhook 1: dcim | device type, create, http://localhost
            Webhook 2: dcim | console port, create, http://localhost
        """
        self.add_permissions("extras.add_webhook")

        data = (
            {
                "content_types": ["dcim.consoleport"],
                "name": "api-test-7",
                "type_create": self.webhooks[0].type_create,
                "payload_url": self.webhooks[0].payload_url,
                "http_method": self.webhooks[0].http_method,
                "http_content_type": self.webhooks[0].http_content_type,
                "ssl_verification": self.webhooks[0].ssl_verification,
            },
        )

        response = self.client.post(self._get_list_url(), data, format="json", **self.header)
        self.assertHttpStatus(response, status.HTTP_201_CREATED)

    def test_create_webhooks_with_same_content_type_same_url_diff_action(self):
        """
        Create a new webhook with same content_types, same url and diff action with a webhook that exists

        Example:
            Webhook 1: dcim | device type, create, http://localhost
            Webhook 2: dcim | device type, delete, http://localhost
        """
        self.add_permissions("extras.add_webhook")

        data = (
            {
                "content_types": ["dcim.devicetype"],
                "name": "api-test-7",
                "type_update": True,
                "payload_url": self.webhooks[0].payload_url,
                "http_method": self.webhooks[0].http_method,
                "http_content_type": self.webhooks[0].http_content_type,
                "ssl_verification": self.webhooks[0].ssl_verification,
            },
        )

        response = self.client.post(self._get_list_url(), data, format="json", **self.header)
        self.assertHttpStatus(response, status.HTTP_201_CREATED)

    def test_create_webhooks_with_same_content_type_same_url_common_action(self):
        """
        Create a new webhook with same content_types, same url and common action with a webhook that exists

        Example:
            Webhook 1: dcim | device type, create, http://localhost
            Webhook 2: dcim | device type, create, update, http://localhost
        """
        self.add_permissions("extras.add_webhook")

        data = (
            {
                "content_types": ["dcim.devicetype"],
                "name": "api-test-7",
                "type_create": self.webhooks[0].type_create,
                "type_update": True,
                "payload_url": self.webhooks[0].payload_url,
                "http_method": self.webhooks[0].http_method,
                "http_content_type": self.webhooks[0].http_content_type,
                "ssl_verification": self.webhooks[0].ssl_verification,
            },
        )

        response = self.client.post(self._get_list_url(), data, format="json", **self.header)
        self.assertHttpStatus(response, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            response.data[0]["type_create"][0],
            "A webhook already exists for create on dcim | device type to URL http://example.com/test1",
        )

    def test_patch_webhooks_with_same_content_type_same_url_common_action(self):
        self.add_permissions("extras.change_webhook")

        self.webhooks[2].payload_url = self.webhooks[1].payload_url
        self.webhooks[2].save()

        data = {"type_update": True}

        response = self.client.patch(self._get_detail_url(self.webhooks[2]), data, format="json", **self.header)
        self.assertHttpStatus(response, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            response.data["type_update"][0],
            f"A webhook already exists for update on dcim | device type to URL {self.webhooks[1].payload_url}",
        )

    def test_patch_webhooks(self):
        self.add_permissions("extras.change_webhook")

        instance = Webhook.objects.create(
            name="api-test-4",
            type_update=True,
            payload_url=self.webhooks[1].payload_url,
            http_method="POST",
            http_content_type="application/json",
            ssl_verification=True,
        )
        instance.content_types.set([ContentType.objects.get_for_model(DeviceType)])

        data = {"type_delete": True}
        response = self.client.patch(self._get_detail_url(self.webhooks[2]), data, format="json", **self.header)
        self.assertHttpStatus(response, status.HTTP_200_OK)

        data = {"content_types": ["dcim.device"]}
        response = self.client.patch(self._get_detail_url(self.webhooks[2]), data, format="json", **self.header)
        self.assertHttpStatus(response, status.HTTP_200_OK)

        data = {"payload_url": "http://example.com/test4"}
        response = self.client.patch(self._get_detail_url(self.webhooks[2]), data, format="json", **self.header)
        self.assertHttpStatus(response, status.HTTP_200_OK)

    def test_invalid_webhooks_patch(self):
        self.add_permissions("extras.change_webhook")

        # Test patch payload_url with conflicts
        instance_1 = Webhook.objects.create(
            name="api-test-4",
            type_update=True,
            payload_url="http://example.com/test4",
            http_method="POST",
            http_content_type="application/json",
            ssl_verification=True,
        )
        instance_1.content_types.set([ContentType.objects.get_for_model(DeviceType)])

        data = {"payload_url": "http://example.com/test2"}
        response = self.client.patch(self._get_detail_url(instance_1), data, format="json", **self.header)
        self.assertEqual(
            response.data["type_update"][0],
            "A webhook already exists for update on dcim | device type to URL http://example.com/test2",
        )

        # Test patch content_types with conflicts
        instance_2 = Webhook.objects.create(
            name="api-test-5",
            type_create=True,
            payload_url="http://example.com/test1",
            http_method="POST",
            http_content_type="application/json",
            ssl_verification=True,
        )
        instance_2.content_types.set([ContentType.objects.get_for_model(Device)])

        data = {"content_types": ["dcim.devicetype"]}
        response = self.client.patch(self._get_detail_url(instance_2), data, format="json", **self.header)
        self.assertEqual(
            response.data["type_create"][0],
            "A webhook already exists for create on dcim | device type to URL http://example.com/test1",
        )
