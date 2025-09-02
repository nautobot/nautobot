from datetime import timedelta
import json
from unittest import mock
import urllib.parse
import uuid

from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.db.models import Q
from django.test import override_settings
from django.urls import reverse
from django.utils import timezone
from django.utils.html import escape, format_html

from nautobot.circuits.models import Circuit
from nautobot.core.celery import NautobotKombuJSONEncoder
from nautobot.core.choices import ColorChoices
from nautobot.core.models.fields import slugify_dashes_to_underscores
from nautobot.core.models.utils import serialize_object_v2
from nautobot.core.templatetags.helpers import bettertitle
from nautobot.core.testing import extract_form_failures, extract_page_body, ModelViewTestCase, TestCase, ViewTestCases
from nautobot.core.testing.context import load_event_broker_override_settings
from nautobot.core.testing.utils import disable_warnings, get_deletable_objects, post_data
from nautobot.core.utils.permissions import get_permission_for_model
from nautobot.dcim.models import (
    ConsolePort,
    Device,
    DeviceType,
    Interface,
    Location,
    LocationType,
    Manufacturer,
)
from nautobot.extras.choices import (
    CustomFieldTypeChoices,
    DynamicGroupTypeChoices,
    JobExecutionType,
    JobQueueTypeChoices,
    LogLevelChoices,
    MetadataTypeDataTypeChoices,
    ObjectChangeActionChoices,
    SecretsGroupAccessTypeChoices,
    SecretsGroupSecretTypeChoices,
    WebhookHttpMethodChoices,
)
from nautobot.extras.constants import HTTP_CONTENT_TYPE_JSON, JOB_OVERRIDABLE_FIELDS
from nautobot.extras.models import (
    ComputedField,
    ConfigContext,
    ConfigContextSchema,
    Contact,
    ContactAssociation,
    CustomField,
    CustomFieldChoice,
    CustomLink,
    DynamicGroup,
    ExportTemplate,
    ExternalIntegration,
    GitRepository,
    GraphQLQuery,
    Job,
    JobButton,
    JobHook,
    JobLogEntry,
    JobQueue,
    JobResult,
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
from nautobot.extras.templatetags.job_buttons import NO_CONFIRM_BUTTON
from nautobot.extras.tests.constants import BIG_GRAPHQL_DEVICE_QUERY
from nautobot.extras.tests.test_jobs import get_job_class_and_model
from nautobot.extras.tests.test_relationships import RequiredRelationshipTestMixin
from nautobot.extras.utils import RoleModelsQuery, TaggableClassesQuery
from nautobot.ipam.models import IPAddress, Prefix, VLAN, VLANGroup, VRF
from nautobot.tenancy.models import Tenant
from nautobot.users.models import ObjectPermission

# Use the proper swappable User model
User = get_user_model()


class ComputedFieldTestCase(
    ViewTestCases.BulkDeleteObjectsViewTestCase,
    ViewTestCases.CreateObjectViewTestCase,
    ViewTestCases.DeleteObjectViewTestCase,
    ViewTestCases.EditObjectViewTestCase,
    ViewTestCases.GetObjectViewTestCase,
    ViewTestCases.GetObjectChangelogViewTestCase,
    ViewTestCases.ListObjectsViewTestCase,
    ViewTestCases.BulkEditObjectsViewTestCase,
):
    model = ComputedField
    slug_source = "label"
    slugify_function = staticmethod(slugify_dashes_to_underscores)

    @classmethod
    def setUpTestData(cls):
        obj_type = ContentType.objects.get_for_model(Location)
        obj_type_1 = ContentType.objects.get_for_model(Interface)

        computed_fields = (
            ComputedField(
                content_type=obj_type,
                label="Computed Field One",
                key="computed_field_one",
                template="Location name is {{ obj.name }}",
                fallback_value="Template error",
                weight=100,
            ),
            ComputedField(
                content_type=obj_type,
                key="computed_field_two",
                label="Computed Field Two",
                template="Location name is {{ obj.name }}",
                fallback_value="Template error",
                weight=100,
            ),
            ComputedField(
                content_type=obj_type,
                key="computed_field_three",
                label="Computed Field Three",
                template="Location name is {{ obj.name }}",
                weight=100,
            ),
            ComputedField(
                content_type=obj_type,
                label="Computed Field Five",
                template="Location name is {{ obj.name }}",
                fallback_value="Template error",
                weight=100,
            ),
        )
        cls.location_type = LocationType.objects.get(name="Campus")
        status = Status.objects.get_for_model(Location).first()
        cls.location1 = Location(name="NYC", location_type=cls.location_type, status=status)
        cls.location1.save()

        for cf in computed_fields:
            cf.save()

        cls.form_data = {
            "content_type": obj_type.pk,
            "key": "computed_field_four",
            "label": "Computed Field Four",
            "template": "{{ obj.name }} is the best Location!",
            "fallback_value": ":skull_emoji:",
            "weight": 100,
        }
        cls.bulk_edit_data = {
            "content_type": obj_type_1.pk,
            "label": "Updated Label",
            "description": "Bulk updated description",
            "grouping": "General Info",
            "fallback_value": "Fallback from bulk edit",
            "weight": 50,
            "advanced_ui": True,
        }

        cls.slug_test_object = "Computed Field Five"


class ComputedFieldRenderingTestCase(TestCase):
    """Tests for the inclusion of ComputedFields, distinct from tests of the ComputedField views themselves."""

    user_permissions = ["dcim.view_locationtype"]

    def setUp(self):
        super().setUp()
        self.computedfield = ComputedField(
            content_type=ContentType.objects.get_for_model(LocationType),
            key="test",
            label="Computed Field",
            template="FOO {{ obj.name }} BAR",
            fallback_value="Fallback Value",
            weight=100,
        )
        self.computedfield.validated_save()
        self.location_type = LocationType.objects.get(name="Campus")

    def test_view_object_with_computed_field(self):
        """Ensure that the computed field template is rendered."""
        response = self.client.get(self.location_type.get_absolute_url(), follow=True)
        self.assertEqual(response.status_code, 200)
        content = extract_page_body(response.content.decode(response.charset))
        self.assertIn(f"FOO {self.location_type.name} BAR", content, content)

    def test_view_object_with_computed_field_fallback_value(self):
        """Ensure that the fallback_value is rendered if the template fails to render."""
        # Make the template invalid to demonstrate the fallback value
        self.computedfield.template = "FOO {{ obj | invalid_filter }}"
        self.computedfield.validated_save()
        response = self.client.get(self.location_type.get_absolute_url(), follow=True)
        self.assertEqual(response.status_code, 200)
        content = extract_page_body(response.content.decode(response.charset))
        self.assertIn("Fallback Value", content, content)

    def test_view_object_with_computed_field_unsafe_template(self):
        """Ensure that computed field templates can't be used as an XSS vector."""
        self.computedfield.template = '<script>alert("Hello world!"</script>'
        self.computedfield.validated_save()
        response = self.client.get(self.location_type.get_absolute_url(), follow=True)
        self.assertEqual(response.status_code, 200)
        content = extract_page_body(response.content.decode(response.charset))
        self.assertNotIn("<script>alert", content, content)
        self.assertIn("&lt;script&gt;alert", content, content)

    def test_view_object_with_computed_field_unsafe_fallback_value(self):
        """Ensure that computed field fallback values can't be used as an XSS vector."""
        self.computedfield.template = "FOO {{ obj | invalid_filter }}"
        self.computedfield.fallback_value = '<script>alert("Hello world!"</script>'
        self.computedfield.validated_save()
        response = self.client.get(self.location_type.get_absolute_url(), follow=True)
        self.assertEqual(response.status_code, 200)
        content = extract_page_body(response.content.decode(response.charset))
        self.assertNotIn("<script>alert", content, content)
        self.assertIn("&lt;script&gt;alert", content, content)


# TODO: Change base class to PrimaryObjectViewTestCase
# Blocked by absence of standard create/edit, bulk create views
class ConfigContextTestCase(
    ViewTestCases.CreateObjectViewTestCase,
    ViewTestCases.GetObjectViewTestCase,
    ViewTestCases.GetObjectChangelogViewTestCase,
    ViewTestCases.DeleteObjectViewTestCase,
    ViewTestCases.EditObjectViewTestCase,
    ViewTestCases.ListObjectsViewTestCase,
    ViewTestCases.BulkEditObjectsViewTestCase,
    ViewTestCases.BulkDeleteObjectsViewTestCase,
):
    model = ConfigContext

    @classmethod
    def setUpTestData(cls):
        location = Location.objects.filter(location_type=LocationType.objects.get(name="Campus")).first()

        # Create three ConfigContexts
        for i in range(1, 4):
            configcontext = ConfigContext(name=f"Config Context {i}", data={"foo": i})
            configcontext.save()
            configcontext.locations.add(location)

        cls.form_data = {
            "name": "Config Context X",
            "weight": 200,
            "description": "A new config context",
            "is_active": True,
            "regions": [],
            "locations": [location.pk],
            "roles": [],
            "device_types": [],
            "platforms": [],
            "tenant_groups": [],
            "tenants": [],
            "tags": [],
            "data": '{"foo": 123}',
        }

        cls.bulk_edit_data = {
            "weight": 300,
            "is_active": False,
            "description": "New description",
        }

    def test_schema_validation_pass(self):
        """
        Given a config context schema
        And a config context that conforms to that schema
        Assert that the config context passes schema validation via full_clean()
        """
        schema = ConfigContextSchema.objects.create(
            name="Schema 1", data_schema={"type": "object", "properties": {"foo": {"type": "string"}}}
        )
        self.add_permissions("extras.add_configcontext")
        self.add_permissions("extras.view_configcontextschema")

        form_data = {
            "name": "Config Context with schema",
            "weight": 200,
            "description": "A new config context",
            "is_active": True,
            "regions": [],
            "locations": [],
            "roles": [],
            "device_types": [],
            "platforms": [],
            "tenant_groups": [],
            "tenants": [],
            "tags": [],
            "data": '{"foo": "bar"}',
            "config_context_schema": schema.pk,
        }

        # Try POST with model-level permission
        request = {
            "path": self._get_url("add"),
            "data": post_data(form_data),
        }
        self.assertHttpStatus(self.client.post(**request), 302)
        self.assertEqual(
            self._get_queryset().get(name="Config Context with schema").config_context_schema.pk, schema.pk
        )

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
        self.add_permissions("extras.view_configcontextschema")

        form_data = {
            "name": "Config Context with bad schema",
            "weight": 200,
            "description": "A new config context",
            "is_active": True,
            "regions": [],
            "locations": [],
            "roles": [],
            "device_types": [],
            "platforms": [],
            "tenant_groups": [],
            "tenants": [],
            "tags": [],
            "data": '{"foo": "bar"}',
            "config_context_schema": schema.pk,
        }

        # Try POST with model-level permission
        request = {
            "path": self._get_url("add"),
            "data": post_data(form_data),
        }
        self.assertHttpStatus(self.client.post(**request), 200)
        self.assertEqual(self._get_queryset().filter(name="Config Context with schema").count(), 0)


class ConfigContextSchemaTestCase(ViewTestCases.OrganizationalObjectViewTestCase):
    model = ConfigContextSchema

    @classmethod
    def setUpTestData(cls):
        # Create three ConfigContextSchema records
        ConfigContextSchema.objects.create(
            name="Schema 1", data_schema={"type": "object", "properties": {"foo": {"type": "string"}}}
        )
        ConfigContextSchema.objects.create(
            name="Schema 2", data_schema={"type": "object", "properties": {"bar": {"type": "string"}}}
        )
        ConfigContextSchema.objects.create(
            name="Schema 3", data_schema={"type": "object", "properties": {"baz": {"type": "string"}}}
        )
        ConfigContextSchema.objects.create(
            name="Schema 4", data_schema={"type": "object", "properties": {"baz": {"type": "string"}}}
        )

        cls.form_data = {
            "name": "Schema X",
            "data_schema": '{"type": "object","properties": {"baz": {"type": "string"}}}',  # Intentionally misformatted (missing space) to ensure proper formatting on output
        }

        cls.bulk_edit_data = {
            "description": "New description",
        }


class ContactTestCase(ViewTestCases.PrimaryObjectViewTestCase):
    model = Contact

    @classmethod
    def setUpTestData(cls):
        # Contacts associated with ObjectMetadata objects are protected, create some deletable contacts
        Contact.objects.create(name="Deletable contact 1")
        Contact.objects.create(name="Deletable contact 2")
        Contact.objects.create(name="Deletable contact 3")

        cls.form_data = {
            "name": "new contact",
            "phone": "555-0121",
            "email": "new-contact@example.com",
            "address": "Rainbow Road, Ramus NJ",
        }
        cls.bulk_edit_data = {"address": "Carnegie Hall, New York, NY", "phone": "555-0125"}

    @override_settings(EXEMPT_VIEW_PERMISSIONS=["*"])
    def test_create_new_contact_and_assign_contact_to_object(self):
        initial_contact_count = Contact.objects.count()
        initial_contact_association_count = ContactAssociation.objects.count()
        self.add_permissions("extras.add_contact")
        self.add_permissions("extras.add_contactassociation")

        # Try GET with model-level permission
        url = reverse("extras:object_contact_add")
        self.assertHttpStatus(self.client.get(url), 200)
        contact_associated_circuit = Circuit.objects.first()
        self.form_data["associated_object_type"] = ContentType.objects.get_for_model(Circuit).pk
        self.form_data["associated_object_id"] = contact_associated_circuit.pk
        self.form_data["role"] = Role.objects.get_for_model(ContactAssociation).first().pk
        self.form_data["status"] = Status.objects.get_for_model(ContactAssociation).first().pk

        # Try POST with model-level permission
        request = {
            "path": url,
            "data": post_data(self.form_data),
        }
        self.assertHttpStatus(self.client.post(**request), 302)
        self.assertEqual(initial_contact_count + 1, Contact.objects.count())
        self.assertEqual(initial_contact_association_count + 1, ContactAssociation.objects.count())
        contact = Contact.objects.get(name="new contact", phone="555-0121")
        self.assertEqual(contact.name, "new contact")
        self.assertEqual(contact.phone, "555-0121")
        self.assertEqual(contact.email, "new-contact@example.com")
        self.assertEqual(contact.address, "Rainbow Road, Ramus NJ")
        contact_association = ContactAssociation.objects.get(contact=contact)
        self.assertEqual(contact_association.associated_object_type.pk, self.form_data["associated_object_type"])
        self.assertEqual(contact_association.associated_object_id, self.form_data["associated_object_id"])
        self.assertEqual(contact_association.role.pk, self.form_data["role"])
        self.assertEqual(contact_association.status.pk, self.form_data["status"])


class ContactAssociationTestCase(
    ViewTestCases.BulkDeleteObjectsViewTestCase,
    ViewTestCases.BulkEditObjectsViewTestCase,
    ViewTestCases.CreateObjectViewTestCase,
    ViewTestCases.DeleteObjectViewTestCase,
    ViewTestCases.EditObjectViewTestCase,
):
    model = ContactAssociation

    @classmethod
    def setUpTestData(cls):
        roles = Role.objects.get_for_model(ContactAssociation)
        statuses = Status.objects.get_for_model(ContactAssociation)
        ip_addresses = IPAddress.objects.all()
        cls.form_data = {
            "contact": Contact.objects.first().pk,
            "team": None,
            "associated_object_type": ContentType.objects.get_for_model(Circuit).pk,
            "associated_object_id": Circuit.objects.first().pk,
            "role": roles[0].pk,
            "status": statuses[0].pk,
        }
        cls.bulk_edit_data = {
            "role": roles[1].pk,
            "status": statuses[1].pk,
        }
        ContactAssociation.objects.create(
            contact=Contact.objects.first(),
            associated_object_type=ContentType.objects.get_for_model(IPAddress),
            associated_object_id=ip_addresses[0].pk,
            role=roles[2],
            status=statuses[1],
        )
        ContactAssociation.objects.create(
            contact=Contact.objects.last(),
            associated_object_type=ContentType.objects.get_for_model(IPAddress),
            associated_object_id=ip_addresses[1].pk,
            role=roles[1],
            status=statuses[2],
        )
        ContactAssociation.objects.create(
            team=Team.objects.first(),
            associated_object_type=ContentType.objects.get_for_model(IPAddress),
            associated_object_id=ip_addresses[2].pk,
            role=roles[0],
            status=statuses[0],
        )
        ContactAssociation.objects.create(
            team=Team.objects.last(),
            associated_object_type=ContentType.objects.get_for_model(IPAddress),
            associated_object_id=ip_addresses[3].pk,
            role=roles[0],
            status=statuses[1],
        )

    @override_settings(EXEMPT_VIEW_PERMISSIONS=["*"])
    def test_assign_existing_contact_to_object(self):
        contact = Contact.objects.first()
        initial_contact_association_count = ContactAssociation.objects.count()
        self.add_permissions("extras.add_contact")
        self.add_permissions("extras.add_contactassociation")

        # Try GET with model-level permission
        url = reverse("extras:object_contact_team_assign")
        self.assertHttpStatus(self.client.get(url), 200)
        contact_associated_circuit = Circuit.objects.first()
        self.form_data["associated_object_type"] = ContentType.objects.get_for_model(Circuit).pk
        self.form_data["associated_object_id"] = contact_associated_circuit.pk
        self.form_data["role"] = Role.objects.get_for_model(ContactAssociation).first().pk
        self.form_data["status"] = Status.objects.get_for_model(ContactAssociation).first().pk

        # Try POST with model-level permission
        request = {
            "path": url,
            "data": post_data(self.form_data),
        }
        self.assertHttpStatus(self.client.post(**request), 302)
        self.assertEqual(initial_contact_association_count + 1, ContactAssociation.objects.count())
        self.assertEqual(contact.pk, self.form_data["contact"])
        contact_association = ContactAssociation.objects.get(
            contact=contact, associated_object_id=contact_associated_circuit.pk
        )
        self.assertEqual(contact_association.associated_object_type.pk, self.form_data["associated_object_type"])
        self.assertEqual(contact_association.associated_object_id, self.form_data["associated_object_id"])
        self.assertEqual(contact_association.role.pk, self.form_data["role"])
        self.assertEqual(contact_association.status.pk, self.form_data["status"])

    @override_settings(EXEMPT_VIEW_PERMISSIONS=["*"])
    def test_assign_existing_team_to_object(self):
        team = Team.objects.first()
        initial_contact_association_count = ContactAssociation.objects.count()
        self.add_permissions("extras.add_team")
        self.add_permissions("extras.add_contactassociation")

        # Try GET with model-level permission
        url = reverse("extras:object_contact_team_assign")
        self.assertHttpStatus(self.client.get(url), 200)
        contact_associated_circuit = Circuit.objects.first()
        self.form_data["team"] = team.pk
        self.form_data["contact"] = None
        self.form_data["associated_object_type"] = ContentType.objects.get_for_model(Circuit).pk
        self.form_data["associated_object_id"] = contact_associated_circuit.pk
        self.form_data["role"] = Role.objects.get_for_model(ContactAssociation).first().pk
        self.form_data["status"] = Status.objects.get_for_model(ContactAssociation).first().pk

        # Try POST with model-level permission
        request = {
            "path": url,
            "data": post_data(self.form_data),
        }
        self.assertHttpStatus(self.client.post(**request), 302)
        self.assertEqual(initial_contact_association_count + 1, ContactAssociation.objects.count())
        self.assertEqual(team.pk, self.form_data["team"])
        contact_association = ContactAssociation.objects.get(
            team=team, associated_object_id=contact_associated_circuit.pk
        )
        self.assertEqual(contact_association.associated_object_type.pk, self.form_data["associated_object_type"])
        self.assertEqual(contact_association.associated_object_id, self.form_data["associated_object_id"])
        self.assertEqual(contact_association.role.pk, self.form_data["role"])
        self.assertEqual(contact_association.status.pk, self.form_data["status"])


class CustomLinkTestCase(
    ViewTestCases.CreateObjectViewTestCase,
    ViewTestCases.DeleteObjectViewTestCase,
    ViewTestCases.EditObjectViewTestCase,
    ViewTestCases.GetObjectViewTestCase,
    ViewTestCases.GetObjectChangelogViewTestCase,
    ViewTestCases.ListObjectsViewTestCase,
    ViewTestCases.BulkEditObjectsViewTestCase,
):
    model = CustomLink

    @classmethod
    def setUpTestData(cls):
        obj_type = ContentType.objects.get_for_model(Location)
        obj_type1 = ContentType.objects.get_for_model(Interface)

        customlinks = (
            CustomLink(
                content_type=obj_type,
                name="customlink-1",
                text="customlink text 1",
                target_url="http://customlink1.com",
                weight=100,
                button_class="default",
                new_window=False,
            ),
            CustomLink(
                content_type=obj_type,
                name="customlink-2",
                text="customlink text 2",
                target_url="http://customlink2.com",
                weight=100,
                button_class="default",
                new_window=False,
            ),
            CustomLink(
                content_type=obj_type,
                name="customlink-3",
                text="customlink text 3",
                target_url="http://customlink3.com",
                weight=100,
                button_class="default",
                new_window=False,
            ),
        )

        for link in customlinks:
            link.save()

        cls.form_data = {
            "content_type": obj_type.pk,
            "name": "customlink-4",
            "text": "customlink text 4",
            "target_url": "http://customlink4.com",
            "weight": 100,
            "button_class": "default",
            "new_window": False,
        }
        cls.bulk_edit_data = {
            "content_type": obj_type1.pk,
            "weight": 200,
            "button_class": "success",
            "new_window": True,
            "text": "Updated customlink text",
            "target_url": "http://bulk-edit-link.com",
        }


class CustomFieldTestCase(
    # No NotesViewTestCase, at least for now
    ViewTestCases.BulkDeleteObjectsViewTestCase,
    ViewTestCases.CreateObjectViewTestCase,
    ViewTestCases.DeleteObjectViewTestCase,
    ViewTestCases.EditObjectViewTestCase,
    ViewTestCases.GetObjectViewTestCase,
    ViewTestCases.GetObjectChangelogViewTestCase,
    ViewTestCases.ListObjectsViewTestCase,
    ViewTestCases.BulkEditObjectsViewTestCase,
):
    model = CustomField
    slugify_function = staticmethod(slugify_dashes_to_underscores)

    @classmethod
    def setUpTestData(cls):
        ipaddress_ct = ContentType.objects.get_for_model(IPAddress)
        prefix_ct = ContentType.objects.get_for_model(Prefix)
        device_ct = ContentType.objects.get_for_model(Device)
        obj_type = ContentType.objects.get_for_model(Location)

        custom_fields = [
            CustomField(
                type=CustomFieldTypeChoices.TYPE_BOOLEAN,
                label="Custom Field Boolean Type",
                default="",
            ),
            CustomField(
                type=CustomFieldTypeChoices.TYPE_TEXT,
                label="Custom Field Text",
                default="",
            ),
            CustomField(
                type=CustomFieldTypeChoices.TYPE_INTEGER,
                label="Custom Field Integer",
                default="",
            ),
            CustomField(
                type=CustomFieldTypeChoices.TYPE_TEXT,
                # https://github.com/nautobot/nautobot/issues/1962
                label="Custom field? With special / unusual characters!",
                default="",
            ),
        ]

        cls.slug_test_object = "Custom Field Integer"

        for custom_field in custom_fields:
            custom_field.validated_save()
            custom_field.content_types.set([obj_type, device_ct])

        cls.form_data = {
            "content_types": [obj_type.pk],
            "type": CustomFieldTypeChoices.TYPE_BOOLEAN,  # type is mandatory but cannot be changed once set.
            "key": "custom_field_boolean_type",  # key is mandatory but cannot be changed once set.
            "label": "Custom Field Boolean",
            "default": None,
            "filter_logic": "loose",
            "weight": 100,
            # These are the "management_form" fields required by the dynamic CustomFieldChoice formsets.
            "custom_field_choices-TOTAL_FORMS": "0",  # Set to 0 so validation succeeds until we need it
            "custom_field_choices-INITIAL_FORMS": "1",
            "custom_field_choices-MIN_NUM_FORMS": "0",
            "custom_field_choices-MAX_NUM_FORMS": "1000",
        }

        cls.bulk_edit_data = {
            "grouping": "Updated Grouping",
            "description": "Updated description for testing bulk edit.",
            "required": True,
            "filter_logic": "loose",
            "weight": 200,
            "advanced_ui": True,
            "add_content_types": [ipaddress_ct.pk, prefix_ct.pk],
            "remove_content_types": [device_ct.pk],
        }

    def test_create_object_without_permission(self):
        # Can't have two CustomFields with the same "key"
        self.form_data = self.form_data.copy()
        self.form_data["key"] = "custom_field_boolean_2"
        super().test_create_object_without_permission()

    def test_create_object_with_permission(self):
        # Can't have two CustomFields with the same "key"
        self.form_data = self.form_data.copy()
        self.form_data["key"] = "custom_field_boolean_2"
        super().test_create_object_with_permission()

    def test_create_object_with_constrained_permission(self):
        # Can't have two CustomFields with the same "key"
        self.form_data = self.form_data.copy()
        self.form_data["key"] = "custom_field_boolean_2"
        super().test_create_object_with_constrained_permission()

    def test_create_custom_field_with_choices(self):
        """Ensure a select-type CustomField can be created with multiple valid choices.."""
        self.add_permissions("extras.add_customfield", "extras.view_customfield")

        content_type = ContentType.objects.get_for_model(Location)

        form_data = {
            "content_types": [content_type.pk],
            "type": CustomFieldTypeChoices.TYPE_SELECT,
            "key": "select_with_choices",
            "label": "Select Field with Choices",
            "default": "",
            "filter_logic": "loose",
            "weight": 100,
            "custom_field_choices-TOTAL_FORMS": "2",
            "custom_field_choices-INITIAL_FORMS": "0",
            "custom_field_choices-MIN_NUM_FORMS": "0",
            "custom_field_choices-MAX_NUM_FORMS": "1000",
            "custom_field_choices-0-value": "Option A",
            "custom_field_choices-0-weight": "100",
            "custom_field_choices-1-value": "Option B",
            "custom_field_choices-1-weight": "200",
        }

        response = self.client.post(reverse("extras:customfield_add"), data=form_data, follow=True)

        self.assertEqual(response.status_code, 200)
        self.assertTrue(CustomField.objects.filter(key="select_with_choices").exists())

        field = CustomField.objects.get(key="select_with_choices")
        self.assertEqual(field.custom_field_choices.count(), 2)
        self.assertSetEqual(
            set(field.custom_field_choices.values_list("value", flat=True)),
            {"Option A", "Option B"},
        )

    def test_update_select_custom_field_add_choice(self):
        """Test that submitting the edit form with both existing and new choices
        results in the new choice being saved correctly."""
        self.add_permissions("extras.change_customfield", "extras.view_customfield")

        content_type = ContentType.objects.get_for_model(Location)
        field = CustomField.objects.create(
            type=CustomFieldTypeChoices.TYPE_SELECT,
            label="Editable Select Field",
            key="editable_select_field",
        )
        field.content_types.set([content_type])

        # Added initial choice
        initial_choice = CustomFieldChoice.objects.create(
            custom_field=field,
            value="Initial Option",
            weight=100,
        )

        url = reverse("extras:customfield_edit", args=[field.pk])
        form_data = {
            "content_types": [content_type.pk],
            "type": field.type,
            "key": field.key,
            "label": field.label,
            "default": "",
            "filter_logic": "loose",
            "weight": 100,
            "custom_field_choices-TOTAL_FORMS": "2",
            "custom_field_choices-INITIAL_FORMS": "1",
            "custom_field_choices-MIN_NUM_FORMS": "0",
            "custom_field_choices-MAX_NUM_FORMS": "1000",
            "custom_field_choices-0-id": initial_choice.pk,
            "custom_field_choices-0-value": "Initial Option",
            "custom_field_choices-0-weight": "100",
            "custom_field_choices-1-value": "New Option",
            "custom_field_choices-1-weight": "200",
        }

        response = self.client.post(url, data=form_data, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(field.custom_field_choices.count(), 2)
        self.assertTrue(field.custom_field_choices.filter(value="New Option").exists())

    def test_update_select_custom_field_remove_choice(self):
        """Test removing a choice from a select field."""
        self.add_permissions("extras.change_customfield", "extras.view_customfield")

        content_type = ContentType.objects.get_for_model(Location)
        field = CustomField.objects.create(
            type=CustomFieldTypeChoices.TYPE_SELECT,
            label="Deletable Select Field",
            key="deletable_select_field",
        )
        field.content_types.set([content_type])

        choice = CustomFieldChoice.objects.create(
            custom_field=field,
            value="Choice To Delete",
            weight=100,
        )

        url = reverse("extras:customfield_edit", args=[field.pk])
        form_data = {
            "content_types": [content_type.pk],
            "type": field.type,
            "key": field.key,
            "label": field.label,
            "default": "",
            "filter_logic": "loose",
            "weight": 100,
            "custom_field_choices-TOTAL_FORMS": "1",
            "custom_field_choices-INITIAL_FORMS": "1",
            "custom_field_choices-MIN_NUM_FORMS": "0",
            "custom_field_choices-MAX_NUM_FORMS": "1000",
            "custom_field_choices-0-id": choice.pk,
            "custom_field_choices-0-value": choice.value,
            "custom_field_choices-0-weight": choice.weight,
            "custom_field_choices-0-DELETE": "on",
        }

        response = self.client.post(url, data=form_data, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(field.custom_field_choices.count(), 0)

    def test_create_custom_field_with_invalid_choice_data(self):
        """Ensure invalid choice formset blocks saving."""
        self.add_permissions("extras.add_customfield", "extras.view_customfield")

        content_type = ContentType.objects.get_for_model(Location)

        form_data = {
            "content_types": [content_type.pk],
            "type": CustomFieldTypeChoices.TYPE_SELECT,
            "key": "invalid_choice_field",
            "label": "Field with Invalid Choice",
            "default": "",
            "filter_logic": "loose",
            "weight": 100,
            "custom_field_choices-TOTAL_FORMS": "1",
            "custom_field_choices-INITIAL_FORMS": "0",
            "custom_field_choices-MIN_NUM_FORMS": "0",
            "custom_field_choices-MAX_NUM_FORMS": "1000",
            # Invalid: missing weight, empty value
            "custom_field_choices-0-value": "",
        }

        response = self.client.post(reverse("extras:customfield_add"), data=form_data)

        self.assertEqual(response.status_code, 200)
        self.assertFalse(CustomField.objects.filter(key="invalid_choice_field").exists())
        self.assertFormsetError(
            response.context["choices"], form_index=0, field="value", errors=["This field is required."]
        )
        self.assertFormsetError(
            response.context["choices"], form_index=0, field="weight", errors=["This field is required."]
        )


class CustomLinkRenderingTestCase(TestCase):
    """Tests for the inclusion of CustomLinks, distinct from tests of the CustomLink views themselves."""

    user_permissions = ["dcim.view_location"]

    def test_view_object_with_custom_link(self):
        customlink = CustomLink(
            content_type=ContentType.objects.get_for_model(Location),
            name="Test",
            text="FOO {{ obj.name }} BAR",
            target_url="http://example.com/?location={{ obj.name }}",
            new_window=False,
        )
        customlink.save()
        location_type = LocationType.objects.get(name="Campus")
        status = Status.objects.get_for_model(Location).first()
        location = Location(name="Test Location", location_type=location_type, status=status)
        location.save()

        response = self.client.get(location.get_absolute_url(), follow=True)
        self.assertEqual(response.status_code, 200)
        content = extract_page_body(response.content.decode(response.charset))
        self.assertIn(f"FOO {location.name} BAR", content, content)

    def test_view_object_with_unsafe_custom_link_text(self):
        """Ensure that custom links can't be used as a vector for injecting scripts or breaking HTML."""
        customlink = CustomLink(
            content_type=ContentType.objects.get_for_model(Location),
            name="Test",
            text='<script>alert("Hello world!")</script>',
            target_url="http://example.com/?location=None",
            new_window=False,
        )
        customlink.validated_save()
        location_type = LocationType.objects.get(name="Campus")
        status = Status.objects.get_for_model(Location).first()
        location = Location(name="Test Location", location_type=location_type, status=status)
        location.save()

        response = self.client.get(location.get_absolute_url(), follow=True)
        self.assertEqual(response.status_code, 200)
        content = extract_page_body(response.content.decode(response.charset))
        self.assertNotIn("<script>alert", content, content)
        self.assertIn("&lt;script&gt;alert", content, content)
        self.assertIn(format_html('<a href="{}"', customlink.target_url), content, content)

    def test_view_object_with_unsafe_custom_link_url(self):
        """Ensure that custom links can't be used as a vector for injecting scripts or breaking HTML."""
        customlink = CustomLink(
            content_type=ContentType.objects.get_for_model(Location),
            name="Test",
            text="Hello",
            target_url='"><script>alert("Hello world!")</script><a href="',
            new_window=False,
        )
        customlink.validated_save()
        location_type = LocationType.objects.get(name="Campus")
        status = Status.objects.get_for_model(Location).first()
        location = Location(name="Test Location", location_type=location_type, status=status)
        location.save()

        response = self.client.get(location.get_absolute_url(), follow=True)
        self.assertEqual(response.status_code, 200)
        content = extract_page_body(response.content.decode(response.charset))
        self.assertNotIn("<script>alert", content, content)
        self.assertIn("&lt;script&gt;alert", content, content)
        self.assertIn(format_html('<a href="{}"', customlink.target_url), content, content)

    def test_view_object_with_unsafe_custom_link_name(self):
        """Ensure that custom links can't be used as a vector for injecting scripts or breaking HTML."""
        customlink = CustomLink(
            content_type=ContentType.objects.get_for_model(Location),
            name='<script>alert("Hello World")</script>',
            text="Hello",
            target_url="http://example.com/?location={{ obj.name ",  # intentionally bad jinja2 to trigger error case
            new_window=False,
        )
        customlink.validated_save()
        location_type = LocationType.objects.get(name="Campus")
        status = Status.objects.get_for_model(Location).first()
        location = Location(name="Test Location", location_type=location_type, status=status)
        location.save()

        response = self.client.get(location.get_absolute_url(), follow=True)
        self.assertEqual(response.status_code, 200)
        content = extract_page_body(response.content.decode(response.charset))
        self.assertNotIn("<script>alert", content, content)
        self.assertIn("&lt;script&gt;alert", content, content)


class DynamicGroupTestCase(
    ViewTestCases.CreateObjectViewTestCase,
    ViewTestCases.DeleteObjectViewTestCase,
    ViewTestCases.EditObjectViewTestCase,
    ViewTestCases.GetObjectViewTestCase,
    ViewTestCases.GetObjectChangelogViewTestCase,
    ViewTestCases.ListObjectsViewTestCase,
    ViewTestCases.BulkDeleteObjectsViewTestCase,
    # NOTE: This isn't using `ViewTestCases.PrimaryObjectViewTestCase` because bulk-import/edit
    # views for DynamicGroup do not make sense at this time, primarily because `content_type` is
    # immutable after create.
):
    model = DynamicGroup

    @classmethod
    def setUpTestData(cls):
        content_type = ContentType.objects.get_for_model(Device)

        # DynamicGroup objects to test.
        cls.dynamic_groups = [
            DynamicGroup.objects.create(name="DG 1", content_type=content_type),
            DynamicGroup.objects.create(name="DG 2", content_type=content_type),
            DynamicGroup.objects.create(name="DG 3", content_type=content_type),
        ]

        cls.form_data = {
            "name": "new_dynamic_group",
            "description": "I am a new dynamic group object.",
            "content_type": content_type.pk,
            "group_type": DynamicGroupTypeChoices.TYPE_DYNAMIC_FILTER,
            "tenant": Tenant.objects.first().pk,
            "tags": [t.pk for t in Tag.objects.get_for_model(DynamicGroup)],
            # Management form fields required for the dynamic formset
            "dynamic_group_memberships-TOTAL_FORMS": "0",
            "dynamic_group_memberships-INITIAL_FORMS": "1",
            "dynamic_group_memberships-MIN_NUM_FORMS": "0",
            "dynamic_group_memberships-MAX_NUM_FORMS": "1000",
        }

    def _get_queryset(self):
        return super()._get_queryset().filter(group_type=DynamicGroupTypeChoices.TYPE_DYNAMIC_FILTER)  # TODO

    def test_get_object_with_permission(self):
        location_ct = ContentType.objects.get_for_model(Location)
        instance = self._get_queryset().exclude(content_type=location_ct).first()
        # Add view permissions for the group's members:
        self.add_permissions(
            get_permission_for_model(instance.content_type.model_class(), "view"), "extras.view_dynamicgroup"
        )

        response = self.client.get(instance.get_absolute_url())
        self.assertHttpStatus(response, 200)

        response_body = extract_page_body(response.content.decode(response.charset))
        # Check that the "members" table in the detail view includes all appropriate member objects
        for member in instance.members:
            self.assertIn(str(member.pk), response_body)

        # Test accessing DynamicGroup detail view with a different content type, more specifically, TreeModel
        # https://github.com/nautobot/nautobot/issues/6806
        tree_model_dg = DynamicGroup.objects.create(name="DG 4", content_type=location_ct)
        # Add view permissions for the group's members:
        self.add_permissions(get_permission_for_model(tree_model_dg.content_type.model_class(), "view"))
        response = self.client.get(tree_model_dg.get_absolute_url())
        self.assertHttpStatus(response, 200)
        response_body = extract_page_body(response.content.decode(response.charset))
        # Check that the "members" table in the detail view includes all appropriate member objects
        for member in tree_model_dg.members:
            self.assertIn(str(member.pk), response_body)

    def test_get_object_with_constrained_permission(self):
        instance = self._get_queryset().first()
        # Add view permission for one of the group's members but not the others:
        member1, member2 = instance.members[:2]
        obj_perm = ObjectPermission(
            name="Members permission",
            constraints={"pk": member1.pk},
            actions=["view"],
        )
        obj_perm.save()
        obj_perm.users.add(self.user)
        obj_perm.object_types.add(instance.content_type)

        response = super().test_get_object_with_constrained_permission()

        response_body = extract_page_body(response.content.decode(response.charset))
        # Check that the "members" table in the detail view includes all permitted member objects
        self.assertIn(str(member1.pk), response_body)
        self.assertNotIn(str(member2.pk), response_body)

    def test_get_object_dynamic_groups_anonymous(self):
        url = reverse("dcim:device_dynamicgroups", kwargs={"pk": Device.objects.first().pk})
        self.client.logout()
        response = self.client.get(url, follow=True)
        self.assertHttpStatus(response, 200)
        self.assertRedirects(response, f"/login/?next={url}")

    def test_get_object_dynamic_groups_without_permission(self):
        url = reverse("dcim:device_dynamicgroups", kwargs={"pk": Device.objects.first().pk})
        response = self.client.get(url)
        self.assertHttpStatus(response, [403, 404])

    def test_get_object_dynamic_groups_with_permission(self):
        url = reverse("dcim:device_dynamicgroups", kwargs={"pk": Device.objects.first().pk})
        self.add_permissions("dcim.view_device", "extras.view_dynamicgroup")
        response = self.client.get(url)
        self.assertBodyContains(response, "DG 1")
        self.assertBodyContains(response, "DG 2")
        self.assertBodyContains(response, "DG 3")

    def test_get_object_dynamic_groups_with_constrained_permission(self):
        obj_perm = ObjectPermission(
            name="View a device",
            constraints={"pk": Device.objects.first().pk},
            actions=["view"],
        )
        obj_perm.save()
        obj_perm.users.add(self.user)
        obj_perm.object_types.add(ContentType.objects.get_for_model(Device))
        obj_perm_2 = ObjectPermission(
            name="View a Dynamic Group",
            constraints={"pk": self.dynamic_groups[0].pk},
            actions=["view"],
        )
        obj_perm_2.save()
        obj_perm_2.users.add(self.user)
        obj_perm_2.object_types.add(ContentType.objects.get_for_model(DynamicGroup))

        url = reverse("dcim:device_dynamicgroups", kwargs={"pk": Device.objects.first().pk})
        response = self.client.get(url)
        self.assertHttpStatus(response, 200)
        response_body = extract_page_body(response.content.decode(response.charset))
        self.assertIn("DG 1", response_body, msg=response_body)
        self.assertNotIn("DG 2", response_body, msg=response_body)
        self.assertNotIn("DG 3", response_body, msg=response_body)

        url = reverse("dcim:device_dynamicgroups", kwargs={"pk": Device.objects.last().pk})
        response = self.client.get(url)
        self.assertHttpStatus(response, 404)

    def test_edit_object_with_permission(self):
        instance = self._get_queryset().first()
        self.form_data["content_type"] = instance.content_type.pk  # Content-type is not editable after creation
        super().test_edit_object_with_permission()

    def test_edit_object_with_constrained_permission(self):
        instance = self._get_queryset().first()
        self.form_data["content_type"] = instance.content_type.pk  # Content-type is not editable after creation
        super().test_edit_object_with_constrained_permission()

    def test_edit_object_with_content_type_ipam_prefix(self):
        """Assert bug fix #6526: `Error when defining Dynamic Group of Prefixes using `present_in_vrf_id` filter`"""
        content_type = ContentType.objects.get_for_model(Prefix)
        instance = DynamicGroup.objects.create(name="DG Ipam|Prefix", content_type=content_type)
        vrf_instance = VRF.objects.first()
        data = self.form_data.copy()
        data.update(
            {
                "name": "DG Ipam|Prefix",
                "content_type": content_type.pk,
                "filter-present_in_vrf_id": vrf_instance.id,
                "tenant": None,
                "tags": [],
            }
        )
        self.add_permissions("extras.change_dynamicgroup")
        request = {
            "path": self._get_url("edit", instance),
            "data": post_data(data),
        }
        self.assertHttpStatus(self.client.post(**request), 302)
        instance.refresh_from_db()
        self.assertEqual(instance.filter["present_in_vrf_id"], str(vrf_instance.id))

    @override_settings(EXEMPT_VIEW_PERMISSIONS=["*"])
    def test_edit_saved_filter(self):
        """Test that editing a filter works using the edit view."""
        self.add_permissions("extras.add_dynamicgroup", "extras.change_dynamicgroup")

        # Create the object first.
        data = self.form_data.copy()
        request = {
            "path": self._get_url("add"),
            "data": post_data(data),
        }
        self.assertHttpStatus(self.client.post(**request), 302)

        # Now update it.
        instance = self._get_queryset().get(name=data["name"])
        data["filter-serial"] = ["abc123"]
        request = {
            "path": self._get_url("edit", instance),
            "data": post_data(data),
        }
        self.assertHttpStatus(self.client.post(**request), 302)

        instance.refresh_from_db()
        self.assertEqual(instance.filter, {"serial": data["filter-serial"]})

    @override_settings(EXEMPT_VIEW_PERMISSIONS=["*"])
    def test_filter_by_content_type(self):
        """
        Test that filtering by `content_type` in the UI succeeds.

        This is a regression test for https://github.com/nautobot/nautobot/issues/3612
        """
        path = self._get_url("list")
        response = self.client.get(path + "?content_type=dcim.device")
        self.assertHttpStatus(response, 200)

    @override_settings(EXEMPT_VIEW_PERMISSIONS=["*"])
    def test_bulk_assign_successful(self):
        location_ct = ContentType.objects.get_for_model(Location)
        group_1 = DynamicGroup.objects.create(
            content_type=location_ct, name="Group 1", group_type=DynamicGroupTypeChoices.TYPE_STATIC
        )
        group_2 = DynamicGroup.objects.create(
            content_type=location_ct, name="Group 2", group_type=DynamicGroupTypeChoices.TYPE_STATIC
        )
        group_2.add_members(Location.objects.filter(name__startswith="Root"))

        self.add_permissions(
            "extras.add_staticgroupassociation", "extras.delete_staticgroupassociation", "extras.add_dynamicgroup"
        )

        url = reverse("extras:dynamicgroup_bulk_assign")
        request = {
            "path": url,
            "data": post_data(
                {
                    "content_type": location_ct.pk,
                    "pk": list(Location.objects.filter(parent__isnull=True).values_list("pk", flat=True)),
                    "create_and_assign_to_new_group_name": "Root Locations",
                    "add_to_groups": [group_1.pk],
                    "remove_from_groups": [group_2.pk],
                }
            ),
        }
        response = self.client.post(**request, follow=True)
        self.assertHttpStatus(response, 200)
        new_group = DynamicGroup.objects.get(name="Root Locations")
        self.assertEqual(new_group.content_type, location_ct)
        self.assertEqual(new_group.group_type, DynamicGroupTypeChoices.TYPE_STATIC)
        self.assertQuerysetEqualAndNotEmpty(Location.objects.filter(parent__isnull=True), new_group.members)
        self.assertQuerysetEqualAndNotEmpty(Location.objects.filter(parent__isnull=True), group_1.members)
        self.assertQuerysetEqualAndNotEmpty(
            Location.objects.filter(name__startswith="Root").exclude(parent__isnull=True), group_2.members
        )

    @override_settings(EXEMPT_VIEW_PERMISSIONS=["*"])
    def test_bulk_assign_non_static_groups_forbidden(self):
        location_ct = ContentType.objects.get_for_model(Location)
        group_1 = DynamicGroup.objects.create(content_type=location_ct, name="Group 1")
        group_2 = DynamicGroup.objects.create(
            content_type=location_ct, name="Group 2", group_type=DynamicGroupTypeChoices.TYPE_DYNAMIC_SET
        )

        self.add_permissions(
            "extras.add_staticgroupassociation", "extras.delete_staticgroupassociation", "extras.add_dynamicgroup"
        )

        url = reverse("extras:dynamicgroup_bulk_assign")
        request = {
            "path": url,
            "data": post_data(
                {
                    "content_type": location_ct.pk,
                    "pk": list(Location.objects.filter(parent__isnull=True).distinct().values_list("pk", flat=True)),
                    "add_to_groups": [group_1.pk],
                },
            ),
        }
        response = self.client.post(**request, follow=True)
        self.assertHttpStatus(response, 200)
        # TODO check for specific form validation error?

        del request["data"]["add_to_groups"]
        request["data"]["remove_from_groups"] = [group_2.pk]
        response = self.client.post(**request, follow=True)
        self.assertHttpStatus(response, 200)
        # TODO check for specific form validation error?

    # TODO: negative tests for bulk assign - global and object-level permission violations, invalid data, etc.


class ExportTemplateTestCase(
    ViewTestCases.CreateObjectViewTestCase,
    ViewTestCases.DeleteObjectViewTestCase,
    ViewTestCases.EditObjectViewTestCase,
    ViewTestCases.GetObjectViewTestCase,
    ViewTestCases.GetObjectChangelogViewTestCase,
    ViewTestCases.ListObjectsViewTestCase,
    ViewTestCases.BulkEditObjectsViewTestCase,
):
    model = ExportTemplate

    @classmethod
    def setUpTestData(cls):
        obj_type = ContentType.objects.get_for_model(Location)
        obj_type_1 = ContentType.objects.get_for_model(Interface)

        templates = (
            ExportTemplate(
                name="template-1",
                template_code="template-1 test1",
                content_type=obj_type,
            ),
            ExportTemplate(
                name="template-2",
                template_code="template-2 test2",
                content_type=obj_type,
            ),
            ExportTemplate(
                name="template-3",
                template_code="template-3 test3",
                content_type=obj_type,
            ),
        )

        for template in templates:
            template.save()

        cls.form_data = {
            "name": "template-4",
            "content_type": obj_type.pk,
            "template_code": "template-4 test4",
        }
        cls.bulk_edit_data = {
            "content_type": obj_type_1.pk,
            "description": "Updated template description",
            "mime_type": "application/json",
            "file_extension": "json",
        }


class ExternalIntegrationTestCase(ViewTestCases.PrimaryObjectViewTestCase):
    model = ExternalIntegration
    bulk_edit_data = {"timeout": 10, "verify_ssl": True, "extra_config": '{"baz": "quux"}', "headers": '{"a": "b"}'}
    form_data = {
        "name": "Test External Integration",
        "remote_url": "https://example.com/test1/",
        "verify_ssl": False,
        "secrets_group": None,
        "timeout": 10,
        "extra_config": '{"foo": "bar"}',
        "http_method": WebhookHttpMethodChoices.METHOD_GET,
        "headers": '{"header": "fake header"}',
        "ca_file_path": "this/is/a/file/path",
    }


class GitRepositoryTestCase(
    ViewTestCases.BulkDeleteObjectsViewTestCase,
    ViewTestCases.CreateObjectViewTestCase,
    ViewTestCases.DeleteObjectViewTestCase,
    ViewTestCases.EditObjectViewTestCase,
    ViewTestCases.GetObjectViewTestCase,
    ViewTestCases.GetObjectChangelogViewTestCase,
    ViewTestCases.ListObjectsViewTestCase,
):
    model = GitRepository
    slugify_function = staticmethod(slugify_dashes_to_underscores)
    expected_edit_form_buttons = [
        '<button type="submit" name="_dryrun_update" class="btn btn-warning">Update & Dry Run</button>',
        '<button type="submit" name="_update" class="btn btn-primary">Update & Sync</button>',
    ]
    expected_create_form_buttons = [
        '<button type="submit" name="_dryrun_create" class="btn btn-info">Create & Dry Run</button>',
        '<button type="submit" name="_create" class="btn btn-primary">Create & Sync</button>',
        '<button type="submit" name="_addanother" class="btn btn-primary">Create and Add Another</button>',
    ]

    @classmethod
    def setUpTestData(cls):
        secrets_groups = (
            SecretsGroup.objects.create(name="Secrets Group 1"),
            SecretsGroup.objects.create(name="Secrets Group 2"),
        )

        # Create four GitRepository records
        repos = (
            GitRepository(name="Repo 1", slug="repo_1", remote_url="https://example.com/repo1.git"),
            GitRepository(name="Repo 2", slug="repo_2", remote_url="https://some-local-host/repo2.git"),
            GitRepository(name="Repo 3", slug="repo_3", remote_url="https://example.com/repo3.git"),
            GitRepository(name="Repo 4", remote_url="https://example.com/repo4.git", secrets_group=secrets_groups[0]),
        )
        for repo in repos:
            repo.validated_save()

        cls.form_data = {
            "name": "A new Git repository",
            "slug": "a_new_git_repository",
            "remote_url": "http://another-local-host/a_new_git_repository.git",
            "branch": "develop",
            "_token": "1234567890abcdef1234567890abcdef",
            "secrets_group": secrets_groups[1].pk,
            "provided_contents": [
                "extras.configcontext",
                "extras.job",
                "extras.exporttemplate",
            ],
        }

        cls.slug_source = "name"
        cls.slug_test_object = "Repo 4"

    def test_edit_object_with_permission(self):
        instance = self._get_queryset().first()
        form_data = self.form_data.copy()
        form_data["slug"] = instance.slug  # Slug is not editable
        self.form_data = form_data
        super().test_edit_object_with_permission()

    def test_edit_object_with_constrained_permission(self):
        instance = self._get_queryset().first()
        form_data = self.form_data.copy()
        form_data["slug"] = instance.slug  # Slug is not editable
        self.form_data = form_data
        super().test_edit_object_with_constrained_permission()

    @override_settings(EXEMPT_VIEW_PERMISSIONS=["*"])
    def test_view_when_no_sync_job_result_exists(self):
        instance = self._get_queryset().first()
        response = self.client.get(reverse("extras:gitrepository_result", kwargs={"pk": instance.pk}))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["result"], {})

    def test_post_sync_repo_anonymous(self):
        self.client.logout()
        url = reverse("extras:gitrepository_sync", kwargs={"pk": self._get_queryset().first().pk})
        response = self.client.post(url, follow=True)
        self.assertHttpStatus(response, 200)
        self.assertRedirects(response, f"/login/?next={url}")

    def test_post_sync_repo_without_permission(self):
        url = reverse("extras:gitrepository_sync", kwargs={"pk": self._get_queryset().first().pk})
        response = self.client.post(url)
        self.assertHttpStatus(response, [403, 404])

    # TODO: mock/stub out `enqueue_pull_git_repository_and_refresh_data` and test successful POST with permissions

    def test_post_dryrun_repo_anonymous(self):
        self.client.logout()
        url = reverse("extras:gitrepository_dryrun", kwargs={"pk": self._get_queryset().first().pk})
        response = self.client.post(url, follow=True)
        self.assertHttpStatus(response, 200)
        self.assertRedirects(response, f"/login/?next={url}")

    def test_post_dryrun_repo_without_permission(self):
        url = reverse("extras:gitrepository_dryrun", kwargs={"pk": self._get_queryset().first().pk})
        response = self.client.post(url)
        self.assertHttpStatus(response, [403, 404])

    # TODO: mock/stub out `enqueue_git_repository_diff_origin_and_local` and test successful POST with permissions


class MetadataTypeTestCase(ViewTestCases.PrimaryObjectViewTestCase):
    model = MetadataType
    bulk_edit_data = {"description": "A new description"}

    def setUp(self):
        super().setUp()
        self.form_data = {
            "name": "New Metadata Type",
            "description": "A new type of metadata",
            "data_type": MetadataTypeDataTypeChoices.TYPE_DATETIME,
            "content_types": [
                ContentType.objects.get_for_model(Device).pk,
                ContentType.objects.get_for_model(ContactAssociation).pk,
            ],
            "choices-TOTAL_FORMS": "0",
            "choices-INITIAL_FORMS": "5",
            "choices-MIN_NUM_FORMS": "0",
            "choices-MAX_NUM_FORMS": "1000",
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

    def test_edit_object_with_constrained_permission(self):
        # Can't change data_type once set
        self.form_data["data_type"] = self.model.objects.first().data_type
        return super().test_edit_object_with_constrained_permission()

    def test_edit_object_with_permission(self):
        # Can't change data_type once set
        self.form_data["data_type"] = self.model.objects.first().data_type
        return super().test_edit_object_with_permission()


class NoteTestCase(
    ViewTestCases.CreateObjectViewTestCase,
    ViewTestCases.DeleteObjectViewTestCase,
    ViewTestCases.EditObjectViewTestCase,
    ViewTestCases.GetObjectChangelogViewTestCase,
):
    model = Note

    @classmethod
    def setUpTestData(cls):
        content_type = ContentType.objects.get_for_model(Location)
        cls.location = Location.objects.filter(location_type=LocationType.objects.get(name="Campus")).first()
        user = User.objects.first()

        # Notes Objects to test
        Note.objects.create(
            note="Location has been placed on maintenance.",
            user=user,
            assigned_object_type=content_type,
            assigned_object_id=cls.location.pk,
        )
        Note.objects.create(
            note="Location maintenance has ended.",
            user=user,
            assigned_object_type=content_type,
            assigned_object_id=cls.location.pk,
        )
        Note.objects.create(
            note="Location is under duress.",
            user=user,
            assigned_object_type=content_type,
            assigned_object_id=cls.location.pk,
        )

        cls.form_data = {
            "note": "This is Location note.",
            "assigned_object_type": content_type.pk,
            "assigned_object_id": cls.location.pk,
        }
        cls.expected_object_note = '<textarea name="object_note" cols="40" rows="10" class="form-control" placeholder="Note" id="id_object_note"></textarea>'

    def test_note_on_bulk_update_perms(self):
        self.add_permissions("dcim.add_location", "extras.add_note")
        response = self.client.get(reverse("dcim:location_add"))
        self.assertContains(response, self.expected_object_note, html=True)

    def test_note_on_bulk_update_no_perms(self):
        self.add_permissions("dcim.add_location")
        response = self.client.get(reverse("dcim:location_add"))
        self.assertNotContains(response, self.expected_object_note, html=True)

    def test_note_on_create_edit_perms(self):
        self.add_permissions("dcim.change_location", "extras.add_note")
        response = self.client.post(reverse("dcim:location_bulk_edit"), data={"pk": self.location.pk})
        self.assertContains(response, self.expected_object_note, html=True)

    def test_note_on_create_edit_no_perms(self):
        self.add_permissions("dcim.change_location")
        response = self.client.post(reverse("dcim:location_bulk_edit"), data={"pk": self.location.pk})
        self.assertNotContains(response, self.expected_object_note, html=True)


class SavedViewTest(ModelViewTestCase):
    """
    Tests for Saved Views
    """

    model = SavedView

    def get_view_url_for_saved_view(self, saved_view=None, action="detail"):
        """
        Since saved view detail url redirects, we need to manually construct its detail url
        to test the content of its response.
        """
        url = ""

        if action == "detail" and saved_view:
            url = reverse(saved_view.view) + f"?saved_view={saved_view.pk}"
        elif action == "edit" and saved_view:
            url = saved_view.get_absolute_url() + "update-config/"
        elif action == "create":
            url = reverse("extras:savedview_add")

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
        self.add_permissions("extras.view_savedview")
        self.add_permissions(f"{app_label}.view_{model_name}")

        # Try GET with model-level permission
        # SavedView detail view should redirect to the View from which it is derived
        response = self.client.get(instance.get_absolute_url(), follow=True)
        self.assertBodyContains(response, escape(instance.name))

        query_strings = ["&table_changes_pending=true", "&per_page=1234", "&status=active", "&sort=name"]
        for string in query_strings:
            view_url = self.get_view_url_for_saved_view(instance) + string
            response = self.client.get(view_url)
            # Assert that the star sign is rendered on the page since there are unsaved changes
            self.assertBodyContains(response, '<i title="Pending changes not saved">')

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
        self.assertBodyContains(
            response,
            f"You do not have the required permission to modify this Saved View owned by {instance.owner}",
        )

    @override_settings(EXEMPT_VIEW_PERMISSIONS=["*"])
    def test_update_saved_view_as_owner(self):
        view_name = "dcim:location_list"
        instance = SavedView.objects.create(
            name="Location Saved View",
            owner=self.user,
            view=view_name,
            is_global_default=True,
        )

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
        delete_url = reverse("extras:savedview_delete", kwargs={"pk": instance.pk})
        different_user = User.objects.create(username="User 2", is_active=True)
        # Try delete the saved view with a different user from the owner of the saved view
        self.client.force_login(different_user)
        response = self.client.post(delete_url, follow=True)
        self.assertBodyContains(
            response,
            f"You do not have the required permission to delete this Saved View owned by {instance.owner}",
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
        delete_url = reverse("extras:savedview_delete", kwargs={"pk": instance.pk})
        # Delete functionality should work even without "extras.delete_savedview" permissions
        # if the saved view belongs to the user.
        instance.owner.is_active = True
        instance.owner.save()
        self.client.force_login(instance.owner)
        response = self.client.post(delete_url, follow=True)
        self.assertBodyContains(response, "Are you sure you want to delete saved view")

    @override_settings(EXEMPT_VIEW_PERMISSIONS=["*"])
    def test_create_saved_view(self):
        instance = self._get_queryset().first()
        # User should be able to create saved view with only "{app_label}.view_{model_name}" permission
        # self.add_permissions("extras.add_savedview")
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

    @override_settings(EXEMPT_VIEW_PERMISSIONS=["*"])
    def test_is_global_default(self):
        view_name = "dcim:location_list"
        SavedView.objects.create(
            name="Global Location Default View",
            owner=self.user,
            view=view_name,
            is_global_default=True,
        )
        response = self.client.get(reverse(view_name), follow=True)
        # Assert that Location List View got redirected to Saved View set as global default
        self.assertBodyContains(response, "<strong>Global Location Default View</strong>", html=True)

    @override_settings(EXEMPT_VIEW_PERMISSIONS=["*"])
    def test_user_default(self):
        view_name = "dcim:location_list"
        sv = SavedView.objects.create(
            name="User Location Default View",
            owner=self.user,
            view=view_name,
            is_global_default=True,
        )
        UserSavedViewAssociation.objects.create(user=self.user, saved_view=sv, view_name=sv.view)
        response = self.client.get(reverse(view_name), follow=True)
        # Assert that Location List View got redirected to Saved View set as user default
        self.assertBodyContains(response, "<strong>User Location Default View</strong>", html=True)

    @override_settings(EXEMPT_VIEW_PERMISSIONS=["*"])
    def test_user_default_precedes_global_default(self):
        view_name = "dcim:location_list"
        SavedView.objects.create(
            name="Global Location Default View",
            owner=self.user,
            view=view_name,
            is_global_default=True,
        )
        sv = SavedView.objects.create(
            name="User Location Default View",
            owner=self.user,
            view=view_name,
        )
        UserSavedViewAssociation.objects.create(user=self.user, saved_view=sv, view_name=sv.view)
        response = self.client.get(reverse(view_name), follow=True)
        # Assert that Location List View got redirected to Saved View set as user default
        self.assertBodyContains(response, "<strong>User Location Default View</strong>", html=True)

    @override_settings(EXEMPT_VIEW_PERMISSIONS=["*"])
    def test_filtered_view_precedes_global_default(self):
        view_name = "dcim:location_list"
        # Global saved view that will show Floor type locations only.
        SavedView.objects.create(
            name="Global Location Default View",
            owner=self.user,
            view=view_name,
            is_global_default=True,
            config={
                "filter_params": {
                    "location_type": ["Floor"],
                }
            },
        )
        response = self.client.get(reverse(view_name) + "?location_type=Campus", follow=True)
        # Assert that the user is not redirected to the global default view
        # But instead redirected to the filtered view
        self.assertNotIn(
            "<strong>Global Location Default View</strong>",
            extract_page_body(response.content.decode(response.charset)),
        )

        # Floor type locations (Floor-<number>) should not be visible in the response
        self.assertNotIn(
            "Floor-",
            extract_page_body(response.content.decode(response.charset)),
        )

    @override_settings(EXEMPT_VIEW_PERMISSIONS=["*"])
    def test_filtered_view_precedes_user_default(self):
        view_name = "dcim:location_list"
        # User saved view that will show Floor type locations only.
        sv = SavedView.objects.create(
            name="User Location Default View",
            owner=self.user,
            view=view_name,
            config={
                "filter_params": {
                    "location_type": ["Floor"],
                }
            },
        )
        UserSavedViewAssociation.objects.create(user=self.user, saved_view=sv, view_name=sv.view)
        response = self.client.get(reverse(view_name) + "?location_type=Campus", follow=True)
        # Assert that the user is not redirected to the user default view
        # But instead redirected to the filtered view
        self.assertNotIn(
            "<strong>User Location Default View</strong>", extract_page_body(response.content.decode(response.charset))
        )
        # Floor type locations (Floor-<number>) should not be visible in the response
        self.assertNotIn(
            "Floor-",
            extract_page_body(response.content.decode(response.charset)),
        )

    @override_settings(EXEMPT_VIEW_PERMISSIONS=[])
    def test_is_shared(self):
        view_name = "dcim:location_list"
        new_user = User.objects.create(username="Different User", is_active=True)
        sv_shared = SavedView.objects.create(
            name="Shared Location Saved View",
            owner=new_user,
            view=view_name,
        )
        sv_not_shared = SavedView.objects.create(
            name="Private Location Saved View",
            owner=new_user,
            view=view_name,
            is_shared=False,
        )
        app_label = view_name.split(":")[0]
        model_name = view_name.split(":")[1].split("_")[0]
        self.add_permissions(f"{app_label}.view_{model_name}")
        response = self.client.get(reverse(view_name), follow=True)
        # Assert that Location List View got redirected to Saved View set as user default
        self.assertHttpStatus(response, 200)
        response_body = extract_page_body(response.content.decode(response.charset))
        self.assertIn(str(sv_shared.pk), response_body, msg=response_body)
        self.assertNotIn(str(sv_not_shared.pk), response_body, msg=response_body)

    @override_settings(EXEMPT_VIEW_PERMISSIONS=["*"])
    def test_create_saved_views_contain_boolean_filter_params(self):
        """
        Test the entire Save View workflow from creating a Saved View to rendering the View with boolean filter parameters.
        """
        with self.subTest("Create job Saved View with boolean filter parameters"):
            view_name = "extras:job_list"
            app_label = view_name.split(":")[0]
            model_name = view_name.split(":")[1].split("_")[0]
            self.add_permissions(f"{app_label}.view_{model_name}")
            create_query_strings = [
                "&hidden=True",
            ]
            create_url = self.get_view_url_for_saved_view(action="create")
            sv_name = "Hidden Jobs"
            request = {
                "path": create_url,
                "data": post_data({"name": sv_name, "view": f"{view_name}", "params": "".join(create_query_strings)}),
            }
            self.assertHttpStatus(self.client.post(**request), 302)
            instance = SavedView.objects.get(name=sv_name)
            hidden_job = Job.objects.get(name="Example hidden job")
            hidden_job.description = "I should not show in the UI!"
            hidden_job.save()
            self.assertEqual(instance.config["filter_params"]["hidden"], "True")
            response = self.client.get(reverse(view_name) + "?saved_view=" + str(instance.pk), follow=True)
            # Assert that Job List View rendered with the boolean filter parameter without error
            self.assertHttpStatus(response, 200)
            response_body = extract_page_body(response.content.decode(response.charset))
            self.assertIn(str(instance.pk), response_body, msg=response_body)
            self.assertBodyContains(response, f"<strong>{sv_name}</strong>", html=True)
            # This is the description
            self.assertBodyContains(response, "I should not show in the UI!", html=True)

        with self.subTest("Create device Saved View with boolean filter parameters"):
            view_name = "dcim:device_list"
            app_label = view_name.split(":")[0]
            model_name = view_name.split(":")[1].split("_")[0]
            self.add_permissions(f"{app_label}.view_{model_name}")
            create_query_strings = [
                "&per_page=12",
                "&has_primary_ip=True",
                "&sort=name",
            ]
            create_url = self.get_view_url_for_saved_view(action="create")
            sv_name = "Devices with primary ips"
            request = {
                "path": create_url,
                "data": post_data({"name": sv_name, "view": f"{view_name}", "params": "".join(create_query_strings)}),
            }
            self.assertHttpStatus(self.client.post(**request), 302)
            instance = SavedView.objects.get(name=sv_name)
            self.assertEqual(instance.config["pagination_count"], 12)
            self.assertEqual(instance.config["filter_params"]["has_primary_ip"], "True")
            self.assertEqual(instance.config["sort_order"], ["name"])
            response = self.client.get(reverse(view_name) + "?saved_view=" + str(instance.pk), follow=True)
            # Assert that Job List View rendered with the boolean filter parameter without error
            self.assertHttpStatus(response, 200)
            response_body = extract_page_body(response.content.decode(response.charset))
            self.assertIn(str(instance.pk), response_body, msg=response_body)
            self.assertBodyContains(response, f"<strong>{sv_name}</strong>", html=True)

    @override_settings(EXEMPT_VIEW_PERMISSIONS=["*"])
    def test_update_saved_view_contain_boolean_filter_params(self):
        with self.subTest("Update job Saved View with boolean filter parameters"):
            view_name = "extras:job_list"
            sv_name = "Non-hidden jobs"
            instance = SavedView.objects.create(
                name=sv_name,
                owner=self.user,
                view=view_name,
            )
            update_query_strings = ["hidden=False"]
            update_url = self.get_view_url_for_saved_view(instance, "edit") + "?" + "".join(update_query_strings)
            # Try update the saved view with the same user as the owner of the saved view
            instance.owner.is_active = True
            instance.owner.save()
            self.client.force_login(instance.owner)
            response = self.client.get(update_url)
            self.assertHttpStatus(response, 302)
            instance.refresh_from_db()
            self.assertEqual(instance.config["filter_params"]["hidden"], "False")
            response = self.client.get(reverse(view_name) + "?saved_view=" + str(instance.pk), follow=True)
            # Assert that Job List View rendered with the boolean filter parameter without error
            self.assertHttpStatus(response, 200)
            response_body = extract_page_body(response.content.decode(response.charset))
            self.assertNotIn("Example hidden job", response_body, msg=response_body)
            self.assertBodyContains(response, f"<strong>{sv_name}</strong>", html=True)

        with self.subTest("Update device Saved View with boolean filter parameters"):
            view_name = "dcim:device_list"
            sv_name = "Devices with no primary ips"
            instance = SavedView.objects.create(
                name=sv_name,
                owner=self.user,
                view=view_name,
            )
            update_query_strings = ["has_primary_ip=False"]
            update_url = self.get_view_url_for_saved_view(instance, "edit") + "?" + "".join(update_query_strings)
            # Try update the saved view with the same user as the owner of the saved view
            instance.owner.is_active = True
            instance.owner.save()
            self.client.force_login(instance.owner)
            response = self.client.get(update_url)
            self.assertHttpStatus(response, 302)
            instance.refresh_from_db()
            self.assertEqual(instance.config["filter_params"]["has_primary_ip"], "False")
            response = self.client.get(reverse(view_name) + "?saved_view=" + str(instance.pk), follow=True)
            # Assert that Job List View rendered with the boolean filter parameter without error
            self.assertHttpStatus(response, 200)
            response_body = extract_page_body(response.content.decode(response.charset))
            self.assertBodyContains(response, f"<strong>{sv_name}</strong>", html=True)


# Not a full-fledged PrimaryObjectViewTestCase as there's no BulkEditView for Secrets
class SecretTestCase(
    ViewTestCases.GetObjectViewTestCase,
    ViewTestCases.GetObjectChangelogViewTestCase,
    ViewTestCases.CreateObjectViewTestCase,
    ViewTestCases.EditObjectViewTestCase,
    ViewTestCases.DeleteObjectViewTestCase,
    ViewTestCases.ListObjectsViewTestCase,
    ViewTestCases.BulkDeleteObjectsViewTestCase,
):
    model = Secret

    @classmethod
    def setUpTestData(cls):
        secrets = (
            Secret(
                name="View Test 1",
                provider="environment-variable",
                parameters={"variable": "VIEW_TEST_1"},
                tags=[t.pk for t in Tag.objects.get_for_model(Secret)],
            ),
            Secret(
                name="View Test 2",
                provider="environment-variable",
                parameters={"variable": "VIEW_TEST_2"},
            ),
            Secret(
                name="View Test 3",
                provider="environment-variable",
                parameters={"variable": "VIEW_TEST_3"},
            ),
        )

        for secret in secrets:
            secret.validated_save()

        cls.form_data = {
            "name": "View Test 4",
            "provider": "environment-variable",
            "parameters": '{"variable": "VIEW_TEST_4"}',
        }


class SecretsGroupTestCase(
    ViewTestCases.OrganizationalObjectViewTestCase,
    ViewTestCases.BulkEditObjectsViewTestCase,
):
    model = SecretsGroup
    custom_test_permissions = [
        "extras.view_secret",
        "extras.add_secretsgroup",
        "extras.view_secretsgroup",
        "extras.add_secretsgroupassociation",
        "extras.change_secretsgroupassociation",
    ]

    @classmethod
    def setUpTestData(cls):
        secrets_groups = (
            SecretsGroup.objects.create(name="Group 1", description="First Group"),
            SecretsGroup.objects.create(name="Group 2"),
            SecretsGroup.objects.create(name="Group 3"),
        )

        secrets = (
            Secret.objects.create(name="secret 1", provider="text-file", parameters={"path": "/tmp"}),  # noqa: S108  # hardcoded-temp-file -- false positive
            Secret.objects.create(name="secret 2", provider="text-file", parameters={"path": "/tmp"}),  # noqa: S108  # hardcoded-temp-file -- false positive
            Secret.objects.create(name="secret 3", provider="text-file", parameters={"path": "/tmp"}),  # noqa: S108  # hardcoded-temp-file -- false positive
        )

        SecretsGroupAssociation.objects.create(
            secrets_group=secrets_groups[0],
            secret=secrets[0],
            access_type=SecretsGroupAccessTypeChoices.TYPE_GENERIC,
            secret_type=SecretsGroupSecretTypeChoices.TYPE_USERNAME,
        )
        SecretsGroupAssociation.objects.create(
            secrets_group=secrets_groups[0],
            secret=secrets[1],
            access_type=SecretsGroupAccessTypeChoices.TYPE_GENERIC,
            secret_type=SecretsGroupSecretTypeChoices.TYPE_PASSWORD,
        )
        SecretsGroupAssociation.objects.create(
            secrets_group=secrets_groups[1],
            secret=secrets[1],
            access_type=SecretsGroupAccessTypeChoices.TYPE_GENERIC,
            secret_type=SecretsGroupSecretTypeChoices.TYPE_PASSWORD,
        )

        cls.form_data = {
            "name": "Group 4",
            "description": "Some description",
            # Management form fields required for the dynamic Secret formset
            "secrets_group_associations-TOTAL_FORMS": "0",
            "secrets_group_associations-INITIAL_FORMS": "1",
            "secrets_group_associations-MIN_NUM_FORMS": "0",
            "secrets_group_associations-MAX_NUM_FORMS": "1000",
        }
        cls.bulk_edit_data = {
            "description": "This is a very detailed new description",
        }

    def test_create_group_with_valid_secret_association(self):
        """Test that a SecretsGroup with a valid Secret association saves correctly via the formset."""
        self.add_permissions(*self.custom_test_permissions)
        # Create a secret to associate
        secret = Secret.objects.create(
            name="AWS_Secret",
            provider="text-file",
            parameters={"path": "/tmp"},  # noqa: S108  # hardcoded-temp-file -- false positive
        )

        form_data = {
            "name": "test",
            "description": "test bulk edits",
            "secrets_group_associations-TOTAL_FORMS": "1",
            "secrets_group_associations-INITIAL_FORMS": "0",
            "secrets_group_associations-MIN_NUM_FORMS": "0",
            "secrets_group_associations-MAX_NUM_FORMS": "1000",
            "secrets_group_associations-0-secret": secret.pk,
            "secrets_group_associations-0-access_type": SecretsGroupAccessTypeChoices.TYPE_HTTP,
            "secrets_group_associations-0-secret_type": SecretsGroupSecretTypeChoices.TYPE_PASSWORD,
        }

        # Submit the form to the "add SecretsGroup" view
        response = self.client.post(reverse("extras:secretsgroup_add"), data=form_data, follow=True)

        self.assertEqual(response.status_code, 200)
        self.assertTrue(SecretsGroup.objects.filter(name="test").exists())

        # Checks that the association was created correctly
        group = SecretsGroup.objects.get(name="test")
        self.assertEqual(group.secrets_group_associations.count(), 1)

        association = group.secrets_group_associations.first()
        self.assertEqual(association.secret, secret)
        self.assertEqual(association.access_type, SecretsGroupAccessTypeChoices.TYPE_HTTP)
        self.assertEqual(association.secret_type, SecretsGroupSecretTypeChoices.TYPE_PASSWORD)

    def test_create_group_with_invalid_secret_association(self):
        """Test that invalid Secret association formset raises validation error and does not save."""
        self.add_permissions(*self.custom_test_permissions)
        url = reverse("extras:secretsgroup_add")

        form_data = {
            "name": "Invalid Secrets Group",
            "description": "Missing required fields",
            "secrets_group_associations-TOTAL_FORMS": "1",
            "secrets_group_associations-INITIAL_FORMS": "0",
            "secrets_group_associations-MIN_NUM_FORMS": "0",
            "secrets_group_associations-MAX_NUM_FORMS": "1000",
            "secrets_group_associations-0-secret": "",  # invalid
            "secrets_group_associations-0-access_type": SecretsGroupAccessTypeChoices.TYPE_HTTP,
            "secrets_group_associations-0-secret_type": "",  # invalid
        }

        response = self.client.post(url, data=form_data)

        self.assertEqual(response.status_code, 200)

        # Checks that no new SecretsGroup was created
        self.assertFalse(SecretsGroup.objects.filter(name="Invalid Secrets Group").exists())

        # Checks that formset errors are raised in the context
        self.assertFormsetError(
            response.context["secrets"], form_index=0, field="secret", errors=["This field is required."]
        )

    def test_create_group_with_deleted_secret_fails_cleanly(self):
        """
        Creating a SecretsGroup with a deleted Secret should fail with a formset error.
        """
        self.add_permissions(*self.custom_test_permissions)

        secret = Secret.objects.create(name="TempSecret", provider="text-file", parameters={"path": "/tmp"})  # noqa: S108  # hardcoded-temp-file -- false positive
        secret_pk = secret.pk
        secret.delete()

        form_data = {
            "name": "Test Group",
            "description": "This should not be created",
            "secrets_group_associations-TOTAL_FORMS": "1",
            "secrets_group_associations-INITIAL_FORMS": "0",
            "secrets_group_associations-MIN_NUM_FORMS": "0",
            "secrets_group_associations-MAX_NUM_FORMS": "1000",
            "secrets_group_associations-0-secret": secret_pk,
            "secrets_group_associations-0-access_type": SecretsGroupAccessTypeChoices.TYPE_HTTP,
            "secrets_group_associations-0-secret_type": SecretsGroupSecretTypeChoices.TYPE_PASSWORD,
        }

        response = self.client.post(reverse("extras:secretsgroup_add"), data=form_data)
        self.assertEqual(response.status_code, 200)

        self.assertFormsetError(
            response.context["secrets"],
            form_index=0,
            field="secret",
            errors=["Select a valid choice. That choice is not one of the available choices."],
        )
        self.assertFalse(SecretsGroup.objects.filter(name="Test Group").exists())


class GraphQLQueriesTestCase(
    ViewTestCases.CreateObjectViewTestCase,
    ViewTestCases.DeleteObjectViewTestCase,
    ViewTestCases.EditObjectViewTestCase,
    ViewTestCases.GetObjectViewTestCase,
    ViewTestCases.GetObjectChangelogViewTestCase,
    ViewTestCases.ListObjectsViewTestCase,
):
    model = GraphQLQuery

    @classmethod
    def setUpTestData(cls):
        graphqlqueries = (
            GraphQLQuery(
                name="graphql-query-1",
                query="{ query: locations {name} }",
            ),
            GraphQLQuery(
                name="graphql-query-2",
                query='{ devices(role: "edge") { id, name, device_role { name } } }',
            ),
            GraphQLQuery(
                name="graphql-query-3",
                query=BIG_GRAPHQL_DEVICE_QUERY,
            ),
            GraphQLQuery(
                name="Graphql Query 5",
                query='{ devices(role: "edge") { id, name, device_role { name } } }',
            ),
        )

        for query in graphqlqueries:
            query.full_clean()
            query.save()

        cls.form_data = {
            "name": "graphql-query-4",
            "query": "{query: locations {name}}",
        }


#
# Jobs, Scheduling, and Approvals
#


class ScheduledJobTestCase(
    ViewTestCases.GetObjectViewTestCase,
    ViewTestCases.ListObjectsViewTestCase,
    ViewTestCases.DeleteObjectViewTestCase,
    ViewTestCases.BulkDeleteObjectsViewTestCase,
):
    model = ScheduledJob

    @classmethod
    def setUpTestData(cls):
        user = User.objects.create(username="user1", is_active=True)
        ScheduledJob.objects.create(
            name="test1",
            task="pass_job.TestPassJob",
            interval=JobExecutionType.TYPE_IMMEDIATELY,
            user=user,
            start_time=timezone.now(),
        )
        ScheduledJob.objects.create(
            name="test2",
            task="pass_job.TestPassJob",
            interval=JobExecutionType.TYPE_DAILY,
            user=user,
            start_time=timezone.now(),
        )
        ScheduledJob.objects.create(
            name="test3",
            task="pass_job.TestPassJob",
            interval=JobExecutionType.TYPE_CUSTOM,
            user=user,
            start_time=timezone.now(),
            crontab="15 10 * * *",
        )

    def test_only_enabled_is_listed(self):
        self.add_permissions("extras.view_scheduledjob")

        # this should not appear, since it's not enabled
        ScheduledJob.objects.create(
            enabled=False,
            name="test4",
            task="pass_job.TestPassJob",
            interval=JobExecutionType.TYPE_IMMEDIATELY,
            user=self.user,
            start_time=timezone.now(),
        )

        response = self.client.get(self._get_url("list"))
        self.assertHttpStatus(response, 200)
        self.assertNotIn("test4", extract_page_body(response.content.decode(response.charset)))

    def test_non_valid_crontab_syntax(self):
        self.add_permissions("extras.view_scheduledjob")

        def scheduled_job_factory(name, crontab):
            ScheduledJob.objects.create(
                enabled=True,
                name=name,
                task="pass_job.TestPassJob",
                interval=JobExecutionType.TYPE_CUSTOM,
                user=self.user,
                start_time=timezone.now(),
                crontab=crontab,
            )

        with self.assertRaises(ValidationError):
            scheduled_job_factory("test5", None)

        with self.assertRaises(ValidationError):
            scheduled_job_factory("test6", "")

        with self.assertRaises(ValidationError):
            scheduled_job_factory("test7", "not_enough_values_to_unpack")

        with self.assertRaises(ValidationError):
            scheduled_job_factory("test8", "one too many values to unpack")

        with self.assertRaises(ValidationError):
            scheduled_job_factory("test9", "-1 * * * *")

        with self.assertRaises(ValidationError):
            scheduled_job_factory("test10", "invalid literal * * *")

    def test_valid_crontab_syntax(self):
        self.add_permissions("extras.view_scheduledjob")

        ScheduledJob.objects.create(
            enabled=True,
            name="test11",
            task="pass_job.TestPassJob",
            interval=JobExecutionType.TYPE_CUSTOM,
            user=self.user,
            start_time=timezone.now(),
            crontab="*/15 9,17 3 * 1-5",
        )

        response = self.client.get(self._get_url("list"))
        self.assertHttpStatus(response, 200)
        self.assertIn("test11", extract_page_body(response.content.decode(response.charset)))


class ApprovalQueueTestCase(
    # It would be nice to use ViewTestCases.GetObjectViewTestCase as well,
    # but we can't directly use it as it uses instance.get_absolute_url() rather than self._get_url("view", instance)
    ViewTestCases.ListObjectsViewTestCase,
):
    model = ScheduledJob
    # Many interactions with a ScheduledJob also require permissions to view the associated Job
    user_permissions = ("extras.view_job",)

    def _get_url(self, action, instance=None):
        if action == "list":
            return reverse("extras:scheduledjob_approval_queue_list")
        if action == "view" and instance is not None:
            return reverse("extras:scheduledjob_approval_request_view", kwargs={"pk": instance.pk})
        raise ValueError("This override is only valid for list and view test cases")

    def get_list_url(self):
        return reverse("extras:scheduledjob_approval_queue_list")

    def setUp(self):
        super().setUp()
        self.job_model = Job.objects.get_for_class_path("dry_run.TestDryRun")
        self.job_model_2 = Job.objects.get_for_class_path("fail.TestFailJob")

        ScheduledJob.objects.create(
            name="test1",
            task="dry_run.TestDryRun",
            job_model=self.job_model,
            interval=JobExecutionType.TYPE_IMMEDIATELY,
            user=self.user,
            approval_required=True,
            start_time=timezone.now(),
        )
        ScheduledJob.objects.create(
            name="test2",
            task="fail.TestFailJob",
            job_model=self.job_model_2,
            interval=JobExecutionType.TYPE_IMMEDIATELY,
            user=self.user,
            approval_required=True,
            start_time=timezone.now(),
        )

    def test_only_approvable_is_listed(self):
        self.add_permissions("extras.view_scheduledjob")

        ScheduledJob.objects.create(
            name="test4",
            task="pass_job.TestPassJob",
            job_model=self.job_model,
            interval=JobExecutionType.TYPE_IMMEDIATELY,
            user=self.user,
            approval_required=False,
            start_time=timezone.now(),
        )

        response = self.client.get(self._get_url("list"))
        self.assertHttpStatus(response, 200)
        self.assertNotIn("test4", extract_page_body(response.content.decode(response.charset)))

    #
    # Reimplementations of ViewTestCases.GetObjectViewTestCase test functions.
    # Needed because those use instance.get_absolute_url() instead of self._get_url("view", instance)...
    #

    @override_settings(EXEMPT_VIEW_PERMISSIONS=["*"])
    def test_get_object_anonymous(self):
        self.client.logout()
        response = self.client.get(self._get_url("view", self._get_queryset().first()))
        self.assertHttpStatus(response, 200)

    @override_settings(EXEMPT_VIEW_PERMISSIONS=[])
    def test_get_object_without_permission(self):
        instance = self._get_queryset().first()

        with disable_warnings("django.request"):
            self.assertHttpStatus(self.client.get(self._get_url("view", instance)), 403)

    @override_settings(EXEMPT_VIEW_PERMISSIONS=[])
    def test_get_object_with_permission(self):
        instance = self._get_queryset().first()

        # Add model-level permission
        obj_perm = ObjectPermission(name="Test permission", actions=["view"])
        obj_perm.save()
        obj_perm.users.add(self.user)
        obj_perm.object_types.add(ContentType.objects.get_for_model(self.model))

        # Try GET with model-level permission
        response = self.client.get(self._get_url("view", instance))
        # The object's display name or string representation should appear in the response
        self.assertBodyContains(response, getattr(instance, "display", str(instance)))

        # skip GetObjectViewTestCase checks for Relationships and Custom Fields since this isn't actually a detail view

    @override_settings(EXEMPT_VIEW_PERMISSIONS=[])
    def test_get_object_with_constrained_permission(self):
        instance1, instance2 = self._get_queryset().all()[:2]

        # Add object-level permission
        obj_perm = ObjectPermission(
            name="Test permission",
            constraints={"pk": instance1.pk},
            # To get a different rendering flow than the "test_get_object_with_permission" test above,
            # enable additional permissions for this object so that interaction buttons are rendered.
            actions=["view", "add", "change", "delete"],
        )
        obj_perm.save()
        obj_perm.users.add(self.user)
        obj_perm.object_types.add(ContentType.objects.get_for_model(self.model))

        # Try GET to permitted object
        self.assertHttpStatus(self.client.get(self._get_url("view", instance1)), 200)

        # Try GET to non-permitted object
        self.assertHttpStatus(self.client.get(self._get_url("view", instance2)), 404)

    #
    # Additional test cases specific to the job approval view
    #

    @override_settings(EXEMPT_VIEW_PERMISSIONS=["*"])
    def test_post_anonymous(self):
        """Anonymous users may not take any action with regard to job approval requests."""
        self.client.logout()
        response = self.client.post(self._get_url("view", self._get_queryset().first()))
        self.assertBodyContains(response, "You do not have permission to run jobs")
        # No job was submitted
        self.assertFalse(JobResult.objects.filter(name=self.job_model.name).exists())

    @override_settings(EXEMPT_VIEW_PERMISSIONS=[])
    def test_post_dry_run_not_runnable(self):
        """A non-enabled job cannot be dry-run."""
        self.add_permissions("extras.view_scheduledjob")
        instance = self._get_queryset().first()
        data = {"_dry_run": True}

        response = self.client.post(self._get_url("view", instance), data)
        self.assertBodyContains(response, "This job cannot be run at this time")
        # No job was submitted
        self.assertFalse(JobResult.objects.filter(name=instance.job_model.name).exists())

    @override_settings(EXEMPT_VIEW_PERMISSIONS=[])
    def test_post_dry_run_needs_job_run_permission(self):
        """A user without run_job permission cannot dry-run a job."""
        self.add_permissions("extras.view_scheduledjob")
        instance = self._get_queryset().first()
        instance.job_model.enabled = True
        instance.job_model.save()
        data = {"_dry_run": True}

        response = self.client.post(self._get_url("view", instance), data)
        self.assertBodyContains(response, "You do not have permission to run this job")
        # No job was submitted
        self.assertFalse(JobResult.objects.filter(name=instance.job_model.name).exists())

    @override_settings(EXEMPT_VIEW_PERMISSIONS=[])
    def test_post_dry_run_needs_specific_job_run_permission(self):
        """A user without run_job permission FOR THAT SPECIFIC JOB cannot dry-run a job."""
        self.add_permissions("extras.view_scheduledjob")
        instance1, instance2 = self._get_queryset().all()[:2]
        data = {"_dry_run": True}
        obj_perm = ObjectPermission(name="Test permission", constraints={"pk": instance1.job_model.pk}, actions=["run"])
        obj_perm.save()
        obj_perm.users.add(self.user)
        obj_perm.object_types.add(ContentType.objects.get_for_model(Job))
        instance1.job_model.enabled = True
        instance1.job_model.save()
        instance2.job_model.enabled = True
        instance2.job_model.save()

        response = self.client.post(self._get_url("view", instance2), data)
        self.assertBodyContains(response, "You do not have permission to run this job")
        # No job was submitted
        job_names = [instance1.job_model.name, instance2.job_model.name]
        self.assertFalse(JobResult.objects.filter(name__in=job_names).exists())

    @override_settings(EXEMPT_VIEW_PERMISSIONS=["*"])
    @mock.patch("nautobot.extras.views.get_worker_count", return_value=1)
    def test_post_dry_run_not_supported(self, _):
        """Request a dry run on a job that doesn't support dryrun."""
        self.add_permissions("extras.view_scheduledjob")
        instance = ScheduledJob.objects.filter(name="test2").first()
        instance.job_model.enabled = True
        instance.job_model.save()
        obj_perm = ObjectPermission(name="Test permission", constraints={"pk": instance.job_model.pk}, actions=["run"])
        obj_perm.save()
        obj_perm.users.add(self.user)
        obj_perm.object_types.add(ContentType.objects.get_for_model(Job))
        data = {"_dry_run": True}

        response = self.client.post(self._get_url("view", instance), data)
        # Job was not submitted
        self.assertFalse(JobResult.objects.filter(name=instance.job_model.class_path).exists())
        self.assertContains(response, "This job does not support dryrun")

    @override_settings(EXEMPT_VIEW_PERMISSIONS=["*"])
    @mock.patch("nautobot.extras.views.get_worker_count", return_value=1)
    @mock.patch("nautobot.extras.models.jobs.JobResult.enqueue_job")
    def test_post_dry_run_success(self, mock_enqueue_job, _):
        """Successfully request a dry run based on object-based run_job permissions."""
        self.add_permissions("extras.view_scheduledjob")
        instance = ScheduledJob.objects.filter(name="test1").first()
        instance.job_model.enabled = True
        instance.job_model.save()
        obj_perm = ObjectPermission(name="Test permission", constraints={"pk": instance.job_model.pk}, actions=["run"])
        obj_perm.save()
        obj_perm.users.add(self.user)
        obj_perm.object_types.add(ContentType.objects.get_for_model(Job))
        data = {"_dry_run": True}

        mock_enqueue_job.side_effect = lambda job_model, *args, **kwargs: JobResult.objects.create(name=job_model.name)

        response = self.client.post(self._get_url("view", instance), data)
        # Job was submitted
        mock_enqueue_job.assert_called_once()
        job_result = JobResult.objects.get(name=instance.job_model.name)
        self.assertRedirects(response, reverse("extras:jobresult", kwargs={"pk": job_result.pk}))

    @override_settings(EXEMPT_VIEW_PERMISSIONS=["*"])
    def test_post_deny_different_user_lacking_permissions(self):
        """A user needs both delete_scheduledjob and approve_job permissions to deny a job request."""
        user1 = User.objects.create_user(username="testuser1")
        user2 = User.objects.create_user(username="testuser2")

        # Give both users view_scheduledjob permission
        obj_perm = ObjectPermission(name="View", actions=["view"])
        obj_perm.save()
        obj_perm.users.add(user1, user2)
        obj_perm.object_types.add(ContentType.objects.get_for_model(ScheduledJob))

        # Give user1 delete_scheduledjob permission but not approve_job permission
        obj_perm = ObjectPermission(name="Delete", actions=["delete"])
        obj_perm.save()
        obj_perm.users.add(user1)
        obj_perm.object_types.add(ContentType.objects.get_for_model(ScheduledJob))

        # Give user2 approve_job permission but not delete_scheduledjob permission
        obj_perm = ObjectPermission(name="Approve", actions=["approve"])
        obj_perm.save()
        obj_perm.users.add(user2)
        obj_perm.object_types.add(ContentType.objects.get_for_model(Job))

        instance = self._get_queryset().first()
        data = {"_deny": True}

        for user in (user1, user2):
            self.client.force_login(user)
            response = self.client.post(self._get_url("view", instance), data)
            self.assertBodyContains(response, "You do not have permission")
            # Request was not deleted
            self.assertEqual(1, len(ScheduledJob.objects.filter(pk=instance.pk)), msg=str(user))

    @override_settings(EXEMPT_VIEW_PERMISSIONS=["*"])
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
    def test_post_deny_different_user_permitted(self):
        """A user with appropriate permissions can deny a job request."""
        user = User.objects.create_user(username="testuser1")
        instance = self._get_queryset().first()

        # Give user view_scheduledjob and delete_scheduledjob permissions
        obj_perm = ObjectPermission(name="View", actions=["view", "delete"], constraints={"pk": instance.pk})
        obj_perm.save()
        obj_perm.users.add(user)
        obj_perm.object_types.add(ContentType.objects.get_for_model(ScheduledJob))

        # Give user approve_job permission
        obj_perm = ObjectPermission(name="Approve", actions=["approve"], constraints={"pk": instance.job_model.pk})
        obj_perm.save()
        obj_perm.users.add(user)
        obj_perm.object_types.add(ContentType.objects.get_for_model(Job))

        data = {"_deny": True}

        self.client.force_login(user)
        with self.assertLogs("nautobot.events") as cm:
            response = self.client.post(self._get_url("view", instance), data)
        self.assertRedirects(response, reverse("extras:scheduledjob_approval_queue_list"))
        # Request was deleted
        self.assertEqual(0, len(ScheduledJob.objects.filter(pk=instance.pk)))
        # Event was published
        expected_payload = {"data": serialize_object_v2(instance)}
        self.assertEqual(
            cm.output,
            [
                f"INFO:nautobot.events.nautobot.jobs.approval.denied:{json.dumps(expected_payload, cls=NautobotKombuJSONEncoder, indent=4)}"
            ],
        )

        # Check object-based permissions are enforced for a different instance
        instance = self._get_queryset().first()
        response = self.client.post(self._get_url("view", instance), data)
        self.assertBodyContains(response, "You do not have permission")
        # Request was not deleted
        self.assertEqual(1, len(ScheduledJob.objects.filter(pk=instance.pk)), msg=str(user))

    @override_settings(EXEMPT_VIEW_PERMISSIONS=["*"])
    def test_post_approve_cannot_self_approve(self):
        self.add_permissions("extras.change_scheduledjob")
        self.add_permissions("extras.approve_job")
        instance = self._get_queryset().first()
        data = {"_approve": True}

        response = self.client.post(self._get_url("view", instance), data)
        self.assertBodyContains(response, "You cannot approve your own job request")
        # Job was not approved
        instance.refresh_from_db()
        self.assertIsNone(instance.approved_by_user)

    @override_settings(EXEMPT_VIEW_PERMISSIONS=["*"])
    def test_post_approve_different_user_lacking_permissions(self):
        """A user needs both change_scheduledjob and approve_job permissions to approve a job request."""
        user1 = User.objects.create_user(username="testuser1")
        user2 = User.objects.create_user(username="testuser2")

        # Give both users view_scheduledjob permission
        obj_perm = ObjectPermission(name="View", actions=["view"])
        obj_perm.save()
        obj_perm.users.add(user1, user2)
        obj_perm.object_types.add(ContentType.objects.get_for_model(ScheduledJob))

        # Give user1 change_scheduledjob permission but not approve_job permission
        obj_perm = ObjectPermission(name="Change", actions=["change"])
        obj_perm.save()
        obj_perm.users.add(user1)
        obj_perm.object_types.add(ContentType.objects.get_for_model(ScheduledJob))

        # Give user2 approve_job permission but not change_scheduledjob permission
        obj_perm = ObjectPermission(name="Approve", actions=["approve"])
        obj_perm.save()
        obj_perm.users.add(user2)
        obj_perm.object_types.add(ContentType.objects.get_for_model(Job))

        instance = self._get_queryset().first()
        data = {"_approve": True}

        for user in (user1, user2):
            self.client.force_login(user)
            response = self.client.post(self._get_url("view", instance), data)
            self.assertBodyContains(response, "You do not have permission")
            # Job was not approved
            instance.refresh_from_db()
            self.assertIsNone(instance.approved_by_user)

    @override_settings(EXEMPT_VIEW_PERMISSIONS=["*"])
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
    def test_post_approve_different_user_permitted(self):
        """A user with appropriate permissions can approve a job request."""
        user = User.objects.create_user(username="testuser1")
        instance = self._get_queryset().first()

        # Give user view_scheduledjob and change_scheduledjob permissions
        obj_perm = ObjectPermission(name="View", actions=["view", "change"], constraints={"pk": instance.pk})
        obj_perm.save()
        obj_perm.users.add(user)
        obj_perm.object_types.add(ContentType.objects.get_for_model(ScheduledJob))

        # Give user approve_job permission
        obj_perm = ObjectPermission(name="Approve", actions=["approve"], constraints={"pk": instance.job_model.pk})
        obj_perm.save()
        obj_perm.users.add(user)
        obj_perm.object_types.add(ContentType.objects.get_for_model(Job))

        data = {"_approve": True}

        self.client.force_login(user)
        with self.assertLogs("nautobot.events") as cm:
            response = self.client.post(self._get_url("view", instance), data)

        self.assertRedirects(response, reverse("extras:scheduledjob_approval_queue_list"))
        # Job was scheduled
        instance.refresh_from_db()
        self.assertEqual(instance.approved_by_user, user)
        # Event was published
        expected_payload = {"data": serialize_object_v2(instance)}
        self.assertEqual(
            cm.output,
            [
                f"INFO:nautobot.events.nautobot.jobs.approval.approved:{json.dumps(expected_payload, cls=NautobotKombuJSONEncoder, indent=4)}"
            ],
        )

        # Check object-based permissions are enforced for a different instance
        instance = self._get_queryset().last()
        response = self.client.post(self._get_url("view", instance), data)
        self.assertBodyContains(response, "You do not have permission")
        # Job was not scheduled
        instance.refresh_from_db()
        self.assertIsNone(instance.approved_by_user)


class JobQueueTestCase(ViewTestCases.PrimaryObjectViewTestCase):
    model = JobQueue

    @classmethod
    def setUpTestData(cls):
        cls.form_data = {
            "name": "Test Job Queue",
            "queue_type": JobQueueTypeChoices.TYPE_CELERY,
            "description": "This is a very detailed description",
            "tenant": Tenant.objects.first().pk,
            "tags": [t.pk for t in Tag.objects.get_for_model(JobQueue)],
        }
        cls.bulk_edit_data = {
            "queue_type": JobQueueTypeChoices.TYPE_KUBERNETES,
            "description": "This is a very detailed new description",
            "tenant": Tenant.objects.last().pk,
            # TODO add tests for add_tags/remove_tags fields in TagsBulkEditFormMixin
        }


class JobResultTestCase(
    ViewTestCases.GetObjectViewTestCase,
    ViewTestCases.ListObjectsViewTestCase,
    ViewTestCases.DeleteObjectViewTestCase,
    ViewTestCases.BulkDeleteObjectsViewTestCase,
):
    model = JobResult

    @classmethod
    def setUpTestData(cls):
        JobResult.objects.create(name="pass_job.TestPassJob")
        JobResult.objects.create(name="fail.TestFailJob")
        JobLogEntry.objects.create(
            log_level=LogLevelChoices.LOG_INFO,
            job_result=JobResult.objects.first(),
            grouping="run",
            message="This is a test",
        )

    def test_get_joblogentrytable_anonymous(self):
        url = reverse("extras:jobresult_log-table", kwargs={"pk": JobResult.objects.first().pk})
        self.client.logout()
        response = self.client.get(url, follow=True)
        self.assertHttpStatus(response, 200)
        self.assertRedirects(response, f"/login/?next={url}")

    def test_get_joblogentrytable_without_permission(self):
        url = reverse("extras:jobresult_log-table", kwargs={"pk": JobResult.objects.first().pk})
        response = self.client.get(url)
        self.assertHttpStatus(response, [403, 404])

    def test_get_joblogentrytable_with_permission(self):
        url = reverse("extras:jobresult_log-table", kwargs={"pk": JobResult.objects.first().pk})
        self.add_permissions("extras.view_jobresult", "extras.view_joblogentry")
        response = self.client.get(url)
        self.assertBodyContains(response, "This is a test")

    # TODO test with constrained permissions on both JobResult and JobLogEntry records


class JobTestCase(
    # note no CreateObjectViewTestCase - we do not support user creation of Job records
    ViewTestCases.BulkDeleteObjectsViewTestCase,
    ViewTestCases.BulkEditObjectsViewTestCase,
    ViewTestCases.DeleteObjectViewTestCase,
    ViewTestCases.EditObjectViewTestCase,
    ViewTestCases.GetObjectViewTestCase,
    ViewTestCases.GetObjectChangelogViewTestCase,
    ViewTestCases.ListObjectsViewTestCase,
):
    """
    The Job view test cases.
    """

    model = Job

    def _get_queryset(self):
        """Don't include hidden Jobs or non-installed Jobs, as they won't appear in the UI by default."""
        return self.model.objects.filter(installed=True, hidden=False)

    @classmethod
    def setUpTestData(cls):
        # Job model objects are automatically created during database migrations

        # But we do need to make sure the ones we're testing are flagged appropriately
        cls.test_pass = Job.objects.get(job_class_name="TestPassJob")
        default_job_queue = JobQueue.objects.get(name="default", queue_type=JobQueueTypeChoices.TYPE_CELERY)
        cls.test_pass.default_job_queue = default_job_queue
        cls.test_pass.enabled = True
        cls.test_pass.save()

        cls.run_urls = (
            # Legacy URL (job class path based)
            reverse("extras:job_run_by_class_path", kwargs={"class_path": cls.test_pass.class_path}),
            # Current URL (job model pk based)
            reverse("extras:job_run", kwargs={"pk": cls.test_pass.pk}),
        )

        cls.test_required_args = Job.objects.get(job_class_name="TestRequired")
        cls.test_required_args.enabled = True
        cls.test_pass.default_job_queue = default_job_queue
        cls.test_required_args.save()

        cls.extra_run_urls = (
            # Legacy URL (job class path based)
            reverse("extras:job_run_by_class_path", kwargs={"class_path": cls.test_required_args.class_path}),
            # Current URL (job model pk based)
            reverse("extras:job_run", kwargs={"pk": cls.test_required_args.pk}),
        )

        # Create an entry for a non-installed Job as well
        cls.test_not_installed = Job(
            module_name="nonexistent",
            job_class_name="NoSuchJob",
            grouping="Nonexistent Jobs",
            name="No such job",
            enabled=True,
            installed=False,
        )
        cls.test_not_installed.default_job_queue = default_job_queue
        cls.test_not_installed.validated_save()

        cls.data_run_immediately = {
            "_schedule_type": "immediately",
        }
        job_queues = JobQueue.objects.all()[:3]
        pk_list = [queue.pk for queue in job_queues]
        pk_list += [default_job_queue.pk]
        job_queues = JobQueue.objects.filter(pk__in=pk_list)
        cls.form_data = {
            "enabled": True,
            "grouping_override": True,
            "grouping": "Overridden Grouping",
            "name_override": True,
            "name": "Overridden Name",
            "description_override": True,
            "description": "This is an overridden description of a job.",
            "dryrun_default_override": True,
            "dryrun_default": True,
            "hidden_override": True,
            "hidden": False,
            "approval_required_override": True,
            "approval_required": True,
            "soft_time_limit_override": True,
            "soft_time_limit": 350,
            "time_limit_override": True,
            "time_limit": 650,
            "has_sensitive_variables": False,
            "has_sensitive_variables_override": True,
            "job_queues": [queue.pk for queue in job_queues],
            "job_queues_override": True,
            "default_job_queue": default_job_queue.pk,
        }
        # This form is emulating the non-conventional JobBulkEditForm
        cls.bulk_edit_data = {
            "enabled": True,
            "clear_grouping_override": True,
            "grouping": "",
            "clear_description_override": False,
            "description": "Overridden Description",
            "clear_dryrun_default_override": False,
            "dryrun_default": "",
            "clear_hidden_override": True,
            "hidden": False,
            "clear_approval_required_override": True,
            "approval_required": True,
            "clear_soft_time_limit_override": False,
            "soft_time_limit": 350,
            "clear_time_limit_override": True,
            "time_limit": "",
            "has_sensitive_variables": False,
            "clear_has_sensitive_variables_override": False,
            "job_queues": [queue.pk for queue in job_queues],
            "clear_job_queues_override": False,
            "clear_default_job_queue_override": False,
            "default_job_queue": default_job_queue.pk,
        }

    def get_deletable_object(self):
        """
        Get an instance that can be deleted.
        Exclude system jobs
        """
        # filter out the system jobs:
        queryset = self._get_queryset().exclude(module_name__startswith="nautobot.")
        return get_deletable_objects(self.model, queryset).first()

    def get_deletable_object_pks(self):
        """
        Get a list of PKs corresponding to jobs that can be safely bulk-deleted.
        Excluding system jobs
        """
        queryset = self._get_queryset().exclude(module_name__startswith="nautobot.")
        return get_deletable_objects(self.model, queryset).values_list("pk", flat=True)[:3]

    def test_delete_system_jobs_fail(self):
        instance = self._get_queryset().filter(module_name__startswith="nautobot.").first()
        job_name = instance.name
        request = {
            "path": self._get_url("delete", instance),
            "data": post_data({"confirm": True}),
        }

        # Try delete with delete job permission
        self.add_permissions("extras.delete_job")
        response = self.client.post(**request, follow=True)
        self.assertBodyContains(
            response, f"Unable to delete Job {instance}. System Job cannot be deleted", status_code=403
        )
        # assert Job still exists
        self.assertTrue(self._get_queryset().filter(name=job_name).exists())

        # Try delete as a superuser
        self.user.is_superuser = True
        response = self.client.post(**request, follow=True)
        self.assertBodyContains(
            response, f"Unable to delete Job {instance}. System Job cannot be deleted", status_code=403
        )
        # assert Job still exists
        self.assertTrue(self._get_queryset().filter(name=job_name).exists())

    def validate_job_data_after_bulk_edit(self, pk_list, old_data):
        # Name is bulk-editable
        overridable_fields = [field for field in JOB_OVERRIDABLE_FIELDS if field != "name"]
        for instance in self._get_queryset().filter(pk__in=pk_list):
            self.assertEqual(instance.enabled, True)
            job_class = instance.job_class
            if job_class is not None:
                for overridable_field in overridable_fields:
                    # clear_override_field is obtained from adding "clear_" to the front and "_override" to the back of overridable_field
                    # e.g grouping -> clear_grouping_override
                    clear_override_field = "clear_" + overridable_field + "_override"
                    # override_field is obtained from adding "_override" to the back of overridable_field
                    # e.g grouping -> grouping_override
                    override_field = overridable_field + "_override"
                    reset_override = self.bulk_edit_data.get(clear_override_field, False)
                    if overridable_field == "task_queues":
                        override_value = self.bulk_edit_data.get(overridable_field).split(",")
                    else:
                        override_value = self.bulk_edit_data.get(overridable_field)
                    # if clear_override is true, assert that values are reverted back to default values
                    if reset_override is True:
                        self.assertEqual(getattr(instance, overridable_field), getattr(job_class, overridable_field))
                        self.assertEqual(getattr(instance, override_field), False)
                    # if clear_override is false, assert that job attribute is set to the new value from the form
                    elif reset_override is False and (override_value is False or override_value):
                        self.assertEqual(getattr(instance, overridable_field), override_value)
                        self.assertEqual(getattr(instance, override_field), True)
                    # if clear_override is false and no new value is entered, assert that value of the job is unchanged
                    else:
                        self.assertEqual(getattr(instance, overridable_field), old_data[instance.pk][overridable_field])
                        self.assertEqual(getattr(instance, override_field), old_data[instance.pk][overridable_field])
                # Special case for task queues/job queues
                override_value = self.bulk_edit_data.get("job_queues")
                self.assertEqual(list(instance.job_queues.values_list("pk", flat=True)), override_value)
                self.assertEqual(instance.job_queues_override, True)

    def validate_object_data_after_bulk_edit(self, pk_list):
        instances = self._get_queryset().filter(pk__in=pk_list)
        overridable_fields = [field for field in JOB_OVERRIDABLE_FIELDS if field != "name"]
        old_data = {}
        for instance in instances:
            old_data[instance.pk] = {}
            job_class = instance.job_class
            if job_class is not None:
                for field in overridable_fields:
                    old_data[instance.pk][field] = getattr(job_class, field)
        self.validate_job_data_after_bulk_edit(pk_list, old_data)

    #
    # Additional test cases for the "job" (legacy run) and "job_run" (updated run) views follow
    #

    @override_settings(EXEMPT_VIEW_PERMISSIONS=[])
    def test_get_run_without_permission(self):
        for run_url in self.run_urls:
            self.assertHttpStatus(self.client.get(run_url), 403, msg=run_url)

    @override_settings(EXEMPT_VIEW_PERMISSIONS=[])
    def test_get_run_with_permission(self):
        """
        Get view with appropriate global permissions.

        Note that this view is conditional on run_job permission, not view_job permission,
        so EXEMPT_VIEW_PERMISSIONS=["*"] does NOT apply here.
        """
        self.add_permissions("extras.run_job")
        for run_url in self.run_urls:
            response = self.client.get(run_url)
            self.assertBodyContains(response, "TestPassJob")

    @override_settings(EXEMPT_VIEW_PERMISSIONS=[])
    def test_get_run_with_constrained_permission(self):
        """Get view with appropriate object-based permissions."""
        obj_perm = ObjectPermission(
            name="Job permission",
            constraints={"module_name": self.test_pass.module_name},
            actions=["run"],
        )
        obj_perm.save()
        obj_perm.users.add(self.user)
        obj_perm.object_types.add(ContentType.objects.get_for_model(Job))

        # Try GET with a permitted object
        for run_url in self.run_urls:
            self.assertHttpStatus(self.client.get(run_url), 200, msg=run_url)

        # Try GET with a non-permitted object
        for run_url in self.extra_run_urls:
            self.assertHttpStatus(self.client.get(run_url), 404, msg=run_url)

    @override_settings(EXEMPT_VIEW_PERMISSIONS=[])
    def test_run_without_permission(self):
        for run_url in self.run_urls:
            self.assertHttpStatus(self.client.post(run_url), 403, msg=run_url)

    def test_run_missing_schedule(self):
        self.add_permissions("extras.run_job")

        for run_url in self.run_urls:
            response = self.client.post(run_url)
            self.assertHttpStatus(response, 200, msg=run_url)

            errors = extract_form_failures(response.content.decode(response.charset))
            self.assertEqual(errors, ["_schedule_type: This field is required."])

    @mock.patch("nautobot.extras.views.get_worker_count", return_value=0)
    def test_run_now_no_worker(self, _):
        self.add_permissions("extras.run_job")
        self.add_permissions("extras.view_jobresult")

        for run_url in self.run_urls:
            response = self.client.post(run_url, self.data_run_immediately, follow=True)

            result = JobResult.objects.latest()
            self.assertRedirects(response, reverse("extras:jobresult", kwargs={"pk": result.pk}))
            self.assertBodyContains(response, "No celery workers found")

    @mock.patch("nautobot.extras.views.get_worker_count", return_value=1)
    def test_run_now(self, _):
        self.add_permissions("extras.run_job")
        self.add_permissions("extras.view_jobresult")

        for run_url in self.run_urls:
            response = self.client.post(run_url, self.data_run_immediately)

            result = JobResult.objects.latest()
            self.assertRedirects(response, reverse("extras:jobresult", kwargs={"pk": result.pk}))

    @mock.patch("nautobot.extras.views.get_worker_count", return_value=1)
    def test_run_now_constrained_permissions(self, _):
        obj_perm = ObjectPermission(
            name="Job permission",
            constraints={"module_name": self.test_pass.module_name},
            actions=["run"],
        )
        obj_perm.save()
        obj_perm.users.add(self.user)
        obj_perm.object_types.add(ContentType.objects.get_for_model(Job))

        self.add_permissions("extras.view_jobresult")

        # Try POST with a permitted object
        for run_url in self.run_urls:
            response = self.client.post(run_url, self.data_run_immediately)

            result = JobResult.objects.latest()
            self.assertIsNotNone(result, msg=run_url)
            self.assertRedirects(response, reverse("extras:jobresult", kwargs={"pk": result.pk}))

        # Try POST with a non-permitted object
        for run_url in self.extra_run_urls:
            self.assertHttpStatus(self.client.post(run_url, self.data_run_immediately), 404, msg=run_url)

    @mock.patch("nautobot.extras.views.get_worker_count", return_value=1)
    def test_run_now_not_installed(self, _):
        self.add_permissions("extras.run_job")

        for run_url in (
            reverse("extras:job_run_by_class_path", kwargs={"class_path": self.test_not_installed.class_path}),
            reverse("extras:job_run", kwargs={"pk": self.test_not_installed.pk}),
        ):
            response = self.client.post(run_url, self.data_run_immediately)
            self.assertBodyContains(response, "Job is not presently installed")

            self.assertFalse(JobResult.objects.filter(name=self.test_not_installed.name).exists())

    @mock.patch("nautobot.extras.views.get_worker_count", return_value=1)
    def test_run_now_not_enabled(self, _):
        self.add_permissions("extras.run_job")

        for run_url in (
            reverse("extras:job_run_by_class_path", kwargs={"class_path": "fail.TestFailJob"}),
            reverse("extras:job_run", kwargs={"pk": Job.objects.get(job_class_name="TestFailJob").pk}),
        ):
            response = self.client.post(run_url, self.data_run_immediately)
            self.assertBodyContains(response, "Job is not enabled to be run")
            self.assertFalse(JobResult.objects.filter(name="fail.TestFailJob").exists())

    def test_run_now_missing_args(self):
        self.add_permissions("extras.run_job")

        for run_url in self.extra_run_urls:
            response = self.client.post(run_url, self.data_run_immediately)
            self.assertHttpStatus(response, 200, msg=run_url)

            errors = extract_form_failures(response.content.decode(response.charset))
            self.assertEqual(errors, ["var: This field is required."])

    @mock.patch("nautobot.extras.views.get_worker_count", return_value=1)
    def test_run_now_with_args(self, _):
        self.add_permissions("extras.run_job")
        self.add_permissions("extras.view_jobresult")

        data = {
            "_schedule_type": "immediately",
            "var": "12",
        }

        for run_url in self.extra_run_urls:
            response = self.client.post(run_url, data)

            result = JobResult.objects.latest()
            self.assertRedirects(response, reverse("extras:jobresult", kwargs={"pk": result.pk}))

    def test_rerun_job(self):
        self.add_permissions("extras.run_job")
        self.add_permissions("extras.view_jobresult")

        job_queue = JobQueue.objects.create(name="uniquequeue", queue_type=JobQueueTypeChoices.TYPE_CELERY)
        job_celery_kwargs = {
            "nautobot_job_job_model_id": self.test_required_args.id,
            "nautobot_job_profile": True,
            "nautobot_job_ignore_singleton_lock": True,
            "nautobot_job_user_id": self.user.id,
            "queue": job_queue.name,
        }
        self.test_required_args.job_queues.set([job_queue])
        self.test_required_args.is_singleton_override = True
        self.test_required_args.has_sensitive_variables_override = True
        self.test_required_args.is_singleton = True
        self.test_required_args.has_sensitive_variables = False
        self.test_required_args.validated_save()
        previous_result = JobResult.objects.create(
            job_model=self.test_required_args,
            user=self.user,
            task_kwargs={"var": "456"},
            celery_kwargs=job_celery_kwargs,
        )

        run_url = reverse("extras:job_run", kwargs={"pk": self.test_required_args.pk})
        response = self.client.get(f"{run_url}?kwargs_from_job_result={previous_result.pk!s}")
        content = extract_page_body(response.content.decode(response.charset))
        self.assertInHTML(f'<option value="{job_queue.pk}" selected>{job_queue}</option>', content)
        self.assertInHTML(
            '<input type="text" name="var" value="456" class="form-control" required placeholder="None" id="id_var">',
            content,
        )
        self.assertInHTML('<input type="hidden" name="_profile" value="True" id="id__profile">', content)
        self.assertInHTML(
            '<input type="checkbox" name="_ignore_singleton_lock" id="id__ignore_singleton_lock" checked>', content
        )

    @mock.patch("nautobot.extras.views.get_worker_count", return_value=1)
    def test_run_later_missing_name(self, _):
        self.add_permissions("extras.run_job")

        data = {
            "_schedule_type": "future",
        }

        for run_url in self.run_urls:
            response = self.client.post(run_url, data)
            self.assertHttpStatus(response, 200, msg=run_url)

            errors = extract_form_failures(response.content.decode(response.charset))
            self.assertEqual(errors, ["_schedule_name: Please provide a name for the job schedule."])

    @mock.patch("nautobot.extras.views.get_worker_count", return_value=1)
    def test_run_later_missing_date(self, _):
        self.add_permissions("extras.run_job")

        data = {
            "_schedule_type": "future",
            "_schedule_name": "test",
        }

        for i, run_url in enumerate(self.run_urls):
            data["_schedule_name"] = f"test {i}"
            response = self.client.post(run_url, data)
            self.assertHttpStatus(response, 200, msg=run_url)

            errors = extract_form_failures(response.content.decode(response.charset))
            self.assertEqual(
                errors,
                [
                    "_schedule_start_time: Please enter a valid date and time greater than or equal to the current date and time."
                ],
            )

    @mock.patch("nautobot.extras.views.get_worker_count", return_value=1)
    def test_run_later_date_passed(self, _):
        self.add_permissions("extras.run_job")

        data = {
            "_schedule_type": "future",
            "_schedule_name": "test",
            "_schedule_start_time": str(timezone.now() - timedelta(minutes=1)),
        }

        for i, run_url in enumerate(self.run_urls):
            data["_schedule_name"] = f"test {i}"
            response = self.client.post(run_url, data)
            self.assertHttpStatus(response, 200, msg=run_url)

            errors = extract_form_failures(response.content.decode(response.charset))
            self.assertEqual(
                errors,
                [
                    "_schedule_start_time: Please enter a valid date and time greater than or equal to the current date and time."
                ],
            )

    @mock.patch("nautobot.extras.views.get_worker_count", return_value=1)
    def test_run_later(self, _):
        self.add_permissions("extras.run_job")
        self.add_permissions("extras.view_scheduledjob")

        start_time = timezone.now() + timedelta(minutes=1)
        data = {
            "_schedule_type": "future",
            "_schedule_name": "test",
            "_schedule_start_time": str(start_time),
        }

        for i, run_url in enumerate(self.run_urls):
            data["_schedule_name"] = f"test {i}"
            response = self.client.post(run_url, data)
            self.assertRedirects(response, reverse("extras:scheduledjob_list"))

            scheduled = ScheduledJob.objects.get(name=f"test {i}")
            self.assertEqual(scheduled.start_time, start_time)

    @mock.patch("nautobot.extras.views.get_worker_count", return_value=1)
    def test_run_job_with_sensitive_variables_for_future(self, _):
        self.add_permissions("extras.run_job")
        self.add_permissions("extras.view_scheduledjob")

        self.test_pass.has_sensitive_variables = True
        self.test_pass.has_sensitive_variables_override = True
        self.test_pass.validated_save()

        start_time = timezone.now() + timedelta(minutes=1)
        data = {
            "_schedule_type": "future",
            "_schedule_name": "test",
            "_schedule_start_time": str(start_time),
        }
        for i, run_url in enumerate(self.run_urls):
            data["_schedule_name"] = f"test {i}"
            response = self.client.post(run_url, data)
            self.assertBodyContains(response, "Unable to schedule job: Job may have sensitive input variables.")

    @mock.patch("nautobot.extras.views.get_worker_count", return_value=1)
    def test_run_job_with_invalid_task_queue(self, _):
        self.add_permissions("extras.run_job")
        self.add_permissions("extras.view_jobresult")

        self.test_pass.task_queues = []
        self.test_pass.job_queues_override = True
        self.test_pass.validated_save()
        job_queue = JobQueue.objects.create(name="invalid", queue_type=JobQueueTypeChoices.TYPE_CELERY)
        data = {
            "_schedule_type": "immediately",
            "_job_queue": job_queue.pk,
        }

        for run_url in self.run_urls:
            response = self.client.post(run_url, data)
            self.assertHttpStatus(response, 200, msg=run_url)

            errors = extract_form_failures(response.content.decode(response.charset))
            self.assertEqual(
                errors,
                ["_job_queue: Select a valid choice. That choice is not one of the available choices."],
            )

    @mock.patch("nautobot.extras.views.get_worker_count", return_value=1)
    def test_run_job_with_sensitive_variables_and_requires_approval(self, _):
        self.add_permissions("extras.run_job")
        self.add_permissions("extras.view_scheduledjob")

        self.test_pass.has_sensitive_variables = True
        self.test_pass.approval_required = True
        self.test_pass.save()

        data = {
            "_schedule_type": "immediately",
        }
        for run_url in self.run_urls:
            # Assert warning message shows in get
            response = self.client.get(run_url)
            self.assertBodyContains(
                response,
                "This job is flagged as possibly having sensitive variables but is also flagged as requiring approval.",
            )

            # Assert run button is disabled
            self.assertBodyContains(
                response,
                """
                <button type="submit" name="_run" id="id__run" class="btn btn-primary" disabled="disabled">
                    <i class="mdi mdi-play"></i> Run Job Now
                </button>
                """,
                html=True,
            )
            # Assert error message shows after post
            response = self.client.post(run_url, data)
            self.assertBodyContains(
                response,
                "Unable to run or schedule job: "
                "This job is flagged as possibly having sensitive variables but is also flagged as requiring approval."
                "One of these two flags must be removed before this job can be scheduled or run.",
            )

    @mock.patch("nautobot.extras.views.get_worker_count", return_value=1)
    def test_run_job_with_approval_required_creates_scheduled_job_internal_future(self, _):
        self.add_permissions("extras.run_job")
        self.add_permissions("extras.view_scheduledjob")

        self.test_pass.approval_required = True
        self.test_pass.save()
        data = {
            "_schedule_type": "immediately",
        }
        for run_url in self.run_urls:
            response = self.client.post(run_url, data)
            scheduled_job = ScheduledJob.objects.last()
            self.assertTrue(scheduled_job.interval, JobExecutionType.TYPE_FUTURE)
            self.assertRedirects(
                response,
                reverse("extras:scheduledjob_approval_queue_list"),
            )

    def test_job_object_change_log_view(self):
        """Assert Job change log view displays appropriate header"""
        instance = self.test_pass
        self.add_permissions("extras.view_objectchange", "extras.view_job")
        response = self.client.get(instance.get_changelog_url())
        self.assertBodyContains(response, f"{instance.name} - Change Log")


class JobButtonTestCase(
    ViewTestCases.CreateObjectViewTestCase,
    ViewTestCases.DeleteObjectViewTestCase,
    ViewTestCases.EditObjectViewTestCase,
    ViewTestCases.GetObjectViewTestCase,
    ViewTestCases.GetObjectChangelogViewTestCase,
    ViewTestCases.ListObjectsViewTestCase,
):
    model = JobButton

    @classmethod
    def setUpTestData(cls):
        jbr_simple = Job.objects.get(job_class_name="TestJobButtonReceiverSimple")
        jbr_simple.enabled = True
        jbr_simple.save()
        jbr_complex = Job.objects.get(job_class_name="TestJobButtonReceiverComplex")
        jbr_complex.enabled = True
        jbr_complex.save()

        job_buttons = (
            JobButton.objects.create(
                name="JobButton1",
                text="JobButton1",
                job=jbr_simple,
                confirmation=True,
            ),
            JobButton.objects.create(
                name="JobButton2",
                text="JobButton2",
                job=jbr_simple,
                confirmation=False,
            ),
            JobButton.objects.create(
                name="JobButton3",
                text="JobButton3",
                job=jbr_complex,
                confirmation=True,
                weight=50,
            ),
        )

        location_ct = ContentType.objects.get_for_model(Location)
        for jb in job_buttons:
            jb.content_types.set([location_ct])

        cls.form_data = {
            "content_types": [location_ct.pk],
            "name": "jobbutton-4",
            "text": "jobbutton text 4",
            "job": jbr_complex.pk,
            "weight": 100,
            "button_class": "default",
            "confirmation": False,
        }


class JobButtonRenderingTestCase(TestCase):
    """Tests for the rendering of JobButtons, distinct from tests of the JobButton views themselves."""

    user_permissions = ["dcim.view_locationtype"]

    def setUp(self):
        super().setUp()
        self.job = Job.objects.get(job_class_name="TestJobButtonReceiverSimple")
        self.job.enabled = True
        self.job.save()

        self.job_button_1 = JobButton(
            name="JobButton 1",
            text="JobButton {{ obj.name }}",
            job=self.job,
            confirmation=False,
        )
        self.job_button_1.validated_save()
        self.job_button_1.content_types.add(ContentType.objects.get_for_model(LocationType))

        job_2 = Job.objects.get(job_class_name="TestJobButtonReceiverComplex")
        job_2.enabled = True
        job_2.save()

        self.job_button_2 = JobButton(
            name="JobButton 2",
            text="Click me!",
            job=job_2,
            confirmation=False,
        )
        self.job_button_2.validated_save()
        self.job_button_2.content_types.add(ContentType.objects.get_for_model(LocationType))

        self.location_type = LocationType.objects.get(name="Campus")

    def test_view_object_with_job_button(self):
        """Ensure that the job button is rendered."""
        response = self.client.get(self.location_type.get_absolute_url(), follow=True)
        self.assertBodyContains(response, f"JobButton {self.location_type.name}")
        self.assertBodyContains(response, "Click me!")

    def test_task_queue_hidden_input_is_present(self):
        """
        Ensure that the job button respects the job class' task_queues and the job class default job queue is passed as a hidden form input.
        """
        self.job.job_queues_override = True
        task_queues = ["overriden_queue", "default", "priority"]
        for queue in task_queues:
            JobQueue.objects.get_or_create(name=queue, defaults={"queue_type": JobQueueTypeChoices.TYPE_CELERY})
        self.job.task_queues = ["overriden_queue", "default", "priority"]
        self.job.save()
        response = self.client.get(self.location_type.get_absolute_url(), follow=True)
        self.assertEqual(response.status_code, 200)
        content = extract_page_body(response.content.decode(response.charset))
        job_queues = self.job.job_queues.all()
        _job_queue = job_queues[0]
        self.assertIn(f'<input type="hidden" name="_job_queue" value="{_job_queue.pk}">', content, content)

        self.job.job_queues_override = False
        self.job.save()
        self.job.job_queues.set([])
        response = self.client.get(self.location_type.get_absolute_url(), follow=True)
        self.assertEqual(response.status_code, 200)
        content = extract_page_body(response.content.decode(response.charset))
        self.assertIn(
            f'<input type="hidden" name="_job_queue" value="{self.job.default_job_queue.pk}">', content, content
        )

    def test_view_object_with_unsafe_text(self):
        """Ensure that JobButton text can't be used as a vector for XSS."""
        self.job_button_1.text = '<script>alert("Hello world!")</script>'
        self.job_button_1.validated_save()
        response = self.client.get(self.location_type.get_absolute_url(), follow=True)
        self.assertEqual(response.status_code, 200)
        content = extract_page_body(response.content.decode(response.charset))
        self.assertNotIn("<script>alert", content, content)
        self.assertIn("&lt;script&gt;alert", content, content)

        # Make sure grouped rendering is safe too
        self.job_button_1.group_name = '<script>alert("Goodbye")</script>'
        self.job_button_1.validated_save()
        response = self.client.get(self.location_type.get_absolute_url(), follow=True)
        self.assertEqual(response.status_code, 200)
        content = extract_page_body(response.content.decode(response.charset))
        self.assertNotIn("<script>alert", content, content)
        self.assertIn("&lt;script&gt;alert", content, content)

    def test_view_object_with_unsafe_name(self):
        """Ensure that JobButton names can't be used as a vector for XSS."""
        self.job_button_1.text = "JobButton {{ obj"
        self.job_button_1.name = '<script>alert("Yo")</script>'
        self.job_button_1.validated_save()
        response = self.client.get(self.location_type.get_absolute_url(), follow=True)
        self.assertEqual(response.status_code, 200)
        content = extract_page_body(response.content.decode(response.charset))
        self.assertNotIn("<script>alert", content, content)
        self.assertIn("&lt;script&gt;alert", content, content)

    def test_render_constrained_run_permissions(self):
        obj_perm = ObjectPermission(
            name="Test permission",
            constraints={"pk": self.job_button_1.job.pk},
            actions=["run"],
        )
        obj_perm.save()
        obj_perm.users.add(self.user)
        obj_perm.object_types.add(ContentType.objects.get_for_model(Job))

        with self.subTest("Ungrouped buttons"):
            response = self.client.get(self.location_type.get_absolute_url(), follow=True)
            self.assertEqual(response.status_code, 200)
            content = extract_page_body(response.content.decode(response.charset))
            self.assertInHTML(
                NO_CONFIRM_BUTTON.format(
                    button_id=self.job_button_1.pk,
                    button_text=f"JobButton {self.location_type.name}",
                    button_class=self.job_button_1.button_class,
                    disabled="",
                ),
                content,
            )
            self.assertInHTML(
                NO_CONFIRM_BUTTON.format(
                    button_id=self.job_button_2.pk,
                    button_text="Click me!",
                    button_class=self.job_button_2.button_class,
                    disabled="disabled",
                ),
                content,
            )

        with self.subTest("Grouped buttons"):
            self.job_button_1.group_name = "Grouping"
            self.job_button_1.validated_save()
            self.job_button_2.group_name = "Grouping"
            self.job_button_2.validated_save()

            response = self.client.get(self.location_type.get_absolute_url(), follow=True)
            self.assertEqual(response.status_code, 200)
            content = extract_page_body(response.content.decode(response.charset))
            self.assertInHTML(
                "<li>"
                + NO_CONFIRM_BUTTON.format(
                    button_id=self.job_button_1.pk,
                    button_text=f"JobButton {self.location_type.name}",
                    button_class="link",
                    disabled="",
                )
                + "</li>",
                content,
            )
            self.assertInHTML(
                "<li>"
                + NO_CONFIRM_BUTTON.format(
                    button_id=self.job_button_2.pk,
                    button_text="Click me!",
                    button_class="link",
                    disabled="disabled",
                )
                + "</li>",
                content,
            )


class JobCustomTemplateTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        # Job model objects are automatically created during database migrations

        # But we do need to make sure the ones we're testing are flagged appropriately
        cls.example_job = Job.objects.get(job_class_name="ExampleCustomFormJob")
        cls.example_job.enabled = True
        cls.example_job.save()

        cls.run_url = reverse("extras:job_run", kwargs={"pk": cls.example_job.pk})

    def test_rendering_custom_template(self):
        self.assertIsNotNone(self.example_job.job_class)
        obj_perm = ObjectPermission(name="Test permission", actions=["view", "run"])
        obj_perm.save()
        obj_perm.users.add(self.user)
        obj_perm.object_types.add(ContentType.objects.get_for_model(Job))
        with self.assertTemplateUsed("example_app/custom_job_form.html"):
            self.client.get(self.run_url)


class JobHookTestCase(ViewTestCases.OrganizationalObjectViewTestCase, ViewTestCases.BulkEditObjectsViewTestCase):
    model = JobHook

    @classmethod
    def setUpTestData(cls):
        # Get valid job from registered job modules
        module = "job_hook_receiver"
        name = "TestJobHookReceiverLog"
        _job_class, job = get_job_class_and_model(module, name)

        # Create content type for Job Hooks
        obj_type = ContentType.objects.get_for_model(ConsolePort)
        device_ct = ContentType.objects.get_for_model(Device)
        ipaddress_ct = ContentType.objects.get_for_model(IPAddress)
        prefix_ct = ContentType.objects.get_for_model(Prefix)

        # Create JobHook instances
        cls.job_hooks = (
            JobHook(
                name="jobhook-1",
                enabled=True,
                job=job,
                type_create=True,
            ),
            JobHook(
                name="jobhook-2",
                enabled=True,
                job=job,
                type_update=True,
            ),
            JobHook(
                name="jobhook-3",
                enabled=True,
                job=job,
                type_delete=True,
            ),
        )

        for job_hook in cls.job_hooks:
            job_hook.save()
            job_hook.content_types.set([obj_type])  # Set after save

        # Form data for create test
        cls.form_data = {
            "name": "jobhook-4",
            "content_types": [device_ct.pk],  # Use int PK
            "enabled": True,
            "type_create": True,
            "type_update": False,
            "type_delete": False,
            "job": job.pk,
        }

        # Bulk edit data
        cls.bulk_edit_data = {
            "enabled": False,
            "type_create": True,  # Make sure these change values
            "type_update": True,
            "type_delete": True,
            "add_content_types": [ipaddress_ct.pk, prefix_ct.pk],
            "remove_content_types": [device_ct.pk],
        }


# TODO: Convert to StandardTestCases.Views
class ObjectChangeTestCase(TestCase):
    user_permissions = ("extras.view_objectchange",)

    @classmethod
    def setUpTestData(cls):
        location_type = LocationType.objects.get(name="Campus")
        location_status = Status.objects.get_for_model(Location).first()
        location = Location(name="Location 1", location_type=location_type, status=location_status)
        location.save()

        # Create three ObjectChanges
        user = User.objects.create_user(username="testuser2")
        for _ in range(1, 4):
            oc = location.to_objectchange(action=ObjectChangeActionChoices.ACTION_UPDATE)
            oc.user = user
            oc.request_id = uuid.uuid4()
            oc.save()

    def test_objectchange_list(self):
        url = reverse("extras:objectchange_list")
        params = {
            "user": User.objects.first().pk,
        }

        response = self.client.get(f"{url}?{urllib.parse.urlencode(params)}")
        self.assertHttpStatus(response, 200)

    def test_objectchange(self):
        objectchange = ObjectChange.objects.first()
        response = self.client.get(objectchange.get_absolute_url())
        self.assertHttpStatus(response, 200)


class ObjectMetadataTestCase(
    ViewTestCases.ListObjectsViewTestCase,
):
    model = ObjectMetadata

    @override_settings(EXEMPT_VIEW_PERMISSIONS=["*"])
    def test_value_column_in_list_view_rendered_correctly(self):
        """
        GET a list of objects as an authenticated user with permission to view the objects.
        """
        instance1 = self._get_queryset().filter(contact__isnull=False).first()
        instance2 = self._get_queryset().filter(team__isnull=False).first()

        # Try GET to permitted objects
        response = self.client.get(self._get_url("list"))
        self.assertHttpStatus(response, 200)
        content = extract_page_body(response.content.decode(response.charset))
        # Check if the contact or team absolute url is rendered in the ObjectListView table
        self.assertIn(instance1.contact.get_absolute_url(), content, msg=content)
        self.assertIn(instance2.team.get_absolute_url(), content, msg=content)
        # TODO check if other types of values are rendered correctly

    @override_settings(EXEMPT_VIEW_PERMISSIONS=[])
    def test_list_objects_with_constrained_permission(self):
        instance1 = self._get_queryset().first()
        instance2 = self._get_queryset().filter(~Q(assigned_object_id=instance1.assigned_object_id)).first()
        self._get_queryset().filter(~Q(pk=instance1.pk) & ~Q(pk=instance2.pk)).delete()

        # Add object-level permission
        obj_perm = ObjectPermission(
            name="Test permission",
            constraints={"pk": instance1.pk},
            actions=["view", "add"],
        )
        obj_perm.save()
        obj_perm.users.add(self.user)
        obj_perm.object_types.add(ContentType.objects.get_for_model(self.model))

        # Try GET with object-level permission
        response = self.client.get(self._get_url("list"))
        self.assertHttpStatus(response, 200)
        content = extract_page_body(response.content.decode(response.charset))
        # Since we do not render the absolute url in ObjectListView of ObjectMetadata, we need to check assigned_object
        # fields and if they are rendered.
        self.assertIn(instance1.assigned_object.get_absolute_url(), content, msg=content)
        self.assertNotIn(instance2.assigned_object.get_absolute_url(), content, msg=content)


class RelationshipTestCase(
    ViewTestCases.CreateObjectViewTestCase,
    ViewTestCases.DeleteObjectViewTestCase,
    ViewTestCases.EditObjectViewTestCase,
    ViewTestCases.BulkDeleteObjectsViewTestCase,
    ViewTestCases.GetObjectViewTestCase,
    ViewTestCases.GetObjectChangelogViewTestCase,
    ViewTestCases.ListObjectsViewTestCase,
    RequiredRelationshipTestMixin,
    ViewTestCases.BulkEditObjectsViewTestCase,
):
    model = Relationship
    slug_source = "label"
    slugify_function = staticmethod(slugify_dashes_to_underscores)

    @classmethod
    def setUpTestData(cls):
        interface_type = ContentType.objects.get_for_model(Interface)
        device_type = ContentType.objects.get_for_model(Device)
        vlan_type = ContentType.objects.get_for_model(VLAN)
        status = Status.objects.get_for_model(Interface).first()

        Relationship(
            label="Device VLANs",
            key="device_vlans",
            type="many-to-many",
            source_type=device_type,
            destination_type=vlan_type,
        ).validated_save()
        Relationship(
            label="Primary VLAN",
            key="primary_vlan",
            type="one-to-many",
            source_type=vlan_type,
            destination_type=device_type,
        ).validated_save()
        Relationship(
            label="Primary Interface",
            type="one-to-one",
            source_type=device_type,
            destination_type=interface_type,
        ).validated_save()

        cls.form_data = {
            "label": "VLAN-to-Interface",
            "key": "vlan_to_interface",
            "type": "many-to-many",
            "source_type": vlan_type.pk,
            "source_label": "Interfaces",
            "source_hidden": False,
            "source_filter": '{"status": ["' + status.name + '"]}',
            "destination_type": interface_type.pk,
            "destination_label": "VLANs",
            "destination_hidden": True,
            "destination_filter": None,
        }
        cls.bulk_edit_data = {
            "description": "This is a relationship between VLANs and Interfaces.",
            "type": "many-to-many",
            "source_type": vlan_type.pk,
            "source_label": "Interfaces",
            "source_hidden": False,
            "source_filter": '{"status": ["' + status.name + '"]}',
            "destination_type": interface_type.pk,
            "destination_label": "VLANs",
            "destination_hidden": True,
            "destination_filter": None,
            "advanced_ui": True,
        }

        cls.slug_test_object = "Primary Interface"


class RelationshipAssociationTestCase(
    # TODO? ViewTestCases.CreateObjectViewTestCase,
    ViewTestCases.DeleteObjectViewTestCase,
    # TODO? ViewTestCases.EditObjectViewTestCase,
    ViewTestCases.BulkDeleteObjectsViewTestCase,
    # TODO? ViewTestCases.GetObjectViewTestCase,
    ViewTestCases.ListObjectsViewTestCase,
):
    model = RelationshipAssociation

    @classmethod
    def setUpTestData(cls):
        device_type = ContentType.objects.get_for_model(Device)
        vlan_type = ContentType.objects.get_for_model(VLAN)

        # Since RelationshipAssociation.get_absolute_url() is actually the Relationship's URL,
        # we want to have separate Relationships as well to allow distinguishing between them.
        relationship_1 = Relationship(
            label="Device VLANs 1",
            key="device_vlans_1",
            type="many-to-many",
            source_type=device_type,
            destination_type=vlan_type,
        )
        relationship_2 = Relationship(
            label="Device VLANs 2",
            key="device_vlans_2",
            type="many-to-many",
            source_type=device_type,
            destination_type=vlan_type,
        )
        relationship_3 = Relationship(
            label="Device VLANs 3",
            key="device_vlans_3",
            type="many-to-many",
            source_type=device_type,
            destination_type=vlan_type,
        )
        cls.relationship = relationship_1
        relationship_1.validated_save()
        relationship_2.validated_save()
        relationship_3.validated_save()
        manufacturer = Manufacturer.objects.first()
        devicetype = DeviceType.objects.create(manufacturer=manufacturer, model="Device Type 1")
        devicerole = Role.objects.get_for_model(Device).first()
        devicestatus = Status.objects.get_for_model(Device).first()
        location = Location.objects.first()
        devices = (
            Device.objects.create(
                name="Device 1", device_type=devicetype, role=devicerole, location=location, status=devicestatus
            ),
            Device.objects.create(
                name="Device 2", device_type=devicetype, role=devicerole, location=location, status=devicestatus
            ),
            Device.objects.create(
                name="Device 3", device_type=devicetype, role=devicerole, location=location, status=devicestatus
            ),
        )
        vlan_status = Status.objects.get_for_model(VLAN).first()
        vlan_group = VLANGroup.objects.create(name="Test VLANGroup 1")
        vlans = (
            VLAN.objects.create(vid=1, name="VLAN 1", status=vlan_status, vlan_group=vlan_group),
            VLAN.objects.create(vid=2, name="VLAN 2", status=vlan_status, vlan_group=vlan_group),
            VLAN.objects.create(vid=3, name="VLAN 3", status=vlan_status, vlan_group=vlan_group),
        )

        RelationshipAssociation(
            relationship=relationship_1,
            source_type=device_type,
            source_id=devices[0].pk,
            destination_type=vlan_type,
            destination_id=vlans[0].pk,
        ).validated_save()
        RelationshipAssociation(
            relationship=relationship_2,
            source_type=device_type,
            source_id=devices[1].pk,
            destination_type=vlan_type,
            destination_id=vlans[1].pk,
        ).validated_save()
        RelationshipAssociation(
            relationship=relationship_3,
            source_type=device_type,
            source_id=devices[2].pk,
            destination_type=vlan_type,
            destination_id=vlans[2].pk,
        ).validated_save()

    def test_list_objects_with_constrained_permission(self):
        instance1, instance2 = RelationshipAssociation.objects.all()[:2]

        # Add object-level permission
        obj_perm = ObjectPermission(
            name="Test permission",
            constraints={"pk": instance1.pk},
            actions=["view"],
        )
        obj_perm.save()
        obj_perm.users.add(self.user)
        obj_perm.object_types.add(ContentType.objects.get_for_model(self.model))

        response = self.client.get(self._get_url("list"))
        self.assertHttpStatus(response, 200)
        content = extract_page_body(response.content.decode(response.charset))
        self.assertIn(instance1.source.name, content, msg=content)
        self.assertIn(instance1.destination.name, content, msg=content)
        self.assertNotIn(instance2.source.name, content, msg=content)
        self.assertNotIn(instance2.destination.name, content, msg=content)

    def test_get_object_with_advanced_relationships(self):
        device_type = ContentType.objects.get_for_model(Device)
        vlan_type = ContentType.objects.get_for_model(VLAN)
        Relationship.objects.create(
            label="Device VLANs 4",
            key="device_vlans_4",
            type="one-to-many",
            source_type=device_type,
            source_label="Device VLANs Advanced",
            destination_type=vlan_type,
            destination_label="VLANs",
            advanced_ui=True,
        )
        Relationship.objects.create(
            label="Device VLANs 5",
            key="device_vlans_5",
            type="one-to-many",
            source_type=device_type,
            source_label="Device VLANs Main",
            destination_type=vlan_type,
            destination_label="VLANs",
            advanced_ui=False,
        )

        device = Device.objects.first()
        # Add model-level permission
        self.add_permissions(f"{Device._meta.app_label}.view_{Device._meta.model_name}")
        # Try GET the main tab
        response = self.client.get(device.get_absolute_url())
        response_content = extract_page_body(response.content.decode(response.charset))
        # The relationship's source label should be in the advanced tab since advance_ui=True
        # a.k.a its index should be greater than the index of the advanced tab
        self.assertGreater(response_content.find("Device VLANs Advanced"), response_content.find('id="advanced"'))
        # The relationship's source label should not be in the advanced tab since advance_ui=False
        # a.k.a its index should be smaller than the index of the advanced tab
        self.assertGreater(response_content.find('id="advanced"'), response_content.find("Device VLANs Main"))


class StaticGroupAssociationTestCase(
    ViewTestCases.BulkDeleteObjectsViewTestCase,
    ViewTestCases.DeleteObjectViewTestCase,
    ViewTestCases.GetObjectViewTestCase,
    ViewTestCases.GetObjectChangelogViewTestCase,
    ViewTestCases.ListObjectsViewTestCase,
):
    model = StaticGroupAssociation

    def test_list_objects_omits_hidden_by_default(self):
        """The list view should not by default include associations for hidden groups."""
        sga1 = StaticGroupAssociation.all_objects.filter(
            dynamic_group__group_type=DynamicGroupTypeChoices.TYPE_STATIC
        ).first()
        self.assertIsNotNone(sga1)
        sga2 = StaticGroupAssociation.all_objects.exclude(
            dynamic_group__group_type=DynamicGroupTypeChoices.TYPE_STATIC
        ).first()
        self.assertIsNotNone(sga2)

        self.add_permissions("extras.view_staticgroupassociation")
        response = self.client.get(self._get_url("list"))
        self.assertHttpStatus(response, 200)
        content = extract_page_body(response.content.decode(response.charset))

        self.assertIn(sga1.get_absolute_url(), content, msg=content)
        self.assertNotIn(sga2.get_absolute_url(), content, msg=content)

    def test_list_objects_can_explicitly_include_hidden(self):
        """The list view can include hidden groups' associations with the correct query parameter."""
        sga1 = StaticGroupAssociation.all_objects.exclude(
            dynamic_group__group_type=DynamicGroupTypeChoices.TYPE_STATIC
        ).first()
        self.assertIsNotNone(sga1)

        self.add_permissions("extras.view_staticgroupassociation")
        response = self.client.get(f"{self._get_url('list')}?dynamic_group={sga1.dynamic_group.pk}")
        self.assertBodyContains(response, sga1.get_absolute_url())


class StatusTestCase(
    # TODO? ViewTestCases.BulkDeleteObjectsViewTestCase,
    ViewTestCases.CreateObjectViewTestCase,
    ViewTestCases.DeleteObjectViewTestCase,
    ViewTestCases.EditObjectViewTestCase,
    ViewTestCases.GetObjectViewTestCase,
    ViewTestCases.GetObjectChangelogViewTestCase,
    ViewTestCases.ListObjectsViewTestCase,
    ViewTestCases.BulkEditObjectsViewTestCase,
):
    model = Status

    @classmethod
    def setUpTestData(cls):
        # Status objects to test.
        device_ct = ContentType.objects.get_for_model(Device)
        circuit_ct = ContentType.objects.get_for_model(Circuit)
        interface_ct = ContentType.objects.get_for_model(Interface)

        cls.form_data = {
            "name": "new_status",
            "description": "I am a new status object.",
            "color": "ffcc00",
            "content_types": [device_ct.pk],
        }

        cls.bulk_edit_data = {
            "color": "000000",
            "add_content_types": [interface_ct.pk, circuit_ct.pk],
            "remove_content_types": [device_ct.pk],
        }


class TeamTestCase(ViewTestCases.PrimaryObjectViewTestCase):
    model = Team

    @classmethod
    def setUpTestData(cls):
        # Teams associated with ObjectMetadata objects are protected, create some deletable teams
        Team.objects.create(name="Deletable team 1")
        Team.objects.create(name="Deletable team 2")
        Team.objects.create(name="Deletable team 3")

        cls.form_data = {
            "name": "new team",
            "phone": "555-0122",
            "email": "new-team@example.com",
            "address": "Rainbow Road, Ramus NJ",
        }
        cls.bulk_edit_data = {"address": "Carnegie Hall, New York, NY"}

    @override_settings(EXEMPT_VIEW_PERMISSIONS=["*"])
    def test_create_new_team_and_assign_team_to_object(self):
        initial_team_count = Team.objects.count()
        initial_team_association_count = ContactAssociation.objects.count()
        self.add_permissions("extras.add_team")
        self.add_permissions("extras.add_contactassociation")

        # Try GET with model-level permission
        url = reverse("extras:object_team_add")
        self.assertHttpStatus(self.client.get(url), 200)
        team_associated_circuit = Circuit.objects.first()
        self.form_data["associated_object_type"] = ContentType.objects.get_for_model(Circuit).pk
        self.form_data["associated_object_id"] = team_associated_circuit.pk
        self.form_data["role"] = Role.objects.get_for_model(ContactAssociation).first().pk
        self.form_data["status"] = Status.objects.get_for_model(ContactAssociation).first().pk

        # Try POST with model-level permission
        request = {
            "path": url,
            "data": post_data(self.form_data),
        }
        self.assertHttpStatus(self.client.post(**request), 302)
        self.assertEqual(initial_team_count + 1, Team.objects.count())
        self.assertEqual(initial_team_association_count + 1, ContactAssociation.objects.count())
        team = Team.objects.get(name="new team", phone="555-0122")
        self.assertEqual(team.name, "new team")
        self.assertEqual(team.phone, "555-0122")
        self.assertEqual(team.email, "new-team@example.com")
        self.assertEqual(team.address, "Rainbow Road, Ramus NJ")
        contact_association = ContactAssociation.objects.get(team=team)
        self.assertEqual(contact_association.associated_object_type.pk, self.form_data["associated_object_type"])
        self.assertEqual(contact_association.associated_object_id, self.form_data["associated_object_id"])
        self.assertEqual(contact_association.role.pk, self.form_data["role"])
        self.assertEqual(contact_association.status.pk, self.form_data["status"])


class TagTestCase(ViewTestCases.OrganizationalObjectViewTestCase):
    model = Tag

    @classmethod
    def setUpTestData(cls):
        cls.form_data = {
            "name": "Tag X",
            "color": "c0c0c0",
            "comments": "Some comments",
            "content_types": [ct.id for ct in TaggableClassesQuery().as_queryset()],
        }

        cls.bulk_edit_data = {
            "color": "00ff00",
        }

    def test_create_tags_with_content_types(self):
        self.add_permissions("extras.add_tag")
        location_content_type = ContentType.objects.get_for_model(Location)

        form_data = {
            **self.form_data,
            "content_types": [location_content_type.id],
        }

        request = {
            "path": self._get_url("add"),
            "data": post_data(form_data),
        }
        self.assertHttpStatus(self.client.post(**request), 302)

        tag = Tag.objects.filter(name=self.form_data["name"])
        self.assertTrue(tag.exists())
        self.assertEqual(tag[0].content_types.first(), location_content_type)

    def test_create_tags_with_invalid_content_types(self):
        self.add_permissions("extras.add_tag")
        manufacturer_content_type = ContentType.objects.get_for_model(Manufacturer)

        form_data = {
            **self.form_data,
            "content_types": [manufacturer_content_type.id],
        }

        request = {
            "path": self._get_url("add"),
            "data": post_data(form_data),
        }

        response = self.client.post(**request)
        tag = Tag.objects.filter(name=self.form_data["name"])
        self.assertFalse(tag.exists())
        self.assertBodyContains(response, "content_types: Select a valid choice")

    def test_update_tags_remove_content_type(self):
        """Test removing a tag content_type that is been tagged to a model"""
        self.add_permissions("extras.change_tag")

        tag_1 = Tag.objects.get_for_model(Location).first()
        location = Location.objects.first()
        location.tags.add(tag_1)

        form_data = {
            "name": tag_1.name,
            "color": "c0c0c0",
            "content_types": [ContentType.objects.get_for_model(Device).id],
        }

        request = {
            "path": self._get_url("edit", tag_1),
            "data": post_data(form_data),
        }

        response = self.client.post(**request)
        self.assertHttpStatus(
            response, 200, ["content_types: Unable to remove dcim.location. Dependent objects were found."]
        )


class WebhookTestCase(
    ViewTestCases.CreateObjectViewTestCase,
    ViewTestCases.DeleteObjectViewTestCase,
    ViewTestCases.EditObjectViewTestCase,
    ViewTestCases.GetObjectViewTestCase,
    ViewTestCases.GetObjectChangelogViewTestCase,
    ViewTestCases.ListObjectsViewTestCase,
    ViewTestCases.BulkEditObjectsViewTestCase,
):
    model = Webhook

    @classmethod
    def setUpTestData(cls):
        webhooks = (
            Webhook(
                name="webhook-1",
                enabled=True,
                type_create=True,
                payload_url="http://test-url.com/test-1",
                http_content_type=HTTP_CONTENT_TYPE_JSON,
            ),
            Webhook(
                name="webhook-2",
                enabled=True,
                type_update=True,
                payload_url="http://test-url.com/test-2",
                http_content_type=HTTP_CONTENT_TYPE_JSON,
            ),
            Webhook(
                name="webhook-3",
                enabled=True,
                type_delete=True,
                payload_url="http://test-url.com/test-3",
                http_content_type=HTTP_CONTENT_TYPE_JSON,
            ),
        )

        obj_type = ContentType.objects.get_for_model(ConsolePort)
        device_ct = ContentType.objects.get_for_model(Device)
        ipaddress_ct = ContentType.objects.get_for_model(IPAddress)
        prefix_ct = ContentType.objects.get_for_model(Prefix)

        for webhook in webhooks:
            webhook.save()
            webhook.content_types.set([obj_type])

        cls.form_data = {
            "name": "webhook-4",
            "content_types": [obj_type.pk],
            "enabled": True,
            "type_create": True,
            "payload_url": "http://test-url.com/test-4",
            "http_method": "POST",
            "http_content_type": "application/json",
        }
        cls.bulk_edit_data = {
            "enabled": False,
            "type_create": True,
            "type_update": True,
            "type_delete": False,
            "payload_url": "http://test-url.com/test-4",
            "http_method": "POST",
            "http_content_type": "application/json",
            "additional_headers": "Authorization: Token abc123\nX-Custom-Header: ExampleValue",
            "body_template": '{"event": "{{ event }}", "data": {{ data | tojson }}}',
            "secret": "my-secret-key",
            "ssl_verification": True,
            "ca_file_path": "/etc/ssl/certs/ca-certificates.crt",
            "add_content_types": [ipaddress_ct.pk, prefix_ct.pk],
            "remove_content_types": [device_ct.pk],
        }


class RoleTestCase(ViewTestCases.OrganizationalObjectViewTestCase, ViewTestCases.BulkEditObjectsViewTestCase):
    model = Role

    @classmethod
    def setUpTestData(cls):
        # Role objects to test.
        device_ct = ContentType.objects.get_for_model(Device)
        ipaddress_ct = ContentType.objects.get_for_model(IPAddress)
        prefix_ct = ContentType.objects.get_for_model(Prefix)

        cls.form_data = {
            "name": "New Role",
            "description": "I am a new role object.",
            "color": ColorChoices.COLOR_GREY,
            "content_types": [device_ct.pk],
        }

        cls.bulk_edit_data = {
            "color": "000000",
            "description": "I used to be a new role object.",
            "weight": 255,
            "add_content_types": [ipaddress_ct.pk, prefix_ct.pk],
            "remove_content_types": [device_ct.pk],
        }

    @override_settings(EXEMPT_VIEW_PERMISSIONS=["*"])
    def test_view_with_content_types(self):
        """
        Check that the expected panel headings are rendered and unexpected panel headings are not rendered
        """
        eligible_ct_model_classes = RoleModelsQuery().list_subclasses()
        for instance in self._get_queryset().all():
            response = self.client.get(instance.get_absolute_url())
            response_body = extract_page_body(response.content.decode(response.charset))
            role_content_types = instance.content_types.all()
            for model_class in eligible_ct_model_classes:
                verbose_name_plural = model_class._meta.verbose_name_plural
                content_type = ContentType.objects.get_for_model(model_class)
                result = " ".join(bettertitle(elem) for elem in verbose_name_plural.split())
                # Assert tables are correctly rendered
                if content_type not in role_content_types:
                    if result == "Contact Associations":
                        # AssociationContact Table in the contact tab should be there.
                        self.assertIn(
                            f'<strong>{result}</strong>\n                                    <div class="pull-right noprint">\n',
                            response_body,
                        )
                        # ContactAssociationTable related to this role instances should not be there.
                        self.assertNotIn(
                            f'<strong>{result}</strong>\n            </div>\n            \n\n<table class="table table-hover table-headings">\n',
                            response_body,
                        )
                    else:
                        self.assertNotIn(f"<strong>{result}</strong>", response_body)
                else:
                    self.assertIn(f"<strong>{result}</strong>", response_body)
