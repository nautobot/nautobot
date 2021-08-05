import os
import tempfile
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
    Manufacturer,
    Platform,
    Site,
    Region,
)
from nautobot.extras.jobs import get_job, Job
from nautobot.extras.models import (
    ComputedField,
    ConfigContext,
    ConfigContextSchema,
    ExportTemplate,
    FileAttachment,
    FileProxy,
    GitRepository,
    JobResult,
    Status,
    Tag,
)
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


class TagTest(TestCase):
    def test_create_tag_unicode(self):
        tag = Tag(name="Testing Unicode: 台灣")
        tag.save()

        self.assertEqual(tag.slug, "testing-unicode-台灣")


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
        self.region = Region.objects.create(name="Region")
        self.site = Site.objects.create(name="Site-1", slug="site-1", region=self.region)
        self.platform = Platform.objects.create(name="Platform")
        self.tenantgroup = TenantGroup.objects.create(name="Tenant Group")
        self.tenant = Tenant.objects.create(name="Tenant", group=self.tenantgroup)
        self.tag = Tag.objects.create(name="Tag", slug="tag")
        self.tag2 = Tag.objects.create(name="Tag2", slug="tag2")

        self.device = Device.objects.create(
            name="Device 1",
            device_type=self.devicetype,
            device_role=self.devicerole,
            site=self.site,
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
        This test incorperates features from all of the above tests cases to ensure
        the annotate_config_context_data() and get_for_object() queryset methods are the same.
        """
        ConfigContext.objects.create(name="context 1", weight=101, data={"a": 123, "b": 456, "c": 777})
        ConfigContext.objects.create(name="context 2", weight=100, data={"a": 123, "b": 456, "c": 789})
        ConfigContext.objects.create(name="context 3", weight=99, data={"d": 1})
        ConfigContext.objects.create(name="context 4", weight=99, data={"d": 2})

        annotated_queryset = Device.objects.filter(name=self.device.name).annotate_config_context_data()
        self.assertEqual(self.device.get_config_context(), annotated_queryset[0].get_config_context())

    def test_annotation_same_as_get_for_object_device_relations(self):

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
            tenant=self.tenant,
            platform=self.platform,
            device_role=self.devicerole,
            device_type=self.devicetype,
        )
        device.tags.add(self.tag)

        annotated_queryset = Device.objects.filter(name=device.name).annotate_config_context_data()
        self.assertEqual(device.get_config_context(), annotated_queryset[0].get_config_context())

    def test_annotation_same_as_get_for_object_virtualmachine_relations(self):

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
        cluster = Cluster.objects.create(name="Cluster", group=cluster_group, type=cluster_type)
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
        self.assertEqual(
            virtual_machine.get_config_context(),
            annotated_queryset[0].get_config_context(),
        )

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


class JobResultTest(TestCase):
    """
    Tests for the `JobResult` model class.
    """

    def test_related_object(self):
        """Test that the `related_object` property is computed properly."""
        # Case 1: Job, identified by class_path.
        with self.settings(JOBS_ROOT=os.path.join(settings.BASE_DIR, "extras/tests/dummy_jobs")):
            job_class = get_job("local/test_pass/TestPass")
            job_result = JobResult(
                name=job_class.class_path,
                obj_type=ContentType.objects.get(app_label="extras", model="job"),
                job_id=uuid.uuid4(),
            )

            # Can't just do self.assertEqual(job_result.related_object, job_class) here for some reason
            self.assertEqual(type(job_result.related_object), type)
            self.assertTrue(issubclass(job_result.related_object, Job))
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


class StatusTest(TestCase):
    """
    Tests for the `Status` model class.
    """

    def setUp(self):
        self.status = Status.objects.create(name="delete_me", slug="delete-me", color=ColorChoices.COLOR_RED)

        manufacturer = Manufacturer.objects.create(name="Manufacturer 1")
        devicetype = DeviceType.objects.create(manufacturer=manufacturer, model="Device Type 1")
        devicerole = DeviceRole.objects.create(name="Device Role 1")
        site = Site.objects.create(name="Site-1")

        self.device = Device.objects.create(
            name="Device 1",
            device_type=devicetype,
            device_role=devicerole,
            site=site,
            status=self.status,
        )

    def test_uniqueness(self):
        # A `delete_me` Status already exists.
        with self.assertRaises(IntegrityError):
            Status.objects.create(name="delete_me")

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
        self.assertEqual(self.status.color, ColorChoices.COLOR_RED)

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
            self.assertEquals(str(self.status), test)


class ConfigContextSchemaTestCase(TestCase):
    """
    Tests for the ConfigContextSchema model
    """

    def setUp(self):
        context_data = {"a": 123, "b": 456, "c": 777}

        # Schemas
        self.schema_validation_pass = ConfigContextSchema.objects.create(
            name="schema-pass",
            slug="schema-pass",
            data_schema={
                "type": "object",
                "additionalProperties": False,
                "properties": {"a": {"type": "integer"}, "b": {"type": "integer"}, "c": {"type": "integer"}},
            },
        )
        self.schema_validation_fail = ConfigContextSchema.objects.create(
            name="schema-fail",
            slug="schema-fail",
            data_schema={"type": "object", "additionalProperties": False, "properties": {"foo": {"type": "string"}}},
        )

        # ConfigContext
        self.config_context = ConfigContext.objects.create(name="context 1", weight=101, data=context_data)

        # Device
        status = Status.objects.get(slug="active")
        site = Site.objects.create(name="site", slug="site", status=status)
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
        self.config_context.schema = self.schema_validation_fail

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
        self.device.local_context_schema = self.schema_validation_fail

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
        self.virtual_machine.local_context_schema = self.schema_validation_fail

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
        self.site1 = Site.objects.create(name="NYC")

    def test_render_method(self):
        rendered_value = self.good_computed_field.render(context={"obj": self.site1})
        self.assertEqual(rendered_value, f"{self.site1.name} is awesome!")

    def test_render_method_bad_template(self):
        rendered_value = self.bad_computed_field.render(context={"obj": self.site1})
        self.assertEqual(rendered_value, self.bad_computed_field.fallback_value)


class FileProxyTest(TestCase):
    def setUp(self):
        self.dummy_file = SimpleUploadedFile(name="dummy.txt", content=b"I am content.\n")

    def test_create_file_proxy(self):
        """Test creation of `FileProxy` object."""
        fp = FileProxy.objects.create(name=self.dummy_file.name, file=self.dummy_file)

        # Now refresh it and make sure it was saved and retrieved correctly.
        fp.refresh_from_db()
        self.dummy_file.seek(0)  # Reset cursor since it was previously read
        self.assertEqual(fp.name, self.dummy_file.name)
        self.assertEqual(fp.file.read(), self.dummy_file.read())

    def test_delete_file_proxy(self):
        """Test deletion of `FileProxy` object."""
        fp = FileProxy.objects.create(name=self.dummy_file.name, file=self.dummy_file)

        # Assert counts before delete
        self.assertEqual(FileProxy.objects.count(), 1)
        self.assertEqual(FileAttachment.objects.count(), 1)

        # Assert counts after delete
        fp.delete()
        self.assertEqual(FileProxy.objects.count(), 0)
        self.assertEqual(FileAttachment.objects.count(), 0)
