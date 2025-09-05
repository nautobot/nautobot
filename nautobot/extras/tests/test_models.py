from datetime import datetime, timedelta, timezone
import os
import shutil
import tempfile
from unittest import expectedFailure, mock
import uuid
import warnings
from zoneinfo import ZoneInfo

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db.models import ProtectedError
from django.db.utils import IntegrityError
from django.test import override_settings
from django.test.utils import isolate_apps
from django.utils.timezone import get_default_timezone, now
from django_celery_beat.tzcrontab import TzAwareCrontab
from git import GitCommandError
from jinja2.exceptions import TemplateAssertionError, TemplateSyntaxError
import time_machine

from nautobot.circuits.models import CircuitType
from nautobot.core.choices import ColorChoices
from nautobot.core.testing import TestCase
from nautobot.core.testing.models import ModelTestCases
from nautobot.dcim.models import (
    Device,
    DeviceType,
    Location,
    LocationType,
    Manufacturer,
    Platform,
)
from nautobot.extras.choices import (
    JobExecutionType,
    JobResultStatusChoices,
    LogLevelChoices,
    MetadataTypeDataTypeChoices,
    ObjectChangeActionChoices,
    ObjectChangeEventContextChoices,
    SecretsGroupAccessTypeChoices,
    SecretsGroupSecretTypeChoices,
)
from nautobot.extras.constants import (
    JOB_LOG_MAX_ABSOLUTE_URL_LENGTH,
    JOB_LOG_MAX_GROUPING_LENGTH,
    JOB_LOG_MAX_LOG_OBJECT_LENGTH,
    JOB_OVERRIDABLE_FIELDS,
)
from nautobot.extras.datasources.registry import get_datasource_contents
from nautobot.extras.jobs import get_job
from nautobot.extras.models import (
    ComputedField,
    ConfigContext,
    ConfigContextSchema,
    Contact,
    DynamicGroup,
    ExportTemplate,
    ExternalIntegration,
    FileAttachment,
    FileProxy,
    GitRepository,
    Job as JobModel,
    JobLogEntry,
    JobQueue,
    JobResult,
    MetadataChoice,
    MetadataType,
    ObjectChange,
    ObjectMetadata,
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
    Webhook,
)
from nautobot.extras.models.statuses import StatusModel
from nautobot.extras.registry import registry
from nautobot.extras.secrets.exceptions import SecretParametersError, SecretProviderError, SecretValueNotFoundError
from nautobot.extras.tests.git_helper import create_and_populate_git_repository
from nautobot.ipam.models import IPAddress
from nautobot.tenancy.models import Tenant
from nautobot.virtualization.models import (
    Cluster,
    ClusterGroup,
    ClusterType,
    VirtualMachine,
)

from example_app.jobs import ExampleJob

User = get_user_model()


class ComputedFieldTest(ModelTestCases.BaseModelTestCase):
    """
    Tests for the `ComputedField` Model
    """

    model = ComputedField

    def setUp(self):
        self.good_computed_field = ComputedField.objects.create(
            content_type=ContentType.objects.get_for_model(Location),
            key="good_computed_field",
            label="Good Computed Field",
            template="{{ obj.name }} is awesome!",
            fallback_value="This template has errored",
            weight=100,
        )
        self.bad_computed_field = ComputedField.objects.create(
            content_type=ContentType.objects.get_for_model(Location),
            key="bad_computed_field",
            label="Bad Computed Field",
            template="{{ not_in_context | not_a_filter }} is horrible!",
            fallback_value="An error occurred while rendering this template.",
            weight=50,
        )
        self.evil_computed_field = ComputedField.objects.create(
            content_type=ContentType.objects.get_for_model(Secret),
            key="evil_computed_field",
            label="Evil Computed Field",
            template="{{ obj.get_value() }}",
            weight=666,
        )
        self.blank_fallback_value = ComputedField.objects.create(
            content_type=ContentType.objects.get_for_model(Location),
            key="blank_fallback_value",
            label="Blank Fallback Value",
            template="{{ obj.location }}",
            weight=50,
        )
        self.location1 = Location.objects.filter(location_type=LocationType.objects.get(name="Campus")).first()
        self.secret = Secret.objects.create(
            name="Environment Variable Secret",
            provider="environment-variable",
            parameters={"variable": "NAUTOBOT_ROOT"},
        )
        self.secrets_group = SecretsGroup.objects.create(name="Group of Secrets")
        SecretsGroupAssociation.objects.create(
            secrets_group=self.secrets_group,
            secret=self.secret,
            access_type=SecretsGroupAccessTypeChoices.TYPE_GENERIC,
            secret_type=SecretsGroupSecretTypeChoices.TYPE_SECRET,
        )

        # Template strings for validation testing (cannot be saved due to syntax errors)
        self.invalid_template_unclosed_bracket = "{{ obj.name }"
        self.invalid_template_unknown_tag = "{% unknowntag %}{{ obj.name }}{% endunknowntag %}"

    def test_render_method(self):
        rendered_value = self.good_computed_field.render(context={"obj": self.location1})
        self.assertEqual(rendered_value, f"{self.location1.name} is awesome!")

    def test_render_method_undefined_error(self):
        rendered_value = self.blank_fallback_value.render(context={"obj": self.location1})
        self.assertEqual(rendered_value, "")

    def test_render_method_bad_template(self):
        rendered_value = self.bad_computed_field.render(context={"obj": self.location1})
        self.assertEqual(rendered_value, self.bad_computed_field.fallback_value)

    def test_render_method_evil_template(self):
        rendered_value = self.evil_computed_field.render(context={"obj": self.secret})
        self.assertEqual(rendered_value, "")
        self.evil_computed_field.template = "{{ obj.secrets_groups.first().get_secret_value('Generic', 'secret') }}"
        rendered_value = self.evil_computed_field.render(context={"obj": self.secret})
        self.assertEqual(rendered_value, "")

    def test_check_if_key_is_graphql_safe(self):
        """
        Check the GraphQL validation method on CustomField Key Attribute.
        """
        # Check if it catches the cpf.key starting with a digit.
        cpf1 = ComputedField(
            label="Test 1",
            key="12_test_1",
            template="{{obj}}",
            content_type=ContentType.objects.get_for_model(Device),
        )
        with self.assertRaises(ValidationError) as error:
            cpf1.save()
        self.assertIn(
            "This key is not Python/GraphQL safe. Please do not start the key with a digit and do not use hyphens or whitespace",
            str(error.exception),
        )
        # Check if it catches the cpf.key with whitespace.
        cpf1.key = "test 1"
        with self.assertRaises(ValidationError) as error:
            cpf1.save()
        self.assertIn(
            "This key is not Python/GraphQL safe. Please do not start the key with a digit and do not use hyphens or whitespace",
            str(error.exception),
        )
        # Check if it catches the cpf.key with hyphens.
        cpf1.key = "test-1-computed-field"
        with self.assertRaises(ValidationError) as error:
            cpf1.save()
        self.assertIn(
            "This key is not Python/GraphQL safe. Please do not start the key with a digit and do not use hyphens or whitespace",
            str(error.exception),
        )
        # Check if it catches the cpf.key with special characters
        cpf1.key = "test_1_computed_f)(&d"
        with self.assertRaises(ValidationError) as error:
            cpf1.save()
        self.assertIn(
            "This key is not Python/GraphQL safe. Please do not start the key with a digit and do not use hyphens or whitespace",
            str(error.exception),
        )

    def test_template_validation_invalid_syntax(self):
        """
        Test that ComputedField with invalid Jinja2 template syntax raises ValidationError.
        """
        # Invalid template with syntax error - unclosed bracket
        invalid_computed_field = ComputedField(
            label="Invalid Template Test",
            key="invalid_template_test",
            template=self.invalid_template_unclosed_bracket,
            content_type=ContentType.objects.get_for_model(Device),
        )

        with self.assertRaises(ValidationError) as context:
            invalid_computed_field.full_clean()

        # Check that the error message contains template-specific information
        error_dict = context.exception.error_dict
        self.assertIn("template", error_dict)
        self.assertIn("Template syntax error", str(error_dict["template"][0]))
        self.assertIn("line", str(error_dict["template"][0]))

    def test_template_validation_invalid_tag(self):
        """
        Test that ComputedField with invalid Jinja2 tag raises ValidationError.
        """
        # Invalid template with unknown tag
        invalid_computed_field = ComputedField(
            label="Invalid Tag Test",
            key="invalid_tag_test",
            template=self.invalid_template_unknown_tag,
            content_type=ContentType.objects.get_for_model(Device),
        )

        with self.assertRaises(ValidationError) as context:
            invalid_computed_field.full_clean()

        # Check that the error message contains template-specific information
        error_dict = context.exception.error_dict
        self.assertIn("template", error_dict)
        self.assertIn("Template syntax error", str(error_dict["template"][0]))

    def test_bulk_create_valid_templates(self):
        """Test that bulk_create works with valid templates."""
        valid_fields = [
            ComputedField(
                label="Bulk Test 1",
                key="bulk_test_1",
                template="{{ obj.name }} - Test 1",
                content_type=ContentType.objects.get_for_model(Device),
            ),
            ComputedField(
                label="Bulk Test 2",
                key="bulk_test_2",
                template="{{ obj.id }} - Test 2",
                content_type=ContentType.objects.get_for_model(Device),
            ),
        ]

        # Should not raise ValidationError
        created_fields = ComputedField.objects.bulk_create(valid_fields)
        self.assertEqual(len(created_fields), 2)

    def test_bulk_create_invalid_templates(self):
        """Test that bulk_create fails with invalid templates and reports all errors."""
        invalid_fields = [
            ComputedField(
                label="Invalid Test 1",
                key="invalid_test_1",
                template=self.invalid_template_unclosed_bracket,
                content_type=ContentType.objects.get_for_model(Device),
            ),
            ComputedField(
                label="Invalid Test 2",
                key="invalid_test_2",
                template=self.invalid_template_unknown_tag,
                content_type=ContentType.objects.get_for_model(Device),
            ),
        ]

        with self.assertRaises(ValidationError) as context:
            ComputedField.objects.bulk_create(invalid_fields)

        # Check that both errors are reported
        error_message = str(context.exception)
        self.assertIn("Template validation failed", error_message)
        self.assertIn("Invalid Test 1", error_message)
        self.assertIn("Invalid Test 2", error_message)

    def test_bulk_update_template_field(self):
        """Test that bulk_update validates templates when template field is updated."""
        # Create valid objects first
        valid_fields = [
            ComputedField(
                label="Update Test 1",
                key="update_test_1",
                template="{{ obj.name }}",
                content_type=ContentType.objects.get_for_model(Device),
            ),
            ComputedField(
                label="Update Test 2",
                key="update_test_2",
                template="{{ obj.id }}",
                content_type=ContentType.objects.get_for_model(Device),
            ),
        ]
        created_fields = ComputedField.objects.bulk_create(valid_fields)

        # Update with invalid templates
        for field in created_fields:
            field.template = self.invalid_template_unclosed_bracket

        with self.assertRaises(ValidationError) as context:
            ComputedField.objects.bulk_update(created_fields, ["template"])

        # Check that validation error occurred
        error_message = str(context.exception)
        self.assertIn("Template validation failed", error_message)
        self.assertIn("Update Test 1", error_message)
        self.assertIn("Update Test 2", error_message)

    def test_bulk_update_non_template_field(self):
        """Test that bulk_update skips template validation when template field is not updated."""
        # Create a field with invalid template (bypassing validation for this test)
        field = ComputedField(
            label="Non-template Update Test",
            key="non_template_update_test",
            template="{{ obj.name }}",  # Start with valid template
            content_type=ContentType.objects.get_for_model(Device),
        )
        field.save()

        # Manually set invalid template (simulating existing invalid data)
        ComputedField.objects.filter(pk=field.pk).update(template=self.invalid_template_unclosed_bracket)
        field.refresh_from_db()

        # Update only the label field - should not trigger template validation
        field.label = "Updated Label"
        try:
            ComputedField.objects.bulk_update([field], ["label"])
        except ValidationError:
            self.fail("bulk_update should not validate templates when template field is not being updated")

    def test_bulk_create_mixed_valid_invalid(self):
        """Test that bulk_create fails when mixing valid and invalid templates."""
        mixed_fields = [
            ComputedField(
                label="Valid Mixed Test",
                key="valid_mixed_test",
                template="{{ obj.name }} - Valid",
                content_type=ContentType.objects.get_for_model(Device),
            ),
            ComputedField(
                label="Invalid Mixed Test",
                key="invalid_mixed_test",
                template=self.invalid_template_unclosed_bracket,
                content_type=ContentType.objects.get_for_model(Device),
            ),
        ]

        with self.assertRaises(ValidationError) as context:
            ComputedField.objects.bulk_create(mixed_fields)

        # Check that the invalid object is reported but valid one is not
        error_message = str(context.exception)
        self.assertIn("Template validation failed", error_message)
        self.assertIn("Invalid Mixed Test", error_message)
        # Valid object should not appear in error message
        self.assertNotIn("Valid Mixed Test", error_message)

        # Verify no objects were created (all-or-nothing behavior)
        self.assertFalse(ComputedField.objects.filter(key="valid_mixed_test").exists())
        self.assertFalse(ComputedField.objects.filter(key="invalid_mixed_test").exists())

    def test_bulk_update_mixed_valid_invalid(self):
        """Test that bulk_update fails when mixing valid and invalid template updates."""
        # Create valid objects first
        valid_fields = [
            ComputedField(
                label="Valid Update Mixed",
                key="valid_update_mixed",
                template="{{ obj.name }}",
                content_type=ContentType.objects.get_for_model(Device),
            ),
            ComputedField(
                label="Invalid Update Mixed",
                key="invalid_update_mixed",
                template="{{ obj.id }}",
                content_type=ContentType.objects.get_for_model(Device),
            ),
        ]
        created_fields = ComputedField.objects.bulk_create(valid_fields)

        # Update: one with valid template, one with invalid
        created_fields[0].template = "{{ obj.name }} - Updated Valid"  # Valid
        created_fields[1].template = self.invalid_template_unclosed_bracket  # Invalid

        with self.assertRaises(ValidationError) as context:
            ComputedField.objects.bulk_update(created_fields, ["template"])

        # Check that only the invalid object is reported
        error_message = str(context.exception)
        self.assertIn("Template validation failed", error_message)
        self.assertIn("Invalid Update Mixed", error_message)
        # Valid object should not appear in error message
        self.assertNotIn("Valid Update Mixed", error_message)

        # Verify templates were not updated (all-or-nothing behavior)
        created_fields[0].refresh_from_db()
        created_fields[1].refresh_from_db()
        self.assertEqual(created_fields[0].template, "{{ obj.name }}")  # Original template
        self.assertEqual(created_fields[1].template, "{{ obj.id }}")  # Original template


class ConfigContextTest(ModelTestCases.BaseModelTestCase):
    """
    These test cases deal with the weighting, ordering, and deep merge logic of config context data.

    It also ensures the various config context querysets are consistent.
    """

    model = ConfigContext

    @classmethod
    def setUpTestData(cls):
        manufacturer = Manufacturer.objects.first()
        cls.devicetype = DeviceType.objects.create(manufacturer=manufacturer, model="Device Type 1")
        cls.devicerole = Role.objects.get_for_model(Device).first()
        root_location_type = LocationType.objects.create(name="Root Location Type")
        parent_location_type = LocationType.objects.create(name="Parent Location Type", parent=root_location_type)
        location_type = LocationType.objects.create(name="Location Type 1", parent=parent_location_type)
        location_status = Status.objects.get_for_model(Location).first()
        cls.root_location = Location.objects.create(
            name="Root Location", location_type=root_location_type, status=location_status
        )
        cls.parent_location = Location.objects.create(
            name="Parent Location", location_type=parent_location_type, status=location_status, parent=cls.root_location
        )
        cls.location = Location.objects.create(
            name="Location 1", location_type=location_type, status=location_status, parent=cls.parent_location
        )
        cls.platform = Platform.objects.first()
        cls.tenant = Tenant.objects.first()
        cls.tenantgroup = cls.tenant.tenant_group
        cls.child_tenant = Tenant.objects.filter(tenant_group__isnull=False, tenant_group__parent__isnull=False).first()
        cls.parent_tenantgroup = cls.child_tenant.tenant_group.parent
        cls.child_tenantgroup = cls.child_tenant.tenant_group
        cls.tag, cls.tag2 = Tag.objects.get_for_model(Device)[:2]
        cls.dynamic_groups = DynamicGroup.objects.create(
            name="Dynamic Group",
            content_type=ContentType.objects.get_for_model(Device),
            filter={"name": ["Device 1", "Device 2"]},
        )
        cls.dynamic_group_2 = DynamicGroup.objects.create(
            name="Dynamic Group 2",
            content_type=ContentType.objects.get_for_model(Device),
            filter={"name": ["Device 2"]},
        )
        cls.vm_dynamic_group = DynamicGroup.objects.create(
            name="VM Dynamic Group",
            content_type=ContentType.objects.get_for_model(VirtualMachine),
            filter={"name": ["VM 1"]},
        )

        cls.device_status = Status.objects.get_for_model(Device).first()
        cls.device = Device.objects.create(
            name="Device 1",
            device_type=cls.devicetype,
            role=cls.devicerole,
            location=cls.location,
            status=cls.device_status,
        )

        ConfigContext.objects.create(name="context 1", weight=100, data={"a": 123, "b": 456, "c": 777})

    def test_higher_weight_wins(self):
        ConfigContext.objects.create(name="context 2", weight=99, data={"a": 123, "b": 456, "c": 789})

        expected_data = {"a": 123, "b": 456, "c": 777}
        self.assertEqual(self.device.get_config_context(), expected_data)

    def test_name_ordering_after_weight(self):
        ConfigContext.objects.create(name="context 2", weight=100, data={"a": 123, "b": 456, "c": 789})

        expected_data = {"a": 123, "b": 456, "c": 789}
        self.assertEqual(self.device.get_config_context(), expected_data)

    def test_name_uniqueness(self):
        """
        Verify that two ConfigContexts cannot share the same name (GitHub issue #431).
        """
        with self.assertRaises(ValidationError):
            duplicate_context = ConfigContext(name="context 1", weight=200, data={"c": 666})
            duplicate_context.validated_save()

        # If a different context is owned by a GitRepository, it's still considered a duplicate as of 2.0
        repo = GitRepository(
            name="Test Git Repository",
            slug="test_git_repo",
            remote_url="http://localhost/git.git",
        )
        repo.validated_save()

        with self.assertRaises(ValidationError):
            nonduplicate_context = ConfigContext(name="context 1", weight=300, data={"a": "22"}, owner=repo)
            nonduplicate_context.validated_save()

    def test_annotation_same_as_get_for_object(self):
        """
        This test incorporates features from all of the above tests cases to ensure
        the annotate_config_context_data() and get_for_object() queryset methods are the same.
        """
        ConfigContext.objects.create(name="context 2", weight=99, data={"a": 123, "b": 456, "c": 789})
        ConfigContext.objects.create(name="context 3", weight=98, data={"d": 1})
        ConfigContext.objects.create(name="context 4", weight=98, data={"d": 2})

        annotated_queryset = Device.objects.filter(name=self.device.name).annotate_config_context_data()
        self.assertEqual(self.device.get_config_context(), annotated_queryset[0].get_config_context())

    def test_annotation_same_as_get_for_object_device_relations(self):
        location_context = ConfigContext.objects.create(name="location", weight=100, data={"location": 1})
        location_context.locations.add(self.location)
        platform_context = ConfigContext.objects.create(name="platform", weight=100, data={"platform": 1})
        platform_context.platforms.add(self.platform)
        tenant_group_context = ConfigContext.objects.create(name="tenant group", weight=100, data={"tenant_group": 1})
        tenant_group_context.tenant_groups.add(self.tenantgroup)
        tenant_context = ConfigContext.objects.create(name="tenant", weight=100, data={"tenant": 1})
        tenant_context.tenants.add(self.tenant)
        tag_context = ConfigContext.objects.create(name="tag", weight=100, data={"tag": 1})
        tag_context.tags.add(self.tag)
        dynamic_group_context = ConfigContext.objects.create(
            name="dynamic group", weight=100, data={"dynamic_group": 1}
        )
        dynamic_group_context.dynamic_groups.add(self.dynamic_groups)

        device = Device.objects.create(
            name="Device 2",
            location=self.location,
            tenant=self.tenant,
            platform=self.platform,
            role=self.devicerole,
            status=self.device_status,
            device_type=self.devicetype,
        )
        device.tags.add(self.tag)

        annotated_queryset = Device.objects.filter(name=device.name).annotate_config_context_data()
        device_context = device.get_config_context()
        self.assertEqual(device_context, annotated_queryset[0].get_config_context())
        for key in ["location", "platform", "tenant_group", "tenant", "tag", "dynamic_group"]:
            self.assertIn(key, device_context)
        # Add a device type constraint that does not match the device in question to the location config context
        # And make sure that location_context is not applied to it anymore.
        no_match_device_type = DeviceType.objects.exclude(pk=self.devicetype.pk).first()
        location_context.device_types.add(no_match_device_type)
        device_context = device.get_config_context()
        self.assertNotIn("location", device_context)

    def test_annotation_same_as_get_for_object_device_relations_in_child_locations(self):
        location_context = ConfigContext.objects.create(name="root-location", weight=100, data={"location-1": 1})
        location_context.locations.add(self.root_location)
        location_context = ConfigContext.objects.create(name="parent-location", weight=100, data={"location-2": 2})
        location_context.locations.add(self.parent_location)
        location_context = ConfigContext.objects.create(name="location", weight=100, data={"location-3": 3})
        location_context.locations.add(self.location)
        device = Device.objects.create(
            name="Child Location Device",
            location=self.location,
            role=self.devicerole,
            status=self.device_status,
            device_type=self.devicetype,
        )

        device_context = device.get_config_context()
        annotated_queryset = Device.objects.filter(name=device.name).annotate_config_context_data()
        self.assertEqual(device_context, annotated_queryset[0].get_config_context())

        for key in ["location-1", "location-2", "location-3"]:
            self.assertIn(key, device_context)

    def test_annotation_same_as_get_for_object_device_relations_in_child_tenant_groups(self):
        tenant_group_context = ConfigContext.objects.create(
            name="parent_tenant_group", weight=100, data={"parent-group-1": 1}
        )
        tenant_group_context.tenant_groups.add(self.parent_tenantgroup)
        tenant_group_context = ConfigContext.objects.create(
            name="child_tenant_group", weight=100, data={"child-group-1": 2}
        )
        tenant_group_context.tenant_groups.add(self.child_tenantgroup)
        tenant_context = ConfigContext.objects.create(name="child_tenant", weight=100, data={"child-tenant-1": 3})
        tenant_context.tenants.add(self.child_tenant)
        device = Device.objects.create(
            name="Child Tenant Device",
            location=self.location,
            role=self.devicerole,
            status=self.device_status,
            device_type=self.devicetype,
            tenant=self.child_tenant,
        )

        device_context = device.get_config_context()
        annotated_queryset = Device.objects.filter(name=device.name).annotate_config_context_data()
        self.assertEqual(device_context, annotated_queryset[0].get_config_context())

        for key in ["parent-group-1", "child-group-1", "child-tenant-1"]:
            self.assertIn(key, device_context)

    def test_annotation_same_as_get_for_object_virtualmachine_relations(self):
        location_context = ConfigContext.objects.create(name="location", weight=100, data={"location": 1})
        location_context.locations.add(self.location)
        platform_context = ConfigContext.objects.create(name="platform", weight=100, data={"platform": 1})
        platform_context.platforms.add(self.platform)
        tenant_group_context = ConfigContext.objects.create(name="tenant group", weight=100, data={"tenant_group": 1})
        tenant_group_context.tenant_groups.add(self.tenantgroup)
        tenant_context = ConfigContext.objects.create(name="tenant", weight=100, data={"tenant": 1})
        tenant_context.tenants.add(self.tenant)
        tag_context = ConfigContext.objects.create(name="tag", weight=100, data={"tag": 1})
        tag_context.tags.add(self.tag)
        cluster_group = ClusterGroup.objects.create(name="Cluster Group")
        cluster_group_context = ConfigContext.objects.create(
            name="cluster group", weight=100, data={"cluster_group": 1}
        )
        cluster_group_context.cluster_groups.add(cluster_group)
        cluster_type = ClusterType.objects.create(name="Cluster Type 1")
        cluster = Cluster.objects.create(
            name="Cluster",
            cluster_group=cluster_group,
            cluster_type=cluster_type,
            location=self.location,
            tenant=self.tenant,
        )
        cluster_context = ConfigContext.objects.create(name="cluster", weight=100, data={"cluster": 1})
        cluster_context.clusters.add(cluster)
        dynamic_group_context = ConfigContext.objects.create(
            name="vm dynamic group", weight=100, data={"vm_dynamic_group": 1}
        )
        dynamic_group_context.dynamic_groups.add(self.vm_dynamic_group)

        vm_status = Status.objects.get_for_model(VirtualMachine).first()
        virtual_machine = VirtualMachine.objects.create(
            name="VM 1",
            cluster=cluster,
            tenant=self.tenant,
            platform=self.platform,
            role=self.devicerole,
            status=vm_status,
        )
        virtual_machine.tags.add(self.tag)

        annotated_queryset = VirtualMachine.objects.filter(name=virtual_machine.name).annotate_config_context_data()
        vm_context = virtual_machine.get_config_context()

        self.assertEqual(vm_context, annotated_queryset[0].get_config_context())
        for key in [
            "location",
            "platform",
            "tenant_group",
            "tenant",
            "tag",
            "cluster_group",
            "cluster",
            "vm_dynamic_group",
        ]:
            self.assertIn(key, vm_context)
        # Add a platform constraint that does not match the device in question to the location config context
        # And make sure that location_context is not applied to it anymore.
        no_match_platform = Platform.objects.exclude(pk=self.platform.pk).first()
        location_context.platforms.add(no_match_platform)
        device_context = virtual_machine.get_config_context()
        self.assertNotIn("location", device_context)

    def test_annotation_same_as_get_for_object_virtualmachine_relations_in_child_locations(self):
        location_context = ConfigContext.objects.create(name="root-location", weight=100, data={"location-1": 1})
        location_context.locations.add(self.root_location)
        location_context = ConfigContext.objects.create(name="parent-location", weight=100, data={"location-2": 2})
        location_context.locations.add(self.parent_location)
        location_context = ConfigContext.objects.create(name="location", weight=100, data={"location-3": 3})
        location_context.locations.add(self.location)
        vm_status = Status.objects.get_for_model(VirtualMachine).first()
        cluster_group = ClusterGroup.objects.create(name="Cluster Group")
        cluster_type = ClusterType.objects.create(name="Cluster Type 1")
        cluster = Cluster.objects.create(
            name="Cluster",
            cluster_group=cluster_group,
            cluster_type=cluster_type,
            location=self.location,
        )
        virtual_machine = VirtualMachine.objects.create(
            name="Child Location VM",
            cluster=cluster,
            role=self.devicerole,
            status=vm_status,
        )

        annotated_queryset = VirtualMachine.objects.filter(name=virtual_machine.name).annotate_config_context_data()
        vm_context = virtual_machine.get_config_context()

        self.assertEqual(vm_context, annotated_queryset[0].get_config_context())

        for key in [
            "location-1",
            "location-2",
            "location-3",
        ]:
            self.assertIn(key, vm_context)

    def test_annotation_same_as_get_for_object_virtualmachine_relations_in_child_tenant_groups(self):
        tenant_group_context = ConfigContext.objects.create(
            name="parent_tenant_group", weight=100, data={"parent-group-1": 1}
        )
        tenant_group_context.tenant_groups.add(self.parent_tenantgroup)
        tenant_group_context = ConfigContext.objects.create(
            name="child_tenant_group", weight=200, data={"child-group-1": 2}
        )
        tenant_group_context.tenant_groups.add(self.child_tenantgroup)
        tenant_context = ConfigContext.objects.create(name="child_tenant", weight=300, data={"child-tenant-1": 3})
        tenant_context.tenants.add(self.child_tenant)
        vm_status = Status.objects.get_for_model(VirtualMachine).first()
        cluster_group = ClusterGroup.objects.create(name="Cluster Group")
        cluster_type = ClusterType.objects.create(name="Cluster Type 1")
        cluster = Cluster.objects.create(
            name="Cluster",
            cluster_group=cluster_group,
            cluster_type=cluster_type,
            location=self.location,
        )
        virtual_machine = VirtualMachine.objects.create(
            name="Child Tenant VM",
            cluster=cluster,
            role=self.devicerole,
            status=vm_status,
            tenant=self.child_tenant,
        )

        annotated_queryset = VirtualMachine.objects.filter(name=virtual_machine.name).annotate_config_context_data()
        vm_context = virtual_machine.get_config_context()

        self.assertEqual(vm_context, annotated_queryset[0].get_config_context())

        for key in [
            "parent-group-1",
            "child-group-1",
            "child-tenant-1",
        ]:
            self.assertIn(key, vm_context)

    def test_multiple_tags_return_distinct_objects(self):
        """
        Tagged items use a generic relationship, which results in duplicate rows being returned when queried.
        This is combatted by by appending distinct() to the config context querysets. This test creates a config
        context assigned to two tags and ensures objects related by those same two tags result in only a single
        config context record being returned.

        See https://github.com/netbox-community/netbox/issues/5314
        """
        tag_context = ConfigContext.objects.create(name="tag", weight=100, data={"tag": 1})
        tag_context.tags.add(self.tag)
        tag_context.tags.add(self.tag2)

        device = Device.objects.create(
            name="Device 3",
            location=self.location,
            tenant=self.tenant,
            platform=self.platform,
            role=self.devicerole,
            status=self.device_status,
            device_type=self.devicetype,
        )
        device.tags.add(self.tag)
        device.tags.add(self.tag2)

        annotated_queryset = Device.objects.filter(name=device.name).annotate_config_context_data()
        self.assertEqual(ConfigContext.objects.get_for_object(device).count(), 2)  # including one from setUp()
        self.assertEqual(device.get_config_context(), annotated_queryset[0].get_config_context())

    def test_multiple_tags_return_distinct_objects_with_seperate_config_contexts(self):
        """
        Tagged items use a generic relationship, which results in duplicate rows being returned when queried.
        This is combatted by by appending distinct() to the config context querysets. This test creates a config
        context assigned to two tags and ensures objects related by those same two tags result in only a single
        config context record being returned.

        This test case is seperate from the above in that it deals with multiple config context objects in play.

        See https://github.com/netbox-community/netbox/issues/5387
        """
        tag_context_1 = ConfigContext.objects.create(name="tag-1", weight=100, data={"tag": 1})
        tag_context_1.tags.add(self.tag)
        tag_context_2 = ConfigContext.objects.create(name="tag-2", weight=100, data={"tag": 1})
        tag_context_2.tags.add(self.tag2)

        device = Device.objects.create(
            name="Device 3",
            location=self.location,
            tenant=self.tenant,
            platform=self.platform,
            role=self.devicerole,
            status=self.device_status,
            device_type=self.devicetype,
        )
        device.tags.add(self.tag)
        device.tags.add(self.tag2)

        annotated_queryset = Device.objects.filter(name=device.name).annotate_config_context_data()
        self.assertEqual(ConfigContext.objects.get_for_object(device).count(), 3)  # including one from setUp()
        self.assertEqual(device.get_config_context(), annotated_queryset[0].get_config_context())

    @override_settings(CONFIG_CONTEXT_DYNAMIC_GROUPS_ENABLED=True)
    def test_dynamic_group_assignment_uniqueness(self):
        """
        Assert that a Device in a given Dynamic Group with a Config Context associated to it
        does not have a Config Context applied that is associated to another Dynamic Group that
        the device is not a member of.
        """

        device2 = Device.objects.create(
            name="Device 2",
            location=self.location,
            tenant=self.tenant,
            platform=self.platform,
            role=self.devicerole,
            status=self.device_status,
            device_type=self.devicetype,
        )
        dynamic_group_context = ConfigContext.objects.create(
            name="dynamic context 1", weight=100, data={"dynamic_group": "dynamic context 1"}
        )
        dynamic_group_context_2 = ConfigContext.objects.create(
            name="dynamic context 2", weight=100, data={"dynamic_group": "dynamic context 2"}
        )
        dynamic_group_context.dynamic_groups.add(self.dynamic_groups)
        dynamic_group_context_2.dynamic_groups.add(self.dynamic_group_2)

        # Refresh caches
        self.dynamic_groups.update_cached_members()
        self.dynamic_group_2.update_cached_members()

        self.assertIn("dynamic context 1", self.device.get_config_context().values())
        self.assertNotIn("dynamic context 2", self.device.get_config_context().values())
        self.assertIn("dynamic context 2", device2.get_config_context().values())
        self.assertNotIn("dynamic context 1", device2.get_config_context().values())


class ConfigContextSchemaTestCase(ModelTestCases.BaseModelTestCase):
    """
    Tests for the ConfigContextSchema model
    """

    model = ConfigContextSchema

    def setUp(self):
        context_data = {"a": 123, "b": "456", "c": "10.7.7.7"}

        # Schemas
        self.schema_validation_pass = ConfigContextSchema.objects.create(
            name="schema-pass",
            data_schema={
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "a": {"type": "integer"},
                    "b": {"type": "string"},
                    "c": {"type": "string", "format": "ipv4"},
                },
            },
        )
        self.schemas_validation_fail = (
            ConfigContextSchema.objects.create(
                name="schema fail (wrong properties)",
                data_schema={
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {"foo": {"type": "string"}},
                },
            ),
            ConfigContextSchema.objects.create(
                name="schema fail (wrong type)",
                data_schema={"type": "object", "properties": {"b": {"type": "integer"}}},
            ),
            ConfigContextSchema.objects.create(
                name="schema fail (wrong format)",
                data_schema={"type": "object", "properties": {"b": {"type": "string", "format": "ipv4"}}},
            ),
        )

        # ConfigContext
        self.config_context = ConfigContext.objects.create(name="context 1", weight=101, data=context_data)

        # Device
        status = Status.objects.get_for_model(Device).first()
        location = Location.objects.filter(location_type=LocationType.objects.get(name="Campus")).first()
        manufacturer = Manufacturer.objects.first()
        device_type = DeviceType.objects.create(model="device_type", manufacturer=manufacturer)
        device_role = Role.objects.get_for_model(Device).first()
        self.device = Device.objects.create(
            name="device",
            location=location,
            device_type=device_type,
            role=device_role,
            status=status,
            local_config_context_data=context_data,
        )

        # Virtual Machine
        cluster_type = ClusterType.objects.create(name="Cluster Type 1")
        cluster = Cluster.objects.create(name="cluster", cluster_type=cluster_type)
        self.virtual_machine = VirtualMachine.objects.create(
            name="virtual_machine", cluster=cluster, status=status, local_config_context_data=context_data
        )

    def test_existing_config_context_valid_schema_applied(self):
        """
        Given an existing config context object
        And a config context schema object with a json schema
        And the config context context data is valid for the schema
        Assert calling clean on the config context object DOES NOT raise a ValidationError
        """
        self.config_context.config_context_schema = self.schema_validation_pass

        try:
            self.config_context.full_clean()
        except ValidationError:
            self.fail("self.config_context.full_clean() raised ValidationError unexpectedly!")

    def test_existing_config_context_invalid_schema_applied(self):
        """
        Given an existing config context object
        And a config context schema object with a json schema
        And the config context context data is NOT valid for the schema
        Assert calling clean on the config context object DOES raise a ValidationError
        """
        for schema in self.schemas_validation_fail:
            self.config_context.config_context_schema = schema

            with self.assertRaises(ValidationError):
                self.config_context.full_clean()

    def test_existing_config_context_with_no_schema_applied(self):
        """
        Given an existing config context object
        And no schema has been set on the config context object
        Assert calling clean on the config context object DOES NOT raise a ValidationError
        """
        try:
            self.config_context.full_clean()
        except ValidationError:
            self.fail("self.config_context.full_clean() raised ValidationError unexpectedly!")

    def test_existing_device_valid_schema_applied(self):
        """
        Given an existing device object with local_config_context_data
        And a config context schema object with a json schema
        And the device local_config_context_data is valid for the schema
        Assert calling clean on the device object DOES NOT raise a ValidationError
        """
        self.device.local_config_context_schema = self.schema_validation_pass

        try:
            self.device.full_clean()
        except ValidationError:
            self.fail("self.device.full_clean() raised ValidationError unexpectedly!")

    def test_existing_device_invalid_schema_applied(self):
        """
        Given an existing device object with local_config_context_data
        And a config context schema object with a json schema
        And the device local_config_context_data is NOT valid for the schema
        Assert calling clean on the device object DOES raise a ValidationError
        """
        for schema in self.schemas_validation_fail:
            self.device.local_config_context_schema = schema

            with self.assertRaises(ValidationError):
                self.device.full_clean()

    def test_existing_device_with_no_schema_applied(self):
        """
        Given an existing device object
        And no schema has been set on the device object
        Assert calling clean on the device object DOES NOT raise a ValidationError
        """
        try:
            self.device.full_clean()
        except ValidationError:
            self.fail("self.config_context.full_clean() raised ValidationError unexpectedly!")

    def test_existing_virtual_machine_valid_schema_applied(self):
        """
        Given an existing virtual machine object with local_config_context_data
        And a config context schema object with a json schema
        And the virtual machine local_config_context_data is valid for the schema
        Assert calling clean on the virtual machine object DOES NOT raise a ValidationError
        """
        self.virtual_machine.local_config_context_schema = self.schema_validation_pass

        try:
            self.virtual_machine.full_clean()
        except ValidationError:
            self.fail("self.virtual_machine.full_clean() raised ValidationError unexpectedly!")

    def test_existing_virtual_machine_invalid_schema_applied(self):
        """
        Given an existing virtual machine object with local_config_context_data
        And a config context schema object with a json schema
        And the virtual machine local_config_context_data is NOT valid for the schema
        Assert calling clean on the virtual machine object DOES raise a ValidationError
        """
        for schema in self.schemas_validation_fail:
            self.virtual_machine.local_config_context_schema = schema

            with self.assertRaises(ValidationError):
                self.virtual_machine.full_clean()

    def test_existing_virtual_machine_with_no_schema_applied(self):
        """
        Given an existing virtual machine object
        And no schema has been set on the virtual machine object
        Assert calling clean on the virtual machine object DOES NOT raise a ValidationError
        """
        try:
            self.virtual_machine.full_clean()
        except ValidationError:
            self.fail("self.config_context.full_clean() raised ValidationError unexpectedly!")

    def test_invalid_json_schema_is_not_allowed(self):
        """
        Given a config context schema object
        With an invalid JSON schema
        Assert calling clean on the config context schema object raises a ValidationError
        """
        invalid_schema = ConfigContextSchema(
            name="invalid", data_schema={"properties": {"this": "is not a valid json schema"}}
        )

        with self.assertRaises(ValidationError):
            invalid_schema.full_clean()

    def test_json_schema_must_be_an_object(self):
        """
        Given a config context schema object
        With a JSON schema of type object
        Assert calling clean on the config context schema object raises a ValidationError
        """
        invalid_schema = ConfigContextSchema(name="invalid", data_schema=["not an object"])

        with self.assertRaises(ValidationError):
            invalid_schema.full_clean()

    def test_json_schema_must_have_type_set_to_object(self):
        """
        Given a config context schema object
        With a JSON schema with type set to integer
        Assert calling clean on the config context schema object raises a ValidationError
        """
        invalid_schema = ConfigContextSchema(
            name="invalid", data_schema={"type": "integer", "properties": {"a": {"type": "string"}}}
        )

        with self.assertRaises(ValidationError):
            invalid_schema.full_clean()

    def test_json_schema_must_have_type_present(self):
        """
        Given a config context schema object
        With a JSON schema with type not present
        Assert calling clean on the config context schema object raises a ValidationError
        """
        invalid_schema = ConfigContextSchema(name="invalid", data_schema={"properties": {"a": {"type": "string"}}})

        with self.assertRaises(ValidationError):
            invalid_schema.full_clean()

    def test_json_schema_must_have_properties_present(self):
        """
        Given a config context schema object
        With a JSON schema with properties not present
        Assert calling clean on the config context schema object raises a ValidationError
        """
        invalid_schema = ConfigContextSchema(name="invalid", data_schema={"type": "object"})

        with self.assertRaises(ValidationError):
            invalid_schema.full_clean()


class ExportTemplateTest(ModelTestCases.BaseModelTestCase):
    """
    Tests for the ExportTemplate model class.
    """

    model = ExportTemplate

    def setUp(self):
        self.device_ct = ContentType.objects.get_for_model(Device)
        ExportTemplate.objects.create(
            content_type=self.device_ct, name="Export Template 1", template_code="hello world"
        )

    def test_name_contenttype_uniqueness(self):
        """
        The pair of (name, content_type) must be unique for an ExportTemplate.

        See GitHub issue #431.
        """
        with self.assertRaises(ValidationError):
            duplicate_template = ExportTemplate(
                content_type=self.device_ct, name="Export Template 1", template_code="foo"
            )
            duplicate_template.validated_save()

        # A differently owned ExportTemplate may not have the same name as of 2.0.
        repo = GitRepository(
            name="Test Git Repository",
            slug="test_git_repo",
            remote_url="http://localhost/git.git",
        )
        repo.validated_save()

        with self.assertRaises(ValidationError):
            nonduplicate_template = ExportTemplate(
                content_type=self.device_ct, name="Export Template 1", owner=repo, template_code="bar"
            )
            nonduplicate_template.validated_save()


class ExternalIntegrationTest(ModelTestCases.BaseModelTestCase):
    """
    Tests for the ExternalIntegration model class.
    """

    model = ExternalIntegration

    def test_remote_url_validation(self):
        with self.assertRaises(ValidationError):
            ei = ExternalIntegration(
                name="Test Integration",
                remote_url="foo://localhost",
            )
            ei.validated_save()

        ei.remote_url = "http://some-local-host"
        ei.validated_save()

    def test_timeout_validation(self):
        with self.assertRaises(ValidationError):
            ei = ExternalIntegration(
                name="Test Integration",
                remote_url="http://localhost",
                timeout=-1,
            )
            ei.validated_save()

        ei.timeout = 0
        ei.validated_save()
        ei.timeout = 65536
        ei.validated_save()

    def test_render_extra_config(self):
        ei_with_extra_config = ExternalIntegration.objects.filter(extra_config__isnull=False)
        ei_without_extra_config = ExternalIntegration.objects.filter(extra_config__isnull=True)
        ei = ei_with_extra_config.first()
        self.assertEqual(
            ei.render_extra_config({}),
            ei.extra_config,
        )
        self.assertEqual(
            ei_without_extra_config.first().render_extra_config({}),
            {},
        )
        # Data gets substituted correctly
        ei.extra_config = {"config": "{{ data }}"}
        ei.save()
        context = {"data": "extra_config_data"}
        self.assertEqual(ei.render_extra_config(context), {"config": "extra_config_data"})
        # Invalid template tag
        ei.extra_config = {"context": "{% foo %}"}
        ei.save()
        with self.assertRaises(TemplateSyntaxError):
            ei.render_extra_config({})
        # Invalid template helper
        ei.extra_config = "{{ data | notvalid }}"
        ei.save()
        with self.assertRaises(TemplateAssertionError):
            ei.render_extra_config({})

    def test_render_headers(self):
        ei_with_headers = ExternalIntegration.objects.filter(headers__isnull=False)
        ei_without_headers = ExternalIntegration.objects.filter(headers__isnull=True)
        ei = ei_with_headers.first()
        self.assertEqual(
            ei.render_headers({}),
            ei.headers,
        )
        self.assertEqual(
            ei_without_headers.first().render_headers({}),
            {},
        )
        # Data gets substituted correctly
        ei.headers = {"headers": "{{ data }}"}
        ei.save()
        context = {"data": "headers_data"}
        self.assertEqual(ei.render_headers(context), {"headers": "headers_data"})
        # Invalid template tag
        ei.headers = {"context": "{% foo %}"}
        ei.save()
        with self.assertRaises(TemplateSyntaxError):
            ei.render_headers({})
        # Invalid template helper
        ei.headers = "{{ data | notvalid }}"
        ei.save()
        with self.assertRaises(TemplateAssertionError):
            ei.render_headers({})


class FileProxyTest(ModelTestCases.BaseModelTestCase):
    model = FileProxy

    def setUp(self):
        self.test_file = SimpleUploadedFile(name="test_file.txt", content=b"I am content.\n")
        self.fp = FileProxy.objects.create(name=self.test_file.name, file=self.test_file)

    @expectedFailure
    def test_get_docs_url(self):
        """Not a user-facing model, so no get_docs_url() return value is expected."""
        super().test_get_docs_url()

    def test_create_file_proxy(self):
        """Test creation of `FileProxy` object."""

        # Now refresh it and make sure it was saved and retrieved correctly.
        self.fp.refresh_from_db()
        self.test_file.seek(0)  # Reset cursor since it was previously read
        self.assertEqual(self.fp.name, self.test_file.name)
        self.assertEqual(self.fp.file.read(), self.test_file.read())

    def test_delete_file_proxy(self):
        """Test deletion of `FileProxy` object."""
        # Assert counts before delete
        self.assertEqual(FileProxy.objects.count(), 1)
        self.assertEqual(FileAttachment.objects.count(), 1)

        # Assert counts after delete
        self.fp.delete()
        self.assertEqual(FileProxy.objects.count(), 0)
        self.assertEqual(FileAttachment.objects.count(), 0)

    def test_natural_key_symmetry(self):
        """Test FileAttachment as well as FileProxy."""
        super().test_natural_key_symmetry()
        instance = FileAttachment.objects.first()
        self.assertIsNotNone(instance)
        self.assertIsNotNone(instance.natural_key())
        self.assertEqual(FileAttachment.objects.get_by_natural_key(*instance.natural_key()), instance)


class GitRepositoryTest(ModelTestCases.BaseModelTestCase):
    """
    Tests for the GitRepository model class.
    """

    model = GitRepository

    def setUp(self):
        self.repo = GitRepository(
            name="Test Git Repository",
            slug="test_git_repo",
            remote_url="http://localhost/git.git",
        )
        self.repo.validated_save()

    def test_filesystem_path(self):
        self.assertEqual(self.repo.filesystem_path, os.path.join(settings.GIT_ROOT, self.repo.slug))

    def test_slug_no_change(self):
        """Confirm that a slug cannot be changed after creation."""
        self.repo.slug = "a_different_slug"
        with self.assertRaises(ValidationError):
            self.repo.validated_save()

    def test_no_module_clobbering(self):
        """Confirm that a slug that shadows an existing Python module is safely rejected."""
        repo = GitRepository(name=":sus:", slug="nautobot", remote_url="http://localhost/git.git")
        with self.assertRaises(ValidationError) as handler:
            repo.validated_save()
        self.assertIn("Please choose a different slug", str(handler.exception))

        repo.slug = "sys"
        with self.assertRaises(ValidationError) as handler:
            repo.validated_save()
        self.assertIn("Please choose a different slug", str(handler.exception))

        # How about part of the stdlib that we don't normally load?
        repo.slug = "tkinter"
        with self.assertRaises(ValidationError) as handler:
            repo.validated_save()
        self.assertIn("Please choose a different slug", str(handler.exception))

    def test_remote_url_hostname(self):
        """Confirm that a bare hostname (no domain name) can be used for a remote URL."""
        self.repo.remote_url = "http://some-private-host/example.git"
        self.repo.validated_save()

    def test_clone_to_directory_context_manager(self):
        """Confirm that the clone_to_directory_context() context manager method works as expected."""
        try:
            specified_path = tempfile.mkdtemp()
            self.tempdir = tempfile.TemporaryDirectory()  # pylint: disable=consider-using-with
            create_and_populate_git_repository(self.tempdir.name, divergent_branch="divergent-branch")
            self.repo_slug = "new_git_repo"
            self.repo = GitRepository(
                name="New Git Repository",
                slug=self.repo_slug,
                remote_url="file://"
                + self.tempdir.name,  # file:// URLs aren't permitted normally, but very useful here!
                branch="main",
                # Provide everything we know we can provide
                provided_contents=[
                    entry.content_identifier for entry in get_datasource_contents("extras.gitrepository")
                ],
            )
            self.repo.save()
            with self.subTest("Clone a repository with no path argument provided"):
                with self.repo.clone_to_directory_context() as path:
                    # assert that the temporary directory was created in the expected location i.e. /tmp/
                    self.assertTrue(path.startswith(tempfile.gettempdir()))
                    self.assertTrue(os.path.exists(path))
                    self.assertTrue(os.path.exists(path + "/config_context_schemas/badschema1.json"))
                    self.assertTrue(os.path.exists(path + "/config_context_schemas/badschema2.json"))
                self.assertFalse(os.path.exists(path))

            with self.subTest("Clone a repository with a path argument provided"):
                with self.repo.clone_to_directory_context(path=specified_path) as path:
                    # assert that the temporary directory was created in the expected location i.e. /tmp/
                    self.assertTrue(path.startswith(specified_path))
                    self.assertTrue(os.path.exists(path))
                    self.assertTrue(os.path.exists(path + "/config_context_schemas/badschema1.json"))
                    self.assertTrue(os.path.exists(path + "/config_context_schemas/badschema2.json"))
                # Temp directory is cleaned up after the context manager exits
                self.assertFalse(os.path.exists(path))

            with self.subTest("Clone a repository with the branch argument provided"):
                with self.repo.clone_to_directory_context(path=specified_path, branch="main") as path:
                    # assert that the temporary directory was created in the expected location i.e. /tmp/
                    self.assertTrue(path.startswith(specified_path))
                    self.assertTrue(os.path.exists(path))
                    self.assertTrue(os.path.exists(path + "/config_context_schemas/badschema1.json"))
                    self.assertTrue(os.path.exists(path + "/config_context_schemas/badschema2.json"))
                # Temp directory is cleaned up after the context manager exits
                self.assertFalse(os.path.exists(path))

            with self.subTest("Clone a repository with non-default branch provided"):
                with self.repo.clone_to_directory_context(path=specified_path, branch="empty-repo") as path:
                    # assert that the temporary directory was created in the expected location i.e. /tmp/
                    self.assertTrue(path.startswith(specified_path))
                    self.assertTrue(os.path.exists(path))
                    # empty-repo should contain no files
                    self.assertFalse(os.path.exists(path + "/config_context_schemas"))
                    self.assertFalse(os.path.exists(path + "/config_contexts"))
                # Temp directory is cleaned up after the context manager exits
                self.assertFalse(os.path.exists(path))

            with self.subTest("Clone a repository with divergent branch provided"):
                with self.repo.clone_to_directory_context(path=specified_path, branch="divergent-branch") as path:
                    # assert that the temporary directory was created in the expected location i.e. /tmp/
                    self.assertTrue(path.startswith(specified_path))
                    self.assertTrue(os.path.exists(path))
                    self.assertTrue(os.path.exists(path + "/config_context_schemas/badschema1.json"))
                    self.assertTrue(os.path.exists(path + "/config_context_schemas/badschema2.json"))
                # Temp directory is cleaned up after the context manager exits
                self.assertFalse(os.path.exists(path))

            with self.subTest("Clone a repository with the head argument provided"):
                with self.repo.clone_to_directory_context(path=specified_path, head="valid-files") as path:
                    # assert that the temporary directory was created in the expected location i.e. /tmp/
                    self.assertTrue(path.startswith(specified_path))
                    self.assertTrue(os.path.exists(path))
                    self.assertTrue(os.path.exists(path + "/config_context_schemas/schema-1.yaml"))
                    self.assertTrue(os.path.exists(path + "/config_contexts/context.yaml"))
                # Temp directory is cleaned up after the context manager exits
                self.assertFalse(os.path.exists(path))

            with self.subTest("Clone a repository with depth argument provided"):
                with self.repo.clone_to_directory_context(path=specified_path, depth=1) as path:
                    # assert that the temporary directory was created in the expected location i.e. /tmp/
                    self.assertTrue(path.startswith(specified_path))
                    self.assertTrue(os.path.exists(path))
                    self.assertTrue(os.path.exists(path + "/config_context_schemas/badschema1.json"))
                    self.assertTrue(os.path.exists(path + "/config_contexts/badcontext2.json"))
                # Temp directory is cleaned up after the context manager exits
                self.assertFalse(os.path.exists(path))

            with self.subTest("Clone a shallow repository with depth and valid head arguments provided"):
                with self.repo.clone_to_directory_context(
                    path=specified_path, depth=1, head="divergent-branch-tag"
                ) as path:
                    # assert that the temporary directory was created in the expected location i.e. /tmp/
                    self.assertTrue(path.startswith(specified_path))
                    self.assertTrue(os.path.exists(path))
                    self.assertTrue(os.path.exists(path + "/config_context_schemas/badschema1.json"))
                    self.assertTrue(os.path.exists(path + "/config_contexts/badcontext2.json"))
                # Temp directory is cleaned up after the context manager exits
                self.assertFalse(os.path.exists(path))

            with self.subTest("Clone a shallow repository with depth and invalid head arguments provided"):
                with self.assertRaisesRegex(GitCommandError, "malformed object name valid-files"):
                    # Shallow copy a repo should only have the latest commit
                    with self.repo.clone_to_directory_context(path=specified_path, depth=1, head="valid-files") as path:
                        pass

            with self.subTest("Clone a shallow repository with depth and valid branch arguments provided"):
                with self.repo.clone_to_directory_context(path=specified_path, depth=1, branch="main") as path:
                    # assert that the temporary directory was created in the expected location i.e. /tmp/
                    self.assertTrue(path.startswith(specified_path))
                    self.assertTrue(os.path.exists(path))
                    self.assertTrue(os.path.exists(path + "/config_context_schemas/badschema1.json"))
                    self.assertTrue(os.path.exists(path + "/config_contexts/badcontext2.json"))
                # Temp directory is cleaned up after the context manager exits
                self.assertFalse(os.path.exists(path))

            with self.subTest("Clone a shallow repository with depth and divergent branch arguments provided"):
                with self.repo.clone_to_directory_context(
                    path=specified_path, depth=1, branch="divergent-branch"
                ) as path:
                    # assert that the temporary directory was created in the expected location i.e. /tmp/
                    self.assertTrue(path.startswith(specified_path))
                    self.assertTrue(os.path.exists(path))
                    self.assertTrue(os.path.exists(path + "/config_context_schemas/badschema1.json"))
                    self.assertTrue(os.path.exists(path + "/config_contexts/badcontext2.json"))
                # Temp directory is cleaned up after the context manager exits
                self.assertFalse(os.path.exists(path))

            with self.subTest("Assert a GitCommandError is raised when an invalid commit hash is provided"):
                with self.assertRaisesRegex(GitCommandError, "malformed object name non-existent"):
                    with self.repo.clone_to_directory_context(path=specified_path, head="non-existent") as path:
                        pass

            with self.subTest("Assert a value error is raised when branch and head are both provided"):
                with self.assertRaisesRegex(ValueError, "Cannot specify both branch and head"):
                    with self.repo.clone_to_directory_context(branch="main", head="valid-files") as path:
                        pass
        finally:
            shutil.rmtree(specified_path, ignore_errors=True)
            shutil.rmtree(self.tempdir.name, ignore_errors=True)

    def test_clone_to_directory_helper_methods(self):
        """Confirm that the clone_to_directory()/cleanup_cloned_directory() methods work as expected."""
        try:
            specified_path = tempfile.mkdtemp()
            self.tempdir = tempfile.TemporaryDirectory()  # pylint: disable=consider-using-with
            create_and_populate_git_repository(self.tempdir.name, divergent_branch="divergent-branch")
            self.repo_slug = "new_git_repo"
            self.repo = GitRepository(
                name="New Git Repository",
                slug=self.repo_slug,
                remote_url="file://"
                + self.tempdir.name,  # file:// URLs aren't permitted normally, but very useful here!
                branch="main",
                # Provide everything we know we can provide
                provided_contents=[
                    entry.content_identifier for entry in get_datasource_contents("extras.gitrepository")
                ],
            )
            self.repo.save()
            with self.subTest("Clone a repository with no path argument provided"):
                path = self.repo.clone_to_directory()
                # assert that the temporary directory was created in the expected location i.e. /tmp/
                self.assertTrue(path.startswith(tempfile.gettempdir()))
                self.assertTrue(os.path.exists(path))
                self.assertTrue(os.path.exists(path + "/config_context_schemas/badschema1.json"))
                self.assertTrue(os.path.exists(path + "/config_context_schemas/badschema2.json"))
                self.repo.cleanup_cloned_directory(path)
                self.assertFalse(os.path.exists(path))

            with self.subTest("Clone a repository with a path argument provided"):
                path = self.repo.clone_to_directory(path=specified_path)
                # assert that the temporary directory was created in the expected location i.e. /tmp/
                self.assertTrue(path.startswith(specified_path))
                self.assertTrue(os.path.exists(path))
                self.assertTrue(os.path.exists(path + "/config_context_schemas/badschema1.json"))
                self.assertTrue(os.path.exists(path + "/config_context_schemas/badschema2.json"))
                self.repo.cleanup_cloned_directory(path)
                self.assertFalse(os.path.exists(path))

            with self.subTest("Clone a repository with the branch argument provided"):
                path = self.repo.clone_to_directory(path=specified_path, branch="main")
                # assert that the temporary directory was created in the expected location i.e. /tmp/
                self.assertTrue(path.startswith(specified_path))
                self.assertTrue(os.path.exists(path))
                self.assertTrue(os.path.exists(path + "/config_context_schemas/badschema1.json"))
                self.assertTrue(os.path.exists(path + "/config_context_schemas/badschema2.json"))
                self.repo.cleanup_cloned_directory(path)
                self.assertFalse(os.path.exists(path))

            with self.subTest("Clone a repository with non-default branch provided"):
                path = self.repo.clone_to_directory(path=specified_path, branch="empty-repo")
                # assert that the temporary directory was created in the expected location i.e. /tmp/
                self.assertTrue(path.startswith(specified_path))
                self.assertTrue(os.path.exists(path))
                self.assertFalse(os.path.exists(path + "/config_context_schemas"))
                self.assertFalse(os.path.exists(path + "/config_contexts"))
                self.repo.cleanup_cloned_directory(path)
                self.assertFalse(os.path.exists(path))

            with self.subTest("Clone a repository with divergent branch provided"):
                path = self.repo.clone_to_directory(path=specified_path, branch="divergent-branch")
                # assert that the temporary directory was created in the expected location i.e. /tmp/
                self.assertTrue(path.startswith(specified_path))
                self.assertTrue(os.path.exists(path))
                self.assertTrue(os.path.exists(path + "/config_context_schemas"))
                self.assertTrue(os.path.exists(path + "/config_contexts"))
                self.repo.cleanup_cloned_directory(path)
                self.assertFalse(os.path.exists(path))

            with self.subTest("Clone a repository with the head argument provided"):
                path = self.repo.clone_to_directory(path=specified_path, head="valid-files")
                # assert that the temporary directory was created in the expected location i.e. /tmp/
                self.assertTrue(path.startswith(specified_path))
                self.assertTrue(os.path.exists(path))
                self.assertTrue(os.path.exists(path + "/config_context_schemas/schema-1.yaml"))
                self.assertTrue(os.path.exists(path + "/config_contexts/context.yaml"))
                self.repo.cleanup_cloned_directory(path)
                self.assertFalse(os.path.exists(path))

            with self.subTest("Clone a repository with depth argument provided"):
                path = self.repo.clone_to_directory(path=specified_path, depth=1)
                # assert that the temporary directory was created in the expected location i.e. /tmp/
                self.assertTrue(path.startswith(specified_path))
                self.assertTrue(os.path.exists(path))
                self.assertTrue(os.path.exists(path + "/config_context_schemas/badschema1.json"))
                self.assertTrue(os.path.exists(path + "/config_contexts/badcontext2.json"))
                self.repo.cleanup_cloned_directory(path)
                self.assertFalse(os.path.exists(path))

            with self.subTest("Clone a shallow repository with depth and valid head arguments provided"):
                path = self.repo.clone_to_directory(path=specified_path, depth=1, head="divergent-branch-tag")
                # assert that the temporary directory was created in the expected location i.e. /tmp/
                self.assertTrue(path.startswith(specified_path))
                self.assertTrue(os.path.exists(path))
                self.assertTrue(os.path.exists(path + "/config_context_schemas/badschema1.json"))
                self.assertTrue(os.path.exists(path + "/config_contexts/badcontext2.json"))
                self.repo.cleanup_cloned_directory(path)
                self.assertFalse(os.path.exists(path))

            with self.subTest("Clone a shallow repository with depth and invalid head arguments provided"):
                with self.assertRaisesRegex(GitCommandError, "malformed object name valid-files"):
                    # Shallow copy a repo should only have the latest commit
                    path = self.repo.clone_to_directory(path=specified_path, depth=1, head="valid-files")
                    self.repo.cleanup_cloned_directory(path)
                    self.assertFalse(os.path.exists(path))

            with self.subTest("Clone a shallow repository with depth and valid branch arguments provided"):
                path = self.repo.clone_to_directory(path=specified_path, depth=1, branch="main")
                # assert that the temporary directory was created in the expected location i.e. /tmp/
                self.assertTrue(path.startswith(specified_path))
                self.assertTrue(os.path.exists(path))
                self.assertTrue(os.path.exists(path + "/config_context_schemas/badschema1.json"))
                self.assertTrue(os.path.exists(path + "/config_contexts/badcontext2.json"))
                self.repo.cleanup_cloned_directory(path)
                self.assertFalse(os.path.exists(path))

            with self.subTest("Clone a shallow repository with depth and divergent branch arguments provided"):
                path = self.repo.clone_to_directory(path=specified_path, depth=1, branch="divergent-branch")
                # assert that the temporary directory was created in the expected location i.e. /tmp/
                self.assertTrue(path.startswith(specified_path))
                self.assertTrue(os.path.exists(path))
                self.assertTrue(os.path.exists(path + "/config_context_schemas/badschema1.json"))
                self.assertTrue(os.path.exists(path + "/config_contexts/badcontext2.json"))
                self.repo.cleanup_cloned_directory(path)
                self.assertFalse(os.path.exists(path))

            with self.subTest("Assert a GitCommandError is raised when an invalid commit hash is provided"):
                with self.assertRaisesRegex(GitCommandError, "malformed object name non-existent"):
                    path = self.repo.clone_to_directory(path=specified_path, head="non-existent")

            with self.subTest("Assert a ValuError is raised when branch and head are both provided"):
                with self.assertRaisesRegex(ValueError, "Cannot specify both branch and head"):
                    path = self.repo.clone_to_directory(branch="main", head="valid-files")
        finally:
            shutil.rmtree(specified_path, ignore_errors=True)
            shutil.rmtree(self.tempdir.name, ignore_errors=True)


class JobModelTest(ModelTestCases.BaseModelTestCase):
    """
    Tests for the `Job` model class.
    """

    model = JobModel

    @classmethod
    def setUpTestData(cls):
        # JobModel instances are automatically instantiated at startup, so we just need to look them up.
        cls.local_job = JobModel.objects.get(job_class_name="TestPassJob")
        cls.job_containing_sensitive_variables = JobModel.objects.get(job_class_name="TestHasSensitiveVariables")
        cls.app_job = JobModel.objects.get(job_class_name="ExampleJob")

    def test_job_class(self):
        self.assertIsNotNone(self.local_job.job_class)
        self.assertEqual(self.local_job.job_class.description, "Validate job import")

        self.assertIsNotNone(self.app_job.job_class)
        self.assertEqual(self.app_job.job_class, ExampleJob)

    def test_class_path(self):
        self.assertEqual(self.local_job.class_path, "pass_job.TestPassJob")
        self.assertIsNotNone(self.local_job.job_class)
        self.assertEqual(self.local_job.class_path, self.local_job.job_class.class_path)

        self.assertEqual(self.app_job.class_path, "example_app.jobs.ExampleJob")
        self.assertEqual(self.app_job.class_path, self.app_job.job_class.class_path)

    def test_latest_result(self):
        self.assertEqual(self.local_job.latest_result, self.local_job.job_results.only("status").first())
        self.assertEqual(self.app_job.latest_result, self.app_job.job_results.only("status").first())
        # TODO(Glenn): create some JobResults and test that this works correctly for them as well.

    def test_defaults(self):
        """Verify that defaults for discovered JobModel instances are as expected."""
        for job_model in JobModel.objects.all():
            with self.subTest(class_path=job_model.class_path):
                try:
                    self.assertTrue(job_model.installed)
                    # System jobs should be enabled by default, all others are disabled by default
                    if job_model.module_name.startswith("nautobot."):
                        self.assertTrue(job_model.enabled)
                    else:
                        self.assertFalse(job_model.enabled)
                    self.assertIsNotNone(job_model.job_class)
                    for field_name in JOB_OVERRIDABLE_FIELDS:
                        if field_name == "name" and "duplicate_name" in job_model.job_class.__module__:
                            pass  # name field for test_duplicate_name jobs tested in test_duplicate_job_name below
                        else:
                            self.assertFalse(
                                getattr(job_model, f"{field_name}_override"),
                                (field_name, getattr(job_model, field_name), getattr(job_model.job_class, field_name)),
                            )
                            self.assertEqual(
                                getattr(job_model, field_name),
                                getattr(job_model.job_class, field_name),
                                field_name,
                            )
                    if not job_model.job_queues_override:
                        self.assertEqual(
                            sorted(job_model.task_queues),
                            sorted(job_model.job_class.task_queues) or [settings.CELERY_TASK_DEFAULT_QUEUE],
                        )
                except AssertionError:
                    print(list(JobModel.objects.all()))
                    print(registry["jobs"])
                    raise

    def test_duplicate_job_name(self):
        self.assertTrue(JobModel.objects.filter(name="TestDuplicateNameNoMeta").exists())
        self.assertTrue(JobModel.objects.filter(name="TestDuplicateNameNoMeta (2)").exists())
        self.assertTrue(JobModel.objects.filter(name="This name is not unique.").exists())
        self.assertTrue(JobModel.objects.filter(name="This name is not unique. (2)").exists())

    def test_clean_overrides(self):
        """Verify that cleaning resets non-overridden fields to their appropriate default values."""

        overridden_attrs = {
            "grouping": "Overridden Grouping",
            "name": "Overridden Name",
            "description": "Overridden Description",
            "dryrun_default": not self.job_containing_sensitive_variables.dryrun_default,
            "hidden": not self.job_containing_sensitive_variables.hidden,
            "approval_required": not self.job_containing_sensitive_variables.approval_required,
            "has_sensitive_variables": not self.job_containing_sensitive_variables.has_sensitive_variables,
            "soft_time_limit": 350,
            "time_limit": 650,
        }

        # Override values to non-defaults and ensure they are preserved
        for field_name, value in overridden_attrs.items():
            setattr(self.job_containing_sensitive_variables, field_name, value)
            setattr(self.job_containing_sensitive_variables, f"{field_name}_override", True)
        self.job_containing_sensitive_variables.validated_save()
        self.job_containing_sensitive_variables.refresh_from_db()
        for field_name, value in overridden_attrs.items():
            self.assertEqual(getattr(self.job_containing_sensitive_variables, field_name), value)
            self.assertTrue(getattr(self.job_containing_sensitive_variables, f"{field_name}_override"))

        # Clear the "*_override" flags and ensure that cleaning resets the corresponding fields to non-overriden values
        for field_name in overridden_attrs:
            setattr(self.job_containing_sensitive_variables, f"{field_name}_override", False)
        self.job_containing_sensitive_variables.validated_save()
        self.job_containing_sensitive_variables.refresh_from_db()
        self.assertIsNotNone(self.job_containing_sensitive_variables.job_class)
        for field_name in overridden_attrs:
            self.assertEqual(
                getattr(self.job_containing_sensitive_variables, field_name),
                getattr(self.job_containing_sensitive_variables.job_class, field_name),
            )
            self.assertFalse(getattr(self.job_containing_sensitive_variables, f"{field_name}_override"))

    def test_clean_input_validation(self):
        """Verify that cleaning enforces validation of potentially unsanitized user input."""
        with self.assertRaises(ValidationError) as handler:
            JobModel(
                module_name="too_long_of_a_module_name.too_long_of_a_module_name.too_long_of_a_module_name.too_long_of_a_module_name.too_long_of_a_module_name",
                job_class_name="JobClass",
                grouping="grouping",
                name="name",
            ).clean()
        self.assertIn("Module name", str(handler.exception))

        with self.assertRaises(ValidationError) as handler:
            JobModel(
                module_name="module_name",
                job_class_name="ThisIsARidiculouslyLongJobClassNameWhoWouldEverDoSuchAnUtterlyRidiculousThingButBetterSafeThanSorrySinceWeAreDealingWithUserInputHere",
                grouping="grouping",
                name="name",
            ).clean()
        self.assertIn("Job class name", str(handler.exception))

        with self.assertRaises(ValidationError) as handler:
            JobModel(
                module_name="module_name",
                job_class_name="JobClassName",
                grouping="OK now this is just ridiculous. Why would you ever want to deal with typing in 255+ characters of grouping information and have to copy-paste it to the other jobs in the same grouping or risk dealing with typos when typing out such a ridiculously long grouping string? Still, once again, better safe than sorry!",
                name="name",
            ).clean()
        self.assertIn("Grouping", str(handler.exception))

        with self.assertRaises(ValidationError) as handler:
            JobModel(
                module_name="module_name",
                job_class_name="JobClassName",
                grouping="grouping",
                name="Similarly, let us hope that no one really wants to specify a job name that is over 100 characters long, it would be a pain to type at the very least and it won't look good in the UI either",
            ).clean()
        self.assertIn("Name", str(handler.exception))

        with self.assertRaises(ValidationError) as handler:
            JobModel(
                module_name="module_name",
                job_class_name="JobClassName",
                grouping="grouping",
                has_sensitive_variables=True,
                approval_required=True,
                name="Job Class Name",
            ).clean()
        self.assertEqual(
            handler.exception.message_dict["approval_required"][0],
            "A job that may have sensitive variables cannot be marked as requiring approval",
        )

    def test_default_job_queue_always_included_in_job_queues(self):
        default_job_queue = JobQueue.objects.first()
        job_queues = list(JobQueue.objects.exclude(pk=default_job_queue.pk))[:3]

        job = JobModel.objects.first()
        job.default_job_queue = default_job_queue
        job.save()
        job.job_queues.set(job_queues)

        self.assertTrue(job.job_queues.filter(pk=default_job_queue.pk).exists())


class JobQueueTest(ModelTestCases.BaseModelTestCase):
    """
    Tests for the `JobQueue` model class.
    """

    model = JobQueue


class MetadataChoiceTest(ModelTestCases.BaseModelTestCase):
    model = MetadataChoice

    def test_immutable_metadata_type(self):
        instance1 = MetadataChoice.objects.first()
        instance2 = MetadataChoice.objects.exclude(metadata_type=instance1.metadata_type).first()
        self.assertIsNotNone(instance2)
        with self.assertRaises(ValidationError):
            instance1.metadata_type = instance2.metadata_type
            instance1.validated_save()

    def test_wrong_metadata_type(self):
        with self.assertRaises(ValidationError):
            instance = MetadataChoice(
                metadata_type=MetadataType.objects.filter(data_type=MetadataTypeDataTypeChoices.TYPE_TEXT).first(),
                value="Hello",
                weight=100,
            )
            self.assertIsNotNone(instance.metadata_type)
            instance.validated_save()


class MetadataTypeTest(ModelTestCases.BaseModelTestCase):
    model = MetadataType

    def test_immutable_data_type(self):
        instance = MetadataType.objects.exclude(data_type=MetadataTypeDataTypeChoices.TYPE_TEXT).first()
        with self.assertRaises(ValidationError):
            instance.data_type = MetadataTypeDataTypeChoices.TYPE_TEXT
            instance.validated_save()


class ObjectChangeTest(ModelTestCases.BaseModelTestCase):
    model = ObjectChange

    @classmethod
    def setUpTestData(cls):
        location_oc = Location.objects.first().to_objectchange(ObjectChangeActionChoices.ACTION_UPDATE)
        location_oc.request_id = uuid.uuid4()
        location_oc.change_context = ObjectChangeEventContextChoices.CONTEXT_ORM
        location_oc.validated_save()

    def test_log(self):
        """Test that logs are rendered correctly."""
        jobs = JobModel.objects.all()[:2]
        job_result = JobResult.objects.create(
            name="irrelevant",
            job_model=jobs[0],
            date_done=now(),
            user=None,
            status=JobResultStatusChoices.STATUS_SUCCESS,
            task_kwargs={},
            scheduled_job=None,
        )
        job_result.use_job_logs_db = False

        # Most basic usage
        job_result.log("Hello")
        log = JobLogEntry.objects.get(job_result=job_result)
        self.assertEqual("Hello", log.message)
        self.assertEqual(LogLevelChoices.LOG_INFO, log.log_level)
        self.assertEqual("main", log.grouping)
        self.assertEqual("", log.log_object)
        self.assertEqual("", log.absolute_url)

        # Advanced usage
        obj = CircuitType.objects.create(name="Advance CT")
        job_result.log("Hi", obj=obj, level_choice=LogLevelChoices.LOG_WARNING, grouping="other")
        log = JobLogEntry.objects.get(job_result=job_result, message="Hi", log_object=obj)
        self.assertEqual("Hi", log.message)
        self.assertEqual(LogLevelChoices.LOG_WARNING, log.log_level)
        self.assertEqual("other", log.grouping)
        self.assertEqual(str(obj), log.log_object)
        self.assertEqual(obj.get_absolute_url(), log.absolute_url)

        # Length constraints
        class MockObject1:
            def __str__(self):
                return "a" * (JOB_LOG_MAX_LOG_OBJECT_LENGTH * 2)

            def get_absolute_url(self):
                return "b" * (JOB_LOG_MAX_ABSOLUTE_URL_LENGTH * 2)

        obj = MockObject1()
        job_result.log("Hi 1", obj=obj, grouping="c" * JOB_LOG_MAX_GROUPING_LENGTH * 2)
        log = JobLogEntry.objects.get(
            job_result=job_result, message="Hi 1", log_object="a" * JOB_LOG_MAX_LOG_OBJECT_LENGTH
        )
        self.assertEqual("Hi 1", log.message)
        self.assertEqual("a" * JOB_LOG_MAX_LOG_OBJECT_LENGTH, log.log_object)
        self.assertEqual("c" * JOB_LOG_MAX_GROUPING_LENGTH, log.grouping)
        self.assertEqual("b" * JOB_LOG_MAX_ABSOLUTE_URL_LENGTH, log.absolute_url)

        # Error handling
        class MockObject2(MockObject1):
            def get_absolute_url(self):
                raise NotImplementedError()

        obj = MockObject2()
        job_result.log("Hi 2", obj=obj)
        log = JobLogEntry.objects.get(job_result=job_result, message="Hi 2")
        self.assertEqual("Hi 2", log.message)
        self.assertEqual("a" * JOB_LOG_MAX_LOG_OBJECT_LENGTH, log.log_object)
        self.assertEqual("", log.absolute_url)


class ObjectMetadataTest(ModelTestCases.BaseModelTestCase):
    model = ObjectMetadata

    def test_immutable_metadata_type(self):
        instance1 = ObjectMetadata.objects.first()
        instance2 = ObjectMetadata.objects.exclude(metadata_type=instance1.metadata_type).first()
        self.assertIsNotNone(instance2)
        with self.assertRaises(ValidationError):
            instance1.metadata_type = instance2.metadata_type
            instance1.validated_save()

    def test_invalid_assigned_object_type_not_allowed(self):
        type_location = MetadataType.objects.create(
            name="Location Metadata Type", data_type=MetadataTypeDataTypeChoices.TYPE_TEXT
        )
        type_location.content_types.add(ContentType.objects.get_for_model(Location))
        with self.assertRaises(ValidationError):
            obj_metadata = ObjectMetadata.objects.create(
                metadata_type=type_location,
                value="Invalid assigned object type",
                scoped_fields=["status"],
                assigned_object_type=ContentType.objects.get_for_model(IPAddress),
                assigned_object_id=Contact.objects.filter(associated_object_metadata__isnull=True).first().pk,
            )
            obj_metadata.validated_save()

    def test_contact_team_mutual_exclusive(self):
        type_contact_team = MetadataType.objects.create(
            name="TCT", data_type=MetadataTypeDataTypeChoices.TYPE_CONTACT_TEAM
        )
        type_contact_team.content_types.add(ContentType.objects.get_for_model(Contact))
        type_contact_team.content_types.add(ContentType.objects.get_for_model(Team))
        instance1 = ObjectMetadata(
            metadata_type=type_contact_team,
            contact=Contact.objects.first(),
            team=Team.objects.first(),
            scoped_fields=["address"],
            assigned_object_type=ContentType.objects.get_for_model(Contact),
            assigned_object_id=Contact.objects.filter(associated_object_metadata__isnull=True).first().pk,
        )
        instance2 = ObjectMetadata(
            metadata_type=type_contact_team,
            contact=None,
            team=None,
            scoped_fields=["phone"],
            assigned_object_type=ContentType.objects.get_for_model(Contact),
            assigned_object_id=Contact.objects.filter(associated_object_metadata__isnull=True).last().pk,
        )
        instance3 = ObjectMetadata(
            metadata_type=type_contact_team,
            contact=Contact.objects.first(),
            team=None,
            scoped_fields=["email"],
            assigned_object_type=ContentType.objects.get_for_model(Team),
            assigned_object_id=Team.objects.filter(associated_object_metadata__isnull=True).first().pk,
        )
        with self.assertRaises(ValidationError):
            instance1.validated_save()

        with self.assertRaises(ValidationError):
            instance2.validated_save()

        with self.assertRaises(ValidationError):
            instance3.value = "Value should be empty"
            instance3.validated_save()

    def test_text_field_value(self):
        obj_type = ContentType.objects.get_for_model(Location)
        text_metadata_type = MetadataType.objects.filter(data_type=MetadataTypeDataTypeChoices.TYPE_TEXT).first()
        text_metadata_type.content_types.add(obj_type)

        # Create an ObjectMetadata
        obj_metadata = ObjectMetadata.objects.create(
            metadata_type=text_metadata_type,
            value="Some text value",
            scoped_fields=["status", "parent"],
            assigned_object_type=obj_type,
            assigned_object_id=Location.objects.filter(associated_object_metadata__isnull=True).first().pk,
        )
        obj_metadata.save()

        # Assign a disallowed value (list) to obj_metadata
        with self.assertRaises(ValidationError) as context:
            obj_metadata.value = ["I", "am", "a", "list"]
            obj_metadata.validated_save()
        self.assertIn("Value must be a string", str(context.exception))

        # Assign another disallowed value (int) to the first Location
        with self.assertRaises(ValidationError) as context:
            obj_metadata.value = 2
            obj_metadata.validated_save()
        self.assertIn("Value must be a string", str(context.exception))

        # Assign another disallowed value (bool) to the first Location
        with self.assertRaises(ValidationError) as context:
            obj_metadata.value = True
            obj_metadata.validated_save()
        self.assertIn("Value must be a string", str(context.exception))
        obj_metadata.delete()

    def test_integer_field_value(self):
        obj_type = ContentType.objects.get_for_model(Location)
        int_metadata_type = MetadataType.objects.filter(data_type=MetadataTypeDataTypeChoices.TYPE_INTEGER).first()
        int_metadata_type.content_types.add(obj_type)
        # Create an ObjectMetadata
        obj_metadata = ObjectMetadata.objects.create(
            metadata_type=int_metadata_type,
            value=15,
            scoped_fields=["status", "parent"],
            assigned_object_type=obj_type,
            assigned_object_id=Location.objects.filter(associated_object_metadata__isnull=True).first().pk,
        )
        obj_metadata.validated_save()

        # Assign another disallowed value (str) to the first Location
        with self.assertRaises(ValidationError) as context:
            obj_metadata.value = "I am not an integer"
            obj_metadata.validated_save()
        self.assertIn("Value must be an integer", str(context.exception))
        # Assign another disallowed value (str of a float) to the first Location
        with self.assertRaises(ValidationError) as context:
            obj_metadata.value = "2.0"
            obj_metadata.validated_save()
        self.assertIn("Value must be an integer", str(context.exception))

        obj_metadata.value = 2.0
        obj_metadata.validated_save()
        self.assertEqual(obj_metadata.value, 2)
        obj_metadata.value = 15.0
        obj_metadata.validated_save()
        self.assertEqual(obj_metadata.value, 15)
        obj_metadata.value = 15.2
        obj_metadata.validated_save()
        self.assertEqual(obj_metadata.value, 15)
        obj_metadata.value = 15
        obj_metadata.validated_save()
        self.assertEqual(obj_metadata.value, 15)
        obj_metadata.value = "15"
        obj_metadata.validated_save()
        self.assertEqual(obj_metadata.value, 15)

        # TODO add validation_minimum/validation_maximum tests
        obj_metadata.delete()

    def test_float_field_value(self):
        obj_type = ContentType.objects.get_for_model(Location)
        float_metadata_type = MetadataType.objects.filter(data_type=MetadataTypeDataTypeChoices.TYPE_FLOAT).first()
        float_metadata_type.content_types.add(obj_type)
        # Create an ObjectMetadata
        obj_metadata = ObjectMetadata.objects.create(
            metadata_type=float_metadata_type,
            value=15.245,
            scoped_fields=["status", "parent"],
            assigned_object_type=obj_type,
            assigned_object_id=Location.objects.filter(associated_object_metadata__isnull=True).first().pk,
        )
        obj_metadata.validated_save()

        # Assign another disallowed value (str) to the first Location
        with self.assertRaises(ValidationError) as context:
            obj_metadata.value = "I am not a float"
            obj_metadata.validated_save()
        self.assertIn("Value must be a float", str(context.exception))

        # Assign another disallowed value (int) to the first Location
        obj_metadata.value = 2
        obj_metadata.validated_save()
        self.assertEqual(obj_metadata.value, 2.0)
        obj_metadata.value = 15
        obj_metadata.validated_save()
        self.assertEqual(obj_metadata.value, 15.0)
        obj_metadata.value = 15.2
        obj_metadata.validated_save()
        self.assertEqual(obj_metadata.value, 15.2)
        obj_metadata.value = "3"
        obj_metadata.validated_save()
        self.assertEqual(obj_metadata.value, 3.0)
        obj_metadata.value = "15.2"
        obj_metadata.validated_save()
        self.assertEqual(obj_metadata.value, 15.2)

        # TODO add validation_minimum/validation_maximum tests
        obj_metadata.delete()

    def test_boolean_field_value(self):
        obj_type = ContentType.objects.get_for_model(Location)
        bool_metadata_type = MetadataType.objects.filter(data_type=MetadataTypeDataTypeChoices.TYPE_BOOLEAN).first()
        bool_metadata_type.content_types.add(obj_type)

        # Create an ObjectMetadata
        obj_metadata = ObjectMetadata.objects.create(
            metadata_type=bool_metadata_type,
            value=False,
            scoped_fields=["status", "parent"],
            assigned_object_type=obj_type,
            assigned_object_id=Location.objects.filter(associated_object_metadata__isnull=True).first().pk,
        )
        obj_metadata.validated_save()

        # Assign a disallowed value (list) to obj_metadata
        with self.assertRaises(ValidationError) as context:
            obj_metadata.value = ["I", "am", "a", "list"]
            obj_metadata.validated_save()
        self.assertIn("Value must be true or false.", str(context.exception))

        # Assign another disallowed value (str) to the first Location
        with self.assertRaises(ValidationError) as context:
            obj_metadata.value = "I am not an integer"
            obj_metadata.validated_save()
        self.assertIn("Value must be true or false.", str(context.exception))

        # Assign another disallowed value (int) to the first Location
        with self.assertRaises(ValidationError) as context:
            obj_metadata.value = 2
            obj_metadata.validated_save()
        self.assertIn("Value must be true or false.", str(context.exception))
        obj_metadata.delete()

    def test_date_field_value(self):
        obj_type = ContentType.objects.get_for_model(Location)
        date_metadata_type = MetadataType.objects.filter(data_type=MetadataTypeDataTypeChoices.TYPE_DATE).first()
        date_metadata_type.content_types.add(obj_type)

        # Create an ObjectMetadata
        obj_metadata = ObjectMetadata.objects.create(
            metadata_type=date_metadata_type,
            value="1994-01-01",
            scoped_fields=["status", "parent"],
            assigned_object_type=obj_type,
            assigned_object_id=Location.objects.filter(associated_object_metadata__isnull=True).first().pk,
        )
        obj_metadata.validated_save()

        # Assign a disallowed value (invalidly formatted date) to obj_metadata
        with self.assertRaises(ValidationError) as context:
            obj_metadata.value = "01/01/1994"
            obj_metadata.validated_save()
        self.assertIn("Date values must be in the format YYYY-MM-DD.", str(context.exception))

        # Assign another disallowed value (str) to the first Location
        with self.assertRaises(ValidationError) as context:
            obj_metadata.value = "I am not an integer"
            obj_metadata.validated_save()
        self.assertIn("Date values must be in the format YYYY-MM-DD.", str(context.exception))

        # Assign another disallowed value (int) to the first Location
        with self.assertRaises(ValidationError) as context:
            obj_metadata.value = 2
            obj_metadata.validated_save()
        self.assertIn("Value must be a date or str object.", str(context.exception))
        # TODO add validation_minimum/validation_maximum tests
        obj_metadata.delete()

    def test_datetime_field_value(self):
        obj_type = ContentType.objects.get_for_model(Location)
        datetime_metadata_type = MetadataType.objects.filter(
            data_type=MetadataTypeDataTypeChoices.TYPE_DATETIME
        ).first()
        datetime_metadata_type.content_types.add(obj_type)

        # Create an ObjectMetadata
        obj_metadata = ObjectMetadata.objects.create(
            metadata_type=datetime_metadata_type,
            value="2024-06-27T17:58:47-0500",
            scoped_fields=["status", "parent"],
            assigned_object_type=obj_type,
            assigned_object_id=Location.objects.filter(associated_object_metadata__isnull=True).first().pk,
        )
        obj_metadata.validated_save()

        # Test valid formats of datetime value
        acceptable_datetime_formats = [
            "YYYY-MM-DDTHH:MM:SS",
            "YYYY-MM-DDTHH:MM:SS(+,-)zzzz",
            "YYYY-MM-DDTHH:MM:SS(+,-)zz:zz",
        ]
        obj_metadata.value = "2024-06-27T17:58:47"
        obj_metadata.validated_save()
        self.assertEqual(obj_metadata.value, "2024-06-27T17:58:47+0000")
        obj_metadata.value = "2024-06-27T17:58:47+0500"
        obj_metadata.validated_save()
        self.assertEqual(obj_metadata.value, "2024-06-27T17:58:47+0500")
        obj_metadata.value = "2024-06-27T17:58:47+05:00"
        obj_metadata.validated_save()
        self.assertEqual(obj_metadata.value, "2024-06-27T17:58:47+05:00")
        obj_metadata.value = datetime(2020, 11, 1, 1)
        obj_metadata.validated_save()
        self.assertEqual(obj_metadata.value, "2020-11-01T01:00:00+00:00")
        obj_metadata.value = datetime(2020, 11, 1, 1, 35, 22)
        obj_metadata.validated_save()
        self.assertEqual(obj_metadata.value, "2020-11-01T01:35:22+00:00")
        obj_metadata.value = datetime(2020, 11, 1, 1, 35, 22, tzinfo=timezone(timedelta(hours=3)))
        obj_metadata.validated_save()
        self.assertEqual(obj_metadata.value, "2020-11-01T01:35:22+03:00")

        error_message = f"Datetime values must be in the following formats {acceptable_datetime_formats}"
        with self.assertRaises(ValidationError) as context:
            obj_metadata.value = "01/01/1994"
            obj_metadata.validated_save()
        self.assertIn(error_message, str(context.exception))
        with self.assertRaises(ValidationError) as context:
            obj_metadata.value = "2024-06-27 17:58:47+0000"
            obj_metadata.validated_save()
        self.assertIn(error_message, str(context.exception))

        with self.assertRaises(ValidationError) as context:
            obj_metadata.value = "I am not an integer"
            obj_metadata.validated_save()
        self.assertIn(error_message, str(context.exception))

        with self.assertRaises(ValidationError) as context:
            obj_metadata.value = 2
            obj_metadata.validated_save()
        self.assertIn("Value must be a datetime or str object", str(context.exception))

        # TODO add validation_minimum/validation_maximum tests
        obj_metadata.delete()

    def test_select_field(self):
        obj_type = ContentType.objects.get_for_model(Location)
        select_metadata_type = MetadataType.objects.filter(data_type=MetadataTypeDataTypeChoices.TYPE_SELECT).first()
        select_metadata_type.content_types.add(obj_type)

        MetadataChoice.objects.create(metadata_type=select_metadata_type, value="Option A")
        MetadataChoice.objects.create(metadata_type=select_metadata_type, value="Option B")
        MetadataChoice.objects.create(metadata_type=select_metadata_type, value="Option C")

        # Create an ObjectMetadata
        obj_metadata = ObjectMetadata.objects.create(
            metadata_type=select_metadata_type,
            value="Option A",
            scoped_fields=["status", "parent"],
            assigned_object_type=obj_type,
            assigned_object_id=Location.objects.filter(associated_object_metadata__isnull=True).first().pk,
        )
        obj_metadata.validated_save()

        with self.assertRaises(ValidationError) as context:
            obj_metadata.value = "Not valid option"
            obj_metadata.validated_save()
        self.assertIn("Invalid choice (Not valid option)", str(context.exception))

    def test_multi_select_field(self):
        obj_type = ContentType.objects.get_for_model(Location)
        multi_select_metadata_type = MetadataType.objects.filter(
            data_type=MetadataTypeDataTypeChoices.TYPE_MULTISELECT
        ).first()
        multi_select_metadata_type.content_types.add(obj_type)

        MetadataChoice.objects.create(metadata_type=multi_select_metadata_type, value="Option A")
        MetadataChoice.objects.create(metadata_type=multi_select_metadata_type, value="Option B")
        MetadataChoice.objects.create(metadata_type=multi_select_metadata_type, value="Option C")

        # Create an ObjectMetadata
        obj_metadata = ObjectMetadata.objects.create(
            metadata_type=multi_select_metadata_type,
            value=["Option A"],
            scoped_fields=["status", "parent"],
            assigned_object_type=obj_type,
            assigned_object_id=Location.objects.filter(associated_object_metadata__isnull=True).first().pk,
        )
        obj_metadata.validated_save()

        invalid_options = ["Not A valid option", "NOT A VALID OPTION"]
        with self.assertRaises(ValidationError) as context:
            obj_metadata.value = invalid_options
            obj_metadata.validated_save()
        self.assertIn(f"Invalid choice(s) ({invalid_options})", str(context.exception))

    def test_no_scoped_fields_overlap(self):
        """
        Test that overlapping scoped_fields of ObjectMetadata with same metadata_type/assigned_object is not allowed.
        """
        ObjectMetadata.objects.create(
            metadata_type=MetadataType.objects.first(),
            contact=Contact.objects.first(),
            scoped_fields=["host", "mask_length", "type", "role", "status"],
            assigned_object_type=ContentType.objects.get_for_model(IPAddress),
            assigned_object_id=IPAddress.objects.filter(associated_object_metadata__isnull=True).first().pk,
        )
        instance2 = ObjectMetadata.objects.create(
            metadata_type=MetadataType.objects.first(),
            contact=Contact.objects.first(),
            scoped_fields=[],
            assigned_object_type=ContentType.objects.get_for_model(IPAddress),
            assigned_object_id=IPAddress.objects.filter(associated_object_metadata__isnull=True).first().pk,
        )
        with self.assertRaises(ValidationError):
            # try scope all fields
            instance2.scoped_fields = []
            instance2.validated_save()

        with self.assertRaises(ValidationError):
            instance2.scoped_fields = ["host", "mask_length"]
            instance2.validated_save()

        with self.assertRaises(ValidationError):
            instance2.scoped_fields = ["role", "status", "type"]
            instance2.validated_save()


class RoleTest(ModelTestCases.BaseModelTestCase):
    """Tests for `Role` model class."""

    model = Role

    def test_get_for_models(self):
        """Test get_for_models returns a Roles for those models."""

        device_ct = ContentType.objects.get_for_model(Device)
        ipaddress_ct = ContentType.objects.get_for_model(IPAddress)

        roles = Role.objects.filter(content_types__in=[device_ct, ipaddress_ct])
        self.assertQuerysetEqualAndNotEmpty(Role.objects.get_for_models([Device, IPAddress]), roles)


class SavedViewTest(ModelTestCases.BaseModelTestCase):
    model = SavedView

    def setUp(self):
        self.user = User.objects.create_user(username="Saved View test user")
        self.sv = SavedView.objects.create(name="Saved View", owner=self.user, view="dcim:location_list")

    def test_is_global_default_saved_view_is_shared_automatically(self):
        self.sv.is_global_default = True
        self.sv.save()
        self.assertEqual(self.sv.is_shared, True)

    def test_setting_new_global_default_saved_view_unset_old_global_default_saved_view(self):
        self.old_global_sv = SavedView.objects.create(
            name="Old Global Saved View", owner=self.user, view="dcim:location_list", is_global_default=True
        )

        self.new_global_sv = SavedView.objects.create(
            name="New Global Saved View", owner=self.user, view="dcim:location_list"
        )
        self.new_global_sv.is_global_default = True
        self.new_global_sv.save()
        self.old_global_sv.refresh_from_db()
        self.assertEqual(self.new_global_sv.is_shared, True)
        self.assertEqual(self.old_global_sv.is_global_default, False)

    def test_multiple_global_default_saved_views_can_exist_for_different_views(self):
        self.device_global_sv = SavedView.objects.create(
            name="Device Global Saved View", owner=self.user, view="dcim:device_list", is_global_default=True
        )
        self.device_global_sv.save()
        self.location_global_sv = SavedView.objects.create(
            name="Location Global Saved View", owner=self.user, view="dcim:location_list", is_global_default=True
        )
        self.location_global_sv.save()
        self.ipaddress_global_sv = SavedView.objects.create(
            name="IP Address Global Saved View", owner=self.user, view="ipam:ipaddress_list", is_global_default=True
        )
        self.ipaddress_global_sv.save()
        self.assertEqual(self.device_global_sv.is_shared, True)
        self.assertEqual(self.location_global_sv.is_shared, True)
        self.assertEqual(self.ipaddress_global_sv.is_shared, True)


@override_settings(TIME_ZONE="UTC")
class ScheduledJobTest(ModelTestCases.BaseModelTestCase):
    """Tests for the `ScheduledJob` model class."""

    model = ScheduledJob

    def setUp(self):
        self.user = User.objects.create_user(username="scheduledjobuser")
        self.job_model = JobModel.objects.get(name="TestPassJob")

        self.daily_utc_job = ScheduledJob.objects.create(
            name="Daily UTC Job",
            task="pass_job.TestPassJob",
            job_model=self.job_model,
            interval=JobExecutionType.TYPE_DAILY,
            start_time=datetime(year=2050, month=1, day=22, hour=17, minute=0, tzinfo=get_default_timezone()),
            time_zone=get_default_timezone(),
        )
        self.daily_est_job = ScheduledJob.objects.create(
            name="Daily EST Job",
            task="pass_job.TestPassJob",
            job_model=self.job_model,
            interval=JobExecutionType.TYPE_DAILY,
            start_time=datetime(year=2050, month=1, day=22, hour=17, minute=0, tzinfo=ZoneInfo("America/New_York")),
            time_zone=ZoneInfo("America/New_York"),
        )
        self.crontab_utc_job = ScheduledJob.create_schedule(
            job_model=self.job_model,
            user=self.user,
            name="Crontab UTC Job",
            interval=JobExecutionType.TYPE_CUSTOM,
            crontab="0 17 * * *",
        )
        self.crontab_est_job = ScheduledJob.objects.create(
            name="Crontab EST Job",
            task="pass_job.TestPassJob",
            job_model=self.job_model,
            interval=JobExecutionType.TYPE_CUSTOM,
            start_time=datetime(year=2050, month=1, day=22, hour=17, minute=0, tzinfo=ZoneInfo("America/New_York")),
            time_zone=ZoneInfo("America/New_York"),
            crontab="0 17 * * *",
        )
        self.one_off_utc_job = ScheduledJob.objects.create(
            name="One-off UTC Job",
            task="pass_job.TestPassJob",
            job_model=self.job_model,
            interval=JobExecutionType.TYPE_FUTURE,
            start_time=datetime(year=2050, month=1, day=22, hour=0, minute=0, tzinfo=ZoneInfo("UTC")),
            time_zone=ZoneInfo("UTC"),
        )
        self.one_off_est_job = ScheduledJob.create_schedule(
            job_model=self.job_model,
            user=self.user,
            name="One-off EST Job",
            interval=JobExecutionType.TYPE_FUTURE,
            start_time=datetime(year=2050, month=1, day=22, hour=0, minute=0, tzinfo=ZoneInfo("America/New_York")),
        )
        self.one_off_immediately_job = ScheduledJob.create_schedule(
            job_model=self.job_model,
            user=self.user,
            name="One-off IMMEDIATELY job",
            interval=JobExecutionType.TYPE_IMMEDIATELY,
            start_time=now(),
        )

    def test_scheduled_job_queue_setter(self):
        """Test the queue property setter on ScheduledJob."""
        invalid_queue = "Invalid job Queue"
        with self.assertRaises(ValidationError) as cm:
            self.daily_utc_job.queue = invalid_queue
            self.daily_utc_job.validated_save()
        self.assertIn(f"Job Queue {invalid_queue} does not exist in the database.", str(cm.exception))

    def test_schedule(self):
        """Test the schedule property."""
        with self.subTest("Test TYPE_DAILY schedules"):
            daily_utc_schedule = self.daily_utc_job.schedule
            daily_est_schedule = self.daily_est_job.schedule
            self.assertIsInstance(daily_utc_schedule, TzAwareCrontab)
            self.assertIsInstance(daily_est_schedule, TzAwareCrontab)
            self.assertNotEqual(daily_utc_schedule, daily_est_schedule)
            # Crontabs are validated in test_to_cron()

        with self.subTest("Test TYPE_CUSTOM schedules"):
            crontab_utc_schedule = self.crontab_utc_job.schedule
            crontab_est_schedule = self.crontab_est_job.schedule
            self.assertIsInstance(crontab_utc_schedule, TzAwareCrontab)
            self.assertIsInstance(crontab_est_schedule, TzAwareCrontab)
            self.assertNotEqual(crontab_utc_schedule, crontab_est_schedule)
            # Crontabs are validated in test_to_cron()

        with self.subTest("Test TYPE_FUTURE schedules"):
            # TYPE_FUTURE schedules are one off, not cron tabs:
            self.assertEqual(self.one_off_utc_job.schedule.clocked_time, self.one_off_utc_job.start_time)
            self.assertEqual(self.one_off_est_job.schedule.clocked_time, self.one_off_est_job.start_time)
            self.assertEqual(
                self.one_off_est_job.schedule.clocked_time - self.one_off_utc_job.schedule.clocked_time,
                timedelta(hours=5),
            )

        with self.subTest("Test TYPE IMMEDIATELY schedules"):
            self.assertTrue(self.one_off_immediately_job.one_off)
            self.assertEqual(self.one_off_immediately_job.interval, JobExecutionType.TYPE_FUTURE)

    def test_to_cron(self):
        """Test the to_cron() method and its interaction with time zone variants."""

        with self.subTest("Test TYPE_DAILY schedule with UTC time zone and UTC schedule time zone"):
            self.daily_utc_job.refresh_from_db()
            daily_utc_schedule = self.daily_utc_job.to_cron()
            self.assertEqual(daily_utc_schedule.tz, ZoneInfo("UTC"))
            self.assertEqual(daily_utc_schedule.hour, {17})
            self.assertEqual(daily_utc_schedule.minute, {0})
            last_run = datetime(2050, 1, 21, 17, 0, tzinfo=ZoneInfo("UTC"))
            with time_machine.travel("2050-01-22 16:59 +0000"):
                is_due, _ = daily_utc_schedule.is_due(last_run_at=last_run)
                self.assertFalse(is_due)
            with time_machine.travel("2050-01-22 17:00 +0000"):
                is_due, _ = daily_utc_schedule.is_due(last_run_at=last_run)
                self.assertTrue(is_due)

        with self.subTest("Test TYPE_DAILY schedule with UTC time zone and EST schedule time zone"):
            self.daily_est_job.refresh_from_db()
            daily_est_schedule = self.daily_est_job.to_cron()
            self.assertEqual(daily_est_schedule.tz, ZoneInfo("America/New_York"))
            self.assertEqual(daily_est_schedule.hour, {17})
            self.assertEqual(daily_est_schedule.minute, {0})
            last_run = datetime(2050, 1, 21, 22, 0, tzinfo=ZoneInfo("UTC"))
            with time_machine.travel("2050-01-22 21:59 +0000"):
                is_due, _ = daily_est_schedule.is_due(last_run_at=last_run)
                self.assertFalse(is_due)
            with time_machine.travel("2050-01-22 22:00 +0000"):
                is_due, _ = daily_est_schedule.is_due(last_run_at=last_run)
                self.assertTrue(is_due)

        with self.subTest("Test TYPE_CUSTOM schedule with UTC time zone and UTC schedule time zone"):
            self.crontab_utc_job.refresh_from_db()
            crontab_utc_schedule = self.crontab_utc_job.to_cron()
            self.assertEqual(crontab_utc_schedule.tz, ZoneInfo("UTC"))
            self.assertEqual(crontab_utc_schedule.hour, {17})
            self.assertEqual(crontab_utc_schedule.minute, {0})

        with self.subTest("Test TYPE_CUSTOM schedule with UTC time zone and EST schedule time zone"):
            self.crontab_est_job.refresh_from_db()
            crontab_est_schedule = self.crontab_est_job.to_cron()
            self.assertEqual(crontab_est_schedule.tz, ZoneInfo("America/New_York"))
            self.assertEqual(crontab_est_schedule.hour, {17})
            self.assertEqual(crontab_est_schedule.minute, {0})

        with self.subTest("Test TYPE_FUTURE schedules do not map to cron"):
            with self.assertRaises(ValueError):
                self.one_off_utc_job.to_cron()
            with self.assertRaises(ValueError):
                self.one_off_est_job.to_cron()

        with override_settings(TIME_ZONE="America/New_York"):
            with self.subTest("Test TYPE_DAILY schedule with EST time zone and UTC schedule time zone"):
                self.daily_utc_job.refresh_from_db()
                daily_utc_schedule = self.daily_utc_job.to_cron()
                self.assertEqual(daily_utc_schedule.tz, ZoneInfo("UTC"))
                self.assertEqual(daily_utc_schedule.hour, {17})
                self.assertEqual(daily_utc_schedule.minute, {0})
                last_run = datetime(2050, 1, 21, 12, 0, tzinfo=ZoneInfo("America/New_York"))
                with time_machine.travel("2050-01-22 11:59 -0500"):
                    is_due, _ = daily_utc_schedule.is_due(last_run_at=last_run)
                    self.assertFalse(is_due)
                with time_machine.travel("2050-01-22 12:00 -0500"):
                    is_due, _ = daily_utc_schedule.is_due(last_run_at=last_run)
                    self.assertTrue(is_due)

            with self.subTest("Test TYPE_DAILY schedule with EST time zone and EST schedule time zone"):
                self.daily_est_job.refresh_from_db()
                daily_est_schedule = self.daily_est_job.to_cron()
                self.assertEqual(daily_est_schedule.tz, ZoneInfo("America/New_York"))
                self.assertEqual(daily_est_schedule.hour, {17})
                self.assertEqual(daily_est_schedule.minute, {0})
                last_run = datetime(2050, 1, 21, 22, 0, tzinfo=ZoneInfo("America/New_York"))
                with time_machine.travel("2050-01-22 16:59 -0500"):
                    is_due, _ = daily_est_schedule.is_due(last_run_at=last_run)
                    self.assertFalse(is_due)
                with time_machine.travel("2050-01-22 17:00 -0500"):
                    is_due, _ = daily_est_schedule.is_due(last_run_at=last_run)
                    self.assertTrue(is_due)

            with self.subTest("Test TYPE_CUSTOM schedule with EST time zone and UTC schedule time zone"):
                self.crontab_utc_job.refresh_from_db()
                crontab_utc_schedule = self.crontab_utc_job.to_cron()
                self.assertEqual(crontab_utc_schedule.tz, ZoneInfo("UTC"))
                self.assertEqual(crontab_utc_schedule.hour, {17})
                self.assertEqual(crontab_utc_schedule.minute, {0})

            with self.subTest("Test TYPE_CUSTOM schedule with EST time zone and EST schedule time zone"):
                self.crontab_est_job.refresh_from_db()
                crontab_est_schedule = self.crontab_est_job.to_cron()
                self.assertEqual(crontab_est_schedule.tz, ZoneInfo("America/New_York"))
                self.assertEqual(crontab_est_schedule.hour, {17})
                self.assertEqual(crontab_est_schedule.minute, {0})

    def test_crontab_dst(self):
        """Test that TYPE_CUSTOM behavior around DST is as expected."""
        cronjob = ScheduledJob.objects.create(
            name="DST Aware Cronjob",
            task="pass_job.TestPassJob",
            job_model=self.job_model,
            enabled=False,
            interval=JobExecutionType.TYPE_CUSTOM,
            start_time=datetime(year=2024, month=1, day=1, hour=17, minute=0, tzinfo=ZoneInfo("America/New_York")),
            crontab="0 17 * * *",  # 5 PM local time
            time_zone=ZoneInfo("America/New_York"),
        )

        # Before DST takes effect
        with self.subTest("Test UTC time zone with EST job"):
            cronjob.refresh_from_db()
            crontab = cronjob.to_cron()
            with time_machine.travel("2024-03-09 21:59 +0000"):
                is_due, _ = crontab.is_due(last_run_at=datetime(2024, 3, 8, 17, 0, tzinfo=ZoneInfo("America/New_York")))
                self.assertFalse(is_due)
            with time_machine.travel("2024-03-09 22:00 +0000"):
                is_due, _ = crontab.is_due(last_run_at=datetime(2024, 3, 8, 17, 0, tzinfo=ZoneInfo("America/New_York")))
                self.assertTrue(is_due)

        with self.subTest("Test EST time zone with EST job"), override_settings(TIME_ZONE="America/New_York"):
            cronjob.refresh_from_db()
            crontab = cronjob.to_cron()
            with time_machine.travel("2024-03-09 16:59 -0500"):
                is_due, _ = crontab.is_due(last_run_at=datetime(2024, 3, 8, 17, 0, tzinfo=ZoneInfo("America/New_York")))
                self.assertFalse(is_due)
            with time_machine.travel("2024-03-09 17:00 -0500"):
                is_due, _ = crontab.is_due(last_run_at=datetime(2024, 3, 8, 17, 0, tzinfo=ZoneInfo("America/New_York")))
                self.assertTrue(is_due)

        # Day that DST takes effect
        with self.subTest("Test UTC time zone with EDT job"):
            cronjob.refresh_from_db()
            crontab = cronjob.to_cron()
            with time_machine.travel("2024-03-10 20:59 +0000"):
                is_due, _ = crontab.is_due(last_run_at=datetime(2024, 3, 9, 17, 0, tzinfo=ZoneInfo("America/New_York")))
                self.assertFalse(is_due)
            with time_machine.travel("2024-03-10 21:00 +0000"):
                is_due, _ = crontab.is_due(last_run_at=datetime(2024, 3, 9, 17, 0, tzinfo=ZoneInfo("America/New_York")))
                self.assertTrue(is_due)

        with self.subTest("Test EDT time zone with EDT job"), override_settings(TIME_ZONE="America/New_York"):
            cronjob.refresh_from_db()
            crontab = cronjob.to_cron()
            with time_machine.travel("2024-03-10 16:59 -0400"):
                is_due, _ = crontab.is_due(last_run_at=datetime(2024, 3, 9, 17, 0, tzinfo=ZoneInfo("America/New_York")))
                self.assertFalse(is_due)
            with time_machine.travel("2024-03-10 17:00 -0400"):
                is_due, _ = crontab.is_due(last_run_at=datetime(2024, 3, 9, 17, 0, tzinfo=ZoneInfo("America/New_York")))
                self.assertTrue(is_due)

    def test_daily_dst(self):
        """Test the interaction of TYPE_DAILY around DST."""
        daily = ScheduledJob.objects.create(
            name="Daily Job",
            task="pass_job.TestPassJob",
            job_model=self.job_model,
            enabled=False,
            interval=JobExecutionType.TYPE_DAILY,
            start_time=datetime(year=2024, month=1, day=1, hour=17, minute=0, tzinfo=ZoneInfo("America/New_York")),
            time_zone=ZoneInfo("America/New_York"),
        )

        # Before DST takes effect
        with self.subTest("Test UTC time zone with EST job"):
            daily.refresh_from_db()
            crontab = daily.to_cron()
            with time_machine.travel("2024-03-09 21:59 +0000"):
                is_due, _ = crontab.is_due(last_run_at=datetime(2024, 3, 8, 17, 0, tzinfo=ZoneInfo("America/New_York")))
                self.assertFalse(is_due)
            with time_machine.travel("2024-03-09 22:00 +0000"):
                is_due, _ = crontab.is_due(last_run_at=datetime(2024, 3, 8, 17, 0, tzinfo=ZoneInfo("America/New_York")))
                self.assertTrue(is_due)

        with self.subTest("Test EST time zone with EST job"), override_settings(TIME_ZONE="America/New_York"):
            daily.refresh_from_db()
            crontab = daily.to_cron()
            with time_machine.travel("2024-03-09 16:59 -0500"):
                is_due, _ = crontab.is_due(last_run_at=datetime(2024, 3, 8, 17, 0, tzinfo=ZoneInfo("America/New_York")))
                self.assertFalse(is_due)
            with time_machine.travel("2024-03-09 17:00 -0500"):
                is_due, _ = crontab.is_due(last_run_at=datetime(2024, 3, 8, 17, 0, tzinfo=ZoneInfo("America/New_York")))
                self.assertTrue(is_due)

        # Day that DST takes effect
        with self.subTest("Test UTC time zone with EDT job"):
            daily.refresh_from_db()
            crontab = daily.to_cron()
            with time_machine.travel("2024-03-10 20:59 +0000"):
                is_due, _ = crontab.is_due(last_run_at=datetime(2024, 3, 9, 17, 0, tzinfo=ZoneInfo("America/New_York")))
                self.assertFalse(is_due)
            with time_machine.travel("2024-03-10 21:00 +0000"):
                is_due, _ = crontab.is_due(last_run_at=datetime(2024, 3, 9, 17, 0, tzinfo=ZoneInfo("America/New_York")))
                self.assertTrue(is_due)

        with self.subTest("Test EDT time zone with EDT job"), override_settings(TIME_ZONE="America/New_York"):
            daily.refresh_from_db()
            crontab = daily.to_cron()
            with time_machine.travel("2024-03-10 16:59 -0400"):
                is_due, _ = crontab.is_due(last_run_at=datetime(2024, 3, 9, 17, 0, tzinfo=ZoneInfo("America/New_York")))
                self.assertFalse(is_due)
            with time_machine.travel("2024-03-10 17:00 -0400"):
                is_due, _ = crontab.is_due(last_run_at=datetime(2024, 3, 9, 17, 0, tzinfo=ZoneInfo("America/New_York")))
                self.assertTrue(is_due)

    # TODO uncomment when we have a way to setup the NautobotDatabaseScheduler correctly
    # @mock.patch("nautobot.extras.utils.run_kubernetes_job_and_return_job_result")
    # def test_nautobot_database_scheduler_apply_async_method(self, mock_run_kubernetes_job_and_return_job_result):
    #     jq = JobQueue.objects.create(name="kubernetes", queue_type=JobQueueTypeChoices.TYPE_KUBERNETES)
    #     sj = ScheduledJob.objects.create(
    #         name="Export Object List Hourly",
    #         task="nautobot.core.jobs.ExportObjectList",
    #         job_model=JobModel.objects.get(name="Export Object List"),
    #         interval=JobExecutionType.TYPE_HOURLY,
    #         user=User.objects.first(),
    #         approval_required=False,
    #         start_time=datetime.now(ZoneInfo("America/New_York")),
    #         time_zone=ZoneInfo("America/New_York"),
    #         job_queue=jq,
    #         kwargs='{"content_type": 1}',
    #     )
    #     jr = JobResult.objects.create(
    #         name=sj.job_model.name,
    #         job_model=sj.job_model,
    #         scheduled_job=sj,
    #         user=sj.user,
    #     )
    #     mock_run_kubernetes_job_and_return_job_result.return_value = jr
    #     entry = NautobotScheduleEntry(model=sj)
    #     scheduler = NautobotDatabaseScheduler(app=entry.app)
    #     scheduler.apply_async(entry=entry, producer=None, advance=False)
    #     Check scheduled job runs correctly with no job queue
    #     sj.job_queue = None
    #     sj.save()
    #     entry = NautobotScheduleEntry(model=sj)
    #     scheduler = NautobotDatabaseScheduler(app=entry.app)
    #     scheduler.apply_async(entry=entry, producer=None, advance=False)


class SecretTest(ModelTestCases.BaseModelTestCase):
    """
    Tests for the `Secret` model class.
    """

    model = Secret

    def setUp(self):
        self.environment_secret = Secret.objects.create(
            name="Environment Variable Secret",
            provider="environment-variable",
            parameters={"variable": "NAUTOBOT_TEST_ENVIRONMENT_VARIABLE"},
        )
        self.environment_secret_templated = Secret.objects.create(
            name="Environment Variable Templated Secret",
            provider="environment-variable",
            parameters={"variable": "NAUTOBOT_TEST_{{ obj.name | upper }}"},
        )
        self.text_file_secret = Secret.objects.create(
            name="Text File Secret",
            provider="text-file",
            parameters={"path": os.path.join(tempfile.gettempdir(), "secret-file.txt")},
        )
        self.text_file_secret_templated = Secret.objects.create(
            name="Text File Templated Secret",
            provider="text-file",
            parameters={"path": os.path.join(tempfile.gettempdir(), "{{ obj.name }}", "secret-file.txt")},
        )

        self.location = Location.objects.filter(location_type=LocationType.objects.get(name="Campus")).first()
        self.location.name = "nyc"
        self.location.save()

    def test_environment_variable_value_not_found(self):
        """Failure to retrieve an environment variable raises an exception."""
        with self.assertRaises(SecretValueNotFoundError) as handler:
            self.environment_secret.get_value()
        self.assertEqual(
            str(handler.exception),
            f'SecretValueNotFoundError: Secret "{self.environment_secret}" '
            '(provider "EnvironmentVariableSecretsProvider"): '
            'Undefined environment variable "NAUTOBOT_TEST_ENVIRONMENT_VARIABLE"!',
        )

        with self.assertRaises(SecretValueNotFoundError) as handler:
            self.environment_secret.get_value(obj=None)
        self.assertEqual(
            str(handler.exception),
            f'SecretValueNotFoundError: Secret "{self.environment_secret}" '
            '(provider "EnvironmentVariableSecretsProvider"): '
            'Undefined environment variable "NAUTOBOT_TEST_ENVIRONMENT_VARIABLE"!',
        )

        with self.assertRaises(SecretValueNotFoundError) as handler:
            self.environment_secret.get_value(obj=self.location)
        self.assertEqual(
            str(handler.exception),
            f'SecretValueNotFoundError: Secret "{self.environment_secret}" '
            '(provider "EnvironmentVariableSecretsProvider"): '
            'Undefined environment variable "NAUTOBOT_TEST_ENVIRONMENT_VARIABLE"!',
        )

        with self.assertRaises(SecretValueNotFoundError) as handler:
            self.environment_secret_templated.get_value(obj=self.location)
        self.assertEqual(
            str(handler.exception),
            f'SecretValueNotFoundError: Secret "{self.environment_secret_templated}" '
            '(provider "EnvironmentVariableSecretsProvider"): '
            'Undefined environment variable "NAUTOBOT_TEST_NYC"!',
        )

    def test_environment_variable_value_missing_parameters(self):
        """A mis-defined environment variable secret raises an exception on access."""
        self.environment_secret.parameters = {}

        with self.assertRaises(SecretParametersError) as handler:
            self.environment_secret.get_value()
        self.assertEqual(
            str(handler.exception),
            f'SecretParametersError: Secret "{self.environment_secret}" '
            '(provider "EnvironmentVariableSecretsProvider"): '
            'The "variable" parameter is mandatory!',
        )

        with self.assertRaises(SecretParametersError) as handler:
            self.environment_secret.get_value(obj=None)
        self.assertEqual(
            str(handler.exception),
            f'SecretParametersError: Secret "{self.environment_secret}" '
            '(provider "EnvironmentVariableSecretsProvider"): '
            'The "variable" parameter is mandatory!',
        )

        with self.assertRaises(SecretParametersError) as handler:
            self.environment_secret.get_value(obj=self.location)
        self.assertEqual(
            str(handler.exception),
            f'SecretParametersError: Secret "{self.environment_secret}" '
            '(provider "EnvironmentVariableSecretsProvider"): '
            'The "variable" parameter is mandatory!',
        )

    def test_environment_variable_templated_missing_object(self):
        """A templated secret requires an object for context."""
        # Since we're not using Jinja2's StrictUndefined, it just renders as an empty string if obj is omitted or None,
        # For this secret it results in a rendered value of "", which is of course not a defined environment variable.
        with self.assertRaises(SecretValueNotFoundError) as handler:
            self.environment_secret_templated.get_value()
        self.assertEqual(
            str(handler.exception),
            f'SecretValueNotFoundError: Secret "{self.environment_secret_templated}" '
            '(provider "EnvironmentVariableSecretsProvider"): '
            'Undefined environment variable "NAUTOBOT_TEST_"!',
        )

        with self.assertRaises(SecretValueNotFoundError) as handler:
            self.environment_secret_templated.get_value(obj=None)
        self.assertEqual(
            str(handler.exception),
            f'SecretValueNotFoundError: Secret "{self.environment_secret_templated}" '
            '(provider "EnvironmentVariableSecretsProvider"): '
            'Undefined environment variable "NAUTOBOT_TEST_"!',
        )

    def test_environment_variable_templated_bad_template(self):
        """Error handling."""
        # Malformed Jinja2
        self.environment_secret_templated.parameters["variable"] = "{{ obj."
        with self.assertRaises(SecretParametersError) as handler:
            self.environment_secret_templated.get_value(obj=self.location)
        self.assertEqual(
            str(handler.exception),
            f'SecretParametersError: Secret "{self.environment_secret_templated}" '
            '(provider "EnvironmentVariableSecretsProvider"): '
            "expected name or number",
        )

        # Template references attribute not present on the provided obj
        # Since we're not using Jinja2's StrictUndefined, this just renders as an empty string
        self.environment_secret_templated.parameters["variable"] = "{{ obj.primary_ip4 }}"
        with self.assertRaises(SecretValueNotFoundError) as handler:
            self.environment_secret_templated.get_value(obj=self.location)
        self.assertEqual(
            str(handler.exception),
            f'SecretValueNotFoundError: Secret "{self.environment_secret_templated}" '
            '(provider "EnvironmentVariableSecretsProvider"): '
            'Undefined environment variable ""!',
        )

    @mock.patch.dict(os.environ, {"NAUTOBOT_TEST_ENVIRONMENT_VARIABLE": "supersecretvalue"})
    def test_environment_variable_value_success(self):
        """Successful retrieval of an environment variable secret."""
        self.assertEqual(self.environment_secret.get_value(), "supersecretvalue")
        # It's OK to pass a context obj even if the secret in question isn't templated
        self.assertEqual(self.environment_secret.get_value(obj=self.location), "supersecretvalue")

    @mock.patch.dict(os.environ, {"NAUTOBOT_TEST_ENVIRONMENT_VARIABLE": ""})
    def test_environment_variable_value_success_empty(self):
        """Successful retrieval of an environment variable secret even if set to an empty string."""
        self.assertEqual(self.environment_secret.get_value(), "")
        # It's OK to pass a context obj even if the secret in question isn't templated
        self.assertEqual(self.environment_secret.get_value(obj=self.location), "")

    @mock.patch.dict(os.environ, {"NAUTOBOT_TEST_NYC": "lessthansecretvalue"})
    def test_environment_variable_templated_success(self):
        """Successful retrieval of a templated environment variable secret."""
        self.assertEqual(self.environment_secret_templated.get_value(obj=self.location), "lessthansecretvalue")

    def test_text_file_clean_validation(self):
        secret = Secret.objects.create(
            name="Path shenanigans",
            provider="text-file",
            parameters={"path": "relative/path/to/file"},
        )
        with self.assertRaises(ValidationError):
            secret.clean()
        secret.parameters = {"path": "/opt/nautobot/../../etc/passwd"}
        with self.assertRaises(ValidationError):
            secret.clean()

    def test_text_file_value_not_found(self):
        """Failure to retrieve a file raises an exception."""
        path = self.text_file_secret.rendered_parameters(obj=None)["path"]
        with self.assertRaises(SecretValueNotFoundError) as handler:
            self.text_file_secret.get_value()
        self.assertEqual(
            str(handler.exception),
            f'SecretValueNotFoundError: Secret "{self.text_file_secret}" (provider "TextFileSecretsProvider"): '
            f'File "{path}" not found!',
        )

        with self.assertRaises(SecretValueNotFoundError) as handler:
            self.text_file_secret.get_value(obj=None)
        self.assertEqual(
            str(handler.exception),
            f'SecretValueNotFoundError: Secret "{self.text_file_secret}" (provider "TextFileSecretsProvider"): '
            f'File "{path}" not found!',
        )

        with self.assertRaises(SecretValueNotFoundError) as handler:
            self.text_file_secret.get_value(obj=self.location)
        self.assertEqual(
            str(handler.exception),
            f'SecretValueNotFoundError: Secret "{self.text_file_secret}" (provider "TextFileSecretsProvider"): '
            f'File "{path}" not found!',
        )

    def test_text_file_value_missing_parameters(self):
        """A mis-defined text file secret raises an exception."""
        self.text_file_secret.parameters = {}
        with self.assertRaises(SecretParametersError) as handler:
            self.text_file_secret.get_value()
        self.assertEqual(
            str(handler.exception),
            f'SecretParametersError: Secret "{self.text_file_secret}" (provider "TextFileSecretsProvider"): '
            'The "path" parameter is mandatory!',
        )

        with self.assertRaises(SecretParametersError) as handler:
            self.text_file_secret.get_value(obj=None)
        self.assertEqual(
            str(handler.exception),
            f'SecretParametersError: Secret "{self.text_file_secret}" (provider "TextFileSecretsProvider"): '
            'The "path" parameter is mandatory!',
        )

        with self.assertRaises(SecretParametersError) as handler:
            self.text_file_secret.get_value(obj=self.location)
        self.assertEqual(
            str(handler.exception),
            f'SecretParametersError: Secret "{self.text_file_secret}" (provider "TextFileSecretsProvider"): '
            'The "path" parameter is mandatory!',
        )

    def test_text_file_value_success(self):
        """Successful retrieval of a text file secret."""
        with open(self.text_file_secret.parameters["path"], "w", encoding="utf8") as file_handle:
            file_handle.write("Hello world!")
        try:
            self.assertEqual(self.text_file_secret.get_value(), "Hello world!")
            # It's OK to pass a context obj even if the secret in question isn't templated
            self.assertEqual(self.text_file_secret.get_value(obj=self.location), "Hello world!")
        finally:
            os.remove(self.text_file_secret.parameters["path"])

    def test_text_file_value_stripped(self):
        """Assert that retrieval of a text file secret value is stripped."""
        with open(self.text_file_secret.parameters["path"], "w", encoding="utf8") as file_handle:
            file_handle.write(" Hello world!  \n\n")
        try:
            self.assertEqual(self.text_file_secret.get_value(), "Hello world!")
            # It's OK to pass a context obj even if the secret in question isn't templated
            self.assertEqual(self.text_file_secret.get_value(obj=self.location), "Hello world!")
        finally:
            os.remove(self.text_file_secret.parameters["path"])

    def test_text_file_value_success_empty(self):
        """Successful retrieval of a text file secret from an empty file."""
        with open(self.text_file_secret.parameters["path"], "w", encoding="utf8"):
            pass
        try:
            self.assertEqual(self.text_file_secret.get_value(), "")
            # It's OK to pass a context obj even if the secret in question isn't templated
            self.assertEqual(self.text_file_secret.get_value(obj=self.location), "")
        finally:
            os.remove(self.text_file_secret.parameters["path"])

    def test_text_file_templated_value_success(self):
        """Successful retrieval of a templated text file secret."""
        path = self.text_file_secret_templated.rendered_parameters(obj=self.location)["path"]
        if not os.path.exists(os.path.dirname(path)):
            os.makedirs(os.path.dirname(path))
        with open(path, "w", encoding="utf8") as file_handle:
            file_handle.write("Hello?")
        try:
            self.assertEqual(self.text_file_secret_templated.get_value(obj=self.location), "Hello?")
        finally:
            os.remove(path)
            os.rmdir(os.path.dirname(path))

    def test_unknown_provider(self):
        """An unknown/unsupported provider raises an exception."""
        self.environment_secret.provider = "it-is-a-mystery"
        with self.assertRaises(ValidationError) as handler:
            self.environment_secret.clean()
        self.assertEqual(
            str(handler.exception),
            "{'provider': ['No registered provider \"it-is-a-mystery\" is available']}",
        )

        with self.assertRaises(SecretProviderError) as handler:
            self.environment_secret.get_value()
        self.assertEqual(
            str(handler.exception),
            f'SecretProviderError: Secret "{self.environment_secret}" (provider "it-is-a-mystery"): '
            'No registered provider "it-is-a-mystery" is available',
        )

        with self.assertRaises(SecretProviderError) as handler:
            self.environment_secret.get_value(obj=None)
        self.assertEqual(
            str(handler.exception),
            f'SecretProviderError: Secret "{self.environment_secret}" (provider "it-is-a-mystery"): '
            'No registered provider "it-is-a-mystery" is available',
        )

        with self.assertRaises(SecretProviderError) as handler:
            self.environment_secret.get_value(obj=self.location)
        self.assertEqual(
            str(handler.exception),
            f'SecretProviderError: Secret "{self.environment_secret}" (provider "it-is-a-mystery"): '
            'No registered provider "it-is-a-mystery" is available',
        )


class SecretsGroupTest(ModelTestCases.BaseModelTestCase):
    """
    Tests for the `SecretsGroup` model class.
    """

    model = SecretsGroup

    def setUp(self):
        self.secrets_group = SecretsGroup(name="Secrets Group 1")
        self.secrets_group.validated_save()

        self.environment_secret = Secret.objects.create(
            name="Environment Variable Secret",
            provider="environment-variable",
            parameters={"variable": "NAUTOBOT_TEST_ENVIRONMENT_VARIABLE"},
        )

        SecretsGroupAssociation.objects.create(
            secrets_group=self.secrets_group,
            secret=self.environment_secret,
            access_type=SecretsGroupAccessTypeChoices.TYPE_GENERIC,
            secret_type=SecretsGroupSecretTypeChoices.TYPE_SECRET,
        )

    def test_get_secret_value_no_such_type(self):
        """Looking up a secret type/access type not present in the group is an exception."""
        with self.assertRaises(SecretsGroupAssociation.DoesNotExist):
            # Access type matches but not secret type
            self.secrets_group.get_secret_value(
                access_type=SecretsGroupAccessTypeChoices.TYPE_GENERIC,
                secret_type=SecretsGroupSecretTypeChoices.TYPE_USERNAME,
            )
        with self.assertRaises(SecretsGroupAssociation.DoesNotExist):
            # Secret type matches but not access type
            self.secrets_group.get_secret_value(
                access_type=SecretsGroupAccessTypeChoices.TYPE_NETCONF,
                secret_type=SecretsGroupSecretTypeChoices.TYPE_SECRET,
            )

    def test_get_secret_value_secret_error(self):
        """Looking up a secret may succeed but retrieving its value may fail."""
        with self.assertRaises(SecretValueNotFoundError):
            self.secrets_group.get_secret_value(
                access_type=SecretsGroupAccessTypeChoices.TYPE_GENERIC,
                secret_type=SecretsGroupSecretTypeChoices.TYPE_SECRET,
            )
        with self.assertRaises(SecretValueNotFoundError):
            self.secrets_group.get_secret_value(
                access_type=SecretsGroupAccessTypeChoices.TYPE_GENERIC,
                secret_type=SecretsGroupSecretTypeChoices.TYPE_SECRET,
                obj=self.environment_secret,
            )

    @mock.patch.dict(os.environ, {"NAUTOBOT_TEST_ENVIRONMENT_VARIABLE": "supersecretvalue"})
    def test_get_secret_value_success(self):
        """It's possible to successfully look up a secret and its value."""
        self.assertEqual(
            self.secrets_group.get_secret_value(
                access_type=SecretsGroupAccessTypeChoices.TYPE_GENERIC,
                secret_type=SecretsGroupSecretTypeChoices.TYPE_SECRET,
            ),
            "supersecretvalue",
        )
        self.assertEqual(
            self.secrets_group.get_secret_value(
                access_type=SecretsGroupAccessTypeChoices.TYPE_GENERIC,
                secret_type=SecretsGroupSecretTypeChoices.TYPE_SECRET,
                obj=self.environment_secret,
            ),
            "supersecretvalue",
        )


class StaticGroupAssociationTest(ModelTestCases.BaseModelTestCase):
    model = StaticGroupAssociation


class StatusTest(ModelTestCases.BaseModelTestCase):
    """
    Tests for the `Status` model class.
    """

    model = Status

    def setUp(self):
        self.status = Status.objects.create(name="New Device Status")
        self.status.content_types.add(ContentType.objects.get_for_model(Device))

        manufacturer = Manufacturer.objects.first()
        devicetype = DeviceType.objects.create(manufacturer=manufacturer, model="Device Type 1")
        devicerole = Role.objects.get_for_model(Device).first()
        location = Location.objects.filter(location_type=LocationType.objects.get(name="Campus")).first()

        self.device = Device.objects.create(
            name="Device 1",
            device_type=devicetype,
            role=devicerole,
            location=location,
            status=self.status,
        )

    def test_uniqueness(self):
        with self.assertRaises(IntegrityError):
            Status.objects.create(name=self.status.name)

    def test_delete_protection(self):
        # Protected delete will fail
        with self.assertRaises(ProtectedError):
            self.status.delete()

        # Delete the device
        self.device.delete()

        # Now that it's not in use, delete will succeed.
        self.status.delete()
        self.assertEqual(self.status.pk, None)

    def test_color(self):
        # Valid color
        self.status.color = ColorChoices.COLOR_PURPLE
        self.status.full_clean()

        # Invalid color
        self.status.color = "red"
        with self.assertRaises(ValidationError):
            self.status.full_clean()

    def test_name(self):
        # Test a bunch of wackado names.
        tests = [
            "CAPSLOCK",
            "---;;a;l^^^2ZSsljk¡",
            "-42",
            "392405834ioafdjskl;ajr30894fjakl;fs___π",
        ]
        for test in tests:
            self.status.name = test
            self.status.clean()
            self.status.save()
            self.assertEqual(str(self.status), test)

    @isolate_apps("nautobot.extras.tests")
    def test_deprecated_mixin_class(self):
        """Test that inheriting from StatusModel raises a DeprecationWarning."""
        with warnings.catch_warnings(record=True) as warn_list:
            warnings.simplefilter("always")

            class MyModel(StatusModel):  # pylint: disable=unused-variable
                pass

        self.assertEqual(len(warn_list), 1)
        warning = warn_list[0]
        self.assertTrue(issubclass(warning.category, DeprecationWarning))
        self.assertIn("StatusModel is deprecated", str(warning))
        self.assertIn("Instead of deriving MyModel from StatusModel", str(warning))
        self.assertIn("please directly declare `status = StatusField(...)` on your model instead", str(warning))


class TagTest(ModelTestCases.BaseModelTestCase):
    model = Tag

    def test_create_tag_unicode(self):
        tag = Tag(name="Testing Unicode: 台灣")
        tag.save()

        self.assertEqual(tag.name, "Testing Unicode: 台灣")


class JobLogEntryTest(TestCase):  # TODO: change to BaseModelTestCase
    """
    Tests for the JobLogEntry Model.
    """

    def setUp(self):
        module = "pass_job"
        name = "TestPassJob"
        job_class = get_job(f"{module}.{name}")

        self.job_result = JobResult.objects.create(name=job_class.class_path, user=None)

    def test_log_entry_creation(self):
        log = JobLogEntry(
            log_level=LogLevelChoices.LOG_INFO,
            job_result=self.job_result,
            grouping="run",
            message="This is a test",
        )
        log.save()

        self.assertEqual(JobLogEntry.objects.filter(job_result=self.job_result).count(), 1)
        log_object = JobLogEntry.objects.filter(job_result=self.job_result).first()
        self.assertEqual(log_object.message, log.message)
        self.assertEqual(log_object.log_level, log.log_level)
        self.assertEqual(log_object.grouping, log.grouping)


class JobResultTestCase(TestCase):
    def test_passing_invalid_data_into_job_result(self):
        """JobResult.result was changed from TextField to JSONField in https://github.com/nautobot/nautobot/pull/4133/files.
        Assert passing json serializable and non-serializable data into JobResult.result"""

        with self.subTest("Assert Passing Valid data"):
            data = {
                "output": "valid data",
            }
            job_result = JobResult.objects.create(name="ExampleJob1", user=None, result=data)
            self.assertTrue(job_result.present_in_database)
            self.assertEqual(job_result.result, data)

        with self.subTest("Assert Passing Invalid data"):
            with self.assertRaises(TypeError) as err:
                JobResult.objects.create(name="ExampleJob2", user=None, result=lambda: 1)
            self.assertEqual(str(err.exception), "Object of type function is not JSON serializable")

    def test_get_task(self):
        """Assert bug fix for `Cannot resolve keyword 'task_id' into field` #5440"""
        data = {
            "output": "valid data",
        }
        job_result = JobResult.objects.create(name="ExampleJob1", user=None, result=data)

        self.assertEqual(JobResult.objects.get_task(job_result.pk), job_result)


class WebhookTest(ModelTestCases.BaseModelTestCase):
    model = Webhook

    def setUp(self):
        device_content_type = ContentType.objects.get_for_model(Device)
        self.url = "http://example.com/test"

        self.webhooks = [
            Webhook(
                name="webhook-1",
                enabled=True,
                type_create=True,
                type_update=True,
                type_delete=False,
                payload_url=self.url,
                http_method="POST",
                http_content_type="application/json",
            ),
            Webhook(
                name="webhook-2",
                enabled=True,
                type_create=False,
                type_update=False,
                type_delete=True,
                payload_url=self.url,
                http_method="POST",
                http_content_type="application/json",
            ),
        ]
        for webhook in self.webhooks:
            webhook.save()
            webhook.content_types.add(device_content_type)

    def test_type_error_not_raised_when_calling_check_for_conflicts(self):
        """
        Test type error not raised when calling Webhook.check_for_conflicts() without passing all accepted arguments
        """
        conflicts = Webhook.check_for_conflicts(instance=self.webhooks[1], type_create=True)
        self.assertEqual(
            conflicts["type_create"],
            [f"A webhook already exists for create on dcim | device to URL {self.url}"],
        )
