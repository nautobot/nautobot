import os
import tempfile
import datetime
from unittest import mock
import uuid

from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db.models import ProtectedError
from django.db.utils import IntegrityError

from nautobot.dcim.models import (
    Device,
    DeviceRole,
    DeviceType,
    Location,
    LocationType,
    Manufacturer,
    Platform,
    Site,
)
from nautobot.extras.constants import JOB_OVERRIDABLE_FIELDS
from nautobot.extras.choices import LogLevelChoices, SecretsGroupAccessTypeChoices, SecretsGroupSecretTypeChoices
from nautobot.extras.jobs import get_job, Job as JobClass
from nautobot.extras.models import (
    ComputedField,
    ConfigContext,
    ConfigContextSchema,
    ExportTemplate,
    FileAttachment,
    FileProxy,
    GitRepository,
    Job as JobModel,
    JobLogEntry,
    JobResult,
    Secret,
    SecretsGroup,
    SecretsGroupAssociation,
    Status,
    Tag,
    Webhook,
)
from nautobot.extras.utils import get_job_content_type
from nautobot.extras.secrets.exceptions import SecretParametersError, SecretProviderError, SecretValueNotFoundError
from nautobot.ipam.models import IPAddress
from nautobot.tenancy.models import Tenant, TenantGroup
from nautobot.utilities.choices import ColorChoices
from nautobot.utilities.testing import TestCase, TransactionTestCase
from nautobot.virtualization.models import (
    Cluster,
    ClusterGroup,
    ClusterType,
    VirtualMachine,
)


class ComputedFieldTest(TestCase):
    """
    Tests for the `ComputedField` Model
    """

    def setUp(self):
        self.good_computed_field = ComputedField.objects.create(
            content_type=ContentType.objects.get_for_model(Site),
            slug="good_computed_field",
            label="Good Computed Field",
            template="{{ obj.name }} is awesome!",
            fallback_value="This template has errored",
            weight=100,
        )
        self.bad_computed_field = ComputedField.objects.create(
            content_type=ContentType.objects.get_for_model(Site),
            slug="bad_computed_field",
            label="Bad Computed Field",
            template="{{ not_in_context | not_a_filter }} is horrible!",
            fallback_value="An error occurred while rendering this template.",
            weight=50,
        )
        self.blank_fallback_value = ComputedField.objects.create(
            content_type=ContentType.objects.get_for_model(Site),
            slug="blank_fallback_value",
            label="Blank Fallback Value",
            template="{{ obj.location }}",
            weight=50,
        )
        self.site1 = Site.objects.first()

    def test_render_method(self):
        rendered_value = self.good_computed_field.render(context={"obj": self.site1})
        self.assertEqual(rendered_value, f"{self.site1.name} is awesome!")

    def test_render_method_undefined_error(self):
        rendered_value = self.blank_fallback_value.render(context={"obj": self.site1})
        self.assertEqual(rendered_value, "")

    def test_render_method_bad_template(self):
        rendered_value = self.bad_computed_field.render(context={"obj": self.site1})
        self.assertEqual(rendered_value, self.bad_computed_field.fallback_value)


class ConfigContextTest(TestCase):
    """
    These test cases deal with the weighting, ordering, and deep merge logic of config context data.

    It also ensures the various config context querysets are consistent.
    """

    def setUp(self):

        manufacturer = Manufacturer.objects.create(name="Manufacturer 1", slug="manufacturer-1")
        self.devicetype = DeviceType.objects.create(
            manufacturer=manufacturer, model="Device Type 1", slug="device-type-1"
        )
        self.devicerole = DeviceRole.objects.create(name="Device Role 1", slug="device-role-1")
        self.site = Site.objects.filter(region__isnull=False).first()
        self.region = self.site.region
        location_type = LocationType.objects.create(name="Location Type 1")
        self.location = Location.objects.create(name="Location 1", location_type=location_type, site=self.site)
        self.platform = Platform.objects.create(name="Platform")
        self.tenantgroup = TenantGroup.objects.create(name="Tenant Group")
        self.tenant = Tenant.objects.create(name="Tenant", group=self.tenantgroup)
        self.tag, self.tag2 = Tag.objects.get_for_model(Device)[:2]

        self.device = Device.objects.create(
            name="Device 1",
            device_type=self.devicetype,
            device_role=self.devicerole,
            site=self.site,
            location=self.location,
        )

    def test_higher_weight_wins(self):

        ConfigContext.objects.create(name="context 1", weight=101, data={"a": 123, "b": 456, "c": 777})
        ConfigContext.objects.create(name="context 2", weight=100, data={"a": 123, "b": 456, "c": 789})

        expected_data = {"a": 123, "b": 456, "c": 777}
        self.assertEqual(self.device.get_config_context(), expected_data)

    def test_name_ordering_after_weight(self):

        ConfigContext.objects.create(name="context 1", weight=100, data={"a": 123, "b": 456, "c": 777})
        ConfigContext.objects.create(name="context 2", weight=100, data={"a": 123, "b": 456, "c": 789})

        expected_data = {"a": 123, "b": 456, "c": 789}
        self.assertEqual(self.device.get_config_context(), expected_data)

    def test_name_uniqueness(self):
        """
        Verify that two unowned ConfigContexts cannot share the same name (GitHub issue #431).
        """
        ConfigContext.objects.create(name="context 1", weight=100, data={"a": 123, "b": 456, "c": 777})
        with self.assertRaises(ValidationError):
            duplicate_context = ConfigContext(name="context 1", weight=200, data={"c": 666})
            duplicate_context.validated_save()

        # If a different context is owned by a GitRepository, that's not considered a duplicate
        repo = GitRepository(
            name="Test Git Repository",
            slug="test-git-repo",
            remote_url="http://localhost/git.git",
            username="oauth2",
        )
        repo.save(trigger_resync=False)

        nonduplicate_context = ConfigContext(name="context 1", weight=300, data={"a": "22"}, owner=repo)
        nonduplicate_context.validated_save()

    def test_annotation_same_as_get_for_object(self):
        """
        This test incorporates features from all of the above tests cases to ensure
        the annotate_config_context_data() and get_for_object() queryset methods are the same.
        """
        ConfigContext.objects.create(name="context 1", weight=101, data={"a": 123, "b": 456, "c": 777})
        ConfigContext.objects.create(name="context 2", weight=100, data={"a": 123, "b": 456, "c": 789})
        ConfigContext.objects.create(name="context 3", weight=99, data={"d": 1})
        ConfigContext.objects.create(name="context 4", weight=99, data={"d": 2})

        annotated_queryset = Device.objects.filter(name=self.device.name).annotate_config_context_data()
        self.assertEqual(self.device.get_config_context(), annotated_queryset[0].get_config_context())

    def test_annotation_same_as_get_for_object_device_relations(self):

        location_context = ConfigContext.objects.create(name="location", weight=100, data={"location": 1})
        location_context.locations.add(self.location)
        site_context = ConfigContext.objects.create(name="site", weight=100, data={"site": 1})
        site_context.sites.add(self.site)
        region_context = ConfigContext.objects.create(name="region", weight=100, data={"region": 1})
        region_context.regions.add(self.region)
        platform_context = ConfigContext.objects.create(name="platform", weight=100, data={"platform": 1})
        platform_context.platforms.add(self.platform)
        tenant_group_context = ConfigContext.objects.create(name="tenant group", weight=100, data={"tenant_group": 1})
        tenant_group_context.tenant_groups.add(self.tenantgroup)
        tenant_context = ConfigContext.objects.create(name="tenant", weight=100, data={"tenant": 1})
        tenant_context.tenants.add(self.tenant)
        tag_context = ConfigContext.objects.create(name="tag", weight=100, data={"tag": 1})
        tag_context.tags.add(self.tag)

        device = Device.objects.create(
            name="Device 2",
            site=self.site,
            location=self.location,
            tenant=self.tenant,
            platform=self.platform,
            device_role=self.devicerole,
            device_type=self.devicetype,
        )
        device.tags.add(self.tag)

        annotated_queryset = Device.objects.filter(name=device.name).annotate_config_context_data()
        device_context = device.get_config_context()
        self.assertEqual(device_context, annotated_queryset[0].get_config_context())
        for key in ["location", "site", "region", "platform", "tenant_group", "tenant", "tag"]:
            self.assertIn(key, device_context)

    def test_annotation_same_as_get_for_object_virtualmachine_relations(self):

        location_context = ConfigContext.objects.create(name="location", weight=100, data={"location": 1})
        location_context.locations.add(self.location)
        site_context = ConfigContext.objects.create(name="site", weight=100, data={"site": 1})
        site_context.sites.add(self.site)
        region_context = ConfigContext.objects.create(name="region", weight=100, data={"region": 1})
        region_context.regions.add(self.region)
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
            group=cluster_group,
            type=cluster_type,
            site=self.site,
            location=self.location,
        )
        cluster_context = ConfigContext.objects.create(name="cluster", weight=100, data={"cluster": 1})
        cluster_context.clusters.add(cluster)

        virtual_machine = VirtualMachine.objects.create(
            name="VM 1",
            cluster=cluster,
            tenant=self.tenant,
            platform=self.platform,
            role=self.devicerole,
        )
        virtual_machine.tags.add(self.tag)

        annotated_queryset = VirtualMachine.objects.filter(name=virtual_machine.name).annotate_config_context_data()
        vm_context = virtual_machine.get_config_context()
        self.assertEqual(vm_context, annotated_queryset[0].get_config_context())
        for key in [
            "location",
            "site",
            "region",
            "platform",
            "tenant_group",
            "tenant",
            "tag",
            "cluster_group",
            "cluster",
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
            site=self.site,
            tenant=self.tenant,
            platform=self.platform,
            device_role=self.devicerole,
            device_type=self.devicetype,
        )
        device.tags.add(self.tag)
        device.tags.add(self.tag2)

        annotated_queryset = Device.objects.filter(name=device.name).annotate_config_context_data()
        self.assertEqual(ConfigContext.objects.get_for_object(device).count(), 1)
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
            site=self.site,
            tenant=self.tenant,
            platform=self.platform,
            device_role=self.devicerole,
            device_type=self.devicetype,
        )
        device.tags.add(self.tag)
        device.tags.add(self.tag2)

        annotated_queryset = Device.objects.filter(name=device.name).annotate_config_context_data()
        self.assertEqual(ConfigContext.objects.get_for_object(device).count(), 2)
        self.assertEqual(device.get_config_context(), annotated_queryset[0].get_config_context())


class ConfigContextSchemaTestCase(TestCase):
    """
    Tests for the ConfigContextSchema model
    """

    def setUp(self):
        context_data = {"a": 123, "b": "456", "c": "10.7.7.7"}

        # Schemas
        self.schema_validation_pass = ConfigContextSchema.objects.create(
            name="schema-pass",
            slug="schema-pass",
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
                slug="schema-fail-wrong-properties",
                data_schema={
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {"foo": {"type": "string"}},
                },
            ),
            ConfigContextSchema.objects.create(
                name="schema fail (wrong type)",
                slug="schema-fail-wrong-type",
                data_schema={"type": "object", "properties": {"b": {"type": "integer"}}},
            ),
            ConfigContextSchema.objects.create(
                name="schema fail (wrong format)",
                slug="schema-fail-wrong-format",
                data_schema={"type": "object", "properties": {"b": {"type": "string", "format": "ipv4"}}},
            ),
        )

        # ConfigContext
        self.config_context = ConfigContext.objects.create(name="context 1", weight=101, data=context_data)

        # Device
        status = Status.objects.get(slug="active")
        site = Site.objects.first()
        manufacturer = Manufacturer.objects.create(name="manufacturer", slug="manufacturer")
        device_type = DeviceType.objects.create(model="device_type", manufacturer=manufacturer)
        device_role = DeviceRole.objects.create(name="device_role", slug="device-role", color="ffffff")
        self.device = Device.objects.create(
            name="device",
            site=site,
            device_type=device_type,
            device_role=device_role,
            status=status,
            local_context_data=context_data,
        )

        # Virtual Machine
        cluster_type = ClusterType.objects.create(name="cluster_type", slug="cluster-type")
        cluster = Cluster.objects.create(name="cluster", type=cluster_type)
        self.virtual_machine = VirtualMachine.objects.create(
            name="virtual_machine", cluster=cluster, status=status, local_context_data=context_data
        )

    def test_existing_config_context_valid_schema_applied(self):
        """
        Given an existing config context object
        And a config context schema object with a json schema
        And the config context context data is valid for the schema
        Assert calling clean on the config context object DOES NOT raise a ValidationError
        """
        self.config_context.schema = self.schema_validation_pass

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
            self.config_context.schema = schema

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
        Given an existing device object with local_context_data
        And a config context schema object with a json schema
        And the device local_context_data is valid for the schema
        Assert calling clean on the device object DOES NOT raise a ValidationError
        """
        self.device.local_context_schema = self.schema_validation_pass

        try:
            self.device.full_clean()
        except ValidationError:
            self.fail("self.device.full_clean() raised ValidationError unexpectedly!")

    def test_existing_device_invalid_schema_applied(self):
        """
        Given an existing device object with local_context_data
        And a config context schema object with a json schema
        And the device local_context_data is NOT valid for the schema
        Assert calling clean on the device object DOES raise a ValidationError
        """
        for schema in self.schemas_validation_fail:
            self.device.local_context_schema = schema

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
        Given an existing virtual machine object with local_context_data
        And a config context schema object with a json schema
        And the virtual machine local_context_data is valid for the schema
        Assert calling clean on the virtual machine object DOES NOT raise a ValidationError
        """
        self.virtual_machine.local_context_schema = self.schema_validation_pass

        try:
            self.virtual_machine.full_clean()
        except ValidationError:
            self.fail("self.virtual_machine.full_clean() raised ValidationError unexpectedly!")

    def test_existing_virtual_machine_invalid_schema_applied(self):
        """
        Given an existing virtual machine object with local_context_data
        And a config context schema object with a json schema
        And the virtual machine local_context_data is NOT valid for the schema
        Assert calling clean on the virtual machine object DOES raise a ValidationError
        """
        for schema in self.schemas_validation_fail:
            self.virtual_machine.local_context_schema = schema

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
            name="invalid", slug="invalid", data_schema={"properties": {"this": "is not a valid json schema"}}
        )

        with self.assertRaises(ValidationError):
            invalid_schema.full_clean()

    def test_json_schema_must_be_an_object(self):
        """
        Given a config context schema object
        With a JSON schema of type object
        Assert calling clean on the config context schema object raises a ValidationError
        """
        invalid_schema = ConfigContextSchema(name="invalid", slug="invalid", data_schema=["not an object"])

        with self.assertRaises(ValidationError):
            invalid_schema.full_clean()

    def test_json_schema_must_have_type_set_to_object(self):
        """
        Given a config context schema object
        With a JSON schema with type set to integer
        Assert calling clean on the config context schema object raises a ValidationError
        """
        invalid_schema = ConfigContextSchema(
            name="invalid", slug="invalid", data_schema={"type": "integer", "properties": {"a": {"type": "string"}}}
        )

        with self.assertRaises(ValidationError):
            invalid_schema.full_clean()

    def test_json_schema_must_have_type_present(self):
        """
        Given a config context schema object
        With a JSON schema with type not present
        Assert calling clean on the config context schema object raises a ValidationError
        """
        invalid_schema = ConfigContextSchema(
            name="invalid", slug="invalid", data_schema={"properties": {"a": {"type": "string"}}}
        )

        with self.assertRaises(ValidationError):
            invalid_schema.full_clean()

    def test_json_schema_must_have_properties_present(self):
        """
        Given a config context schema object
        With a JSON schema with properties not present
        Assert calling clean on the config context schema object raises a ValidationError
        """
        invalid_schema = ConfigContextSchema(name="invalid", slug="invalid", data_schema={"type": "object"})

        with self.assertRaises(ValidationError):
            invalid_schema.full_clean()


class ExportTemplateTest(TestCase):
    """
    Tests for the ExportTemplate model class.
    """

    def test_name_contenttype_uniqueness(self):
        """
        The pair of (name, content_type) must be unique for an un-owned ExportTemplate.

        See GitHub issue #431.
        """
        device_ct = ContentType.objects.get_for_model(Device)
        ExportTemplate.objects.create(content_type=device_ct, name="Export Template 1", template_code="hello world")

        with self.assertRaises(ValidationError):
            duplicate_template = ExportTemplate(content_type=device_ct, name="Export Template 1", template_code="foo")
            duplicate_template.validated_save()

        # A differently owned ExportTemplate may have the same name
        repo = GitRepository(
            name="Test Git Repository",
            slug="test-git-repo",
            remote_url="http://localhost/git.git",
            username="oauth2",
        )
        repo.save(trigger_resync=False)
        nonduplicate_template = ExportTemplate(
            content_type=device_ct, name="Export Template 1", owner=repo, template_code="bar"
        )
        nonduplicate_template.validated_save()


class FileProxyTest(TestCase):
    def setUp(self):
        self.test_file = SimpleUploadedFile(name="test_file.txt", content=b"I am content.\n")

    def test_create_file_proxy(self):
        """Test creation of `FileProxy` object."""
        fp = FileProxy.objects.create(name=self.test_file.name, file=self.test_file)

        # Now refresh it and make sure it was saved and retrieved correctly.
        fp.refresh_from_db()
        self.test_file.seek(0)  # Reset cursor since it was previously read
        self.assertEqual(fp.name, self.test_file.name)
        self.assertEqual(fp.file.read(), self.test_file.read())

    def test_delete_file_proxy(self):
        """Test deletion of `FileProxy` object."""
        fp = FileProxy.objects.create(name=self.test_file.name, file=self.test_file)

        # Assert counts before delete
        self.assertEqual(FileProxy.objects.count(), 1)
        self.assertEqual(FileAttachment.objects.count(), 1)

        # Assert counts after delete
        fp.delete()
        self.assertEqual(FileProxy.objects.count(), 0)
        self.assertEqual(FileAttachment.objects.count(), 0)


class GitRepositoryTest(TransactionTestCase):
    """
    Tests for the GitRepository model class.

    Note: This is a TransactionTestCase, rather than a TestCase, because the GitRepository save() method uses
    transaction.on_commit(), which doesn't get triggered in a normal TestCase.
    """

    SAMPLE_TOKEN = "dc6542736e7b02c159d14bc08f972f9ec1e2c45fa"

    def setUp(self):
        self.repo = GitRepository(
            name="Test Git Repository",
            slug="test-git-repo",
            remote_url="http://localhost/git.git",
            username="oauth2",
        )
        self.repo.save(trigger_resync=False)

    def test_token_rendered(self):
        self.assertEqual(self.repo.token_rendered, "—")
        self.repo._token = self.SAMPLE_TOKEN
        self.assertEqual(self.repo.token_rendered, GitRepository.TOKEN_PLACEHOLDER)
        self.repo._token = ""
        self.assertEqual(self.repo.token_rendered, "—")

    def test_filesystem_path(self):
        self.assertEqual(self.repo.filesystem_path, os.path.join(settings.GIT_ROOT, self.repo.slug))

    def test_save_preserve_token(self):
        self.repo._token = self.SAMPLE_TOKEN
        self.repo.save(trigger_resync=False)
        self.assertEqual(self.repo._token, self.SAMPLE_TOKEN)
        # As if the user had submitted an "Edit" form, which displays the token placeholder instead of the actual token
        self.repo._token = GitRepository.TOKEN_PLACEHOLDER
        self.repo.save(trigger_resync=False)
        self.assertEqual(self.repo._token, self.SAMPLE_TOKEN)
        # As if the user had deleted a pre-existing token from the UI
        self.repo._token = ""
        self.repo.save(trigger_resync=False)
        self.assertEqual(self.repo._token, "")

    def test_verify_user(self):
        self.assertEqual(self.repo.username, "oauth2")

    def test_save_relocate_directory(self):
        with tempfile.TemporaryDirectory() as tmpdirname:
            with self.settings(GIT_ROOT=tmpdirname):
                initial_path = self.repo.filesystem_path
                self.assertIn(self.repo.slug, initial_path)
                os.makedirs(initial_path)

                self.repo.slug = "a-new-location"
                self.repo.save(trigger_resync=False)

                self.assertFalse(os.path.exists(initial_path))
                new_path = self.repo.filesystem_path
                self.assertIn(self.repo.slug, new_path)
                self.assertTrue(os.path.isdir(new_path))


class JobModelTest(TestCase):
    """
    Tests for the `Job` model class.
    """

    @classmethod
    def setUpTestData(cls):
        # JobModel instances are automatically instantiated at startup, so we just need to look them up.
        cls.local_job = JobModel.objects.get(job_class_name="TestPass")
        cls.job_containing_sensitive_variables = JobModel.objects.get(job_class_name="ExampleLoggingJob")
        cls.plugin_job = JobModel.objects.get(job_class_name="ExampleJob")

    def test_job_class(self):
        self.assertEqual(self.local_job.job_class.description, "Validate job import")

        from example_plugin.jobs import ExampleJob

        self.assertEqual(self.plugin_job.job_class, ExampleJob)

    def test_class_path(self):
        self.assertEqual(self.local_job.class_path, "local/test_pass/TestPass")
        self.assertEqual(self.local_job.class_path, self.local_job.job_class.class_path)

        self.assertEqual(self.plugin_job.class_path, "plugins/example_plugin.jobs/ExampleJob")
        self.assertEqual(self.plugin_job.class_path, self.plugin_job.job_class.class_path)

    def test_latest_result(self):
        self.assertEqual(self.local_job.latest_result, None)
        self.assertEqual(self.plugin_job.latest_result, None)
        # TODO(Glenn): create some JobResults and test that this works correctly for them as well.

    def test_defaults(self):
        """Verify that defaults for discovered JobModel instances are as expected."""
        for job_model in JobModel.objects.all():
            self.assertTrue(job_model.installed)
            self.assertFalse(job_model.enabled)
            for field_name in JOB_OVERRIDABLE_FIELDS:
                self.assertFalse(getattr(job_model, f"{field_name}_override"))
                self.assertEqual(getattr(job_model, field_name), getattr(job_model.job_class, field_name))

    def test_clean_overrides(self):
        """Verify that cleaning resets non-overridden fields to their appropriate default values."""

        overridden_attrs = {
            "grouping": "Overridden Grouping",
            "name": "Overridden Name",
            "description": "Overridden Description",
            "commit_default": not self.job_containing_sensitive_variables.commit_default,
            "hidden": not self.job_containing_sensitive_variables.hidden,
            "read_only": not self.job_containing_sensitive_variables.read_only,
            "approval_required": not self.job_containing_sensitive_variables.approval_required,
            "has_sensitive_variables": not self.job_containing_sensitive_variables.has_sensitive_variables,
            "soft_time_limit": 350,
            "time_limit": 650,
            "task_queues": ["overridden", "worker", "queues"],
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
                source="local",
                module_name="too_long_of_a_module_name.too_long_of_a_module_name.too_long_of_a_module_name.too_long_of_a_module_name.too_long_of_a_module_name",
                job_class_name="JobClass",
                grouping="grouping",
                name="name",
            ).clean()
        self.assertIn("Module name", str(handler.exception))

        with self.assertRaises(ValidationError) as handler:
            JobModel(
                source="local",
                module_name="module_name",
                job_class_name="ThisIsARidiculouslyLongJobClassNameWhoWouldEverDoSuchAnUtterlyRidiculousThingButBetterSafeThanSorrySinceWeAreDealingWithUserInputHere",
                grouping="grouping",
                name="name",
            ).clean()
        self.assertIn("Job class name", str(handler.exception))

        with self.assertRaises(ValidationError) as handler:
            JobModel(
                source="local",
                module_name="module_name",
                job_class_name="JobClassName",
                grouping="OK now this is just ridiculous. Why would you ever want to deal with typing in 255+ characters of grouping information and have to copy-paste it to the other jobs in the same grouping or risk dealing with typos when typing out such a ridiculously long grouping string? Still, once again, better safe than sorry!",
                name="name",
            ).clean()
        self.assertIn("Grouping", str(handler.exception))

        with self.assertRaises(ValidationError) as handler:
            JobModel(
                source="local",
                module_name="module_name",
                job_class_name="JobClassName",
                grouping="grouping",
                name="Similarly, let us hope that no one really wants to specify a job name that is over 100 characters long, it would be a pain to type at the very least and it won't look good in the UI either",
            ).clean()
        self.assertIn("Name", str(handler.exception))

        with self.assertRaises(ValidationError) as handler:
            JobModel(
                source="local",
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


class JobResultTest(TestCase):
    """
    Tests for the `JobResult` model class.
    """

    def test_related_object(self):
        """Test that the `related_object` property is computed properly."""
        # Case 1: Job, identified by class_path.
        job_class = get_job("local/test_pass/TestPass")
        job_result = JobResult(
            name=job_class.class_path,
            obj_type=get_job_content_type(),
            job_id=uuid.uuid4(),
        )

        # Can't just do self.assertEqual(job_result.related_object, job_class) here for some reason
        self.assertEqual(type(job_result.related_object), type)
        self.assertTrue(issubclass(job_result.related_object, JobClass))
        self.assertEqual(job_result.related_object.class_path, "local/test_pass/TestPass")

        job_result.name = "local/no_such_job/NoSuchJob"
        self.assertIsNone(job_result.related_object)

        job_result.name = "not-a-class-path"
        self.assertIsNone(job_result.related_object)

        # Case 2: GitRepository, identified by name.
        repo = GitRepository(
            name="Test Git Repository",
            slug="test-git-repo",
            remote_url="http://localhost/git.git",
            username="oauth2",
        )
        repo.save(trigger_resync=False)

        job_result = JobResult(
            name=repo.name,
            obj_type=ContentType.objects.get_for_model(repo),
            job_id=uuid.uuid4(),
        )

        self.assertEqual(job_result.related_object, repo)

        job_result.name = "No such GitRepository"
        self.assertIsNone(job_result.related_object)

        # Case 3: Related object with no name, identified by PK/ID
        ip_address = IPAddress.objects.create(address="1.1.1.1/32")
        job_result = JobResult(
            name="irrelevant",
            obj_type=ContentType.objects.get_for_model(ip_address),
            job_id=ip_address.pk,
        )

        self.assertEqual(job_result.related_object, ip_address)

        job_result.job_id = uuid.uuid4()
        self.assertIsNone(job_result.related_object)


class SecretTest(TestCase):
    """
    Tests for the `Secret` model class.
    """

    def setUp(self):
        self.environment_secret = Secret.objects.create(
            name="Environment Variable Secret",
            slug="env-var",
            provider="environment-variable",
            parameters={"variable": "NAUTOBOT_TEST_ENVIRONMENT_VARIABLE"},
        )
        self.environment_secret_templated = Secret.objects.create(
            name="Environment Variable Templated Secret",
            slug="env-var-templated",
            provider="environment-variable",
            parameters={"variable": "NAUTOBOT_TEST_{{ obj.slug | upper }}"},
        )
        self.text_file_secret = Secret.objects.create(
            name="Text File Secret",
            slug="text",
            provider="text-file",
            parameters={"path": os.path.join(tempfile.gettempdir(), "secret-file.txt")},
        )
        self.text_file_secret_templated = Secret.objects.create(
            name="Text File Templated Secret",
            slug="text-templated",
            provider="text-file",
            parameters={"path": os.path.join(tempfile.gettempdir(), "{{ obj.slug }}", "secret-file.txt")},
        )

        self.site = Site.objects.first()
        self.site.slug = "nyc"

    def test_environment_variable_value_not_found(self):
        """Failure to retrieve an environment variable raises an exception."""
        with self.assertRaises(SecretValueNotFoundError):
            self.environment_secret.get_value()
        with self.assertRaises(SecretValueNotFoundError):
            self.environment_secret.get_value(obj=None)
        with self.assertRaises(SecretValueNotFoundError):
            self.environment_secret.get_value(obj=self.site)

        with self.assertRaises(SecretValueNotFoundError):
            self.environment_secret_templated.get_value(obj=self.site)

    def test_environment_variable_value_missing_parameters(self):
        """A mis-defined environment variable secret raises an exception on access."""
        self.environment_secret.parameters = {}
        with self.assertRaises(SecretParametersError):
            self.environment_secret.get_value()
        with self.assertRaises(SecretParametersError):
            self.environment_secret.get_value(obj=None)
        with self.assertRaises(SecretParametersError):
            self.environment_secret.get_value(obj=self.site)

    def test_environment_variable_templated_missing_object(self):
        """A templated secret requires an object for context."""
        # Since we're not using Jinja2's StrictUndefined, it just renders as an empty string if obj is omitted or None,
        # For this secret it results in a rendered value of "", which is of course not a defined environment variable.
        with self.assertRaises(SecretValueNotFoundError):
            self.environment_secret_templated.get_value()
        with self.assertRaises(SecretValueNotFoundError):
            self.environment_secret_templated.get_value(obj=None)

    def test_environment_variable_templated_bad_template(self):
        """Error handling."""
        # Malformed Jinja2
        self.environment_secret_templated.parameters["variable"] = "{{ obj."
        with self.assertRaises(SecretParametersError):
            self.environment_secret_templated.get_value(obj=self.site)
        # Template references attribute not present on the provided obj
        # Since we're not using Jinja2's StrictUndefined, this just renders as an empty string
        self.environment_secret_templated.parameters["variable"] = "{{ obj.primary_ip4 }}"
        with self.assertRaises(SecretValueNotFoundError):
            self.environment_secret_templated.get_value(obj=self.site)

    @mock.patch.dict(os.environ, {"NAUTOBOT_TEST_ENVIRONMENT_VARIABLE": "supersecretvalue"})
    def test_environment_variable_value_success(self):
        """Successful retrieval of an environment variable secret."""
        self.assertEqual(self.environment_secret.get_value(), "supersecretvalue")
        # It's OK to pass a context obj even if the secret in question isn't templated
        self.assertEqual(self.environment_secret.get_value(obj=self.site), "supersecretvalue")

    @mock.patch.dict(os.environ, {"NAUTOBOT_TEST_ENVIRONMENT_VARIABLE": ""})
    def test_environment_variable_value_success_empty(self):
        """Successful retrieval of an environment variable secret even if set to an empty string."""
        self.assertEqual(self.environment_secret.get_value(), "")
        # It's OK to pass a context obj even if the secret in question isn't templated
        self.assertEqual(self.environment_secret.get_value(obj=self.site), "")

    @mock.patch.dict(os.environ, {"NAUTOBOT_TEST_NYC": "lessthansecretvalue"})
    def test_environment_variable_templated_success(self):
        """Successful retrieval of a templated environment variable secret."""
        self.assertEqual(self.environment_secret_templated.get_value(obj=self.site), "lessthansecretvalue")

    def test_text_file_clean_validation(self):
        secret = Secret.objects.create(
            name="Path shenanigans",
            slug="path-shenanigans",
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
        with self.assertRaises(SecretValueNotFoundError):
            self.text_file_secret.get_value()
        with self.assertRaises(SecretValueNotFoundError):
            self.text_file_secret.get_value(obj=None)
        with self.assertRaises(SecretValueNotFoundError):
            self.text_file_secret.get_value(obj=self.site)

    def test_text_file_value_missing_parameters(self):
        """A mis-defined text file secret raises an exception."""
        self.text_file_secret.parameters = {}
        with self.assertRaises(SecretParametersError):
            self.text_file_secret.get_value()
        with self.assertRaises(SecretParametersError):
            self.text_file_secret.get_value(obj=None)
        with self.assertRaises(SecretParametersError):
            self.text_file_secret.get_value(obj=self.site)

    def test_text_file_value_success(self):
        """Successful retrieval of a text file secret."""
        with open(self.text_file_secret.parameters["path"], "w", encoding="utf8") as file_handle:
            file_handle.write("Hello world!")
        try:
            self.assertEqual(self.text_file_secret.get_value(), "Hello world!")
            # It's OK to pass a context obj even if the secret in question isn't templated
            self.assertEqual(self.text_file_secret.get_value(obj=self.site), "Hello world!")
        finally:
            os.remove(self.text_file_secret.parameters["path"])

    def test_text_file_value_stripped(self):
        """Assert that retrieval of a text file secret value is stripped."""
        with open(self.text_file_secret.parameters["path"], "w", encoding="utf8") as file_handle:
            file_handle.write(" Hello world!  \n\n")
        try:
            self.assertEqual(self.text_file_secret.get_value(), "Hello world!")
            # It's OK to pass a context obj even if the secret in question isn't templated
            self.assertEqual(self.text_file_secret.get_value(obj=self.site), "Hello world!")
        finally:
            os.remove(self.text_file_secret.parameters["path"])

    def test_text_file_value_success_empty(self):
        """Successful retrieval of a text file secret from an empty file."""
        with open(self.text_file_secret.parameters["path"], "w", encoding="utf8"):
            pass
        try:
            self.assertEqual(self.text_file_secret.get_value(), "")
            # It's OK to pass a context obj even if the secret in question isn't templated
            self.assertEqual(self.text_file_secret.get_value(obj=self.site), "")
        finally:
            os.remove(self.text_file_secret.parameters["path"])

    def test_text_file_templated_value_success(self):
        """Successful retrieval of a templated text file secret."""
        path = self.text_file_secret_templated.rendered_parameters(obj=self.site)["path"]
        if not os.path.exists(os.path.dirname(path)):
            os.makedirs(os.path.dirname(path))
        with open(path, "w", encoding="utf8") as file_handle:
            file_handle.write("Hello?")
        try:
            self.assertEqual(self.text_file_secret_templated.get_value(obj=self.site), "Hello?")
        finally:
            os.remove(path)
            os.rmdir(os.path.dirname(path))

    def test_unknown_provider(self):
        """An unknown/unsupported provider raises an exception."""
        self.environment_secret.provider = "it-is-a-mystery"
        with self.assertRaises(ValidationError):
            self.environment_secret.clean()
        with self.assertRaises(SecretProviderError):
            self.environment_secret.get_value()
        with self.assertRaises(SecretProviderError):
            self.environment_secret.get_value(obj=None)
        with self.assertRaises(SecretProviderError):
            self.environment_secret.get_value(obj=self.site)


class SecretsGroupTest(TestCase):
    """
    Tests for the `SecretsGroup` model class.
    """

    def setUp(self):
        self.secrets_group = SecretsGroup(name="Secrets Group 1", slug="secrets-group-1")
        self.secrets_group.validated_save()

        self.environment_secret = Secret.objects.create(
            name="Environment Variable Secret",
            slug="env-var",
            provider="environment-variable",
            parameters={"variable": "NAUTOBOT_TEST_ENVIRONMENT_VARIABLE"},
        )

        SecretsGroupAssociation.objects.create(
            group=self.secrets_group,
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


class StatusTest(TestCase):
    """
    Tests for the `Status` model class.
    """

    def setUp(self):
        self.status = Status.objects.create(name="New Device Status")
        self.status.content_types.add(ContentType.objects.get_for_model(Device))

        manufacturer = Manufacturer.objects.create(name="Manufacturer 1")
        devicetype = DeviceType.objects.create(manufacturer=manufacturer, model="Device Type 1")
        devicerole = DeviceRole.objects.create(name="Device Role 1")
        site = Site.objects.first()

        self.device = Device.objects.create(
            name="Device 1",
            device_type=devicetype,
            device_role=devicerole,
            site=site,
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


class TagTest(TestCase):
    def test_create_tag_unicode(self):
        tag = Tag(name="Testing Unicode: 台灣")
        tag.save()

        self.assertEqual(tag.slug, "testing-unicode-台灣")


class JobLogEntryTest(TestCase):
    """
    Tests for the JobLogEntry Model.
    """

    def setUp(self):
        module = "test_pass"
        name = "TestPass"
        job_class = get_job(f"local/{module}/{name}")

        self.job_result = JobResult.objects.create(
            name=job_class.class_path,
            obj_type=get_job_content_type(),
            user=None,
            job_id=uuid.uuid4(),
        )

    def test_log_entry_creation(self):

        log = JobLogEntry(
            log_level=LogLevelChoices.LOG_SUCCESS,
            job_result=self.job_result,
            grouping="run",
            message="This is a test",
        )
        log.save()

        self.assertEqual(JobLogEntry.objects.all().count(), 1)
        log_object = JobLogEntry.objects.first()
        self.assertEqual(log_object.message, log.message)
        self.assertEqual(log_object.log_level, log.log_level)
        self.assertEqual(log_object.grouping, log.grouping)

    def test_to_csv_no_log_object(self):
        """Check that `to_csv` returns the correct data from the JobLogEntry model."""
        expected_data = ("2020-01-26 15:37:36", "run", "success", "", "Django Test")

        joblogentry_a = JobLogEntry(
            job_result=self.job_result,
            log_level=LogLevelChoices.LOG_SUCCESS,
            grouping="run",
            message="Django Test",
            created=datetime.datetime(2020, 1, 26, 15, 37, 36),
            log_object="",
            absolute_url="",
        )
        joblogentry_a.validated_save()
        csv_data = joblogentry_a.to_csv()
        self.assertEqual(expected_data, csv_data)

    def test_to_csv_with_log_object(self):
        """Check that `to_csv` returns the correct data from the JobLogEntry model."""
        expected_data = ("2030-05-26 15:37:36", "run", "success", "ams01-dist-01", "Django Test 2")

        joblogentry_a = JobLogEntry(
            job_result=self.job_result,
            log_level=LogLevelChoices.LOG_SUCCESS,
            grouping="run",
            message="Django Test 2",
            created=datetime.datetime(2030, 5, 26, 15, 37, 36),
            log_object="ams01-dist-01",
            absolute_url="https://nautobot.io/dcim/devices/8d769e14-286a-489c-b705-bd15c476abbb",
        )
        joblogentry_a.validated_save()
        csv_data = joblogentry_a.to_csv()
        self.assertEqual(expected_data, csv_data)


class WebhookTest(TestCase):
    def test_type_error_not_raised_when_calling_check_for_conflicts(self):
        """
        Test type error not raised when calling Webhook.check_for_conflicts() without passing all accepted arguments
        """
        device_content_type = ContentType.objects.get_for_model(Device)
        url = "http://example.com/test"

        webhooks = [
            Webhook(
                name="webhook-1",
                enabled=True,
                type_create=True,
                type_update=True,
                type_delete=False,
                payload_url=url,
                http_method="POST",
                http_content_type="application/json",
            ),
            Webhook(
                name="webhook-2",
                enabled=True,
                type_create=False,
                type_update=False,
                type_delete=True,
                payload_url=url,
                http_method="POST",
                http_content_type="application/json",
            ),
        ]
        for webhook in webhooks:
            webhook.save()
            webhook.content_types.add(device_content_type)

        data = {"type_create": True}

        conflicts = Webhook.check_for_conflicts(instance=webhooks[1], type_create=data.get("type_create"))
        self.assertEqual(
            conflicts["type_create"],
            [f"A webhook already exists for create on dcim | device to URL {url}"],
        )
