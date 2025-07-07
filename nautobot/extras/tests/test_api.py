from datetime import datetime, timedelta
import tempfile
from unittest import mock, skip
import uuid
from zoneinfo import ZoneInfo

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from django.urls import reverse
from django.utils.timezone import make_aware, now
from rest_framework import status

from nautobot.core.choices import ColorChoices
from nautobot.core.models.fields import slugify_dashes_to_underscores
from nautobot.core.testing import APITestCase, APIViewTestCases
from nautobot.core.testing.utils import disable_warnings, get_deletable_objects
from nautobot.core.utils.lookup import get_route_for_model
from nautobot.core.utils.permissions import get_permission_for_model
from nautobot.dcim.models import (
    Controller,
    ControllerManagedDeviceGroup,
    Device,
    DeviceType,
    Location,
    LocationType,
    Manufacturer,
    Rack,
    RackGroup,
)
from nautobot.dcim.tests import test_views
from nautobot.extras.api.serializers import ConfigContextSerializer, JobResultSerializer
from nautobot.extras.choices import (
    DynamicGroupOperatorChoices,
    DynamicGroupTypeChoices,
    JobExecutionType,
    JobQueueTypeChoices,
    JobResultStatusChoices,
    MetadataTypeDataTypeChoices,
    ObjectChangeActionChoices,
    ObjectChangeEventContextChoices,
    RelationshipTypeChoices,
    SecretsGroupAccessTypeChoices,
    SecretsGroupSecretTypeChoices,
    WebhookHttpMethodChoices,
)
from nautobot.extras.jobs import get_job
from nautobot.extras.models import (
    ComputedField,
    ConfigContext,
    ConfigContextSchema,
    Contact,
    ContactAssociation,
    CustomField,
    CustomLink,
    DynamicGroup,
    DynamicGroupMembership,
    ExportTemplate,
    ExternalIntegration,
    FileProxy,
    GitRepository,
    GraphQLQuery,
    ImageAttachment,
    Job,
    JobLogEntry,
    JobQueue,
    JobQueueAssignment,
    JobResult,
    MetadataChoice,
    MetadataType,
    Note,
    ObjectChange,
    ObjectMetadata,
    Relationship,
    RelationshipAssociation,
    Role,
    SavedView,
    ScheduledJob,
    Secret,
    SecretsGroup,
    SecretsGroupAssociation,
    StaticGroupAssociation,
    Status,
    Tag,
    Team,
    UserSavedViewAssociation,
    Webhook,
)
from nautobot.extras.models.jobs import JobButton, JobHook
from nautobot.extras.tests.constants import BIG_GRAPHQL_DEVICE_QUERY
from nautobot.extras.tests.test_relationships import RequiredRelationshipTestMixin
from nautobot.extras.utils import TaggableClassesQuery
from nautobot.ipam.models import IPAddress, Prefix, VLAN, VLANGroup
from nautobot.tenancy.models import Tenant
from nautobot.users.models import ObjectPermission

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
    choices_fields = ["content_type"]
    create_data = [
        {
            "content_type": "dcim.location",
            "label": "Computed Field 4",
            "template": "{{ obj.name }}",
            "fallback_value": "error",
        },
        {
            "content_type": "dcim.location",
            "label": "Computed Field 5",
            "template": "{{ obj.name }}",
            "fallback_value": "error",
        },
        {
            "content_type": "dcim.location",
            "label": "Computed Field 6",
            "template": "{{ obj.name }}",
        },
        {
            "content_type": "dcim.location",
            "label": "Computed Field 7",
            "template": "{{ obj.name }}",
            "fallback_value": "error",
        },
    ]
    update_data = {
        "content_type": "dcim.location",
        "key": "cf1",
        "label": "My Computed Field",
    }
    bulk_update_data = {
        "description": "New description",
    }
    slug_source = "label"
    slugify_function = staticmethod(slugify_dashes_to_underscores)

    @classmethod
    def setUpTestData(cls):
        location_ct = ContentType.objects.get_for_model(Location)

        ComputedField.objects.create(
            key="cf1",
            label="Computed Field One",
            template="{{ obj.name }}",
            fallback_value="error",
            content_type=location_ct,
        )
        ComputedField.objects.create(
            key="cf2",
            label="Computed Field Two",
            template="{{ obj.name }}",
            fallback_value="error",
            content_type=location_ct,
        )
        ComputedField.objects.create(
            key="cf3",
            label="Computed Field Three",
            template="{{ obj.name }}",
            fallback_value="error",
            content_type=location_ct,
        )

        cls.location = Location.objects.filter(location_type=LocationType.objects.get(name="Campus")).first()

    def test_computed_field_include(self):
        """Test that explicitly including a computed field behaves as expected."""
        self.add_permissions("dcim.view_location")
        url = reverse("dcim-api:location-detail", kwargs={"pk": self.location.pk})

        # First get the object without computed fields.
        response = self.client.get(url, **self.header)
        self.assertNotIn("computed_fields", response.json())

        # Now get it with computed fields.
        params = {"include": "computed_fields"}
        response = self.client.get(url, data=params, **self.header)
        self.assertIn("computed_fields", response.json())


class ConfigContextTest(APIViewTestCases.APIViewTestCase):
    model = ConfigContext
    bulk_update_data = {
        "description": "New description",
    }
    choices_fields = ["owner_content_type"]

    @classmethod
    def setUpTestData(cls):
        ConfigContext.objects.create(name="Config Context 1", weight=100, data={"foo": 123})
        ConfigContext.objects.create(name="Config Context 2", weight=200, data={"bar": 456})
        ConfigContext.objects.create(name="Config Context 3", weight=300, data={"baz": 789})
        cls.create_data = [
            {
                "name": "Config Context 4",
                "data": {"more_foo": True},
                "tags": [tag.pk for tag in Tag.objects.get_for_model(Device)],
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

    def test_render_configcontext_for_object(self):
        """
        Test rendering config context data for a device.
        """
        manufacturer = Manufacturer.objects.first()
        devicetype = DeviceType.objects.create(manufacturer=manufacturer, model="Device Type 1")
        devicerole = Role.objects.get_for_model(Device).first()
        devicestatus = Status.objects.get_for_model(Device).first()
        location = Location.objects.filter(location_type=LocationType.objects.get(name="Campus")).first()
        device = Device.objects.create(
            name="Device 1", device_type=devicetype, role=devicerole, status=devicestatus, location=location
        )

        # Test default config contexts (created at test setup)
        rendered_context = device.get_config_context()
        self.assertEqual(rendered_context["foo"], 123)
        self.assertEqual(rendered_context["bar"], 456)
        self.assertEqual(rendered_context["baz"], 789)

        # Test API response as well
        self.add_permissions("dcim.view_device")
        device_url = reverse("dcim-api:device-detail", kwargs={"pk": device.pk})
        response = self.client.get(device_url + "?include=config_context", **self.header)
        self.assertHttpStatus(response, status.HTTP_200_OK)
        self.assertIn("config_context", response.data)
        self.assertEqual(response.data["config_context"], {"foo": 123, "bar": 456, "baz": 789}, response.data)

        # Add another context specific to the location
        configcontext4 = ConfigContext(name="Config Context 4", data={"location_data": "ABC"})
        configcontext4.save()
        configcontext4.locations.add(location)
        rendered_context = device.get_config_context()
        self.assertEqual(rendered_context["location_data"], "ABC")
        response = self.client.get(device_url + "?include=config_context", **self.header)
        self.assertHttpStatus(response, status.HTTP_200_OK)
        self.assertIn("config_context", response.data)
        self.assertEqual(response.data["config_context"]["location_data"], "ABC", response.data["config_context"])

        # Override one of the default contexts
        configcontext5 = ConfigContext(name="Config Context 5", weight=2000, data={"foo": 999})
        configcontext5.save()
        configcontext5.locations.add(location)
        rendered_context = device.get_config_context()
        self.assertEqual(rendered_context["foo"], 999)
        response = self.client.get(device_url + "?include=config_context", **self.header)
        self.assertHttpStatus(response, status.HTTP_200_OK)
        self.assertIn("config_context", response.data)
        self.assertEqual(response.data["config_context"]["foo"], 999, response.data["config_context"])

        # Add a context which does NOT match our device and ensure it does not apply
        location2 = Location.objects.filter(location_type=LocationType.objects.get(name="Campus")).last()
        configcontext6 = ConfigContext(name="Config Context 6", weight=2000, data={"bar": 999})
        configcontext6.save()
        configcontext6.locations.add(location2)
        rendered_context = device.get_config_context()
        self.assertEqual(rendered_context["bar"], 456)
        response = self.client.get(device_url + "?include=config_context", **self.header)
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
            name="Schema 1", data_schema={"type": "object", "properties": {"foo": {"type": "string"}}}
        )
        self.add_permissions("extras.add_configcontext", "extras.view_configcontextschema")

        data = {
            "name": "Config Context with schema",
            "weight": 100,
            "data": {"foo": "bar"},
            "config_context_schema": str(schema.pk),
        }
        response = self.client.post(self._get_list_url(), data, format="json", **self.header)
        self.assertHttpStatus(response, status.HTTP_201_CREATED)
        self.assertEqual(response.data["config_context_schema"]["url"], self.absolute_api_url(schema))

    def test_schema_validation_fails(self):
        """
        Given a config context schema
        And a config context that *does not* conform to that schema
        Assert that the config context fails schema validation via full_clean()
        """
        schema = ConfigContextSchema.objects.create(
            name="Schema 1", data_schema={"type": "object", "properties": {"foo": {"type": "integer"}}}
        )
        self.add_permissions("extras.add_configcontext")

        data = {
            "name": "Config Context with bad schema",
            "weight": 100,
            "data": {"foo": "bar"},
            "config_context_schema": str(schema.pk),
        }
        response = self.client.post(self._get_list_url(), data, format="json", **self.header)
        self.assertHttpStatus(response, status.HTTP_400_BAD_REQUEST)

    @override_settings(CONFIG_CONTEXT_DYNAMIC_GROUPS_ENABLED=True)
    def test_with_dynamic_groups_enabled(self):
        """Asserts that `ConfigContextSerializer.dynamic_group` is present when feature flag is enabled."""
        serializer = ConfigContextSerializer()
        self.assertIn("dynamic_groups", serializer.fields)

    @override_settings(CONFIG_CONTEXT_DYNAMIC_GROUPS_ENABLED=False)
    def test_without_dynamic_groups_enabled(self):
        """Asserts that `ConfigContextSerializer.dynamic_group` is NOT present the when feature flag is disabled."""
        serializer = ConfigContextSerializer()
        self.assertNotIn("dynamic_groups", serializer.fields)


class ConfigContextSchemaTest(APIViewTestCases.APIViewTestCase):
    model = ConfigContextSchema
    create_data = [
        {
            "name": "Schema 4",
            "data_schema": {"type": "object", "properties": {"foo": {"type": "string"}}},
        },
        {
            "name": "Schema 5",
            "data_schema": {"type": "object", "properties": {"bar": {"type": "string"}}},
        },
        {
            "name": "Schema 6",
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
    choices_fields = ["owner_content_type"]

    @classmethod
    def setUpTestData(cls):
        ConfigContextSchema.objects.create(
            name="Schema 1", data_schema={"type": "object", "properties": {"foo": {"type": "string"}}}
        )
        ConfigContextSchema.objects.create(
            name="Schema 2", data_schema={"type": "object", "properties": {"bar": {"type": "string"}}}
        )
        ConfigContextSchema.objects.create(
            name="Schema 3", data_schema={"type": "object", "properties": {"baz": {"type": "string"}}}
        )


class ContentTypeTest(APITestCase):
    """
    ContentTypeViewSet does not have permission checks,
    So It should be accessible with or without permission override
    e.g. @override_settings(EXEMPT_VIEW_PERMISSIONS=["contenttypes.contenttype"])
    """

    def test_list_objects_with_or_without_permission(self):
        contenttype_count = ContentType.objects.count()

        response = self.client.get(reverse("extras-api:contenttype-list"), **self.header)
        self.assertHttpStatus(response, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], contenttype_count)

    def test_get_object_with_or_without_permission(self):
        contenttype = ContentType.objects.first()

        url = reverse("extras-api:contenttype-detail", kwargs={"pk": contenttype.pk})
        self.assertHttpStatus(self.client.get(url, **self.header), status.HTTP_200_OK)


#
#  Contacts
#


class ContactTest(APIViewTestCases.APIViewTestCase):
    model = Contact
    bulk_update_data = {
        "address": "Carnegie Hall, New York, NY",
    }

    @classmethod
    def setUpTestData(cls):
        # Contacts associated with ObjectMetadata objects are protected, create some deletable contacts
        Contact.objects.create(name="Deletable contact 1")
        Contact.objects.create(name="Deletable contact 2")
        Contact.objects.create(name="Deletable contact 3")

        cls.create_data = [
            {
                "name": "Contact 1",
                "phone": "555-0121",
                "email": "contact1@example.com",
                "teams": [Team.objects.first().pk, Team.objects.last().pk],
            },
            {
                "name": "Contact 2",
                "phone": "555-0122",
                "email": "contact2@example.com",
                "address": "Bowser's Castle, Staten Island, NY",
            },
            {
                "name": "Contact 3",
                "phone": "555-0123",
            },
            {
                "name": "Contact 4",
                "email": "contact4@example.com",
            },
        ]


class ContactAssociationTestCase(APIViewTestCases.APIViewTestCase):
    model = ContactAssociation
    create_data = []
    choices_fields = ["associated_object_type"]

    @classmethod
    def setUpTestData(cls):
        roles = Role.objects.get_for_model(ContactAssociation)
        statuses = Status.objects.get_for_model(ContactAssociation)
        ip_addresses = IPAddress.objects.all()
        devices = Device.objects.all()
        ContactAssociation.objects.create(
            contact=Contact.objects.first(),
            associated_object_type=ContentType.objects.get_for_model(IPAddress),
            associated_object_id=ip_addresses[0].pk,
            role=roles[0],
            status=statuses[0],
        )
        ContactAssociation.objects.create(
            contact=Contact.objects.last(),
            associated_object_type=ContentType.objects.get_for_model(IPAddress),
            associated_object_id=ip_addresses[1].pk,
            role=roles[1],
            status=statuses[1],
        )
        ContactAssociation.objects.create(
            team=Team.objects.first(),
            associated_object_type=ContentType.objects.get_for_model(IPAddress),
            associated_object_id=ip_addresses[2].pk,
            role=roles[1],
            status=statuses[0],
        )
        ContactAssociation.objects.create(
            team=Team.objects.last(),
            associated_object_type=ContentType.objects.get_for_model(IPAddress),
            associated_object_id=ip_addresses[3].pk,
            role=roles[2],
            status=statuses[1],
        )
        cls.create_data = [
            {
                "contact": Contact.objects.first().pk,
                "team": None,
                "associated_object_type": "ipam.ipaddress",
                "associated_object_id": ip_addresses[4].pk,
                "role": roles[3].pk,
                "status": statuses[0].pk,
            },
            {
                "contact": Contact.objects.last().pk,
                "team": None,
                "associated_object_type": "dcim.device",
                "associated_object_id": devices[0].pk,
                "role": roles[3].pk,
                "status": statuses[0].pk,
            },
            {
                "contact": None,
                "team": Team.objects.first().pk,
                "associated_object_type": "ipam.ipaddress",
                "associated_object_id": ip_addresses[5].pk,
                "role": roles[3].pk,
                "status": statuses[2].pk,
            },
            {
                "contact": None,
                "team": Team.objects.last().pk,
                "associated_object_type": "dcim.device",
                "associated_object_id": devices[1].pk,
                "role": roles[3].pk,
                "status": statuses[0].pk,
            },
        ]
        cls.bulk_update_data = {
            "role": roles[4].pk,
            "status": statuses[1].pk,
        }


class CreatedUpdatedFilterTest(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.location1 = Location.objects.filter(location_type=LocationType.objects.get(name="Campus")).first()
        cls.rackgroup1 = RackGroup.objects.create(location=cls.location1, name="Test Rack Group 1")
        cls.rackrole1 = Role.objects.get_for_model(Rack).first()
        cls.rackstatus1 = Status.objects.get_for_model(Rack).first()
        cls.rack1 = Rack.objects.create(
            location=cls.location1,
            rack_group=cls.rackgroup1,
            role=cls.rackrole1,
            status=cls.rackstatus1,
            name="Test Rack 1",
            u_height=42,
        )
        cls.rack2 = Rack.objects.create(
            location=cls.location1,
            rack_group=cls.rackgroup1,
            role=cls.rackrole1,
            status=cls.rackstatus1,
            name="Test Rack 2",
            u_height=42,
        )

        # change the created and last_updated of one
        Rack.objects.filter(pk=cls.rack2.pk).update(
            created=make_aware(datetime(2001, 2, 3, 0, 1, 2, 3)),
            last_updated=make_aware(datetime(2001, 2, 3, 1, 2, 3, 4)),
        )

    def test_get_rack_created(self):
        self.add_permissions("dcim.view_rack")
        url = reverse("dcim-api:rack-list")
        response = self.client.get(f"{url}?created=2001-02-03%2000:01:02.000003", **self.header)

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

        response = self.client.get(f"{url}?created__gte=2001-02-03%2000:01:03", **self.header)
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

        response = self.client.get(f"{url}?created__lte=2001-02-03%2000:01:03", **self.header)
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


class CustomFieldTest(APIViewTestCases.APIViewTestCase):
    """Tests for the CustomField REST API."""

    model = CustomField
    create_data = [
        {
            "content_types": ["dcim.location"],
            "label": "Custom Field 4",
            "key": "custom_field_4",
            "type": "date",
            "weight": 100,
        },
        {
            "content_types": ["dcim.location", "dcim.device"],
            "label": "Custom Field 5",
            "key": "custom_field_5",
            "type": "url",
            "default": "http://example.com",
            "weight": 200,
        },
        {
            "content_types": ["dcim.location"],
            "label": "Custom Field 6",
            "key": "custom_field_6",
            "type": "select",
            "description": "A select custom field",
            "weight": 300,
        },
    ]
    update_data = {
        "content_types": ["dcim.location"],
        "description": "New description",
        "label": "Non-unique label",
    }
    bulk_update_data = {
        "description": "New description",
    }
    choices_fields = ["filter_logic", "type"]

    @classmethod
    def setUpTestData(cls):
        location_ct = ContentType.objects.get_for_model(Location)

        custom_fields = (
            CustomField(key="cf1", label="Custom Field 1", type="text"),
            CustomField(key="cf2", label="Custom Field 2", type="integer"),
            CustomField(key="cf3", label="Custom Field 3", type="boolean"),
        )
        for cf in custom_fields:
            cf.validated_save()
            cf.content_types.add(location_ct)

    def test_create_object_required_fields(self):
        """For this API version, `label` and `key` are required fields."""
        self.add_permissions("extras.add_customfield")

        incomplete_data = {
            "content_types": ["dcim.location"],
            "type": "date",
        }

        response = self.client.post(self._get_list_url(), incomplete_data, format="json", **self.header)
        self.assertHttpStatus(response, status.HTTP_400_BAD_REQUEST)
        self.maxDiff = None
        self.assertEqual(
            response.data,
            # Since we are setting blank=True on the key field, we only need to check
            # error messages from the label field.
            {"label": ["This field is required."]},
        )


class CustomLinkTest(APIViewTestCases.APIViewTestCase):
    model = CustomLink
    create_data = [
        {
            "content_type": "dcim.location",
            "name": "api-test-4",
            "text": "API customlink text 4",
            "target_url": "http://api-test-4.com/test4",
            "weight": 100,
            "new_window": False,
        },
        {
            "content_type": "dcim.location",
            "name": "api-test-5",
            "text": "API customlink text 5",
            "target_url": "http://api-test-5.com/test5",
            "weight": 100,
            "new_window": False,
        },
        {
            "content_type": "dcim.location",
            "name": "api-test-6",
            "text": "API customlink text 6",
            "target_url": "http://api-test-6.com/test6",
            "weight": 100,
            "new_window": False,
        },
    ]
    choices_fields = ["button_class", "content_type"]

    @classmethod
    def setUpTestData(cls):
        obj_type = ContentType.objects.get_for_model(Location)

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
        location_type = LocationType.objects.get(name="Campus")
        location_status = Status.objects.get_for_model(Location).first()
        locations = (
            Location.objects.create(name="Location 1", location_type=location_type, status=location_status),
            Location.objects.create(name="Location 2", location_type=location_type, status=location_status),
            Location.objects.create(name="Location 3", location_type=location_type, status=location_status),
        )

        manufacturer = Manufacturer.objects.first()
        device_type = DeviceType.objects.create(
            manufacturer=manufacturer,
            model="device Type 1",
        )
        device_role = Role.objects.get_for_model(Device).first()
        statuses = Status.objects.get_for_model(Device)
        Device.objects.create(
            name="device-location-1",
            status=statuses[0],
            role=device_role,
            device_type=device_type,
            location=locations[0],
        )
        Device.objects.create(
            name="device-location-2",
            status=statuses[0],
            role=device_role,
            device_type=device_type,
            location=locations[1],
        )
        Device.objects.create(
            name="device-location-3",
            status=statuses[1],
            role=device_role,
            device_type=device_type,
            location=locations[2],
        )

        # Then the DynamicGroups.
        cls.content_type = ContentType.objects.get_for_model(Device)
        cls.groups = [
            DynamicGroup.objects.create(
                name="API DynamicGroup 1",
                content_type=cls.content_type,
                filter={"status": [statuses[0].name]},
            ),
            DynamicGroup.objects.create(
                name="API DynamicGroup 2",
                content_type=cls.content_type,
                filter={"status": [statuses[0].name]},
            ),
            DynamicGroup.objects.create(
                name="API DynamicGroup 3",
                content_type=cls.content_type,
                filter={"location": [f"{locations[2].name}"]},
            ),
        ]


class DynamicGroupTest(DynamicGroupTestMixin, APIViewTestCases.APIViewTestCase):
    model = DynamicGroup
    choices_fields = ["content_type", "group_type"]

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        cls.create_data = [
            {
                "name": "API DynamicGroup 4",
                "content_type": "dcim.device",
                "filter": {"location": ["Location 1"]},
                "tags": [tag.pk for tag in Tag.objects.get_for_model(DynamicGroup)],
                "tenant": Tenant.objects.first().pk,
            },
            {
                "name": "API DynamicGroup 5",
                "content_type": "dcim.device",
                "group_type": "dynamic-filter",
                "filter": {"has_interfaces": False},
            },
            {
                "name": "API DynamicGroup 6",
                "content_type": "dcim.device",
                "filter": {"location": ["Location 2"]},
            },
            {
                "name": "API DynamicGroup 7",
                "content_type": "dcim.device",
                "group_type": "static",
            },
        ]
        cls.update_data = {
            "name": "A new name",
            "tags": [],
            "tenant": Tenant.objects.last().pk,
            "description": "a new description",
        }

    def test_changing_content_type_not_allowed(self):
        self.add_permissions("extras.change_dynamicgroup")
        data = {
            "content_type": "circuits.circuittermination",
        }
        response = self.client.patch(self._get_detail_url(self.groups[0]), data, format="json", **self.header)
        self.assertHttpStatus(response, status.HTTP_400_BAD_REQUEST)

    def test_get_members(self):
        """Test that the `/members/` API endpoint returns what is expected."""
        self.add_permissions("extras.view_dynamicgroup")
        instance = DynamicGroup.objects.filter(static_group_associations__isnull=False).distinct().first()
        self.add_permissions(get_permission_for_model(instance.content_type.model_class(), "view"))
        member_count = instance.members.count()
        url = reverse("extras-api:dynamicgroup-members", kwargs={"pk": instance.pk})
        response = self.client.get(url, **self.header)
        self.assertHttpStatus(response, status.HTTP_200_OK)
        self.assertEqual(member_count, len(response.json()["results"]))

    def test_get_members_with_constrained_permission(self):
        """Test that the `/members/` API endpoint enforces permissions on the member model."""
        self.add_permissions("extras.view_dynamicgroup")
        instance = DynamicGroup.objects.filter(static_group_associations__isnull=False).distinct().first()
        obj1 = instance.members.first()
        obj_perm = ObjectPermission(
            name="Test permission",
            constraints={"pk__in": [obj1.pk]},
            actions=["view"],
        )
        obj_perm.save()
        obj_perm.users.add(self.user)
        obj_perm.object_types.add(instance.content_type)

        url = reverse("extras-api:dynamicgroup-members", kwargs={"pk": instance.pk})
        response = self.client.get(url, **self.header)
        self.assertHttpStatus(response, status.HTTP_200_OK)
        self.assertEqual(response.json()["count"], 1)
        self.assertEqual(response.json()["results"][0]["id"], str(obj1.pk))


class DynamicGroupMembershipTest(DynamicGroupTestMixin, APIViewTestCases.APIViewTestCase):
    model = DynamicGroupMembership
    choices_fields = ["operator"]

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        parent = DynamicGroup.objects.create(
            name="parent",
            content_type=cls.content_type,
            filter={},
        )
        parent2 = DynamicGroup.objects.create(
            name="parent2",
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

    # TODO: Either improve test base or or write a more specific test for this model.
    @skip("DynamicGroupMembership has a `name` property but it's the Group name and not exposed on the API")
    def test_list_objects_ascending_ordered(self):
        pass

    @skip("DynamicGroupMembership has a `name` property but it's the Group name and not exposed on the API")
    def test_list_objects_descending_ordered(self):
        pass


class ExportTemplateTest(APIViewTestCases.APIViewTestCase):
    model = ExportTemplate
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


class ExternalIntegrationTest(APIViewTestCases.APIViewTestCase):
    model = ExternalIntegration
    create_data = [
        {
            "name": "Test External Integration 1",
            "remote_url": "ssh://example.com/test1/",
            "verify_ssl": False,
            "timeout": 5,
            "extra_config": "{'foo': 'bar'}",
            "http_method": WebhookHttpMethodChoices.METHOD_DELETE,
            "headers": "{'header': 'fake header'}",
            "ca_file_path": "/this/is/a/file/path",
        },
        {
            "name": "Test External Integration 2",
            "remote_url": "http://example.com/test2/",
            "http_method": WebhookHttpMethodChoices.METHOD_POST,
        },
        {
            "name": "Test External Integration 3",
            "remote_url": "https://example.com/test3/",
            "verify_ssl": True,
            "timeout": 30,
            "extra_config": "{'foo': ['bat', 'baz']}",
            "headers": "{'new_header': 'fake header'}",
            "ca_file_path": "/this/is/a/new/file/path",
        },
    ]
    bulk_update_data = {"timeout": 10, "verify_ssl": True, "extra_config": r"{}"}
    choices_fields = ["http_method"]


class FileProxyTest(
    APIViewTestCases.GetObjectViewTestCase,
    APIViewTestCases.ListObjectsViewTestCase,
):
    model = FileProxy

    @classmethod
    def setUpTestData(cls):
        job = Job.objects.first()
        job_results = (
            JobResult.objects.create(
                job_model=job,
                name=job.class_path,
                date_done=now(),
                status=JobResultStatusChoices.STATUS_SUCCESS,
            ),
            JobResult.objects.create(
                job_model=job,
                name=job.class_path,
                date_done=now(),
                status=JobResultStatusChoices.STATUS_SUCCESS,
            ),
            JobResult.objects.create(
                job_model=job,
                name=job.class_path,
                date_done=now(),
                status=JobResultStatusChoices.STATUS_SUCCESS,
            ),
        )
        cls.file_proxies = []
        for i, job_result in enumerate(job_results):
            file = SimpleUploadedFile(name=f"Output {i}.txt", content=f"Content {i}\n".encode("utf-8"))
            file_proxy = FileProxy.objects.create(name=file.name, file=file, job_result=job_result)
            cls.file_proxies.append(file_proxy)

    @override_settings(EXEMPT_VIEW_PERMISSIONS=[])
    def test_download_file_without_permission(self):
        """Test `download` action without permission."""
        url = reverse("extras-api:fileproxy-download", kwargs={"pk": self.file_proxies[0].pk})
        response = self.client.get(url, **self.header)
        self.assertHttpStatus(response, status.HTTP_403_FORBIDDEN)

    @override_settings(EXEMPT_VIEW_PERMISSIONS=[])
    def test_download_file_with_permission(self):
        """Test `download` action with permission."""
        obj_perm = ObjectPermission(
            name="Test permission", constraints={"pk": self.file_proxies[0].pk}, actions=["view"]
        )
        obj_perm.validated_save()
        obj_perm.object_types.add(ContentType.objects.get_for_model(self.model))
        obj_perm.users.add(self.user)

        # FileProxy permitted by permission
        url = reverse("extras-api:fileproxy-download", kwargs={"pk": self.file_proxies[0].pk})
        response = self.client.get(url, **self.header)
        self.assertHttpStatus(response, status.HTTP_200_OK)
        content = b"".join(data for data in response)
        self.assertEqual(content.decode("utf-8"), "Content 0\n")

        # FileProxy not permitted by permission
        url = reverse("extras-api:fileproxy-download", kwargs={"pk": self.file_proxies[1].pk})
        response = self.client.get(url, **self.header)
        self.assertHttpStatus(response, status.HTTP_404_NOT_FOUND)


class GitRepositoryTest(APIViewTestCases.APIViewTestCase):
    model = GitRepository
    bulk_update_data = {
        "branch": "develop",
    }
    choices_fields = ["provided_contents"]
    slug_source = "name"
    slugify_function = staticmethod(slugify_dashes_to_underscores)

    @classmethod
    def setUpTestData(cls):
        secrets_groups = (
            SecretsGroup.objects.create(name="Secrets Group 1"),
            SecretsGroup.objects.create(name="Secrets Group 2"),
        )

        cls.repos = (
            GitRepository(
                name="Repo 1",
                slug="repo_1",
                remote_url="https://example.com/repo1.git",
                secrets_group=secrets_groups[0],
            ),
            GitRepository(
                name="Repo 2",
                slug="repo_2",
                remote_url="https://example.com/repo2.git",
                secrets_group=secrets_groups[0],
            ),
            GitRepository(name="Repo 3", slug="repo_3", remote_url="https://example.com/repo3.git"),
        )
        for repo in cls.repos:
            repo.save()

        cls.create_data = [
            {
                "name": "New Git Repository 1",
                "slug": "new_git_repository_1",
                "remote_url": "https://example.com/newrepo1.git",
                "secrets_group": secrets_groups[1].pk,
                "provided_contents": ["extras.configcontext", "extras.exporttemplate"],
            },
            {
                "name": "New Git Repository 2",
                "slug": "new_git_repository_2",
                "remote_url": "https://example.com/newrepo2.git",
                "secrets_group": secrets_groups[1].pk,
            },
            {
                "name": "New Git Repository 3",
                "slug": "new_git_repository_3",
                "remote_url": "https://example.com/newrepo3.git",
                "secrets_group": secrets_groups[1].pk,
            },
            {
                "name": "New Git Repository 4",
                "remote_url": "https://example.com/newrepo3.git",
                "secrets_group": secrets_groups[1].pk,
            },
        ]

        # slug is enforced non-editable in clean because we want it to be providable by the user on creation
        # but not modified afterward
        cls.update_data = {
            "name": "A Different Repo Name",
            "remote_url": "https://example.com/fake.git",
        }

    @override_settings(EXEMPT_VIEW_PERMISSIONS=[])
    @mock.patch("nautobot.extras.api.views.get_worker_count")
    def test_run_git_sync_no_celery_worker(self, mock_get_worker_count):
        """Git sync cannot be triggered if Celery is not running."""
        mock_get_worker_count.return_value = 0
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
    @mock.patch("nautobot.extras.api.views.get_worker_count", return_value=1)
    def test_run_git_sync_with_permissions(self, _):
        """Git sync request can be submitted successfully."""
        self.add_permissions("extras.change_gitrepository")
        url = reverse("extras-api:gitrepository-sync", kwargs={"pk": self.repos[0].id})
        response = self.client.post(url, format="json", **self.header)
        self.assertHttpStatus(response, status.HTTP_200_OK)
        self.assertIn("message", response.data)
        self.assertIn("job_result", response.data)
        self.assertEqual(response.data["message"], f"Repository {self.repos[0].name} sync job added to queue.")
        self.assertIsInstance(response.data["job_result"], dict)

    def test_create_with_app_provided_contents(self):
        """Test that `provided_contents` published by an App works."""
        self.add_permissions("extras.add_gitrepository")
        self.add_permissions("extras.change_gitrepository")
        url = self._get_list_url()
        data = {
            "name": "app_test",
            "slug": "app_test",
            "remote_url": "https://localhost/app-test",
            "provided_contents": ["example_app.textfile"],
        }
        response = self.client.post(url, data, format="json", **self.header)
        self.assertHttpStatus(response, status.HTTP_201_CREATED)
        self.assertEqual(list(response.data["provided_contents"]), data["provided_contents"])


class GraphQLQueryTest(APIViewTestCases.APIViewTestCase):
    model = GraphQLQuery
    create_data = [
        {
            "name": "graphql-query-4",
            "query": "{ query: locations {name} }",
        },
        {
            "name": "graphql-query-5",
            "query": '{ devices(role: "edge") { id, name, role { name } } }',
        },
        {
            "name": "Graphql Query 6",
            "query": '{ devices(role: "edge") { id, name, role { name } } }',
        },
    ]

    choices_fields = ["owner_content_type"]

    @classmethod
    def setUpTestData(cls):
        cls.graphqlqueries = (
            GraphQLQuery(
                name="graphql-query-1",
                query="{ locations {name} }",
            ),
            GraphQLQuery(
                name="graphql-query-2",
                query='{ devices(role: "edge") { id, name, role { name } } }',
            ),
            GraphQLQuery(
                name="graphql-query-3",
                query=BIG_GRAPHQL_DEVICE_QUERY,
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
        self.assertEqual({"data": {"locations": []}}, response.data)

        url = reverse("extras-api:graphqlquery-run", kwargs={"pk": self.graphqlqueries[2].pk})
        response = self.client.post(url, **self.header)
        self.assertHttpStatus(response, status.HTTP_200_OK)
        self.assertEqual({"data": {"devices": []}}, response.data)


# TODO(Glenn): Standardize to APIViewTestCase (needs create & update tests)
class ImageAttachmentTest(
    APIViewTestCases.GetObjectViewTestCase,
    APIViewTestCases.ListObjectsViewTestCase,
    APIViewTestCases.DeleteObjectViewTestCase,
):
    model = ImageAttachment
    choices_fields = ["content_type"]

    @classmethod
    def setUpTestData(cls):
        ct = ContentType.objects.get_for_model(Location)

        location = Location.objects.filter(location_type=LocationType.objects.get(name="Campus")).first()

        ImageAttachment.objects.create(
            content_type=ct,
            object_id=location.pk,
            name="Image Attachment 1",
            image="http://example.com/image1.png",
            image_height=100,
            image_width=100,
        )
        ImageAttachment.objects.create(
            content_type=ct,
            object_id=location.pk,
            name="Image Attachment 2",
            image="http://example.com/image2.png",
            image_height=100,
            image_width=100,
        )
        ImageAttachment.objects.create(
            content_type=ct,
            object_id=location.pk,
            name="Image Attachment 3",
            image="http://example.com/image3.png",
            image_height=100,
            image_width=100,
        )

    # TODO: Unskip after resolving #2908, #2909
    @skip("DRF's built-in OrderingFilter triggering natural key attribute error in our base")
    def test_list_objects_ascending_ordered(self):
        pass

    @skip("DRF's built-in OrderingFilter triggering natural key attribute error in our base")
    def test_list_objects_descending_ordered(self):
        pass


class JobTest(
    # note no CreateObjectViewTestCase - we do not support user creation of Job records
    APIViewTestCases.GetObjectViewTestCase,
    APIViewTestCases.ListObjectsViewTestCase,
    APIViewTestCases.UpdateObjectViewTestCase,
    APIViewTestCases.DeleteObjectViewTestCase,
    APIViewTestCases.NotesURLViewTestCase,
):
    """Test cases for the Jobs REST API."""

    model = Job
    choices_fields = None

    def setUp(self):
        super().setUp()
        self.default_job_name = "api_test_job.APITestJob"
        self.job_class = get_job(self.default_job_name)
        self.assertIsNotNone(self.job_class)
        self.job_model = Job.objects.get_for_class_path(self.default_job_name)
        self.job_model.enabled = True
        self.job_model.validated_save()

    @classmethod
    def setUpTestData(cls):
        cls.update_data = {
            # source, module_name, job_class_name, installed are NOT editable
            "grouping_override": True,
            "grouping": "Overridden grouping",
            "name_override": True,
            "name": "Overridden name",
            "description_override": True,
            "description": "This is an overridden description.",
            "enabled": True,
            "approval_required_override": True,
            "approval_required": True,
            "dryrun_default_override": True,
            "dryrun_default": True,
            "hidden_override": True,
            "hidden": True,
            "soft_time_limit_override": True,
            "soft_time_limit": 350.1,
            "time_limit_override": True,
            "time_limit": 650,
            "has_sensitive_variables": False,
            "has_sensitive_variables_override": True,
        }
        cls.bulk_update_data = {
            "enabled": True,
            "approval_required_override": True,
            "approval_required": True,
            "has_sensitive_variables": False,
            "has_sensitive_variables_override": True,
        }

    run_success_response_status = status.HTTP_201_CREATED

    def get_run_url(self, class_path="api_test_job.APITestJob"):
        job_model = Job.objects.get_for_class_path(class_path)
        return reverse("extras-api:job-run", kwargs={"pk": job_model.pk})

    def get_deletable_object(self):
        """
        Get an instance that can be deleted.
        Exclude system jobs
        """
        # filter out the system jobs:
        queryset = self._get_queryset().exclude(module_name__startswith="nautobot.")
        instance = get_deletable_objects(self.model, queryset).first()
        if instance is None:
            self.fail("Couldn't find a single deletable object!")
        return instance

    def get_deletable_object_pks(self):
        """
        Get a list of PKs corresponding to jobs that can be safely bulk-deleted.
        Exclude system jobs
        """
        queryset = self._get_queryset().exclude(module_name__startswith="nautobot.")
        instances = get_deletable_objects(self.model, queryset).values_list("pk", flat=True)[:3]
        if len(instances) < 3:
            self.fail(f"Couldn't find 3 deletable objects, only found {len(instances)}!")
        return instances

    def test_delete_system_jobs_fail(self):
        self.add_permissions("extras.delete_job")
        instance = self._get_queryset().filter(module_name__startswith="nautobot.").first()
        job_name = instance.name
        url = self._get_detail_url(instance)
        self.client.delete(url, **self.header)
        # assert Job still exists
        self.assertTrue(self._get_queryset().filter(name=job_name).exists())
        self.user.is_superuser = True
        self.client.delete(url, **self.header)
        # assert Job still exists
        self.assertTrue(self._get_queryset().filter(name=job_name).exists())

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
            {"name": "var4", "type": "ObjectVar", "required": True, "model": "extras.role"},
        )

    def test_get_job_variables_by_name(self):
        """Test the job/<name>/variables API endpoint."""
        self.add_permissions("extras.view_job")
        route = get_route_for_model(self.model, "variables", api=True)
        response = self.client.get(reverse(route, kwargs={"name": self.job_model.name}), **self.header)
        self.assertEqual(4, len(response.data))  # 4 variables, in order
        self.assertEqual(response.data[0], {"name": "var1", "type": "StringVar", "required": True})
        self.assertEqual(response.data[1], {"name": "var2", "type": "IntegerVar", "required": True})
        self.assertEqual(response.data[2], {"name": "var3", "type": "BooleanVar", "required": False})
        self.assertEqual(
            response.data[3],
            {"name": "var4", "type": "ObjectVar", "required": True, "model": "extras.role"},
        )

    @override_settings(EXEMPT_VIEW_PERMISSIONS=["*"])
    def test_update_job_with_sensitive_variables_set_approval_required_to_true(self):
        job_model = Job.objects.get_for_class_path("api_test_job.APITestJob")
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
        job_model = Job.objects.get_for_class_path("api_test_job.APITestJob")
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
            constraints={"module_name__in": ["pass_job", "fail"]},
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
        job_model = Job.objects.get_for_class_path("pass_job.TestPassJob")
        job_model.enabled = True
        job_model.validated_save()
        url = self.get_run_url("pass_job.TestPassJob")
        response = self.client.post(url, **self.header)
        self.assertHttpStatus(response, self.run_success_response_status)

    @override_settings(EXEMPT_VIEW_PERMISSIONS=[])
    @mock.patch("nautobot.extras.api.views.get_worker_count")
    def test_run_job_not_enabled(self, mock_get_worker_count):
        """Job run request enforces the Job.enabled flag."""
        mock_get_worker_count.return_value = 1
        self.add_permissions("extras.run_job")

        job_model = Job.objects.get_for_class_path(self.default_job_name)
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
            module_name="uninstalled_module",
            job_class_name="NoSuchJob",
            grouping="Uninstalled Module",
            name="No such job",
            installed=False,
            enabled=True,
            default_job_queue=JobQueue.objects.get(name="default", queue_type=JobQueueTypeChoices.TYPE_CELERY),
        )
        job_model.validated_save()

        url = self.get_run_url("uninstalled_module.NoSuchJob")
        with disable_warnings("django.request"):
            response = self.client.post(url, {}, format="json", **self.header)
        self.assertHttpStatus(response, status.HTTP_405_METHOD_NOT_ALLOWED)

    @override_settings(EXEMPT_VIEW_PERMISSIONS=[])
    @mock.patch("nautobot.extras.api.views.get_worker_count")
    def test_run_job_no_worker(self, mock_get_worker_count):
        """Job run cannot be requested if Celery is not running."""
        mock_get_worker_count.return_value = 0
        self.add_permissions("extras.run_job")
        class_path = "api_test_job.APITestJob"
        job_model = Job.objects.get_for_class_path(class_path)
        # Make sure no queues are associated with it so it is using the celery default queue.
        # And the error message is deterministic on line 1573
        job_model.job_queues.set([])
        device_role = Role.objects.get_for_model(Device).first()
        job_data = {
            "var1": "FooBar",
            "var2": 123,
            "var3": False,
            "var4": device_role.pk,
        }

        data = {
            "data": job_data,
        }

        url = self.get_run_url()
        response = self.client.post(url, data, format="json", **self.header)
        self.assertHttpStatus(response, status.HTTP_503_SERVICE_UNAVAILABLE)
        self.assertEqual(
            response.data["detail"],
            f"Unable to process request: No celery workers running on queue {job_model.default_job_queue.name}.",
        )

    @override_settings(EXEMPT_VIEW_PERMISSIONS=["*"])
    @mock.patch("nautobot.extras.api.views.get_worker_count")
    def test_run_job_object_var(self, mock_get_worker_count):
        """Job run requests can reference objects by their primary keys."""
        mock_get_worker_count.return_value = 1
        self.add_permissions("extras.run_job")
        device_role = Role.objects.get_for_model(Device).first()
        job_data = {
            "var1": "FooBar",
            "var2": 123,
            "var3": False,
            "var4": device_role.pk,
        }

        data = {
            "data": job_data,
            "schedule": {
                "name": "test",
                "interval": "future",
                "start_time": str(now() + timedelta(minutes=1)),
            },
        }

        url = self.get_run_url()
        response = self.client.post(url, data, format="json", **self.header)
        self.assertHttpStatus(response, self.run_success_response_status)

        schedule = ScheduledJob.objects.last()
        self.assertEqual(schedule.kwargs["var4"], str(device_role.pk))

        self.assertIn("scheduled_job", response.data)
        self.assertIn("job_result", response.data)
        self.assertEqual(response.data["scheduled_job"]["id"], str(schedule.pk))
        self.assertEqual(response.data["scheduled_job"]["url"], self.absolute_api_url(schedule))
        self.assertEqual(response.data["scheduled_job"]["name"], schedule.name)
        # Python < 3.11 doesn't understand the datetime string "2023-04-27T18:33:16.017865Z",
        # but it *does* understand the string "2023-04-27T18:33:17.330836+00:00"
        self.assertEqual(
            datetime.fromisoformat(response.data["scheduled_job"]["start_time"].replace("Z", "+00:00")),
            schedule.start_time,
        )
        self.assertEqual(response.data["scheduled_job"]["interval"], schedule.interval)
        self.assertIsNone(response.data["job_result"])

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
        device_role = Role.objects.get_for_model(Device).first()
        job_data = {
            "var1": "FooBar",
            "var2": 123,
            "var3": False,
            "var4": device_role.pk,
        }

        data = {
            "data": job_data,
            # schedule is omitted
        }

        url = self.get_run_url()
        response = self.client.post(url, data, format="json", **self.header)
        self.assertHttpStatus(response, self.run_success_response_status)

        # Assert that a JobResult for this job was NOT created.
        self.assertFalse(JobResult.objects.filter(name=self.job_model.name).exists())

        # Assert that we have an immediate ScheduledJob and that it matches the job_model.
        schedule = ScheduledJob.objects.last()
        self.assertIsNotNone(schedule)
        self.assertEqual(schedule.interval, JobExecutionType.TYPE_FUTURE)
        self.assertEqual(schedule.approval_required, self.job_model.approval_required)
        self.assertEqual(schedule.kwargs["var4"], str(device_role.pk))

    @override_settings(EXEMPT_VIEW_PERMISSIONS=["*"])
    @mock.patch("nautobot.extras.api.views.get_worker_count")
    @mock.patch("nautobot.extras.models.jobs.JobResult.enqueue_job")
    def test_run_job_object_var_lookup(self, mock_enqueue_job, mock_get_worker_count):
        """Job run requests can reference objects by their attributes."""
        mock_get_worker_count.return_value = 1
        mock_enqueue_job.return_value = None
        self.add_permissions("extras.run_job")
        device_role = Role.objects.get_for_model(Device).first()
        job_data = {
            "var1": "FooBar",
            "var2": 123,
            "var3": False,
            "var4": {"name": device_role.name},
        }

        # This handles things like ObjectVar fields looked up by non-UUID
        # Jobs are executed with deserialized data
        deserialized_data = self.job_class.deserialize_data(job_data)
        self.job_model.job_queues.set([])

        self.assertEqual(
            deserialized_data,
            {"var1": "FooBar", "var2": 123, "var3": False, "var4": device_role},
        )

        url = self.get_run_url()
        response = self.client.post(url, {"data": job_data}, format="json", **self.header)
        self.assertHttpStatus(response, self.run_success_response_status)

        # Ensure the enqueue_job args deserialize to the same as originally inputted
        expected_enqueue_job_args = (self.job_model, self.user)
        expected_enqueue_job_kwargs = {
            "job_queue": self.job_model.default_job_queue,
            **self.job_class.serialize_data(deserialized_data),
        }
        mock_enqueue_job.assert_called_with(*expected_enqueue_job_args, **expected_enqueue_job_kwargs)

    @override_settings(EXEMPT_VIEW_PERMISSIONS=["*"])
    @mock.patch("nautobot.extras.api.views.get_worker_count")
    def test_run_job_response_job_result(self, mock_get_worker_count):
        """Test job run response contains nested job result."""
        mock_get_worker_count.return_value = 1
        self.add_permissions("extras.run_job")
        device_role = Role.objects.get_for_model(Device).first()
        job_data = {
            "var1": "FooBar",
            "var2": 123,
            "var3": False,
            "var4": {"name": device_role.name},
        }

        url = self.get_run_url()
        response = self.client.post(url, {"data": job_data}, format="json", **self.header)
        self.assertHttpStatus(response, self.run_success_response_status)

        job_result = JobResult.objects.filter(name=self.job_model.name).latest()

        self.assertIn("scheduled_job", response.data)
        self.assertIn("job_result", response.data)
        self.assertIsNone(response.data["scheduled_job"])
        data_job_result = response.data["job_result"]
        expected_data_job_result = JobResultSerializer(job_result, context={"request": response.wsgi_request}).data
        self.assertEqual(data_job_result, expected_data_job_result)

    @override_settings(EXEMPT_VIEW_PERMISSIONS=["*"])
    @mock.patch("nautobot.extras.api.views.get_worker_count")
    def test_run_job_with_both_task_queue_and_job_queue_specified(self, mock_get_worker_count):
        """Test job run response contains nested job result."""
        mock_get_worker_count.return_value = 1
        self.add_permissions("extras.run_job")
        device_role = Role.objects.get_for_model(Device).first()
        job_data = {
            "var1": "FooBar",
            "var2": 123,
            "var3": False,
            "var4": {"name": device_role.name},
        }

        url = self.get_run_url()
        response = self.client.post(
            url,
            {
                "data": job_data,
                "task_queue": "default",
                "job_queue": "default",
            },
            format="json",
            **self.header,
        )
        self.assertHttpStatus(response, status.HTTP_400_BAD_REQUEST)
        self.assertIn(
            "task_queue and job_queue are both specified. Please specify only one or another.", str(response.content)
        )

    @override_settings(EXEMPT_VIEW_PERMISSIONS=["*"])
    @mock.patch("nautobot.extras.api.views.get_worker_count")
    def test_run_job_file_data_commit(self, mock_get_worker_count):
        """Job run requests can reference objects by their attributes."""

        test_file = SimpleUploadedFile(name="test_file.txt", content=b"I am content.\n")

        job_model = Job.objects.get_for_class_path("field_order.TestFieldOrder")
        job_model.enabled = True
        job_model.validated_save()

        mock_get_worker_count.return_value = 1
        self.add_permissions("extras.run_job")

        job_data = {
            "var2": "Ground control to Major Tom",
            "var23": "Commencing countdown, engines on",
            "var1": test_file,
        }

        url = self.get_run_url(class_path="field_order.TestFieldOrder")
        response = self.client.post(url, data=job_data, **self.header)
        self.assertHttpStatus(response, self.run_success_response_status)

    @override_settings(EXEMPT_VIEW_PERMISSIONS=["*"])
    @mock.patch("nautobot.extras.api.views.get_worker_count")
    def test_run_job_file_data_only(self, mock_get_worker_count):
        """Job run requests can reference objects by their attributes."""

        test_file = SimpleUploadedFile(name="test_file.txt", content=b"I am content.\n")

        job_model = Job.objects.get_for_class_path("field_order.TestFieldOrder")
        job_model.enabled = True
        job_model.validated_save()

        mock_get_worker_count.return_value = 1
        self.add_permissions("extras.run_job")

        job_data = {
            "var2": "Ground control to Major Tom",
            "var23": "Commencing countdown, engines on",
            "var1": test_file,
        }

        url = self.get_run_url(class_path="field_order.TestFieldOrder")
        response = self.client.post(url, data=job_data, **self.header)
        self.assertHttpStatus(response, self.run_success_response_status)

    @override_settings(EXEMPT_VIEW_PERMISSIONS=["*"])
    @mock.patch("nautobot.extras.api.views.get_worker_count")
    def test_run_job_file_data_schedule(self, mock_get_worker_count):
        """Job run requests can reference objects by their attributes."""

        test_file = SimpleUploadedFile(name="test_file.txt", content=b"I am content.\n")

        job_model = Job.objects.get_for_class_path("field_order.TestFieldOrder")
        job_model.enabled = True
        job_model.validated_save()

        mock_get_worker_count.return_value = 1
        self.add_permissions("extras.run_job")

        job_data = {
            "var2": "Ground control to Major Tom",
            "var23": "Commencing countdown, engines on",
            "var1": test_file,
            "_schedule_start_time": str(now() + timedelta(minutes=1)),
            "_schedule_interval": "future",
            "_schedule_name": "test",
        }

        url = self.get_run_url(class_path="field_order.TestFieldOrder")
        response = self.client.post(url, data=job_data, **self.header)
        self.assertHttpStatus(response, self.run_success_response_status)

    @override_settings(EXEMPT_VIEW_PERMISSIONS=["*"])
    @mock.patch("nautobot.extras.api.views.get_worker_count")
    def test_run_job_future(self, mock_get_worker_count):
        """In addition to the base test case provided by JobAPIRunTestMixin, also verify the JSON response data."""
        mock_get_worker_count.return_value = 1
        self.add_permissions("extras.run_job")
        d = Role.objects.get_for_model(Device).first()
        data = {
            "data": {"var1": "x", "var2": 1, "var3": False, "var4": d.pk},
            "schedule": {
                "start_time": str(now() + timedelta(minutes=1)),
                "interval": "future",
                "name": "test",
            },
        }

        url = self.get_run_url()
        response = self.client.post(url, data, format="json", **self.header)
        self.assertHttpStatus(response, self.run_success_response_status)

        schedule = ScheduledJob.objects.last()
        self.assertIn("scheduled_job", response.data)
        self.assertIn("job_result", response.data)
        self.assertEqual(response.data["scheduled_job"]["id"], str(schedule.pk))
        self.assertEqual(response.data["scheduled_job"]["url"], self.absolute_api_url(schedule))
        self.assertEqual(response.data["scheduled_job"]["name"], schedule.name)
        # Python < 3.11 doesn't understand the datetime string "2023-04-27T18:33:16.017865Z",
        # but it *does* understand the string "2023-04-27T18:33:17.330836+00:00"
        self.assertEqual(
            datetime.fromisoformat(response.data["scheduled_job"]["start_time"].replace("Z", "+00:00")),
            schedule.start_time,
        )
        self.assertEqual(response.data["scheduled_job"]["interval"], schedule.interval)
        self.assertIsNone(response.data["job_result"])

    @override_settings(EXEMPT_VIEW_PERMISSIONS=["*"])
    @mock.patch("nautobot.extras.api.views.get_worker_count")
    def test_run_a_job_with_sensitive_variables_for_future(self, mock_get_worker_count):
        mock_get_worker_count.return_value = 1
        self.add_permissions("extras.run_job")

        job_model = Job.objects.get(job_class_name="TestHasSensitiveVariables")
        job_model.enabled = True
        job_model.validated_save()

        url = reverse("extras-api:job-run", kwargs={"pk": job_model.pk})
        data = {
            "data": {},
            "schedule": {
                "start_time": str(now() + timedelta(minutes=1)),
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
    @mock.patch("nautobot.extras.api.views.get_worker_count", return_value=1)
    def test_run_a_job_with_sensitive_variables_immediately(self, _):
        self.add_permissions("extras.run_job")
        d = Role.objects.get_for_model(Device).first()
        data = {
            "data": {"var1": "x", "var2": 1, "var3": False, "var4": d.pk},
            "schedule": {
                "interval": "immediately",
                "name": "test",
            },
        }
        self.job_model.has_sensitive_variables = True
        self.job_model.has_sensitive_variables_override = True
        self.job_model.validated_save()

        url = self.get_run_url()
        response = self.client.post(url, data, format="json", **self.header)
        self.assertHttpStatus(response, self.run_success_response_status)

        job_result = JobResult.objects.get(name=self.job_model.name)
        self.assertEqual(job_result.task_kwargs, {})

    @override_settings(EXEMPT_VIEW_PERMISSIONS=["*"])
    @mock.patch("nautobot.extras.api.views.get_worker_count")
    def test_run_job_future_past(self, mock_get_worker_count):
        mock_get_worker_count.return_value = 1
        self.add_permissions("extras.run_job")
        d = Role.objects.get_for_model(Device).first()
        data = {
            "data": {"var1": "x", "var2": 1, "var3": False, "var4": d.pk},
            "schedule": {
                "start_time": str(now() - timedelta(minutes=1)),
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
        d = Role.objects.get_for_model(Device).first()
        data = {
            "data": {"var1": "x", "var2": 1, "var3": False, "var4": d.pk},
            "schedule": {
                "start_time": str(now() + timedelta(minutes=1)),
                "interval": "hourly",
                "name": "test",
            },
        }

        url = self.get_run_url()
        response = self.client.post(url, data, format="json", **self.header)
        self.assertHttpStatus(response, self.run_success_response_status)

        schedule = ScheduledJob.objects.last()

        self.assertIn("scheduled_job", response.data)
        self.assertIn("job_result", response.data)
        self.assertEqual(response.data["scheduled_job"]["id"], str(schedule.pk))
        self.assertEqual(response.data["scheduled_job"]["url"], self.absolute_api_url(schedule))
        self.assertEqual(response.data["scheduled_job"]["name"], schedule.name)
        # Python < 3.11 doesn't understand the datetime string "2023-04-27T18:33:16.017865Z",
        # but it *does* understand the string "2023-04-27T18:33:17.330836+00:00"
        self.assertEqual(
            datetime.fromisoformat(response.data["scheduled_job"]["start_time"].replace("Z", "+00:00")),
            schedule.start_time,
        )
        self.assertEqual(response.data["scheduled_job"]["interval"], schedule.interval)
        self.assertIsNone(response.data["job_result"])

    @override_settings(EXEMPT_VIEW_PERMISSIONS=[])
    def test_run_job_with_invalid_data(self):
        self.add_permissions("extras.run_job")

        data = {
            "data": "invalid",
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
        d = Role.objects.get_for_model(Device).first()
        data = {
            "data": {"var1": "x", "var2": 1, "var3": False, "var4": d.pk},
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
        d = Role.objects.get_for_model(Device).first()
        data = {
            "data": {"var1": "x", "var2": 1, "var3": False, "var4": d.pk},
            "task_queue": settings.CELERY_TASK_DEFAULT_QUEUE,
        }
        jq, _ = JobQueue.objects.get_or_create(
            name=settings.CELERY_TASK_DEFAULT_QUEUE, defaults={"queue_type": JobQueueTypeChoices.TYPE_CELERY}
        )
        self.job_model.job_queues.set([jq])
        url = self.get_run_url()
        response = self.client.post(url, data, format="json", **self.header)
        self.assertHttpStatus(response, self.run_success_response_status)

    @override_settings(EXEMPT_VIEW_PERMISSIONS=[])
    @mock.patch("nautobot.extras.api.views.get_worker_count", return_value=1)
    def test_run_job_with_default_queue_with_empty_job_model_job_queues(self, _):
        self.add_permissions("extras.run_job")
        job_model = Job.objects.get_for_class_path("pass_job.TestPassJob")
        data = {
            "task_queue": job_model.default_job_queue.name,
        }

        job_model.job_queues.set([])
        job_model.enabled = True
        job_model.validated_save()
        url = self.get_run_url("pass_job.TestPassJob")
        response = self.client.post(url, data, format="json", **self.header)
        self.assertHttpStatus(response, self.run_success_response_status)

    # TODO: Either improve test base or or write a more specific test for this model.
    @skip("Job has a `name` property but grouping is also used to sort Jobs")
    def test_list_objects_ascending_ordered(self):
        pass

    @skip("Job has a `name` property but grouping is also used to sort Jobs")
    def test_list_objects_descending_ordered(self):
        pass


class JobHookTest(APIViewTestCases.APIViewTestCase):
    model = JobHook
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

    @classmethod
    def setUpTestData(cls):
        jhr_log = Job.objects.get(job_class_name="TestJobHookReceiverLog")
        jhr_log.enabled = True
        jhr_log.save()
        jhr_change = Job.objects.get(job_class_name="TestJobHookReceiverChange")
        jhr_change.enabled = True
        jhr_change.save()
        jhr_fail = Job.objects.get(job_class_name="TestJobHookReceiverFail")
        jhr_fail.enabled = True
        jhr_fail.save()

        cls.create_data = [
            {
                "name": "JobHook4",
                "content_types": ["dcim.consoleport"],
                "type_delete": True,
                "job": jhr_log.pk,
                "enabled": False,
            },
            {
                "name": "JobHook5",
                "content_types": ["dcim.consoleport"],
                "type_delete": True,
                "job": jhr_change.pk,
                "enabled": False,
            },
            {
                "name": "JobHook6",
                "content_types": ["dcim.consoleport"],
                "type_delete": True,
                "job": jhr_fail.pk,
                "enabled": False,
            },
        ]
        cls.job_hooks = (
            JobHook(
                name="JobHook1",
                job=jhr_log,
                type_create=True,
                type_delete=True,
            ),
            JobHook(
                name="JobHook2",
                job=jhr_change,
                type_create=True,
                type_delete=True,
            ),
            JobHook(
                name="JobHook3",
                job=jhr_fail,
                type_create=True,
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

        self.add_permissions("extras.add_jobhook", "extras.view_job")
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

        self.add_permissions("extras.change_jobhook", "extras.view_job")
        job_hook2 = JobHook.objects.get(name="JobHook2")
        response = self.client.patch(self._get_detail_url(job_hook2), data, format="json", **self.header)
        self.assertContains(
            response,
            "A job hook already exists for delete on dcim | device type to job TestJobHookReceiverLog",
            status_code=400,
        )


class JobButtonTest(APIViewTestCases.APIViewTestCase):
    model = JobButton
    choices_fields = ["button_class"]

    @classmethod
    def setUpTestData(cls):
        jbr_simple = Job.objects.get(job_class_name="TestJobButtonReceiverSimple")
        jbr_simple.enabled = True
        jbr_simple.save()
        jbr_complex = Job.objects.get(job_class_name="TestJobButtonReceiverComplex")
        jbr_complex.enabled = True
        jbr_complex.save()

        cls.create_data = [
            {
                "name": "JobButton4",
                "text": "JobButton4",
                "content_types": ["dcim.location"],
                "job": jbr_simple.pk,
            },
            {
                "name": "JobButton5",
                "text": "JobButton5",
                "content_types": ["circuits.circuit"],
                "job": jbr_complex.pk,
            },
        ]
        location_type = ContentType.objects.get_for_model(Location)
        device_type = ContentType.objects.get_for_model(Device)

        location_jb = JobButton(
            name="api-test-location",
            text="API job button location text",
            job=jbr_simple,
            weight=100,
            confirmation=True,
        )
        location_jb.save()
        location_jb.content_types.set([location_type])

        device_jb = JobButton.objects.create(
            name="api-test-device",
            text="API job button device text",
            job=jbr_simple,
            weight=100,
            confirmation=True,
        )
        device_jb.save()
        device_jb.content_types.set([device_type])

        complex_jb = JobButton.objects.create(
            name="api-test-complex",
            text="API job button complex text",
            job=jbr_complex,
            weight=100,
            confirmation=True,
        )
        complex_jb.save()
        complex_jb.content_types.set([device_type, location_type])


class JobResultTest(
    APIViewTestCases.GetObjectViewTestCase,
    APIViewTestCases.ListObjectsViewTestCase,
    APIViewTestCases.DeleteObjectViewTestCase,
):
    model = JobResult

    @classmethod
    def setUpTestData(cls):
        jobs = Job.objects.all()[:2]

        JobResult.objects.create(
            job_model=jobs[0],
            name=jobs[0].class_path,
            date_done=now(),
            user=None,
            status=JobResultStatusChoices.STATUS_SUCCESS,
            task_kwargs={},
            scheduled_job=None,
        )
        JobResult.objects.create(
            job_model=None,
            name="deleted_module.deleted_job",
            date_done=now(),
            user=None,
            status=JobResultStatusChoices.STATUS_SUCCESS,
            task_kwargs={"repository_pk": uuid.uuid4()},
            scheduled_job=None,
        )
        JobResult.objects.create(
            job_model=jobs[1],
            name=jobs[1].class_path,
            date_done=None,
            user=None,
            status=JobResultStatusChoices.STATUS_PENDING,
            task_kwargs={"data": {"device": uuid.uuid4(), "multichoices": ["red", "green"], "checkbox": False}},
            scheduled_job=None,
        )


class JobLogEntryTest(
    APIViewTestCases.GetObjectViewTestCase,
    APIViewTestCases.ListObjectsViewTestCase,
):
    model = JobLogEntry
    choices_fields = []

    @classmethod
    def setUpTestData(cls):
        cls.job_result = JobResult.objects.create(name="test")

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
        self.assertEqual(len(response.json()), JobLogEntry.objects.filter(job_result=self.job_result).count())


class JobQueueTestCase(APIViewTestCases.APIViewTestCase):
    model = JobQueue
    choices_fields = ["queue_type"]

    def setUp(self):
        super().setUp()
        self.create_data = [
            {
                "name": "Test API Job Queue 1",
                "queue_type": JobQueueTypeChoices.TYPE_CELERY,
                "description": "Job Queue 1 for API Testing",
                "tenant": Tenant.objects.first().pk,
            },
            {
                "name": "Test API Job Queue 2",
                "queue_type": JobQueueTypeChoices.TYPE_KUBERNETES,
                "description": "Job Queue 2 for API Testing",
                "tenant": Tenant.objects.first().pk,
            },
            {
                "name": "Test API Job Queue 3",
                "queue_type": JobQueueTypeChoices.TYPE_CELERY,
                "description": "Job Queue 3 for API Testing",
                "tenant": Tenant.objects.last().pk,
                "tags": [tag.pk for tag in Tag.objects.get_for_model(JobQueue)],
            },
        ]


class JobQueueAssignmentTestCase(APIViewTestCases.APIViewTestCase):
    model = JobQueueAssignment

    def setUp(self):
        super().setUp()
        jobs = Job.objects.all()[:3]
        job_queues = JobQueue.objects.all()[:3]
        JobQueueAssignment.objects.all().delete()
        JobQueueAssignment.objects.create(job=jobs[0], job_queue=job_queues[0])
        JobQueueAssignment.objects.create(job=jobs[1], job_queue=job_queues[1])
        JobQueueAssignment.objects.create(job=jobs[2], job_queue=job_queues[2])
        self.create_data = [
            {
                "job": jobs[0].pk,
                "job_queue": job_queues[1].pk,
            },
            {
                "job": jobs[1].pk,
                "job_queue": job_queues[2].pk,
            },
            {
                "job": jobs[0].pk,
                "job_queue": job_queues[2].pk,
            },
        ]


class SavedViewTest(APIViewTestCases.APIViewTestCase):
    model = SavedView

    def setUp(self):
        super().setUp()
        self.create_data = [
            {
                "owner": self.user.pk,
                "name": "Saved View 1",
                "view": "circuits:circuit_list",
                "config": {
                    "filter_params": {"circuit_type": ["#047c4c", "#06cc23"], "status": ["Active", "Decommissioned"]}
                },
                "is_global_default": False,
                "is_shared": True,
            },
            {
                "owner": self.user.pk,
                "name": "Saved View 2",
                "view": "dcim:device_list",
                "config": {
                    "filter_params": {
                        "location": ["Campus-01", "Building-02", "Aisle-06"],
                        "role": ["PossibleDangerous", "NervousDangerous"],
                        "status": ["Active", "ExtremeOriginal"],
                    }
                },
                "is_global_default": False,
                "is_shared": False,
            },
            {
                "owner": self.user.pk,
                "name": "Saved View 3",
                "view": "dcim:location_list",
                "config": {
                    "filter_params": {
                        "location_type": ["Campus", "Building", "Elevator"],
                        "parent": ["Campus-01", "Building-02"],
                        "q": "building-02",
                    },
                    "pagination_count": 50,
                    "sort_order": [],
                    "table_config": {
                        "LocationTable": {
                            "columns": ["name", "status", "location_type", "description", "parent", "tenant"]
                        }
                    },
                },
                "is_global_default": False,
                "is_shared": True,
            },
        ]


class UserSavedViewAssociationTest(APIViewTestCases.APIViewTestCase):
    model = UserSavedViewAssociation

    @classmethod
    def setUpTestData(cls):
        cls.saved_view_views_distinct = SavedView.objects.values("view").distinct()
        cls.users = User.objects.all()

        cls.create_data = []
        for i, saved_view in enumerate(cls.saved_view_views_distinct[:3]):
            sv = SavedView.objects.filter(view=saved_view["view"]).first()
            cls.create_data.append(
                {
                    "user": cls.users[i].pk,
                    "saved_view": sv.pk,
                    "view_name": sv.view,
                }
            )
        for i, saved_view in enumerate(cls.saved_view_views_distinct[4:7]):
            sv = SavedView.objects.filter(view=saved_view["view"]).first()
            UserSavedViewAssociation.objects.create(
                user=cls.users[i],
                saved_view=sv,
                view_name=sv.view,
            )

    def test_creating_invalid_user_to_saved_view(self):
        # Add object-level permission
        duplicate_view_name = self.saved_view_views_distinct[0]["view"]
        saved_view = SavedView.objects.filter(view=duplicate_view_name).first()
        user = self.users[0]
        UserSavedViewAssociation.objects.create(
            saved_view=saved_view,
            user=user,
            view_name=saved_view.view,
        )
        duplicate_user_to_savedview_create_data = {
            "user": user.pk,
            "saved_view": saved_view.pk,
            "view_name": duplicate_view_name,
        }
        self.add_permissions("extras.add_usersavedviewassociation", "users.view_user", "extras.view_savedview")
        response = self.client.post(
            self._get_list_url(), duplicate_user_to_savedview_create_data, format="json", **self.header
        )
        self.assertHttpStatus(response, status.HTTP_400_BAD_REQUEST)
        self.assertIn("User saved view association with this User and View name already exists.", str(response.content))


class ScheduledJobTest(
    APIViewTestCases.GetObjectViewTestCase,
    APIViewTestCases.ListObjectsViewTestCase,
):
    model = ScheduledJob
    choices_fields = []

    @classmethod
    def setUpTestData(cls):
        user = User.objects.create(username="user1", is_active=True)
        job_model = Job.objects.get_for_class_path("pass_job.TestPassJob")
        ScheduledJob.objects.create(
            name="test1",
            task="pass_job.TestPassJob",
            job_model=job_model,
            interval=JobExecutionType.TYPE_IMMEDIATELY,
            user=user,
            approval_required=True,
            start_time=now(),
        )
        ScheduledJob.objects.create(
            name="test2",
            task="pass_job.TestPassJob",
            job_model=job_model,
            interval=JobExecutionType.TYPE_DAILY,
            user=user,
            approval_required=True,
            start_time=datetime(2020, 1, 23, 12, 34, 56, tzinfo=ZoneInfo("America/New_York")),
            time_zone=ZoneInfo("America/New_York"),
        )
        ScheduledJob.objects.create(
            name="test3",
            task="pass_job.TestPassJob",
            job_model=job_model,
            interval=JobExecutionType.TYPE_CUSTOM,
            crontab="34 12 * * *",
            enabled=False,
            user=user,
            approval_required=True,
            start_time=now(),
        )


class JobApprovalTest(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.additional_user = User.objects.create(username="user1", is_active=True)
        cls.job_model = Job.objects.get_for_class_path("pass_job.TestPassJob")
        cls.job_model.enabled = True
        cls.job_model.save()
        cls.scheduled_job = ScheduledJob.objects.create(
            name="test pass",
            task="pass_job.TestPassJob",
            job_model=cls.job_model,
            interval=JobExecutionType.TYPE_IMMEDIATELY,
            user=cls.additional_user,
            approval_required=True,
            start_time=now(),
        )
        cls.dryrun_job_model = Job.objects.get_for_class_path("dry_run.TestDryRun")
        cls.dryrun_job_model.enabled = True
        cls.dryrun_job_model.save()
        cls.dryrun_scheduled_job = ScheduledJob.objects.create(
            name="test dryrun",
            task="dry_run.TestDryRun",
            job_model=cls.dryrun_job_model,
            kwargs={"value": 1},
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
            task="pass_job.TestPassJob",
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
            task="pass_job.TestPassJob",
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
            task="pass_job.TestPassJob",
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
        url = reverse("extras-api:scheduledjob-dry-run", kwargs={"pk": self.dryrun_scheduled_job.pk})
        with disable_warnings("django.request"):
            response = self.client.post(url, **self.header)
        self.assertHttpStatus(response, status.HTTP_403_FORBIDDEN)

    @override_settings(EXEMPT_VIEW_PERMISSIONS=["*"])
    def test_dry_run_job_without_run_job_permission(self):
        self.add_permissions("extras.view_scheduledjob")
        url = reverse("extras-api:scheduledjob-dry-run", kwargs={"pk": self.dryrun_scheduled_job.pk})
        response = self.client.post(url, **self.header)
        self.assertHttpStatus(response, status.HTTP_403_FORBIDDEN)

    @override_settings(EXEMPT_VIEW_PERMISSIONS=["*"])
    def test_dry_run_job(self):
        self.add_permissions("extras.run_job", "extras.view_scheduledjob")
        url = reverse("extras-api:scheduledjob-dry-run", kwargs={"pk": self.dryrun_scheduled_job.pk})
        response = self.client.post(url, **self.header)
        self.assertHttpStatus(response, status.HTTP_200_OK)
        # The below fails because JobResult.task_kwargs doesn't get set until *after* the task begins executing.
        # self.assertEqual(response.data["task_kwargs"], {"dryrun": True, "value": 1}, response.data)

    @override_settings(EXEMPT_VIEW_PERMISSIONS=["*"])
    def test_dry_run_not_supported(self):
        self.add_permissions("extras.run_job", "extras.view_scheduledjob")
        url = reverse("extras-api:scheduledjob-dry-run", kwargs={"pk": self.scheduled_job.pk})
        response = self.client.post(url, **self.header)
        self.assertHttpStatus(response, status.HTTP_405_METHOD_NOT_ALLOWED)


class MetadataTypeTest(APIViewTestCases.APIViewTestCase):
    model = MetadataType
    choices_fields = ["data_type"]
    create_data = [
        {
            "name": "System of Record",
            "description": "The SoR that this record or field originates from",
            "data_type": MetadataTypeDataTypeChoices.TYPE_TEXT,
            "content_types": ["dcim.device", "dcim.interface", "ipam.ipaddress"],
        },
        {
            "name": "Last Synced",
            "description": "The last time this record or field was synced from the SoR",
            "data_type": MetadataTypeDataTypeChoices.TYPE_DATETIME,
            "content_types": ["dcim.device", "dcim.interface", "ipam.ipaddress"],
        },
        {
            "name": "Data Owner",
            "data_type": MetadataTypeDataTypeChoices.TYPE_CONTACT_TEAM,
            "content_types": ["extras.customfield"],
        },
    ]
    update_data = {
        "name": "Something new",
        "description": "A new name for existing metadata.",
        "content_types": ["dcim.interface", "ipam.vrf"],
    }

    def get_deletable_object(self):
        return MetadataType.objects.create(name="Delete Me", data_type=MetadataTypeDataTypeChoices.TYPE_SELECT)

    def get_deletable_object_pks(self):
        mdts = [
            MetadataType.objects.create(name="SoR", data_type=MetadataTypeDataTypeChoices.TYPE_SELECT),
            MetadataType.objects.create(name="Colors", data_type=MetadataTypeDataTypeChoices.TYPE_MULTISELECT),
            MetadataType.objects.create(
                name="Location Metadata Type", data_type=MetadataTypeDataTypeChoices.TYPE_SELECT
            ),
        ]
        return [mdt.pk for mdt in mdts]


class MetadataChoiceTest(APIViewTestCases.APIViewTestCase):
    model = MetadataChoice

    update_data = {
        "value": "Something new",
        "weight": 0,
    }

    @classmethod
    def setUpTestData(cls):
        mdts = [
            MetadataType.objects.create(name="SoR", data_type=MetadataTypeDataTypeChoices.TYPE_SELECT),
            MetadataType.objects.create(name="Colors", data_type=MetadataTypeDataTypeChoices.TYPE_MULTISELECT),
        ]

        cls.create_data = [
            {
                "metadata_type": mdts[0].pk,
                "value": "ServiceNow",
                "weight": 200,
            },
            {
                "metadata_type": mdts[0].pk,
                "value": "IPFabric",
            },
            {
                "metadata_type": mdts[1].pk,
                "value": "red",
                "weight": 250,
            },
            {
                "metadata_type": mdts[1].pk,
                "value": "green",
                "weight": 250,
            },
        ]


class ObjectMetadataTest(APIViewTestCases.APIViewTestCase):
    model = ObjectMetadata
    choices_fields = ["assigned_object_type"]
    # ObjectMetadata records created for SoftwareImageFile records will contain a `hashing_algorithm` key;
    # presence of strings like "md5" and "sha256" in the API response for ObjectMetadatas is therefore *not* a failure
    VERBOTEN_STRINGS = ("password",)

    @classmethod
    def setUpTestData(cls):
        # Delete existing metadata objects to avoid conflicts with generate_test_data randomness.
        ObjectMetadata.objects.all().delete()
        mdts = [
            MetadataType.objects.create(name="Location Metadata Type", data_type=MetadataTypeDataTypeChoices.TYPE_TEXT),
            MetadataType.objects.create(name="Device Metadata Type", data_type=MetadataTypeDataTypeChoices.TYPE_TEXT),
            MetadataType.objects.create(
                name="Contact/Team Metadata Type", data_type=MetadataTypeDataTypeChoices.TYPE_CONTACT_TEAM
            ),
        ]
        mdts[0].content_types.set(list(ContentType.objects.values_list("pk", flat=True)))
        mdts[1].content_types.set(list(ContentType.objects.values_list("pk", flat=True)))
        mdts[2].content_types.set(list(ContentType.objects.values_list("pk", flat=True)))
        ObjectMetadata.objects.create(
            metadata_type=mdts[0],
            value="Hey",
            scoped_fields=["parent", "status"],
            assigned_object_type=ContentType.objects.get_for_model(IPAddress),
            assigned_object_id=IPAddress.objects.filter(associated_object_metadata__isnull=True).first().pk,
        )
        ObjectMetadata.objects.create(
            metadata_type=mdts[0],
            value="Hello",
            scoped_fields=["namespace"],
            assigned_object_type=ContentType.objects.get_for_model(Prefix),
            assigned_object_id=Prefix.objects.filter(associated_object_metadata__isnull=True).first().pk,
        )
        ObjectMetadata.objects.create(
            metadata_type=mdts[2],
            contact=Contact.objects.first(),
            scoped_fields=["status"],
            assigned_object_type=ContentType.objects.get_for_model(Prefix),
            assigned_object_id=Prefix.objects.filter(associated_object_metadata__isnull=True).last().pk,
        )
        cls.create_data = [
            {
                "metadata_type": mdts[0].pk,
                "scoped_fields": ["location_type"],
                "value": "random words",
                "assigned_object_type": "dcim.location",
                "assigned_object_id": Location.objects.filter(associated_object_metadata__isnull=True).first().pk,
            },
            {
                "metadata_type": mdts[1].pk,
                "scoped_fields": ["name"],
                "value": "random words",
                "assigned_object_type": "dcim.location",
                "assigned_object_id": Location.objects.filter(associated_object_metadata__isnull=True).first().pk,
            },
            {
                "metadata_type": mdts[2].pk,
                "scoped_fields": [],
                "contact": Contact.objects.first().pk,
                "assigned_object_type": "dcim.device",
                "assigned_object_id": Device.objects.filter(associated_object_metadata__isnull=True).first().pk,
            },
            {
                "metadata_type": mdts[2].pk,
                "scoped_fields": ["interfaces"],
                "team": Team.objects.first().pk,
                "assigned_object_type": "dcim.device",
                "assigned_object_id": Device.objects.filter(associated_object_metadata__isnull=True).last().pk,
            },
        ]
        cls.update_data = {
            "scoped_fields": ["pk"],
        }

    def get_deletable_object(self):
        # TODO: CSV round-trip doesn't work for empty scoped_fields values at present. :-(
        instance = get_deletable_objects(self.model, self._get_queryset().exclude(scoped_fields=[])).first()
        if instance is None:
            self.fail("Couldn't find a single deletable object with non-empty scoped_fields")
        return instance


class NoteTest(APIViewTestCases.APIViewTestCase):
    model = Note
    choices_fields = ["assigned_object_type"]

    @classmethod
    def setUpTestData(cls):
        cls.location1 = Location.objects.filter(location_type=LocationType.objects.get(name="Campus")).first()
        location2 = Location.objects.filter(location_type=LocationType.objects.get(name="Campus")).last()
        cls.location_ct = ContentType.objects.get_for_model(Location)
        user1 = User.objects.create(username="user1", is_active=True)
        user2 = User.objects.create(username="user2", is_active=True)

        cls.create_data = [
            {
                "note": "This is a test.",
                "assigned_object_id": cls.location1.pk,
                "assigned_object_type": "dcim.location",
            },
            {
                "note": "This is a test.",
                "assigned_object_id": location2.pk,
                "assigned_object_type": "dcim.location",
            },
            {
                "note": "This is a note on location 1.",
                "assigned_object_id": cls.location1.pk,
                "assigned_object_type": "dcim.location",
            },
        ]
        cls.bulk_update_data = {
            "note": "Bulk change.",
        }
        Note.objects.create(
            note="location has been placed on maintenance.",
            user=user1,
            assigned_object_type=cls.location_ct,
            assigned_object_id=cls.location1.pk,
        )
        Note.objects.create(
            note="location maintenance has ended.",
            user=user1,
            assigned_object_type=cls.location_ct,
            assigned_object_id=cls.location1.pk,
        )
        Note.objects.create(
            note="location is under duress.",
            user=user2,
            assigned_object_type=cls.location_ct,
            assigned_object_id=location2.pk,
        )

    def get_deletable_object(self):
        """
        Users only create self-authored notes via the REST API; test_recreate_object_csv needs self.user as author.
        """
        return Note.objects.create(
            note="Delete me!",
            user=self.user,
            assigned_object_type=self.location_ct,
            assigned_object_id=self.location1.pk,
        )


class ObjectChangeTest(APIViewTestCases.GetObjectViewTestCase, APIViewTestCases.ListObjectsViewTestCase):
    model = ObjectChange

    # ObjectChange records created for SoftwareImageFile records will contain a `hashing_algorithm` key;
    # presence of strings like "md5" and "sha256" in the API response for ObjectChanges is therefore *not* a failure
    VERBOTEN_STRINGS = ("password",)

    @classmethod
    def setUpTestData(cls):
        cc = ConfigContext.objects.create(name="Config Context 1", weight=100, data={"foo": 123})
        cc_oc = cc.to_objectchange(ObjectChangeActionChoices.ACTION_CREATE)
        cc_oc.request_id = uuid.uuid4()
        cc_oc.change_context = ObjectChangeEventContextChoices.CONTEXT_WEB
        cc_oc.change_context_detail = "extras:configcontext_edit"
        cc_oc.validated_save()

        location_oc = Location.objects.first().to_objectchange(ObjectChangeActionChoices.ACTION_UPDATE)
        location_oc.request_id = uuid.uuid4()
        location_oc.change_context = ObjectChangeEventContextChoices.CONTEXT_ORM
        location_oc.validated_save()

        git_oc = ObjectChange.objects.create(
            user=None,
            user_name="deleted",
            request_id=cc_oc.request_id,
            action=ObjectChangeActionChoices.ACTION_DELETE,
            changed_object_type=ContentType.objects.get_for_model(GitRepository),
            changed_object_id=uuid.UUID("7af2e8d5-6d53-4b79-b488-60448aaaa9e8"),
            change_context=ObjectChangeEventContextChoices.CONTEXT_WEB,
            change_context_detail="extras:gitrepository_delete",
            related_object=cc_oc.changed_object,
            object_repr="demo-git-datasource 2",
            object_data={
                "name": "demo-git-datasource 2",
                "slug": "demo_git_datasource_2",
                "tags": [],
                "branch": "main",
                "created": "2023-06-07T12:49:34.309Z",
                "remote_url": "https://github.com/nautobot/demo-git-datasource.git",
                "current_head": "94e88b76e87ccf1fdf48995d72ede86db4623d60",
                "last_updated": "2023-06-07T12:49:36.368Z",
                "custom_fields": {},
                "secrets_group": None,
                "provided_contents": ["extras.configcontext", "extras.configcontextschema", "extras.exporttemplate"],
            },
            object_data_v2={
                "id": "7af2e8d5-6d53-4b79-b488-60448aaaa9e8",
                "url": "/api/extras/git-repositories/7af2e8d5-6d53-4b79-b488-60448aaaa9e8/",
                "name": "demo-git-datasource 2",
                "slug": "demo_git_datasource_2",
                "branch": "main",
                "created": "2023-06-07T12:49:34.309312Z",
                "display": "demo-git-datasource 2",
                "notes_url": "/api/extras/git-repositories/7af2e8d5-6d53-4b79-b488-60448aaaa9e8/notes/",
                "remote_url": "https://github.com/nautobot/demo-git-datasource.git",
                "object_type": "extras.gitrepository",
                "current_head": "94e88b76e87ccf1fdf48995d72ede86db4623d60",
                "last_updated": "2023-06-07T12:49:36.368627Z",
                "custom_fields": {},
                "secrets_group": None,
                "natural_key_slug": "demo-git-datasource+2",
                "provided_contents": ["extras.configcontextschema", "extras.configcontext", "extras.exporttemplate"],
            },
        )
        git_oc.validated_save()


class RelationshipTest(APIViewTestCases.APIViewTestCase, RequiredRelationshipTestMixin):
    model = Relationship

    create_data = [
        {
            "label": "Device VLANs",
            "key": "device_vlans",
            "type": "many-to-many",
            "source_type": "ipam.vlan",
            "destination_type": "dcim.device",
        },
        {
            "label": "Primary VLAN",
            "key": "primary_vlan",
            "type": "one-to-many",
            "source_type": "ipam.vlan",
            "destination_type": "dcim.device",
        },
        {
            "label": "Primary Interface",
            "key": "primary_interface",
            "type": "one-to-one",
            "source_type": "dcim.device",
            "source_label": "primary interface",
            "destination_type": "dcim.interface",
            "destination_hidden": True,
        },
        {
            "label": "Relationship 1",
            "type": "one-to-one",
            "source_type": "dcim.device",
            "source_label": "primary interface",
            "destination_type": "dcim.interface",
            "destination_hidden": True,
        },
    ]

    bulk_update_data = {
        "source_filter": {"name": ["some-name"]},
    }
    choices_fields = ["destination_type", "source_type", "type", "required_on"]

    @classmethod
    def setUpTestData(cls):
        location_type = ContentType.objects.get_for_model(Location)
        device_type = ContentType.objects.get_for_model(Device)

        cls.relationships = (
            Relationship(
                label="Related locations",
                key="related_locations",
                type="symmetric-many-to-many",
                source_type=location_type,
                destination_type=location_type,
            ),
            Relationship(
                label="Unrelated locations",
                key="unrelated_locations",
                type="many-to-many",
                source_type=location_type,
                source_label="Other locations (from source side)",
                destination_type=location_type,
                destination_label="Other locations (from destination side)",
            ),
            Relationship(
                label="Devices found elsewhere",
                key="devices_elsewhere",
                type="many-to-many",
                source_type=location_type,
                destination_type=device_type,
            ),
        )
        for relationship in cls.relationships:
            relationship.validated_save()
        cls.lt = LocationType.objects.get(name="Campus")
        location_status = Status.objects.get_for_model(Location).first()
        cls.location = Location.objects.create(name="Location 1", status=location_status, location_type=cls.lt)

    def test_get_all_relationships_on_location(self):
        """Verify that all relationships are accurately represented when requested."""
        self.add_permissions("dcim.view_location")
        response = self.client.get(
            reverse("dcim-api:location-detail", kwargs={"pk": self.location.pk}) + "?include=relationships",
            **self.header,
        )
        self.assertHttpStatus(response, status.HTTP_200_OK)
        self.assertIn("relationships", response.data)
        self.assertIsInstance(response.data["relationships"], dict)
        self.maxDiff = None
        self.assertEqual(
            {
                self.relationships[0].key: {
                    "id": str(self.relationships[0].pk),
                    "url": self.absolute_api_url(self.relationships[0]),
                    "label": self.relationships[0].label,
                    "type": self.relationships[0].type,
                    "peer": {
                        "label": "locations",
                        "object_type": "dcim.location",
                        "objects": [],
                    },
                },
                self.relationships[1].key: {
                    "id": str(self.relationships[1].pk),
                    "url": self.absolute_api_url(self.relationships[1]),
                    "label": self.relationships[1].label,
                    "type": self.relationships[1].type,
                    "destination": {
                        "label": self.relationships[1].source_label,  # yes -- it's a bit confusing
                        "object_type": "dcim.location",
                        "objects": [],
                    },
                    "source": {
                        "label": self.relationships[1].destination_label,  # yes -- it's a bit confusing
                        "object_type": "dcim.location",
                        "objects": [],
                    },
                },
                self.relationships[2].key: {
                    "id": str(self.relationships[2].pk),
                    "url": self.absolute_api_url(self.relationships[2]),
                    "label": self.relationships[2].label,
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

    def test_populate_relationship_associations_on_location_create(self):
        """Verify that relationship associations can be populated at instance creation time."""
        location_type = LocationType.objects.get(name="Campus")
        existing_location_1 = Location.objects.create(
            name="Existing Location 1",
            status=Status.objects.get_for_model(Location).first(),
            location_type=location_type,
        )
        existing_location_2 = Location.objects.create(
            name="Existing Location 2",
            status=Status.objects.get_for_model(Location).first(),
            location_type=location_type,
        )
        manufacturer = Manufacturer.objects.first()
        device_type = DeviceType.objects.create(
            manufacturer=manufacturer,
            model="device Type 1",
        )
        device_role = Role.objects.get_for_model(Device).first()
        device_status = Status.objects.get_for_model(Device).first()
        existing_device_1 = Device.objects.create(
            name="existing-device-location-1",
            status=device_status,
            role=device_role,
            device_type=device_type,
            location=existing_location_1,
        )
        existing_device_2 = Device.objects.create(
            name="existing-device-location-2",
            status=device_status,
            role=device_role,
            device_type=device_type,
            location=existing_location_2,
        )

        self.add_permissions(
            "dcim.view_location",
            "dcim.view_locationtype",
            "dcim.view_device",
            "dcim.add_location",
            "extras.view_relationship",
            "extras.add_relationshipassociation",
            "extras.view_status",
        )
        response = self.client.post(
            reverse("dcim-api:location-list"),
            data={
                "name": "New location",
                "status": Status.objects.get_for_model(Location).first().pk,
                "location_type": location_type.pk,
                "relationships": {
                    self.relationships[0].key: {
                        "peer": {
                            "objects": [str(existing_location_1.pk)],
                        },
                    },
                    self.relationships[1].key: {
                        "source": {
                            "objects": [str(existing_location_2.pk)],
                        },
                    },
                    self.relationships[2].key: {
                        "destination": {
                            "objects": [
                                {"name": "existing-device-location-1"},
                                {"name": "existing-device-location-2"},
                            ],
                        },
                    },
                },
            },
            format="json",
            **self.header,
        )
        self.assertHttpStatus(response, status.HTTP_201_CREATED)
        new_location_id = response.data["id"]
        # Peer case - don't distinguish source/destination
        self.assertTrue(
            RelationshipAssociation.objects.filter(
                relationship=self.relationships[0],
                source_type=self.relationships[0].source_type,
                source_id__in=[existing_location_1.pk, new_location_id],
                destination_type=self.relationships[0].destination_type,
                destination_id__in=[existing_location_1.pk, new_location_id],
            ).exists()
        )
        self.assertTrue(
            RelationshipAssociation.objects.filter(
                relationship=self.relationships[1],
                source_type=self.relationships[1].source_type,
                source_id=existing_location_2.pk,
                destination_type=self.relationships[1].destination_type,
                destination_id=new_location_id,
            ).exists()
        )
        self.assertTrue(
            RelationshipAssociation.objects.filter(
                relationship=self.relationships[2],
                source_type=self.relationships[2].source_type,
                source_id=new_location_id,
                destination_type=self.relationships[2].destination_type,
                destination_id=existing_device_1.pk,
            ).exists()
        )
        self.assertTrue(
            RelationshipAssociation.objects.filter(
                relationship=self.relationships[2],
                source_type=self.relationships[2].source_type,
                source_id=new_location_id,
                destination_type=self.relationships[2].destination_type,
                destination_id=existing_device_2.pk,
            ).exists()
        )

    def test_required_relationships(self):
        """
        1. Try creating an object when no required target object exists
        2. Try creating an object without specifying required target object(s)
        3. Try creating an object when all required data is present
        4. Test various bulk create/edit scenarios
        """

        # Delete existing factory generated objects that may interfere with this test
        IPAddress.objects.all().delete()
        Prefix.objects.update(parent=None)
        Prefix.objects.all().delete()
        ControllerManagedDeviceGroup.objects.all().delete()
        VLAN.objects.all().delete()

        # Parameterized tests (for creating and updating single objects):
        self.required_relationships_test(interact_with="api")

        # 4. Bulk create/edit tests:

        # VLAN endpoint to POST, PATCH and PUT multiple objects to:
        vlan_list_endpoint = reverse(get_route_for_model(VLAN, "list", api=True))

        def send_bulk_data(http_method, data):
            return getattr(self.client, http_method)(
                vlan_list_endpoint,
                data=data,
                format="json",
                **self.header,
            )

        device_status = Status.objects.get_for_model(Device).first()
        vlan_groups = VLANGroup.objects.all()[:2]

        # Try deleting all devices and then creating 2 VLANs (fails):
        Controller.objects.filter(controller_device__isnull=False).delete()
        Device.objects.all().delete()
        response = send_bulk_data(
            "post",
            data=[
                {"vid": "7", "name": "7", "status": device_status.pk, "vlan_group": vlan_groups[0].pk},
                {"vid": "8", "name": "8", "status": device_status.pk, "vlan_group": vlan_groups[1].pk},
            ],
        )
        self.assertHttpStatus(response, 400)
        self.assertEqual(
            {
                "relationships": {
                    "vlans_devices_m2m": [
                        "VLANs require at least one device, but no devices exist yet. "
                        "Create a device by posting to /api/dcim/devices/",
                        'You need to specify ["relationships"]["vlans_devices_m2m"]["source"]["objects"].',
                    ]
                }
            },
            response.json(),
        )

        # Create test device for association
        device_for_association = test_views.create_test_device("VLAN Required Device")
        required_relationship_json = {"vlans_devices_m2m": {"source": {"objects": [str(device_for_association.id)]}}}
        expected_error_json = {
            "relationships": {
                "vlans_devices_m2m": [
                    'You need to specify ["relationships"]["vlans_devices_m2m"]["source"]["objects"].'
                ]
            }
        }

        # Test POST, PATCH and PUT
        for method in ["post", "patch", "put"]:
            if method == "post":
                vlan1_json_data = {
                    "vid": "13",
                    "name": "1",
                    "status": device_status.pk,
                    "vlan_group": vlan_groups[0].pk,
                }
                vlan2_json_data = {
                    "vid": "22",
                    "name": "2",
                    "status": device_status.pk,
                    "vlan_group": vlan_groups[1].pk,
                }
            else:
                vlan1 = VLAN.objects.create(name="test_required_relationships1", vid=1, status=device_status)
                vlan2 = VLAN.objects.create(name="test_required_relationships2", vid=2, status=device_status)
                vlan1_json_data = {"status": device_status.pk, "id": str(vlan1.id)}
                # Add required fields for PUT method:
                if method == "put":
                    vlan1_json_data.update({"vid": "4", "name": vlan1.name})

                vlan2_json_data = {"status": device_status.pk, "id": str(vlan2.id)}
                # Add required fields for PUT method:
                if method == "put":
                    vlan2_json_data.update({"vid": "5", "name": vlan2.name})

            # Try method without specifying required relationships for either vlan1 or vlan2 (fails)
            json_data = [vlan1_json_data, vlan2_json_data]
            response = send_bulk_data(method, json_data)
            self.assertHttpStatus(response, 400)
            self.assertEqual(response.json(), expected_error_json)

            # Try method specifying required relationships for just vlan1 (fails)
            vlan1_json_data["relationships"] = required_relationship_json
            json_data = [vlan1_json_data, vlan2_json_data]
            response = send_bulk_data(method, json_data)
            self.assertHttpStatus(response, 400)
            self.assertEqual(response.json(), expected_error_json)

            # Try method specifying required relationships for both vlan1 and vlan2 (succeeds)
            vlan2_json_data["relationships"] = required_relationship_json
            json_data = [vlan1_json_data, vlan2_json_data]
            response = send_bulk_data(method, json_data)
            if method == "post":
                self.assertHttpStatus(response, 201)
            else:
                self.assertHttpStatus(response, 200)

            # Check the relationship associations were actually created
            for vlan in response.json():
                associated_device = vlan["relationships"]["vlans_devices_m2m"]["source"]["objects"][0]
                self.assertEqual(str(device_for_association.id), associated_device["id"])


class RelationshipAssociationTest(APIViewTestCases.APIViewTestCase):
    model = RelationshipAssociation
    choices_fields = ["destination_type", "source_type"]

    @classmethod
    def setUpTestData(cls):
        cls.location_type = ContentType.objects.get_for_model(Location)
        cls.device_type = ContentType.objects.get_for_model(Device)
        cls.location_status = Status.objects.get_for_model(Location).first()

        cls.relationship = Relationship(
            label="Devices found elsewhere",
            key="elsewhere_devices",
            type="many-to-many",
            source_type=cls.location_type,
            destination_type=cls.device_type,
        )
        cls.relationship.validated_save()
        cls.lt = LocationType.objects.get(name="Campus")
        cls.locations = (
            Location.objects.create(name="Empty Location", status=cls.location_status, location_type=cls.lt),
            Location.objects.create(name="Occupied Location", status=cls.location_status, location_type=cls.lt),
            Location.objects.create(name="Another Empty Location", status=cls.location_status, location_type=cls.lt),
        )
        manufacturer = Manufacturer.objects.first()
        devicetype = DeviceType.objects.create(manufacturer=manufacturer, model="Device Type 1")
        devicerole = Role.objects.get_for_model(Device).first()
        device_status = Status.objects.get_for_model(Device).first()
        cls.devices = [
            Device.objects.create(
                name=f"Device {num}",
                device_type=devicetype,
                role=devicerole,
                location=cls.locations[1],
                status=device_status,
            )
            for num in range(1, 5)
        ]

        cls.associations = (
            RelationshipAssociation(
                relationship=cls.relationship,
                source_type=cls.location_type,
                source_id=cls.locations[0].pk,
                destination_type=cls.device_type,
                destination_id=cls.devices[0].pk,
            ),
            RelationshipAssociation(
                relationship=cls.relationship,
                source_type=cls.location_type,
                source_id=cls.locations[0].pk,
                destination_type=cls.device_type,
                destination_id=cls.devices[1].pk,
            ),
            RelationshipAssociation(
                relationship=cls.relationship,
                source_type=cls.location_type,
                source_id=cls.locations[0].pk,
                destination_type=cls.device_type,
                destination_id=cls.devices[2].pk,
            ),
        )
        for association in cls.associations:
            association.validated_save()

        cls.create_data = [
            {
                "relationship": cls.relationship.pk,
                "source_type": "dcim.location",
                "source_id": cls.locations[2].pk,
                "destination_type": "dcim.device",
                "destination_id": cls.devices[0].pk,
            },
            {
                "relationship": cls.relationship.pk,
                "source_type": "dcim.location",
                "source_id": cls.locations[2].pk,
                "destination_type": "dcim.device",
                "destination_id": cls.devices[1].pk,
            },
            {
                "relationship": cls.relationship.pk,
                "source_type": "dcim.location",
                "source_id": cls.locations[2].pk,
                "destination_type": "dcim.device",
                "destination_id": cls.devices[2].pk,
            },
        ]

    def test_create_invalid_relationship_association(self):
        """Test creation of invalid relationship association restricted by destination/source filter."""

        relationship = Relationship.objects.create(
            label="Device to location Rel 1",
            key="device_to_location_rel_1",
            source_type=self.device_type,
            source_filter={"name": [self.devices[0].name]},
            destination_type=self.location_type,
            destination_label="Primary Rack",
            type=RelationshipTypeChoices.TYPE_ONE_TO_ONE,
            destination_filter={"name": [self.locations[0].name]},
        )

        associations = [
            (
                "destination",  # side
                self.locations[2].name,  # field name with an error
                {
                    "relationship": relationship.pk,
                    "source_type": "dcim.device",
                    "source_id": self.devices[0].pk,
                    "destination_type": "dcim.location",
                    "destination_id": self.locations[2].pk,
                },
            ),
            (
                "source",  # side
                self.devices[1].name,  # field name with an error
                {
                    "relationship": relationship.pk,
                    "source_type": "dcim.device",
                    "source_id": self.devices[1].pk,
                    "destination_type": "dcim.location",
                    "destination_id": self.locations[0].pk,
                },
            ),
        ]

        self.add_permissions(
            "extras.add_relationshipassociation", "dcim.view_device", "dcim.view_location", "extras.view_relationship"
        )

        for side, field_error_name, data in associations:
            response = self.client.post(self._get_list_url(), data, format="json", **self.header)
            self.assertHttpStatus(response, status.HTTP_400_BAD_REQUEST)
            self.assertEqual(
                response.data[side],
                [f"{field_error_name} violates {relationship.label} {side}_filter restriction"],
            )

    def test_model_clean_method_is_called(self):
        """Validate RelationshipAssociation clean method is called"""

        data = {
            "relationship": self.relationship.pk,
            "source_type": "dcim.device",
            "source_id": self.locations[2].pk,
            "destination_type": "dcim.device",
            "destination_id": self.devices[2].pk,
        }

        self.add_permissions(
            "extras.add_relationshipassociation", "extras.view_relationship", "dcim.view_device", "dcim.view_location"
        )

        response = self.client.post(self._get_list_url(), data, format="json", **self.header)
        self.assertHttpStatus(response, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            response.data["source_type"], [f"source_type has a different value than defined in {self.relationship}"]
        )

    def test_get_association_data_on_location(self):
        """
        Check that `include=relationships` query parameter on a model endpoint includes relationships/associations.
        """
        self.add_permissions("dcim.view_location")
        response = self.client.get(
            reverse("dcim-api:location-detail", kwargs={"pk": self.locations[0].pk})
            + "?include=relationships"
            + "&depth=1",
            **self.header,
        )
        self.assertHttpStatus(response, status.HTTP_200_OK)
        self.assertIn("relationships", response.data)
        self.assertIsInstance(response.data["relationships"], dict)
        # Ensure consistent ordering
        response.data["relationships"][self.relationship.key]["destination"]["objects"].sort(key=lambda v: v["name"])
        self.maxDiff = None
        relationship_data = response.data["relationships"][self.relationship.key]
        self.assertEqual(relationship_data["id"], str(self.relationship.pk))
        self.assertEqual(relationship_data["url"], self.absolute_api_url(self.relationship))
        self.assertEqual(relationship_data["label"], self.relationship.label)
        self.assertEqual(relationship_data["type"], "many-to-many")
        self.assertEqual(relationship_data["destination"]["label"], "devices")
        self.assertEqual(relationship_data["destination"]["object_type"], "dcim.device")

        objects = response.data["relationships"][self.relationship.key]["destination"]["objects"]
        for i, obj in enumerate(objects):
            self.assertEqual(obj["id"], str(self.devices[i].pk))
            self.assertEqual(obj["url"], self.absolute_api_url(self.devices[i]))
            self.assertEqual(
                obj["display"],
                self.devices[i].display,
            )
            self.assertEqual(
                obj["name"],
                self.devices[i].name,
            )

    def test_update_association_data_on_location(self):
        """
        Check that relationship-associations can be updated via the 'relationships' field.
        """
        self.add_permissions(
            "dcim.view_device",
            "dcim.view_location",
            "dcim.change_location",
            "extras.view_relationship",
            "extras.view_relationshipassociation",
            "extras.add_relationshipassociation",
            "extras.delete_relationshipassociation",
        )
        initial_response = self.client.get(
            reverse("dcim-api:location-detail", kwargs={"pk": self.locations[0].pk}) + "?include=relationships",
            **self.header,
        )
        self.assertHttpStatus(initial_response, status.HTTP_200_OK)

        url = reverse("dcim-api:location-detail", kwargs={"pk": self.locations[0].pk})

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
                str(response.data["relationships"][0]),
                '"nonexistent-relationship" is not a relationship on dcim.Location',
            )
            self.assertEqual(3, RelationshipAssociation.objects.filter(relationship=self.relationship).count())
            for association in self.associations:
                self.assertTrue(RelationshipAssociation.objects.filter(pk=association.pk).exists())

        with self.subTest("Error handling: wrong relationship"):
            Relationship.objects.create(
                label="Device-to-Device",
                key="device_to_device",
                source_type=self.device_type,
                destination_type=self.device_type,
                type=RelationshipTypeChoices.TYPE_ONE_TO_ONE,
            )
            response = self.client.patch(
                url,
                {"relationships": {"device_to_device": {"peer": {"objects": []}}}},
                format="json",
                **self.header,
            )
            self.assertHttpStatus(response, status.HTTP_400_BAD_REQUEST)
            self.assertEqual(
                str(response.data["relationships"][0]), '"device_to_device" is not a relationship on dcim.Location'
            )
            self.assertEqual(3, RelationshipAssociation.objects.filter(relationship=self.relationship).count())
            for association in self.associations:
                self.assertTrue(RelationshipAssociation.objects.filter(pk=association.pk).exists())

        with self.subTest("Error handling: wrong relationship side"):
            response = self.client.patch(
                url,
                {"relationships": {self.relationship.key: {"source": {"objects": []}}}},
                format="json",
                **self.header,
            )
            self.assertHttpStatus(response, status.HTTP_400_BAD_REQUEST)
            self.assertEqual(
                str(response.data["relationships"][0]),
                '"source" is not a valid side for "Devices found elsewhere" on dcim.Location',
            )
            self.assertEqual(3, RelationshipAssociation.objects.filter(relationship=self.relationship).count())
            for association in self.associations:
                self.assertTrue(RelationshipAssociation.objects.filter(pk=association.pk).exists())

        with self.subTest("Valid data: create/no-op/delete on RelationshipAssociations"):
            response = self.client.patch(
                url,
                {
                    "relationships": {
                        self.relationship.key: {
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
            "provider": "text-file",
            "parameters": {
                "path": "/github-tokens/user/myusername.txt",
            },
        },
    ]

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

    def test_secret_check(self):
        """
        Ensure that we can check the validity of a secret.
        """

        with self.subTest("Secret is not accessible"):
            test_secret = Secret.objects.create(
                name="secret-check-test-not-accessible",
                provider="text-file",
                parameters={"path": "/tmp/does-not-matter"},  # noqa: S108  # hardcoded-temp-file -- false positive
            )
            response = self.client.get(reverse("extras-api:secret-check", kwargs={"pk": test_secret.pk}), **self.header)
            self.assertHttpStatus(response, status.HTTP_403_FORBIDDEN)

        self.add_permissions("extras.view_secret")

        with self.subTest("Secret check successful"):
            with tempfile.NamedTemporaryFile() as secret_file:
                secret_file.write(b"HELLO WORLD")
                test_secret = Secret.objects.create(
                    name="secret-check-test-accessible",
                    provider="text-file",
                    parameters={"path": secret_file.name},
                )
                response = self.client.get(
                    reverse("extras-api:secret-check", kwargs={"pk": test_secret.pk}), **self.header
                )
                self.assertHttpStatus(response, status.HTTP_200_OK)
                self.assertEqual(response.data["result"], True)

        with self.subTest("Secret check failed"):
            test_secret = Secret.objects.create(
                name="secret-check-test-failed",
                provider="text-file",
                parameters={"path": "/tmp/does-not-exist"},  # noqa: S108  # hardcoded-temp-file -- false positive
            )
            response = self.client.get(reverse("extras-api:secret-check", kwargs={"pk": test_secret.pk}), **self.header)
            self.assertHttpStatus(response, status.HTTP_200_OK)
            self.assertEqual(response.data["result"], False)
            self.assertIn("SecretValueNotFoundError", response.data["message"])


class SecretsGroupTest(APIViewTestCases.APIViewTestCase):
    model = SecretsGroup
    bulk_update_data = {}

    @classmethod
    def setUpTestData(cls):
        secrets = secrets = (
            Secret.objects.create(
                name="secret-1", provider="environment-variable", parameters={"variable": "SOME_VAR"}
            ),
            Secret.objects.create(
                name="secret-2", provider="environment-variable", parameters={"variable": "ANOTHER_VAR"}
            ),
        )

        secrets_groups = (
            SecretsGroup.objects.create(name="Group A"),
            SecretsGroup.objects.create(name="Group B"),
            SecretsGroup.objects.create(name="Group C", description="Some group"),
        )

        SecretsGroupAssociation.objects.create(
            secret=secrets[0],
            secrets_group=secrets_groups[0],
            access_type=SecretsGroupAccessTypeChoices.TYPE_GENERIC,
            secret_type=SecretsGroupSecretTypeChoices.TYPE_SECRET,
        )
        SecretsGroupAssociation.objects.create(
            secret=secrets[1],
            secrets_group=secrets_groups[1],
            access_type=SecretsGroupAccessTypeChoices.TYPE_GENERIC,
            secret_type=SecretsGroupSecretTypeChoices.TYPE_SECRET,
        )

        cls.create_data = [
            {
                "name": "Secrets Group 1",
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
            SecretsGroup.objects.create(name="Group A"),
            SecretsGroup.objects.create(name="Group B"),
            SecretsGroup.objects.create(name="Group C", description="Some group"),
        )

        SecretsGroupAssociation.objects.create(
            secret=secrets[0],
            secrets_group=secrets_groups[0],
            access_type=SecretsGroupAccessTypeChoices.TYPE_GENERIC,
            secret_type=SecretsGroupSecretTypeChoices.TYPE_SECRET,
        )
        SecretsGroupAssociation.objects.create(
            secret=secrets[1],
            secrets_group=secrets_groups[1],
            access_type=SecretsGroupAccessTypeChoices.TYPE_GENERIC,
            secret_type=SecretsGroupSecretTypeChoices.TYPE_SECRET,
        )
        SecretsGroupAssociation.objects.create(
            secret=secrets[2],
            secrets_group=secrets_groups[2],
            access_type=SecretsGroupAccessTypeChoices.TYPE_GENERIC,
            secret_type=SecretsGroupSecretTypeChoices.TYPE_SECRET,
        )

        cls.create_data = [
            {
                "secrets_group": secrets_groups[0].pk,
                "access_type": SecretsGroupAccessTypeChoices.TYPE_SSH,
                "secret_type": SecretsGroupSecretTypeChoices.TYPE_USERNAME,
                "secret": secrets[0].pk,
            },
            {
                "secrets_group": secrets_groups[1].pk,
                "access_type": SecretsGroupAccessTypeChoices.TYPE_SSH,
                "secret_type": SecretsGroupSecretTypeChoices.TYPE_USERNAME,
                "secret": secrets[1].pk,
            },
            {
                "secrets_group": secrets_groups[2].pk,
                "access_type": SecretsGroupAccessTypeChoices.TYPE_SSH,
                "secret_type": SecretsGroupSecretTypeChoices.TYPE_USERNAME,
                "secret": secrets[2].pk,
            },
        ]


class StaticGroupAssociationTest(APIViewTestCases.APIViewTestCase):
    model = StaticGroupAssociation
    choices_fields = ["associated_object_type"]

    # StaticGroupAssociation records created for SoftwareImageFile records will contain a `hashing_algorithm` key;
    # presence of strings like "md5" and "sha256" in the API response for StaticGroupAssociation is *not* a failure
    VERBOTEN_STRINGS = ("password",)

    @classmethod
    def setUpTestData(cls):
        cls.dg1 = DynamicGroup.objects.create(
            name="Locations",
            content_type=ContentType.objects.get_for_model(Location),
            group_type=DynamicGroupTypeChoices.TYPE_STATIC,
        )
        cls.dg2 = DynamicGroup.objects.create(
            name="Devices",
            content_type=ContentType.objects.get_for_model(Device),
            group_type=DynamicGroupTypeChoices.TYPE_STATIC,
        )
        cls.dg3 = DynamicGroup.objects.create(
            name="VLANs",
            content_type=ContentType.objects.get_for_model(VLAN),
            group_type=DynamicGroupTypeChoices.TYPE_STATIC,
        )
        location_pks = list(Location.objects.values_list("pk", flat=True)[:4])
        device_pks = list(Device.objects.values_list("pk", flat=True)[:4])
        StaticGroupAssociation.objects.create(
            dynamic_group=cls.dg1,
            associated_object_type=ContentType.objects.get_for_model(Location),
            associated_object_id=location_pks[0],
        )
        StaticGroupAssociation.objects.create(
            dynamic_group=cls.dg1,
            associated_object_type=ContentType.objects.get_for_model(Location),
            associated_object_id=location_pks[1],
        )
        StaticGroupAssociation.objects.create(
            dynamic_group=cls.dg2,
            associated_object_type=ContentType.objects.get_for_model(Device),
            associated_object_id=device_pks[0],
        )

        cls.create_data = [
            {
                "dynamic_group": cls.dg1.pk,
                "associated_object_type": "dcim.location",
                "associated_object_id": location_pks[2],
            },
            {
                "dynamic_group": cls.dg1.pk,
                "associated_object_type": "dcim.location",
                "associated_object_id": location_pks[3],
            },
            {
                "dynamic_group": cls.dg2.pk,
                "associated_object_type": "dcim.device",
                "associated_object_id": device_pks[2],
            },
            {
                "dynamic_group": cls.dg2.pk,
                "associated_object_type": "dcim.device",
                "associated_object_id": device_pks[3],
            },
        ]
        # TODO: this isn't really valid since we're changing the associated_object_type but not the associated_object_id
        # Should we disallow bulk-updates of StaticGroupAssociation? Or maybe skip the bulk-update tests at least?
        cls.bulk_update_data = {
            "dynamic_group": cls.dg3.pk,
            "associated_object_type": "ipam.vlan",
        }

    def test_content_type_mismatch(self):
        self.add_permissions("extras.add_staticgroupassociation")
        data = {
            "dynamic_group": self.dg1.pk,
            "associated_object_type": "ipam.ipaddress",
            "associated_object_id": IPAddress.objects.first().pk,
        }
        response = self.client.post(self._get_list_url(), data, format="json", **self.header)
        self.assertHttpStatus(response, status.HTTP_400_BAD_REQUEST)

    def test_list_omits_hidden_by_default(self):
        """Test that the list view defaults to omitting associations of non-static groups."""
        sga1 = StaticGroupAssociation.all_objects.filter(
            dynamic_group__group_type=DynamicGroupTypeChoices.TYPE_STATIC
        ).first()
        self.assertIsNotNone(sga1)
        sga2 = StaticGroupAssociation.all_objects.exclude(
            dynamic_group__group_type=DynamicGroupTypeChoices.TYPE_STATIC
        ).first()
        self.assertIsNotNone(sga2)

        self.add_permissions("extras.view_staticgroupassociation")
        response = self.client.get(self._get_list_url(), **self.header)
        self.assertHttpStatus(response, status.HTTP_200_OK)
        self.assertIsInstance(response.data, dict)
        self.assertIn("results", response.data)
        found_sga1 = False
        found_sga2 = False
        for record in response.data["results"]:
            if record["id"] == str(sga1.id):
                found_sga1 = True
            elif record["id"] == str(sga2.id):
                found_sga2 = True
        self.assertTrue(found_sga1)
        self.assertFalse(found_sga2)

    def test_list_hidden_with_filter(self):
        """Test that the list view can show hidden associations with the appropriate filter."""
        sga1 = StaticGroupAssociation.all_objects.exclude(
            dynamic_group__group_type=DynamicGroupTypeChoices.TYPE_STATIC
        ).first()
        self.assertIsNotNone(sga1)

        self.add_permissions("extras.view_staticgroupassociation")
        response = self.client.get(f"{self._get_list_url()}?dynamic_group={sga1.dynamic_group.pk}", **self.header)
        self.assertHttpStatus(response, status.HTTP_200_OK)
        self.assertIsInstance(response.data, dict)
        self.assertIn("results", response.data)
        found_sga1 = False
        for record in response.data["results"]:
            if record["id"] == str(sga1.id):
                found_sga1 = True
        self.assertTrue(found_sga1)

    def test_changes_to_hidden_groups_not_permitted(self):
        """Test that the REST API cannot create/update/delete hidden associations."""
        self.add_permissions(
            "extras.view_staticgroupassociation",
            "extras.add_staticgroupassociation",
            "extras.delete_staticgroupassociation",
            "extras.change_staticgroupassociation",
        )

        with self.subTest("create hidden association"):
            dg = DynamicGroup.objects.exclude(group_type=DynamicGroupTypeChoices.TYPE_STATIC).first()
            self.assertIsNotNone(dg)
            create_data = {
                "dynamic_group": str(dg.pk),
                "associated_object_type": f"{dg.content_type.app_label}.{dg.content_type.model}",
                "associated_object_id": "00000000-0000-0000-0000-000000000000",
            }
            response = self.client.post(
                f"{self._get_list_url()}?dynamic_group={dg.pk}", create_data, format="json", **self.header
            )
            self.assertHttpStatus(response, [status.HTTP_400_BAD_REQUEST, status.HTTP_403_FORBIDDEN])

        with self.subTest("update hidden association"):
            sga = StaticGroupAssociation.all_objects.exclude(
                dynamic_group__group_type=DynamicGroupTypeChoices.TYPE_STATIC
            ).first()
            self.assertIsNotNone(sga)
            url = self._get_detail_url(sga) + f"?dynamic_group={sga.dynamic_group.pk}"
            update_data = {"associated_object_id": "00000000-0000-0000-0000-000000000000"}
            response = self.client.patch(url, update_data, format="json", **self.header)
            self.assertHttpStatus(response, status.HTTP_404_NOT_FOUND)
            sga.refresh_from_db()
            self.assertNotEqual(sga.associated_object_id, "00000000-0000-0000-0000-000000000000")

        with self.subTest("delete hidden association"):
            sga = StaticGroupAssociation.all_objects.exclude(
                dynamic_group__group_type=DynamicGroupTypeChoices.TYPE_STATIC
            ).first()
            self.assertIsNotNone(sga)
            url = self._get_detail_url(sga) + f"?dynamic_group={sga.dynamic_group.pk}"
            response = self.client.delete(url, **self.header)
            self.assertHttpStatus(response, status.HTTP_404_NOT_FOUND)
            self.assertTrue(StaticGroupAssociation.all_objects.filter(pk=sga.pk).exists())


class StatusTest(APIViewTestCases.APIViewTestCase):
    model = Status
    bulk_update_data = {
        "color": "000000",
    }

    create_data = [
        {
            "name": "Pizza",
            "color": "0000ff",
            "content_types": ["dcim.device", "dcim.rack"],
        },
        {
            "name": "Oysters",
            "color": "00ff00",
            "content_types": ["ipam.ipaddress", "ipam.prefix"],
        },
        {
            "name": "Bad combinations",
            "color": "ff0000",
            "content_types": ["dcim.device"],
        },
        {
            "name": "Status 1",
            "color": "ff0000",
            "content_types": ["dcim.device"],
        },
    ]


class TagTest(APIViewTestCases.APIViewTestCase):
    model = Tag
    create_data = [
        {"name": "Tag 4", "content_types": [Location._meta.label_lower]},
        {"name": "Tag 5", "content_types": [Location._meta.label_lower]},
        {"name": "Tag 6", "content_types": [Location._meta.label_lower]},
    ]

    @classmethod
    def setUpTestData(cls):
        cls.update_data = {
            "name": "A new tag name",
            "content_types": [f"{ct.app_label}.{ct.model}" for ct in TaggableClassesQuery().as_queryset()],
        }
        cls.bulk_update_data = {
            "content_types": [f"{ct.app_label}.{ct.model}" for ct in TaggableClassesQuery().as_queryset()]
        }

    def test_create_tags_with_invalid_content_types(self):
        self.add_permissions("extras.add_tag")

        # Manufacturer is an OrganizationalModel, not a PrimaryModel, and therefore does not support tags
        data = {**self.create_data[0], "content_types": [Manufacturer._meta.label_lower]}
        response = self.client.post(self._get_list_url(), data, format="json", **self.header)

        tag = Tag.objects.filter(name=data["name"])
        self.assertHttpStatus(response, 400)
        self.assertFalse(tag.exists())
        self.assertIn(f"Invalid content type: {Manufacturer._meta.label_lower}", response.data["content_types"])

    def test_create_tags_without_content_types(self):
        self.add_permissions("extras.add_tag")
        data = {
            "name": "Tag 8",
        }

        response = self.client.post(self._get_list_url(), data, format="json", **self.header)
        self.assertHttpStatus(response, 400)
        self.assertEqual(str(response.data["content_types"][0]), "This field is required.")

    def test_update_tags_remove_content_type(self):
        """Test removing a tag content_type that is been tagged to a model"""
        self.add_permissions("extras.change_tag")

        tag_1 = Tag.objects.filter(content_types=ContentType.objects.get_for_model(Location)).first()
        location = Location.objects.filter(location_type=LocationType.objects.get(name="Campus")).first()
        location.tags.add(tag_1)

        tag_content_types = list(tag_1.content_types.all())
        tag_content_types.remove(ContentType.objects.get_for_model(Location))

        url = self._get_detail_url(tag_1)
        data = {"content_types": [f"{ct.app_label}.{ct.model}" for ct in tag_content_types]}

        response = self.client.patch(url, data, format="json", **self.header)
        self.assertHttpStatus(response, 400)
        self.assertEqual(
            str(response.data["content_types"][0]), "Unable to remove dcim.location. Dependent objects were found."
        )

    def test_update_tag_content_type_unchanged(self):
        """Test updating a tag without changing its content-types."""
        self.add_permissions("extras.change_tag")

        tag = Tag.objects.exclude(content_types=ContentType.objects.get_for_model(Location)).first()
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


#
# Team
#


class TeamTest(APIViewTestCases.APIViewTestCase):
    model = Team
    bulk_update_data = {
        "address": "Carnegie Hall, New York, NY",
    }

    @classmethod
    def setUpTestData(cls):
        # Teams associated with ObjectMetadata objects are protected, create some deletable teams
        Team.objects.create(name="Deletable team 1")
        Team.objects.create(name="Deletable team 2")
        Team.objects.create(name="Deletable team 3")

        cls.create_data = [
            {
                "name": "Team 1",
                "phone": "555-0121",
                "email": "team1@example.com",
                "contacts": [Contact.objects.first().pk, Contact.objects.last().pk],
            },
            {
                "name": "Team 2",
                "phone": "555-0122",
                "email": "team2@example.com",
                "address": "Bowser's Castle, Staten Island, NY",
            },
            {
                "name": "Team 3",
                "phone": "555-0123",
            },
            {
                "name": "Team 4",
                "email": "team4@example.com",
                "address": "Rainbow Bridge, Central NJ",
            },
        ]


class WebhookTest(APIViewTestCases.APIViewTestCase):
    model = Webhook
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


class RoleTest(APIViewTestCases.APIViewTestCase):
    model = Role
    bulk_update_data = {
        "color": "000000",
    }

    create_data = [
        {
            "name": "Role 1",
            "color": "0000ff",
            "content_types": ["dcim.device", "dcim.rack"],
        },
        {
            "name": "Role 2",
            "color": "0000ff",
            "content_types": ["dcim.rack"],
        },
        {
            "name": "Role 3",
            "color": "0000ff",
            "content_types": ["ipam.ipaddress", "ipam.vlan"],
        },
    ]
