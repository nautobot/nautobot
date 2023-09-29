from datetime import timedelta
import urllib.parse
import uuid

from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.test import override_settings
from django.urls import reverse
from django.utils import timezone
from unittest import mock

from nautobot.core.choices import ColorChoices
from nautobot.core.models.fields import slugify_dashes_to_underscores
from nautobot.core.testing import ViewTestCases, TestCase, extract_page_body, extract_form_failures
from nautobot.core.testing.utils import disable_warnings, post_data
from nautobot.dcim.models import ConsolePort, Device, DeviceType, Interface, Manufacturer, Location, LocationType
from nautobot.dcim.tests import test_views
from nautobot.extras.choices import (
    CustomFieldTypeChoices,
    JobExecutionType,
    ObjectChangeActionChoices,
    SecretsGroupAccessTypeChoices,
    SecretsGroupSecretTypeChoices,
)
from nautobot.extras.constants import HTTP_CONTENT_TYPE_JSON
from nautobot.extras.models import (
    ConfigContext,
    ConfigContextSchema,
    CustomField,
    CustomLink,
    DynamicGroup,
    ExportTemplate,
    GitRepository,
    GraphQLQuery,
    Job,
    JobButton,
    JobResult,
    Note,
    ObjectChange,
    Relationship,
    RelationshipAssociation,
    Role,
    ScheduledJob,
    Secret,
    SecretsGroup,
    SecretsGroupAssociation,
    Status,
    Tag,
    Webhook,
    ComputedField,
)
from nautobot.extras.tests.constants import BIG_GRAPHQL_DEVICE_QUERY
from nautobot.extras.tests.test_relationships import RequiredRelationshipTestMixin
from nautobot.extras.utils import TaggableClassesQuery
from nautobot.ipam.models import IPAddress, Prefix, VLAN, VLANGroup
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
):
    model = ComputedField
    slug_source = "label"
    slugify_function = staticmethod(slugify_dashes_to_underscores)

    @classmethod
    def setUpTestData(cls):
        obj_type = ContentType.objects.get_for_model(Location)

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

        cls.slug_test_object = "Computed Field Five"


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


# This OrganizationalObjectViewTestCase less BulkImportObjectsViewTestCase
# because it doesn't make sense to support CSV for schemas.
class ConfigContextSchemaTestCase(
    ViewTestCases.CreateObjectViewTestCase,
    ViewTestCases.DeleteObjectViewTestCase,
    ViewTestCases.EditObjectViewTestCase,
    ViewTestCases.GetObjectViewTestCase,
    ViewTestCases.GetObjectChangelogViewTestCase,
    ViewTestCases.ListObjectsViewTestCase,
    ViewTestCases.BulkDeleteObjectsViewTestCase,
    ViewTestCases.BulkEditObjectsViewTestCase,
):
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


class CustomLinkTestCase(
    ViewTestCases.CreateObjectViewTestCase,
    ViewTestCases.DeleteObjectViewTestCase,
    ViewTestCases.EditObjectViewTestCase,
    ViewTestCases.GetObjectViewTestCase,
    ViewTestCases.GetObjectChangelogViewTestCase,
    ViewTestCases.ListObjectsViewTestCase,
):
    model = CustomLink

    @classmethod
    def setUpTestData(cls):
        obj_type = ContentType.objects.get_for_model(Location)

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


class CustomFieldTestCase(
    # No NotesViewTestCase or BulkImportObjectsViewTestCase, at least for now
    ViewTestCases.BulkDeleteObjectsViewTestCase,
    ViewTestCases.CreateObjectViewTestCase,
    ViewTestCases.DeleteObjectViewTestCase,
    ViewTestCases.EditObjectViewTestCase,
    ViewTestCases.GetObjectViewTestCase,
    ViewTestCases.GetObjectChangelogViewTestCase,
    ViewTestCases.ListObjectsViewTestCase,
):
    model = CustomField
    slugify_function = staticmethod(slugify_dashes_to_underscores)

    @classmethod
    def setUpTestData(cls):
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
            custom_field.content_types.set([obj_type])

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


class CustomLinkTest(TestCase):
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
        DynamicGroup.objects.create(name="DG 1", content_type=content_type)
        DynamicGroup.objects.create(name="DG 2", content_type=content_type)
        DynamicGroup.objects.create(name="DG 3", content_type=content_type)

        cls.form_data = {
            "name": "new_dynamic_group",
            "description": "I am a new dynamic group object.",
            "content_type": content_type.pk,
            # Management form fields required for the dynamic formset
            "dynamic_group_memberships-TOTAL_FORMS": "0",
            "dynamic_group_memberships-INITIAL_FORMS": "1",
            "dynamic_group_memberships-MIN_NUM_FORMS": "0",
            "dynamic_group_memberships-MAX_NUM_FORMS": "1000",
        }

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


class ExportTemplateTestCase(
    ViewTestCases.CreateObjectViewTestCase,
    ViewTestCases.DeleteObjectViewTestCase,
    ViewTestCases.EditObjectViewTestCase,
    ViewTestCases.GetObjectViewTestCase,
    ViewTestCases.GetObjectChangelogViewTestCase,
    ViewTestCases.ListObjectsViewTestCase,
):
    model = ExportTemplate

    @classmethod
    def setUpTestData(cls):
        obj_type = ContentType.objects.get_for_model(Location)

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


class GitRepositoryTestCase(
    ViewTestCases.BulkDeleteObjectsViewTestCase,
    ViewTestCases.BulkImportObjectsViewTestCase,
    ViewTestCases.CreateObjectViewTestCase,
    ViewTestCases.DeleteObjectViewTestCase,
    ViewTestCases.EditObjectViewTestCase,
    ViewTestCases.GetObjectViewTestCase,
    ViewTestCases.GetObjectChangelogViewTestCase,
    ViewTestCases.ListObjectsViewTestCase,
):
    model = GitRepository
    slugify_function = staticmethod(slugify_dashes_to_underscores)

    @classmethod
    def setUpTestData(cls):
        secrets_groups = (
            SecretsGroup.objects.create(name="Secrets Group 1"),
            SecretsGroup.objects.create(name="Secrets Group 2"),
        )

        # Create four GitRepository records
        repos = (
            GitRepository(name="Repo 1", slug="repo_1", remote_url="https://example.com/repo1.git"),
            GitRepository(name="Repo 2", slug="repo_2", remote_url="https://example.com/repo2.git"),
            GitRepository(name="Repo 3", slug="repo_3", remote_url="https://example.com/repo3.git"),
            GitRepository(name="Repo 4", remote_url="https://example.com/repo4.git", secrets_group=secrets_groups[0]),
        )
        for repo in repos:
            repo.validated_save()

        cls.form_data = {
            "name": "A new Git repository",
            "slug": "a_new_git_repository",
            "remote_url": "http://example.com/a_new_git_repository.git",
            "branch": "develop",
            "_token": "1234567890abcdef1234567890abcdef",
            "secrets_group": secrets_groups[1].pk,
            "provided_contents": [
                "extras.configcontext",
                "extras.job",
                "extras.exporttemplate",
            ],
        }

        cls.csv_data = (
            "name,slug,remote_url,branch,secrets_group,provided_contents",
            "Git Repository 5,git_repo_5,https://example.com,main,,extras.configcontext",
            "Git Repository 6,git_repo_6,https://example.com,develop,Secrets Group 2,",
            'Git Repository 7,git_repo_7,https://example.com,next,Secrets Group 2,"extras.job,extras.configcontext"',
        )

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


# Not a full-fledged PrimaryObjectViewTestCase as there's no BulkEditView for Secrets
class SecretTestCase(
    ViewTestCases.GetObjectViewTestCase,
    ViewTestCases.GetObjectChangelogViewTestCase,
    ViewTestCases.CreateObjectViewTestCase,
    ViewTestCases.EditObjectViewTestCase,
    ViewTestCases.DeleteObjectViewTestCase,
    ViewTestCases.ListObjectsViewTestCase,
    ViewTestCases.BulkImportObjectsViewTestCase,
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

        cls.csv_data = (
            "name,provider,parameters",
            'View Test 5,environment-variable,{"variable": "VIEW_TEST_5"}',
            'View Test 6,environment-variable,{"variable": "VIEW_TEST_6"}',
            'View Test 7,environment-variable,{"variable": "VIEW_TEST_7"}',
        )


# Not a full-fledged OrganizationalObjectViewTestCase as there's no BulkImportView for SecretsGroups
class SecretsGroupTestCase(
    ViewTestCases.GetObjectViewTestCase,
    ViewTestCases.GetObjectChangelogViewTestCase,
    ViewTestCases.CreateObjectViewTestCase,
    ViewTestCases.EditObjectViewTestCase,
    ViewTestCases.DeleteObjectViewTestCase,
    ViewTestCases.ListObjectsViewTestCase,
    ViewTestCases.BulkDeleteObjectsViewTestCase,
):
    model = SecretsGroup

    @classmethod
    def setUpTestData(cls):
        secrets_groups = (
            SecretsGroup.objects.create(name="Group 1", description="First Group"),
            SecretsGroup.objects.create(name="Group 2"),
            SecretsGroup.objects.create(name="Group 3"),
        )

        secrets = (
            Secret.objects.create(name="secret 1", provider="text-file", parameters={"path": "/tmp"}),
            Secret.objects.create(name="secret 2", provider="text-file", parameters={"path": "/tmp"}),
            Secret.objects.create(name="secret 3", provider="text-file", parameters={"path": "/tmp"}),
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
            task="pass.TestPass",
            interval=JobExecutionType.TYPE_IMMEDIATELY,
            user=user,
            start_time=timezone.now(),
        )
        ScheduledJob.objects.create(
            name="test2",
            task="pass.TestPass",
            interval=JobExecutionType.TYPE_IMMEDIATELY,
            user=user,
            start_time=timezone.now(),
        )
        ScheduledJob.objects.create(
            name="test3",
            task="pass.TestPass",
            interval=JobExecutionType.TYPE_IMMEDIATELY,
            user=user,
            start_time=timezone.now(),
        )

    def test_only_enabled_is_listed(self):
        self.add_permissions("extras.view_scheduledjob")

        # this should not appear, since it’s not enabled
        ScheduledJob.objects.create(
            enabled=False,
            name="test4",
            task="pass.TestPass",
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
                task="pass.TestPass",
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
            task="pass.TestPass",
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

    def setUp(self):
        super().setUp()
        self.job_model = Job.objects.get_for_class_path("dry_run.TestDryRun")
        self.job_model_2 = Job.objects.get_for_class_path("fail.TestFail")

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
            task="fail.TestFail",
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
            task="pass.TestPass",
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
        self.assertHttpStatus(response, 200)

        response_body = extract_page_body(response.content.decode(response.charset))

        # The object's display name or string representation should appear in the response
        self.assertIn(getattr(instance, "display", str(instance)), response_body, msg=response_body)

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
        self.assertHttpStatus(response, 200)
        response_body = extract_page_body(response.content.decode(response.charset))
        self.assertIn("You do not have permission to run jobs", response_body)
        # No job was submitted
        self.assertFalse(JobResult.objects.filter(name=self.job_model.name).exists())

    @override_settings(EXEMPT_VIEW_PERMISSIONS=[])
    def test_post_dry_run_not_runnable(self):
        """A non-enabled job cannot be dry-run."""
        self.add_permissions("extras.view_scheduledjob")
        instance = self._get_queryset().first()
        data = {"_dry_run": True}

        response = self.client.post(self._get_url("view", instance), data)
        self.assertHttpStatus(response, 200)
        response_body = extract_page_body(response.content.decode(response.charset))
        self.assertIn("This job cannot be run at this time", response_body)
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
        self.assertHttpStatus(response, 200)
        response_body = extract_page_body(response.content.decode(response.charset))
        self.assertIn("You do not have permission to run this job", response_body)
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
        self.assertHttpStatus(response, 200)
        response_body = extract_page_body(response.content.decode(response.charset))
        self.assertIn("You do not have permission to run this job", response_body)
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
            self.assertHttpStatus(response, 200, msg=str(user))
            response_body = extract_page_body(response.content.decode(response.charset))
            self.assertIn("You do not have permission", response_body, msg=str(user))
            # Request was not deleted
            self.assertEqual(1, len(ScheduledJob.objects.filter(pk=instance.pk)), msg=str(user))

    @override_settings(EXEMPT_VIEW_PERMISSIONS=["*"])
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
        response = self.client.post(self._get_url("view", instance), data)
        self.assertRedirects(response, reverse("extras:scheduledjob_approval_queue_list"))
        # Request was deleted
        self.assertEqual(0, len(ScheduledJob.objects.filter(pk=instance.pk)))

        # Check object-based permissions are enforced for a different instance
        instance = self._get_queryset().first()
        response = self.client.post(self._get_url("view", instance), data)
        self.assertHttpStatus(response, 200, msg=str(user))
        response_body = extract_page_body(response.content.decode(response.charset))
        self.assertIn("You do not have permission", response_body, msg=str(user))
        # Request was not deleted
        self.assertEqual(1, len(ScheduledJob.objects.filter(pk=instance.pk)), msg=str(user))

    @override_settings(EXEMPT_VIEW_PERMISSIONS=["*"])
    def test_post_approve_cannot_self_approve(self):
        self.add_permissions("extras.change_scheduledjob")
        self.add_permissions("extras.approve_job")
        instance = self._get_queryset().first()
        data = {"_approve": True}

        response = self.client.post(self._get_url("view", instance), data)
        self.assertHttpStatus(response, 200)
        response_body = extract_page_body(response.content.decode(response.charset))
        self.assertIn("You cannot approve your own job request", response_body)
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
            self.assertHttpStatus(response, 200, msg=str(user))
            response_body = extract_page_body(response.content.decode(response.charset))
            self.assertIn("You do not have permission", response_body, msg=str(user))
            # Job was not approved
            instance.refresh_from_db()
            self.assertIsNone(instance.approved_by_user)

    @override_settings(EXEMPT_VIEW_PERMISSIONS=["*"])
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
        response = self.client.post(self._get_url("view", instance), data)
        self.assertRedirects(response, reverse("extras:scheduledjob_approval_queue_list"))
        # Job was scheduled
        instance.refresh_from_db()
        self.assertEqual(instance.approved_by_user, user)

        # Check object-based permissions are enforced for a different instance
        instance = self._get_queryset().last()
        response = self.client.post(self._get_url("view", instance), data)
        self.assertHttpStatus(response, 200, msg=str(user))
        response_body = extract_page_body(response.content.decode(response.charset))
        self.assertIn("You do not have permission", response_body, msg=str(user))
        # Job was not scheduled
        instance.refresh_from_db()
        self.assertIsNone(instance.approved_by_user)


class JobResultTestCase(
    ViewTestCases.GetObjectViewTestCase,
    ViewTestCases.ListObjectsViewTestCase,
    ViewTestCases.DeleteObjectViewTestCase,
    ViewTestCases.BulkDeleteObjectsViewTestCase,
):
    model = JobResult

    @classmethod
    def setUpTestData(cls):
        JobResult.objects.create(name="pass.TestPass")
        JobResult.objects.create(name="fail.TestFail")


class JobTestCase(
    # note no CreateObjectViewTestCase - we do not support user creation of Job records
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
        """Don't include hidden Jobs, non-installed Jobs, JobHookReceivers or JobButtonReceivers as they won't appear in the UI by default."""
        return self.model.objects.filter(
            installed=True, hidden=False, is_job_hook_receiver=False, is_job_button_receiver=False
        )

    @classmethod
    def setUpTestData(cls):
        # Job model objects are automatically created during database migrations

        # But we do need to make sure the ones we're testing are flagged appropriately
        cls.test_pass = Job.objects.get(job_class_name="TestPass")
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
        cls.test_not_installed.validated_save()

        cls.data_run_immediately = {
            "_schedule_type": "immediately",
        }

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
            "task_queues": "overridden,priority",
            "task_queues_override": True,
        }

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
            self.assertHttpStatus(response, 200, msg=run_url)

            response_body = extract_page_body(response.content.decode(response.charset))
            self.assertIn("TestPass", response_body)

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

        for run_url in self.run_urls:
            response = self.client.post(run_url, self.data_run_immediately)
            self.assertHttpStatus(response, 200, msg=run_url)

            content = extract_page_body(response.content.decode(response.charset))
            self.assertIn("Celery worker process not running.", content)

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
            self.assertEqual(response.status_code, 200, msg=run_url)
            response_body = extract_page_body(response.content.decode(response.charset))
            self.assertIn("Job is not presently installed", response_body)

            self.assertFalse(JobResult.objects.filter(name=self.test_not_installed.name).exists())

    @mock.patch("nautobot.extras.views.get_worker_count", return_value=1)
    def test_run_now_not_enabled(self, _):
        self.add_permissions("extras.run_job")

        for run_url in (
            reverse("extras:job_run_by_class_path", kwargs={"class_path": "fail.TestFail"}),
            reverse("extras:job_run", kwargs={"pk": Job.objects.get(job_class_name="TestFail").pk}),
        ):
            response = self.client.post(run_url, self.data_run_immediately)
            self.assertEqual(response.status_code, 200, msg=run_url)
            response_body = extract_page_body(response.content.decode(response.charset))
            self.assertIn("Job is not enabled to be run", response_body)
            self.assertFalse(JobResult.objects.filter(name="fail.TestFail").exists())

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

    @mock.patch("nautobot.extras.jobs.task_queues_as_choices")
    def test_rerun_job(self, mock_task_queues_as_choices):
        self.add_permissions("extras.run_job")
        self.add_permissions("extras.view_jobresult")

        mock_task_queues_as_choices.return_value = [("default", ""), ("queue1", ""), ("uniquequeue", "")]
        job_celery_kwargs = {
            "nautobot_job_job_model_id": self.test_required_args.id,
            "nautobot_job_profile": True,
            "nautobot_job_user_id": self.user.id,
            "queue": "uniquequeue",
        }

        previous_result = JobResult.objects.create(
            job_model=self.test_required_args,
            user=self.user,
            task_kwargs={"var": "456"},
            celery_kwargs=job_celery_kwargs,
        )

        run_url = reverse("extras:job_run", kwargs={"pk": self.test_required_args.pk})
        response = self.client.get(f"{run_url}?kwargs_from_job_result={previous_result.pk!s}")
        content = extract_page_body(response.content.decode(response.charset))

        self.assertInHTML('<option value="uniquequeue" selected>', content)
        self.assertInHTML(
            '<input type="text" name="var" value="456" class="form-control form-control" required placeholder="None" id="id_var">',
            content,
        )
        self.assertInHTML('<input type="hidden" name="_profile" value="True" id="id__profile">', content)

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
            self.assertHttpStatus(response, 200, msg=self.run_urls[1])

            content = extract_page_body(response.content.decode(response.charset))
            self.assertIn("Unable to schedule job: Job may have sensitive input variables.", content)

    @mock.patch("nautobot.extras.views.get_worker_count", return_value=1)
    def test_run_job_with_invalid_task_queue(self, _):
        self.add_permissions("extras.run_job")
        self.add_permissions("extras.view_jobresult")

        self.test_pass.task_queues = []
        self.test_pass.task_queues_override = True
        self.test_pass.validated_save()

        data = {
            "_schedule_type": "immediately",
            "_task_queue": "invalid",
        }

        for run_url in self.run_urls:
            response = self.client.post(run_url, data)
            self.assertHttpStatus(response, 200, msg=run_url)

            errors = extract_form_failures(response.content.decode(response.charset))
            self.assertEqual(
                errors,
                ["_task_queue: Select a valid choice. invalid is not one of the available choices."],
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
            content = extract_page_body(response.content.decode(response.charset))
            self.assertIn(
                "This job is flagged as possibly having sensitive variables but is also flagged as requiring approval.",
                content,
            )

            # Assert run button is disabled
            self.assertInHTML(
                """
                <button type="submit" name="_run" id="id__run" class="btn btn-primary" disabled="disabled">
                    <i class="mdi mdi-play"></i> Run Job Now
                </button>
                """,
                content,
            )
            # Assert error message shows after post
            response = self.client.post(run_url, data)
            self.assertHttpStatus(response, 200, msg=self.run_urls[1])

            content = extract_page_body(response.content.decode(response.charset))
            self.assertIn(
                "Unable to run or schedule job: "
                "This job is flagged as possibly having sensitive variables but is also flagged as requiring approval."
                "One of these two flags must be removed before this job can be scheduled or run.",
                content,
            )

    def test_job_object_change_log_view(self):
        """Assert Job change log view displays appropriate header"""
        instance = self.test_pass
        self.add_permissions("extras.view_objectchange", "extras.view_job")
        response = self.client.get(instance.get_changelog_url())
        content = extract_page_body(response.content.decode(response.charset))

        self.assertHttpStatus(response, 200)
        self.assertIn(f"<h1>{instance.name} - Change Log</h1>", content)


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
        job_buttons = (
            JobButton.objects.create(
                name="JobButton1",
                text="JobButton1",
                job=Job.objects.get(job_class_name="TestJobButtonReceiverSimple"),
                confirmation=True,
            ),
            JobButton.objects.create(
                name="JobButton2",
                text="JobButton2",
                job=Job.objects.get(job_class_name="TestJobButtonReceiverSimple"),
                confirmation=False,
            ),
            JobButton.objects.create(
                name="JobButton3",
                text="JobButton3",
                job=Job.objects.get(job_class_name="TestJobButtonReceiverComplex"),
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
            "job": Job.objects.get(job_class_name="TestJobButtonReceiverComplex").pk,
            "weight": 100,
            "button_class": "default",
            "confirmation": False,
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


class RelationshipTestCase(
    ViewTestCases.CreateObjectViewTestCase,
    ViewTestCases.DeleteObjectViewTestCase,
    ViewTestCases.EditObjectViewTestCase,
    ViewTestCases.BulkDeleteObjectsViewTestCase,
    ViewTestCases.GetObjectViewTestCase,
    ViewTestCases.GetObjectChangelogViewTestCase,
    ViewTestCases.ListObjectsViewTestCase,
    RequiredRelationshipTestMixin,
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

        cls.slug_test_object = "Primary Interface"

    def test_required_relationships(self):
        """
        1. Try creating an object when no required target object exists
        2. Try creating an object without specifying required target object(s)
        3. Try creating an object when all required data is present
        4. Test bulk edit
        """

        # Delete existing factory generated objects that may interfere with this test
        IPAddress.objects.all().delete()
        Prefix.objects.update(parent=None)
        Prefix.objects.all().delete()
        VLAN.objects.all().delete()

        # Parameterized tests (for creating and updating single objects):
        self.required_relationships_test(interact_with="ui")

        # 4. Bulk create/edit tests:

        vlan_status = Status.objects.get_for_model(VLAN).first()
        vlans = (
            VLAN.objects.create(name="test_required_relationships1", vid=1, status=vlan_status),
            VLAN.objects.create(name="test_required_relationships2", vid=2, status=vlan_status),
            VLAN.objects.create(name="test_required_relationships3", vid=3, status=vlan_status),
            VLAN.objects.create(name="test_required_relationships4", vid=4, status=vlan_status),
            VLAN.objects.create(name="test_required_relationships5", vid=5, status=vlan_status),
            VLAN.objects.create(name="test_required_relationships6", vid=6, status=vlan_status),
        )

        # Try deleting all devices and then editing the 6 VLANs (fails):
        Device.objects.all().delete()
        response = self.client.post(
            reverse("ipam:vlan_bulk_edit"), data={"pk": [str(vlan.id) for vlan in vlans], "_apply": [""]}
        )
        self.assertContains(response, "VLANs require at least one device, but no devices exist yet.")

        # Create test device for association
        device_for_association = test_views.create_test_device("VLAN Required Device")

        # Try editing all 6 VLANs without adding the required device(fails):
        response = self.client.post(
            reverse("ipam:vlan_bulk_edit"), data={"pk": [str(vlan.id) for vlan in vlans], "_apply": [""]}
        )
        self.assertContains(
            response,
            "6 VLANs require a device for the required relationship &quot;VLANs require at least one Device&quot;",
        )

        # Try editing 3 VLANs without adding the required device(fails):
        response = self.client.post(
            reverse("ipam:vlan_bulk_edit"), data={"pk": [str(vlan.id) for vlan in vlans[:3]], "_apply": [""]}
        )
        self.assertContains(
            response,
            "These VLANs require a device for the required "
            "relationship &quot;VLANs require at least one Device&quot;",
        )
        for vlan in vlans[:3]:
            self.assertContains(response, f"{str(vlan)}")

        # Try editing 6 VLANs and adding the required device (succeeds):
        response = self.client.post(
            reverse("ipam:vlan_bulk_edit"),
            data={
                "pk": [str(vlan.id) for vlan in vlans],
                "add_cr_vlans_devices_m2m__source": [str(device_for_association.id)],
                "_apply": [""],
            },
            follow=True,
        )
        self.assertContains(response, "Updated 6 VLANs")

        # Try editing 6 VLANs and removing the required device (fails):
        response = self.client.post(
            reverse("ipam:vlan_bulk_edit"),
            data={
                "pk": [str(vlan.id) for vlan in vlans],
                "remove_cr_vlans_devices_m2m__source": [str(device_for_association.id)],
                "_apply": [""],
            },
        )
        self.assertContains(
            response,
            "6 VLANs require a device for the required relationship &quot;VLANs require at least one Device&quot;",
        )


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
        vlan_group = VLANGroup.objects.first()
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
        # TODO: it'd make test failures more readable if we strip the page headers/footers from the content
        self.assertIn(instance1.source.name, content, msg=content)
        self.assertIn(instance1.destination.name, content, msg=content)
        self.assertNotIn(instance2.source.name, content, msg=content)
        self.assertNotIn(instance2.destination.name, content, msg=content)


class StatusTestCase(
    ViewTestCases.CreateObjectViewTestCase,
    ViewTestCases.DeleteObjectViewTestCase,
    ViewTestCases.EditObjectViewTestCase,
    ViewTestCases.GetObjectViewTestCase,
    ViewTestCases.GetObjectChangelogViewTestCase,
    ViewTestCases.ListObjectsViewTestCase,
):
    model = Status

    @classmethod
    def setUpTestData(cls):
        # Status objects to test.
        content_type = ContentType.objects.get_for_model(Device)

        cls.form_data = {
            "name": "new_status",
            "description": "I am a new status object.",
            "color": "ffcc00",
            "content_types": [content_type.pk],
        }

        cls.csv_data = (
            "name,color,content_types"
            "test_status1,ffffff,dcim.device"
            'test_status2,ffffff,"dcim.device,dcim.location"'
            "test_status3,ffffff,dcim.device"
            "test_status4,ffffff,dcim.device"
        )

        cls.bulk_edit_data = {
            "color": "000000",
        }


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

        cls.csv_data = (
            "name,color,description,content_types",
            "Tag 4,ff0000,Fourth tag,dcim.device",
            'Tag 5,00ff00,Fifth tag,"dcim.device,dcim.location"',
            "Tag 6,0000ff,Sixth tag,dcim.location",
        )

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
        vlangroup_content_type = ContentType.objects.get_for_model(VLANGroup)

        form_data = {
            **self.form_data,
            "content_types": [vlangroup_content_type.id],
        }

        request = {
            "path": self._get_url("add"),
            "data": post_data(form_data),
        }

        response = self.client.post(**request)
        tag = Tag.objects.filter(name=self.form_data["name"])
        self.assertFalse(tag.exists())
        self.assertIn("content_types: Select a valid choice", str(response.content))

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


class RoleTestCase(ViewTestCases.OrganizationalObjectViewTestCase):
    model = Role

    @classmethod
    def setUpTestData(cls):
        # Status objects to test.
        content_type = ContentType.objects.get_for_model(Device)

        cls.form_data = {
            "name": "New Role",
            "description": "I am a new role object.",
            "color": ColorChoices.COLOR_GREY,
            "content_types": [content_type.pk],
        }

        cls.csv_data = (
            "name,weight,color,content_types,description",
            "test_role1,1000,ffffff,dcim.device,A Role",
            'test_role2,200,ffffff,"dcim.device,dcim.rack",A Role',
            'test_role3,100,ffffff,"dcim.device,ipam.prefix",A Role',
            'test_role4,50,ffffff,"ipam.ipaddress,ipam.vlan",A Role',
        )

        cls.bulk_edit_data = {
            "color": "000000",
        }
