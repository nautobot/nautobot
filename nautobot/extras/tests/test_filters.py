import uuid

from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.db.models import Q
from django.test import override_settings

from nautobot.core.choices import ColorChoices
from nautobot.core.testing import FilterTestCases
from nautobot.dcim.filters import DeviceFilterSet
from nautobot.dcim.models import (
    Device,
    DeviceType,
    Interface,
    Location,
    LocationType,
    Manufacturer,
    Platform,
    Rack,
)
from nautobot.extras.choices import (
    CustomFieldTypeChoices,
    JobResultStatusChoices,
    ObjectChangeActionChoices,
    SecretsGroupAccessTypeChoices,
    SecretsGroupSecretTypeChoices,
)
from nautobot.extras.constants import HTTP_CONTENT_TYPE_JSON
from nautobot.extras.filters import (
    ComputedFieldFilterSet,
    ConfigContextFilterSet,
    ContentTypeFilterSet,
    CustomFieldChoiceFilterSet,
    CustomLinkFilterSet,
    ExportTemplateFilterSet,
    GitRepositoryFilterSet,
    GraphQLQueryFilterSet,
    ImageAttachmentFilterSet,
    JobFilterSet,
    JobButtonFilterSet,
    JobHookFilterSet,
    JobLogEntryFilterSet,
    JobResultFilterSet,
    ObjectChangeFilterSet,
    RelationshipAssociationFilterSet,
    RelationshipFilterSet,
    RoleFilterSet,
    SecretFilterSet,
    SecretsGroupAssociationFilterSet,
    SecretsGroupFilterSet,
    StatusFilterSet,
    TagFilterSet,
    WebhookFilterSet,
)
from nautobot.extras.models import (
    ComputedField,
    ConfigContext,
    CustomField,
    CustomFieldChoice,
    CustomLink,
    ExportTemplate,
    GitRepository,
    GraphQLQuery,
    ImageAttachment,
    Job,
    JobButton,
    JobHook,
    JobLogEntry,
    JobResult,
    ObjectChange,
    Relationship,
    RelationshipAssociation,
    Role,
    Secret,
    SecretsGroup,
    SecretsGroupAssociation,
    Status,
    Tag,
    Webhook,
)
from nautobot.extras.tests.constants import BIG_GRAPHQL_DEVICE_QUERY
from nautobot.ipam.filters import VLANFilterSet
from nautobot.ipam.models import IPAddress, VLAN, VLANGroup, Namespace, Prefix
from nautobot.tenancy.models import Tenant, TenantGroup
from nautobot.virtualization.models import Cluster, ClusterGroup, ClusterType, VirtualMachine

# Use the proper swappable User model
User = get_user_model()


class ComputedFieldTestCase(FilterTestCases.FilterTestCase):
    queryset = ComputedField.objects.all()
    filterset = ComputedFieldFilterSet

    @classmethod
    def setUpTestData(cls):
        ComputedField.objects.create(
            content_type=ContentType.objects.get_for_model(Location),
            key="computed_field_one",
            label="Computed Field One",
            template="{{ obj.name }} is the name of this location.",
            fallback_value="An error occurred while rendering this template.",
            weight=100,
        )
        # Field whose template will raise a TemplateError
        ComputedField.objects.create(
            content_type=ContentType.objects.get_for_model(Location),
            key="bad_computed_field",
            label="Bad Computed Field",
            template="{{ something_that_throws_an_err | not_a_real_filter }} bad data",
            fallback_value="This template has errored",
            weight=100,
        )
        # Field whose template will raise a TypeError
        ComputedField.objects.create(
            content_type=ContentType.objects.get_for_model(Location),
            key="worse_computed_field",
            label="Worse Computed Field",
            template="{{ obj.images | list }}",
            fallback_value="Another template error",
            weight=200,
        )
        ComputedField.objects.create(
            content_type=ContentType.objects.get_for_model(Device),
            key="device_computed_field",
            label="Device Computed Field",
            template="Hello, world.",
            fallback_value="This template has errored",
            weight=100,
        )

    def test_key(self):
        params = {"key": ["device_computed_field", "worse_computed_field"]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)

    def test_content_type(self):
        params = {"content_type": "dcim.location"}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 3)

    def test_template(self):
        params = {"template": ["Hello, world."]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 1)

    def test_fallback_value(self):
        params = {"fallback_value": ["This template has errored"]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)

    def test_weight(self):
        params = {"weight": [100]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 3)

    def test_search(self):
        # label
        params = {"q": "Field One"}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 1)
        # content_type__app_label
        params = {"q": "dcim"}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 4)
        # content_type__model
        params = {"q": "location"}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 3)
        # template
        params = {"q": "hello"}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 1)
        # fallback_value
        params = {"q": "has errored"}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)


class ConfigContextTestCase(FilterTestCases.FilterTestCase):
    queryset = ConfigContext.objects.all()
    filterset = ConfigContextFilterSet

    @classmethod
    def setUpTestData(cls):
        cls.locations = Location.objects.filter(location_type=LocationType.objects.get(name="Campus"))[:3]

        device_roles = Role.objects.get_for_model(Device)
        cls.device_roles = device_roles

        manufacturer = Manufacturer.objects.first()

        device_types = (
            DeviceType.objects.create(model="Device Type 1", manufacturer=manufacturer),
            DeviceType.objects.create(model="Device Type 2", manufacturer=manufacturer),
            DeviceType.objects.create(model="Device Type 3", manufacturer=manufacturer),
        )
        cls.device_types = device_types

        platforms = Platform.objects.all()[:3]
        cls.platforms = platforms

        cls.locations = Location.objects.all()[:3]

        cluster_groups = (
            ClusterGroup.objects.create(name="Cluster Group 1"),
            ClusterGroup.objects.create(name="Cluster Group 2"),
            ClusterGroup.objects.create(name="Cluster Group 3"),
        )

        cluster_type = ClusterType.objects.create(name="Cluster Type 1")
        clusters = (
            Cluster.objects.create(name="Cluster 1", cluster_type=cluster_type),
            Cluster.objects.create(name="Cluster 2", cluster_type=cluster_type),
            Cluster.objects.create(name="Cluster 3", cluster_type=cluster_type),
        )

        cls.tenant_groups = TenantGroup.objects.filter(tenants__isnull=True)[:3]

        cls.tenants = Tenant.objects.filter(tenant_group__isnull=True)[:3]

        for i in range(0, 3):
            is_active = bool(i % 2)
            c = ConfigContext.objects.create(
                name=f"Config Context {i + 1}",
                is_active=is_active,
                data='{"foo": 123}',
            )
            c.locations.set([cls.locations[i]])
            c.roles.set([device_roles[i]])
            c.device_types.set([device_types[i]])
            c.platforms.set([platforms[i]])
            c.cluster_groups.set([cluster_groups[i]])
            c.clusters.set([clusters[i]])
            c.tenant_groups.set([cls.tenant_groups[i]])
            c.tenants.set([cls.tenants[i]])
            c.locations.set([cls.locations[i]])

    def test_name(self):
        params = {"name": ["Config Context 1", "Config Context 2"]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)

    def test_is_active(self):
        params = {"is_active": True}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 1)
        params = {"is_active": False}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)

    def test_location(self):
        params = {"location_id": [self.locations[0].pk, self.locations[1].pk]}
        self.assertQuerysetEqualAndNotEmpty(
            self.filterset(params, self.queryset).qs, self.queryset.filter(locations__in=params["location_id"])
        )
        params = {"location": [self.locations[0].name, self.locations[1].name]}
        self.assertQuerysetEqualAndNotEmpty(
            self.filterset(params, self.queryset).qs, self.queryset.filter(locations__name__in=params["location"])
        )

    def test_role(self):
        device_role = Role.objects.get_for_model(Device).first()
        vm_role = Role.objects.get_for_model(VirtualMachine).first()
        params = {"role": [device_role.pk, vm_role.name]}
        self.assertQuerysetEqualAndNotEmpty(
            self.filterset(params, self.queryset).qs,
            self.queryset.filter(roles__in=[vm_role, device_role]).distinct(),
        )

    def test_type(self):
        device_types = list(self.device_types[:2])
        filter_params = [
            {"device_type_id": [device_types[0].pk, device_types[1].pk]},
            {"device_type": [device_types[0].pk, device_types[1].model]},
        ]
        for params in filter_params:
            self.assertQuerysetEqualAndNotEmpty(
                self.filterset(params, self.queryset).qs, self.queryset.filter(device_types__in=device_types).distinct()
            )

    def test_platform(self):
        platforms = list(self.platforms[:2])
        filter_params = [
            {"platform_id": [platforms[0].pk, platforms[1].pk]},
            {"platform": [platforms[0].pk, platforms[1].name]},
        ]
        for params in filter_params:
            self.assertQuerysetEqualAndNotEmpty(
                self.filterset(params, self.queryset).qs, self.queryset.filter(platforms__in=platforms).distinct()
            )

    def test_cluster_group(self):
        cluster_groups = list(ClusterGroup.objects.all()[:2])
        filter_params = [
            {"cluster_group_id": [cluster_groups[0].pk, cluster_groups[1].pk]},
            {"cluster_group": [cluster_groups[0].pk, cluster_groups[1].name]},
        ]
        for params in filter_params:
            self.assertQuerysetEqualAndNotEmpty(
                self.filterset(params, self.queryset).qs,
                self.queryset.filter(cluster_groups__in=cluster_groups).distinct(),
            )

    def test_cluster(self):
        clusters = Cluster.objects.all()[:2]
        params = {"cluster_id": [clusters[0].pk, clusters[1].pk]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)

    def test_tenant_group(self):
        tenant_groups = list(self.tenant_groups[:2])
        filter_params = [
            {"tenant_group_id": [tenant_groups[0].pk, tenant_groups[1].pk]},
            {"tenant_group": [tenant_groups[0].name, tenant_groups[1].pk]},
        ]
        for params in filter_params:
            self.assertQuerysetEqualAndNotEmpty(
                self.filterset(params, self.queryset).qs,
                self.queryset.filter(tenant_groups__in=tenant_groups).distinct(),
            )

    def test_tenant(self):
        tenants = list(self.tenants[:2])
        filter_params = [
            {"tenant_id": [tenants[0].pk, tenants[1].pk]},
            {"tenant": [tenants[0].name, tenants[1].pk]},
        ]
        for params in filter_params:
            self.assertQuerysetEqualAndNotEmpty(
                self.filterset(params, self.queryset).qs, self.queryset.filter(tenants__in=tenants).distinct()
            )

    def test_search(self):
        value = self.queryset.values_list("pk", flat=True)[0]
        params = {"q": value}
        self.assertEqual(self.filterset(params, self.queryset).qs.values_list("pk", flat=True)[0], value)

    @override_settings(CONFIG_CONTEXT_DYNAMIC_GROUPS_ENABLED=True)
    def test_with_dynamic_groups_enabled(self):
        """Asserts that `ConfigContextFilterSet.dynamic_group` is present when feature flag is enabled."""
        filter_set = ConfigContextFilterSet()
        self.assertIn("dynamic_groups", filter_set.filters)

    @override_settings(CONFIG_CONTEXT_DYNAMIC_GROUPS_ENABLED=False)
    def test_without_dynamic_groups_enabled(self):
        """Tests that `ConfigContextFilterSet.dynamic_group` is NOT present when feature flag is disabled."""
        filter_set = ConfigContextFilterSet()
        self.assertNotIn("dynamic_groups", filter_set.filters)


class ContentTypeFilterSetTestCase(FilterTestCases.FilterTestCase):
    queryset = ContentType.objects.order_by("app_label", "model")
    filterset = ContentTypeFilterSet

    def test_app_label(self):
        params = {"app_label": ["dcim"]}
        self.assertQuerysetEqual(self.filterset(params, self.queryset).qs, self.queryset.filter(app_label="dcim"))

    def test_model(self):
        params = {"model": ["device", "virtualmachine"]}
        self.assertQuerysetEqual(
            self.filterset(params, self.queryset).qs, self.queryset.filter(model__in=["device", "virtualmachine"])
        )

    def test_search(self):
        params = {"q": "circ"}
        self.assertQuerysetEqual(
            self.filterset(params, self.queryset).qs,
            self.queryset.filter(Q(app_label__icontains="circ") | Q(model__icontains="circ")),
        )


class CustomFieldChoiceFilterSetTestCase(FilterTestCases.FilterTestCase):
    queryset = CustomFieldChoice.objects.all()
    filterset = CustomFieldChoiceFilterSet

    generic_filter_tests = (
        ["value"],
        ["custom_field", "custom_field__key"],
        ["weight"],
    )

    @classmethod
    def setUpTestData(cls):
        obj_type = ContentType.objects.get_for_model(Device)
        cfs = [
            CustomField.objects.create(label=f"Custom Field {num}", type=CustomFieldTypeChoices.TYPE_TEXT)
            for num in range(3)
        ]
        for cf in cfs:
            cf.content_types.set([obj_type])

        for i, val in enumerate(["Value 1", "Value 2", "Value 3"]):
            CustomFieldChoice.objects.create(custom_field=cfs[i], value=val, weight=100 * i)


class CustomLinkTestCase(FilterTestCases.FilterTestCase):
    queryset = CustomLink.objects.all()
    filterset = CustomLinkFilterSet

    @classmethod
    def setUpTestData(cls):
        obj_type = ContentType.objects.get_for_model(Location)

        CustomLink.objects.create(
            content_type=obj_type,
            name="customlink-1",
            text="customlink text 1",
            target_url="http://customlink1.com",
            weight=100,
            button_class="default",
            new_window=False,
        )
        CustomLink.objects.create(
            content_type=obj_type,
            name="customlink-2",
            text="customlink text 2",
            target_url="http://customlink2.com",
            weight=100,
            button_class="default",
            new_window=False,
        )
        CustomLink.objects.create(
            content_type=obj_type,
            name="customlink-3",
            text="customlink text 3",
            target_url="http://customlink3.com",
            weight=100,
            button_class="default",
            new_window=False,
        )

    def test_name(self):
        params = {"name": ["customlink-1"]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 1)

    def test_target_url(self):
        params = {"target_url": ["http://customlink1.com"]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 1)

    def test_weight(self):
        params = {"weight": [100]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 3)

    def test_search(self):
        params = {"q": "customlink"}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 3)


class CustomFieldChoiceTestCase(FilterTestCases.FilterTestCase):
    queryset = CustomFieldChoice.objects.all()
    filterset = CustomFieldChoiceFilterSet

    @classmethod
    def setUpTestData(cls):
        content_type = ContentType.objects.get_for_model(Location)
        fields = [
            CustomField.objects.create(type=CustomFieldTypeChoices.TYPE_TEXT, label=f"field {num}", required=False)
            for num in range(3)
        ]
        cls.fields = fields
        for field in fields:
            field.content_types.set([content_type])

        for num in range(3):
            CustomFieldChoice.objects.create(custom_field=fields[num], value=f"Custom Field Choice {num}")

    def test_field(self):
        fields = list(self.fields[:2])
        filter_params = [
            {"custom_field": [fields[0].key, fields[1].pk]},
        ]
        for params in filter_params:
            self.assertQuerysetEqualAndNotEmpty(
                self.filterset(params, self.queryset).qs, self.queryset.filter(custom_field__in=fields).distinct()
            )


class ExportTemplateTestCase(FilterTestCases.FilterTestCase):
    queryset = ExportTemplate.objects.all()
    filterset = ExportTemplateFilterSet

    @classmethod
    def setUpTestData(cls):
        content_types = ContentType.objects.filter(model__in=["location", "rack", "device"])

        ExportTemplate.objects.create(
            name="Export Template 1",
            content_type=content_types[0],
            template_code="TESTING",
        )
        ExportTemplate.objects.create(
            name="Export Template 2",
            content_type=content_types[1],
            template_code="TESTING",
        )
        ExportTemplate.objects.create(
            name="Export Template 3",
            content_type=content_types[2],
            template_code="TESTING",
        )

    def test_name(self):
        params = {"name": ["Export Template 1", "Export Template 2"]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)

    def test_content_type(self):
        params = {"content_type": ContentType.objects.get(model="location").pk}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 1)

    def test_search(self):
        params = {"q": "export"}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 3)


class GitRepositoryTestCase(FilterTestCases.FilterTestCase):
    queryset = GitRepository.objects.all()
    filterset = GitRepositoryFilterSet

    @classmethod
    def setUpTestData(cls):
        # Create Three GitRepository records
        secrets_groups = [
            SecretsGroup.objects.create(name="Secrets Group 1"),
            SecretsGroup.objects.create(name="Secrets Group 2"),
        ]
        cls.secrets_groups = secrets_groups
        repos = (
            GitRepository(
                name="Repo 1",
                slug="repo_1",
                branch="main",
                provided_contents=[
                    "extras.configcontext",
                ],
                remote_url="https://example.com/repo1.git",
                secrets_group=secrets_groups[0],
            ),
            GitRepository(
                name="Repo 2",
                slug="repo_2",
                branch="develop",
                provided_contents=[
                    "extras.configcontext",
                    "extras.job",
                ],
                remote_url="https://example.com/repo2.git",
                secrets_group=secrets_groups[1],
            ),
            GitRepository(
                name="Repo 3",
                slug="repo_3",
                branch="next",
                provided_contents=[
                    "extras.configcontext",
                    "extras.job",
                    "extras.exporttemplate",
                ],
                remote_url="https://example.com/repo3.git",
            ),
        )
        for repo in repos:
            repo.save()
        repos[0].tags.set(Tag.objects.get_for_model(GitRepository))
        repos[1].tags.set(Tag.objects.get_for_model(GitRepository)[:3])

    def test_id(self):
        params = {"id": self.queryset.values_list("pk", flat=True)[:2]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)

    def test_name(self):
        params = {"name": ["Repo 3", "Repo 2"]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)

    def test_remote_url(self):
        params = {"remote_url": ["https://example.com/repo1.git"]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 1)

    def test_branch(self):
        params = {"branch": ["main", "next"]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)

    def test_provided_contents(self):
        params = {"provided_contents": ["extras.exporttemplate"]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 1)
        params = {"provided_contents": ["extras.job"]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)

    def test_secrets_group(self):
        filter_params = [
            {"secrets_group_id": [self.secrets_groups[0].pk, self.secrets_groups[1].pk]},
            {"secrets_group": [self.secrets_groups[0].name, self.secrets_groups[1].pk]},
        ]
        for params in filter_params:
            self.assertQuerysetEqualAndNotEmpty(
                self.filterset(params, self.queryset).qs,
                self.queryset.filter(secrets_group__in=self.secrets_groups).distinct(),
            )


class GraphQLTestCase(FilterTestCases.NameOnlyFilterTestCase):
    queryset = GraphQLQuery.objects.all()
    filterset = GraphQLQueryFilterSet

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
        )

        for query in graphqlqueries:
            query.clean()
            query.save()

    def test_query(self):
        params = {"query": ["locations"]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 3)


class ImageAttachmentTestCase(FilterTestCases.FilterTestCase):
    queryset = ImageAttachment.objects.all()
    filterset = ImageAttachmentFilterSet

    @classmethod
    def setUpTestData(cls):
        location_ct = ContentType.objects.get(app_label="dcim", model="location")
        rack_ct = ContentType.objects.get(app_label="dcim", model="rack")

        locations = Location.objects.filter(location_type=LocationType.objects.get(name="Campus"))[:2]

        rack_status = Status.objects.get_for_model(Rack).first()
        racks = (
            Rack.objects.create(name="Rack 1", location=locations[0], status=rack_status),
            Rack.objects.create(name="Rack 2", location=locations[1], status=rack_status),
        )

        ImageAttachment.objects.create(
            content_type=location_ct,
            object_id=locations[0].pk,
            name="Image Attachment 1",
            image="http://example.com/image1.png",
            image_height=100,
            image_width=100,
        )
        ImageAttachment.objects.create(
            content_type=location_ct,
            object_id=locations[1].pk,
            name="Image Attachment 2",
            image="http://example.com/image2.png",
            image_height=100,
            image_width=100,
        )
        ImageAttachment.objects.create(
            content_type=rack_ct,
            object_id=racks[0].pk,
            name="Image Attachment 3",
            image="http://example.com/image3.png",
            image_height=100,
            image_width=100,
        )
        ImageAttachment.objects.create(
            content_type=rack_ct,
            object_id=racks[1].pk,
            name="Image Attachment 4",
            image="http://example.com/image4.png",
            image_height=100,
            image_width=100,
        )

    def test_name(self):
        params = {"name": ["Image Attachment 1", "Image Attachment 2"]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)

    def test_content_type(self):
        params = {"content_type": "dcim.location"}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)

    def test_content_type_id_and_object_id(self):
        params = {
            "content_type_id": ContentType.objects.get(app_label="dcim", model="location").pk,
            "object_id": [Location.objects.first().pk],
        }
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 1)


class JobFilterSetTestCase(FilterTestCases.NameOnlyFilterTestCase):
    queryset = Job.objects.all()
    filterset = JobFilterSet

    @classmethod
    def setUpTestData(cls):
        Job.objects.first().tags.set(Tag.objects.get_for_model(Job))
        Job.objects.last().tags.set(Tag.objects.get_for_model(Job)[:3])

    def test_grouping(self):
        params = {"grouping": ["file_upload_pass", "file_upload_fail"]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)

    def test_installed(self):
        params = {"job_class_name": "TestPass", "installed": True}
        self.assertTrue(self.filterset(params, self.queryset).qs.exists())

    def test_enabled(self):
        params = {"job_class_name": "TestPass", "enabled": False}
        self.assertTrue(self.filterset(params, self.queryset).qs.exists())

    def test_dryrun_default(self):
        params = {"dryrun_default": True}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 0)

    def test_hidden(self):
        params = {"hidden": True}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 1)

    def test_read_only(self):
        params = {"read_only": True}
        self.assertQuerysetEqualAndNotEmpty(
            self.filterset(params, self.queryset).qs, self.queryset.filter(read_only=True)
        )

    def test_approval_required(self):
        params = {"approval_required": True}
        self.assertQuerysetEqualAndNotEmpty(
            self.filterset(params, self.queryset).qs,
            self.queryset.filter(approval_required=True),
        )

    def test_search(self):
        params = {"q": "file"}
        expected_matches = (
            Q(name__icontains="file")  # pylint: disable=unsupported-binary-operation
            | Q(grouping__icontains="file")
            | Q(description__icontains="file")
        )
        self.assertQuerysetEqualAndNotEmpty(
            self.filterset(params, self.queryset).qs, self.queryset.filter(expected_matches)
        )
        value = self.queryset.values_list("pk", flat=True)[0]
        params = {"q": value}
        self.assertEqual(self.filterset(params, self.queryset).qs.values_list("pk", flat=True)[0], value)

    def test_is_job_hook_receiver(self):
        params = {"is_job_hook_receiver": True}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 4)


class JobResultFilterSetTestCase(FilterTestCases.FilterTestCase):
    queryset = JobResult.objects.all()
    filterset = JobResultFilterSet

    @classmethod
    def setUpTestData(cls):
        jobs = Job.objects.all()[:3]
        cls.jobs = jobs
        for job in jobs:
            JobResult.objects.create(
                job_model=job,
                name=job.class_path,
                user=User.objects.first(),
                status=JobResultStatusChoices.STATUS_STARTED,
            )

    def test_job_model(self):
        jobs = list(self.jobs[:2])
        filter_params = [
            {"job_model_id": [jobs[0].pk, jobs[1].pk]},
            {"job_model": [jobs[0].pk, jobs[1].name]},
        ]
        for params in filter_params:
            self.assertQuerysetEqualAndNotEmpty(
                self.filterset(params, self.queryset).qs, self.queryset.filter(job_model__in=jobs).distinct()
            )


class JobHookFilterSetTestCase(FilterTestCases.NameOnlyFilterTestCase):
    queryset = JobHook.objects.all()
    filterset = JobHookFilterSet

    @classmethod
    def setUpTestData(cls):
        job_hooks = (
            JobHook.objects.create(
                name="JobHook1",
                job=Job.objects.get(job_class_name="TestJobHookReceiverLog"),
                type_create=True,
                type_update=True,
                type_delete=True,
            ),
            JobHook.objects.create(
                name="JobHook2",
                job=Job.objects.get(job_class_name="TestJobHookReceiverChange"),
                type_create=True,
                type_update=True,
                type_delete=False,
            ),
            JobHook.objects.create(
                name="JobHook3",
                enabled=False,
                job=Job.objects.get(job_class_name="TestJobHookReceiverFail"),
                type_delete=True,
            ),
        )

        devicetype_ct = ContentType.objects.get_for_model(DeviceType)
        job_hooks[0].content_types.set([devicetype_ct])
        job_hooks[1].content_types.set([devicetype_ct])

    def test_name(self):
        params = {"name": ["JobHook1", "JobHook2"]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)

    def test_content_types(self):
        params = {"content_types": ["dcim.devicetype"]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)

    def test_enabled(self):
        params = {"enabled": True}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)

    def test_job(self):
        jobs = Job.objects.filter(job_class_name__in=["TestJobHookReceiverLog", "TestJobHookReceiverChange"])[:2]
        params = {"job": [jobs[0].name, jobs[1].pk]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)

    def test_type_create(self):
        params = {"type_create": True}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)

    def test_type_delete(self):
        params = {"type_delete": True}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)

    def test_type_update(self):
        params = {"type_update": True}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)

    def test_search(self):
        params = {"q": "hook"}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 3)
        params = {"q": "hook1"}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 1)


class JobButtonFilterTestCase(FilterTestCases.FilterTestCase):
    queryset = JobButton.objects.all()
    filterset = JobButtonFilterSet

    @classmethod
    def setUpTestData(cls):
        job_buttons = (
            JobButton.objects.create(
                name="JobButton1",
                text="JobButton1",
                job=Job.objects.get(job_class_name="TestJobButtonReceiverSimple"),
                confirmation=True,
                weight=30,
            ),
            JobButton.objects.create(
                name="JobButton2",
                text="JobButton2",
                job=Job.objects.get(job_class_name="TestJobButtonReceiverSimple"),
                confirmation=False,
                weight=40,
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

    def test_name(self):
        params = {"name": ["JobButton1", "JobButton2"]}
        self.assertQuerysetEqualAndNotEmpty(
            self.filterset(params, self.queryset).qs, self.queryset.filter(name__in=["JobButton1", "JobButton2"])
        )

    def test_job(self):
        job = Job.objects.get(job_class_name="TestJobButtonReceiverSimple")
        params = {"job": [job.pk]}
        self.assertQuerysetEqualAndNotEmpty(
            self.filterset(params, self.queryset).qs, self.queryset.filter(job__pk=job.pk)
        )

        params = {"job": [job.name]}
        self.assertQuerysetEqualAndNotEmpty(
            self.filterset(params, self.queryset).qs, self.queryset.filter(job__name=job.name)
        )

    def test_weight(self):
        params = {"weight": [30, 50]}
        self.assertQuerysetEqualAndNotEmpty(
            self.filterset(params, self.queryset).qs, self.queryset.filter(weight__in=[30, 50])
        )

    def test_search(self):
        params = {"q": "JobButton"}
        self.assertQuerysetEqualAndNotEmpty(
            self.filterset(params, self.queryset).qs,
            self.queryset.filter(name__in=["JobButton1", "JobButton2", "JobButton3"]),
        )


class JobLogEntryTestCase(FilterTestCases.FilterTestCase):
    queryset = JobLogEntry.objects.all()
    filterset = JobLogEntryFilterSet

    @classmethod
    def setUpTestData(cls):
        cls.job_result = JobResult.objects.create(name="test")

        for log_level in ("debug", "info", "warning", "error", "critical"):
            JobLogEntry.objects.create(
                log_level=log_level,
                grouping="run",
                job_result=cls.job_result,
                message=f"I am a {log_level} log.",
            )

    def test_log_level(self):
        params = {"log_level": ["debug"]}
        self.assertQuerysetEqualAndNotEmpty(
            self.filterset(params, self.queryset).qs, self.queryset.filter(log_level="debug")
        )

    def test_grouping(self):
        params = {"grouping": ["run"]}
        self.assertQuerysetEqualAndNotEmpty(
            self.filterset(params, self.queryset).qs, self.queryset.filter(grouping="run")
        )

    def test_message(self):
        params = {"message": ["I am a debug log."]}
        self.assertQuerysetEqualAndNotEmpty(
            self.filterset(params, self.queryset).qs, self.queryset.filter(message="I am a debug log.")
        )

    def test_search(self):
        params = {"q": "run"}
        self.assertQuerysetEqualAndNotEmpty(
            self.filterset(params, self.queryset).qs, self.queryset.filter(grouping__icontains="run")
        )
        params = {"q": "warning log"}
        self.assertQuerysetEqualAndNotEmpty(
            self.filterset(params, self.queryset).qs, self.queryset.filter(message__icontains="warning log")
        )
        params = {"q": "debug"}
        self.assertQuerysetEqualAndNotEmpty(
            self.filterset(params, self.queryset).qs, self.queryset.filter(log_level__icontains="debug")
        )


class ObjectChangeTestCase(FilterTestCases.FilterTestCase):
    queryset = ObjectChange.objects.all()
    filterset = ObjectChangeFilterSet

    @classmethod
    def setUpTestData(cls):
        users = (
            User.objects.create(username="user1"),
            User.objects.create(username="user2"),
            User.objects.create(username="user3"),
        )

        location = Location.objects.first()
        ipaddr_status = Status.objects.get_for_model(IPAddress).first()
        prefix_status = Status.objects.get_for_model(Prefix).first()
        namespace = Namespace.objects.first()
        Prefix.objects.create(prefix="192.0.2.0/24", namespace=namespace, status=prefix_status)
        ipaddress = IPAddress.objects.create(address="192.0.2.1/24", namespace=namespace, status=ipaddr_status)

        ObjectChange.objects.create(
            user=users[0],
            user_name=users[0].username,
            request_id=uuid.uuid4(),
            action=ObjectChangeActionChoices.ACTION_CREATE,
            changed_object=location,
            object_repr=str(location),
            object_data={"name": location.name},
        )
        ObjectChange.objects.create(
            user=users[0],
            user_name=users[0].username,
            request_id=uuid.uuid4(),
            action=ObjectChangeActionChoices.ACTION_UPDATE,
            changed_object=location,
            object_repr=str(location),
            object_data={"name": location.name},
        )
        ObjectChange.objects.create(
            user=users[1],
            user_name=users[1].username,
            request_id=uuid.uuid4(),
            action=ObjectChangeActionChoices.ACTION_DELETE,
            changed_object=location,
            object_repr=str(location),
            object_data={"name": location.name},
        )
        ObjectChange.objects.create(
            user=users[1],
            user_name=users[1].username,
            request_id=uuid.uuid4(),
            action=ObjectChangeActionChoices.ACTION_CREATE,
            changed_object=ipaddress,
            object_repr=str(ipaddress),
            object_data={"address": str(ipaddress.address), "status": str(ipaddress.status)},
        )
        ObjectChange.objects.create(
            user=users[2],
            user_name=users[2].username,
            request_id=uuid.uuid4(),
            action=ObjectChangeActionChoices.ACTION_UPDATE,
            changed_object=ipaddress,
            object_repr=str(ipaddress),
            object_data={"address": str(ipaddress.address), "status": str(ipaddress.status)},
        )
        ObjectChange.objects.create(
            user=users[2],
            user_name=users[2].username,
            request_id=uuid.uuid4(),
            action=ObjectChangeActionChoices.ACTION_DELETE,
            changed_object=ipaddress,
            object_repr=str(ipaddress),
            object_data={"address": str(ipaddress.address), "status": str(ipaddress.status)},
        )

    def test_user(self):
        users = list(User.objects.filter(username__in=["user1", "user2"]))
        filter_params = [
            {"user_id": [users[0].pk, users[1].pk]},
            {"user": [users[0].pk, users[1].username]},
        ]
        for params in filter_params:
            self.assertQuerysetEqualAndNotEmpty(
                self.filterset(params, self.queryset).qs, self.queryset.filter(user__in=users).distinct()
            )

    def test_user_name(self):
        params = {"user_name": ["user1", "user2"]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 4)

    def test_changed_object_type(self):
        params = {"changed_object_type": "dcim.location"}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 3)

    def test_changed_object_type_id(self):
        params = {"changed_object_type_id": ContentType.objects.get(app_label="dcim", model="location").pk}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 3)

    def test_search(self):
        value = self.queryset.values_list("pk", flat=True)[0]
        params = {"q": value}
        self.assertEqual(self.filterset(params, self.queryset).qs.values_list("pk", flat=True)[0], value)


class RelationshipTestCase(FilterTestCases.FilterTestCase):
    queryset = Relationship.objects.all()
    filterset = RelationshipFilterSet

    @classmethod
    def setUpTestData(cls):
        device_type = ContentType.objects.get_for_model(Device)
        interface_type = ContentType.objects.get_for_model(Interface)
        vlan_type = ContentType.objects.get_for_model(VLAN)

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
            key="primary_interface",
            type="one-to-one",
            source_type=device_type,
            destination_type=interface_type,
        ).validated_save()

    def test_label(self):
        """Verify that the filterset supports filtering by label."""
        params = {"label": list(self.queryset.values_list("label", flat=True)[:2])}
        filterset = self.filterset(params, self.queryset)
        self.assertTrue(filterset.is_valid())
        self.assertQuerysetEqualAndNotEmpty(
            filterset.qs.order_by("label"), self.queryset.filter(label__in=params["label"]).order_by("label")
        )

    def test_key(self):
        """Verify that the filterset supports filtering by key."""
        params = {"key": self.queryset.values_list("key", flat=True)[:2]}
        filterset = self.filterset(params, self.queryset)
        self.assertTrue(filterset.is_valid())
        self.assertEqual(filterset.qs.count(), 2)

    def test_type(self):
        params = {"type": ["one-to-many"]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 1)

    def test_source_type(self):
        params = {"source_type": ["dcim.device"]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)

    def test_destination_type(self):
        params = {"destination_type": ["ipam.vlan", "dcim.interface"]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)


class RelationshipAssociationTestCase(FilterTestCases.FilterTestCase):
    queryset = RelationshipAssociation.objects.all()
    filterset = RelationshipAssociationFilterSet

    @classmethod
    def setUpTestData(cls):
        cls.device_type = ContentType.objects.get_for_model(Device)
        cls.vlan_type = ContentType.objects.get_for_model(VLAN)

        cls.relationships = (
            Relationship(
                label="Device VLANs",
                key="device_vlans",
                type="many-to-many",
                source_type=cls.device_type,
                destination_type=cls.vlan_type,
            ),
            Relationship(
                label="Primary VLAN",
                key="primary_vlan",
                type="one-to-many",
                source_type=cls.vlan_type,
                destination_type=cls.device_type,
            ),
            Relationship(
                label="Device Device",
                key="symmetric_device_device",
                type="symmetric-many-to-many",
                source_type=cls.device_type,
                destination_type=cls.device_type,
            ),
        )
        for relationship in cls.relationships:
            relationship.validated_save()

        manufacturer = Manufacturer.objects.first()
        devicetype = DeviceType.objects.create(manufacturer=manufacturer, model="Device Type 1")
        devicerole = Role.objects.get_for_model(Device).first()
        devicestatus = Status.objects.get_for_model(Device).first()
        location = Location.objects.filter(location_type=LocationType.objects.get(name="Campus")).first()
        cls.devices = (
            Device.objects.create(
                name="Device 1", device_type=devicetype, role=devicerole, status=devicestatus, location=location
            ),
            Device.objects.create(
                name="Device 2", device_type=devicetype, role=devicerole, status=devicestatus, location=location
            ),
            Device.objects.create(
                name="Device 3", device_type=devicetype, role=devicerole, status=devicestatus, location=location
            ),
        )
        vlan_status = Status.objects.get_for_model(VLAN).first()
        vlan_group = VLANGroup.objects.first()
        cls.vlans = (
            VLAN.objects.create(vid=1, name="VLAN 1", status=vlan_status, vlan_group=vlan_group),
            VLAN.objects.create(vid=2, name="VLAN 2", status=vlan_status, vlan_group=vlan_group),
        )

        RelationshipAssociation(
            relationship=cls.relationships[0],
            source_type=cls.device_type,
            source_id=cls.devices[0].pk,
            destination_type=cls.vlan_type,
            destination_id=cls.vlans[0].pk,
        ).validated_save()
        RelationshipAssociation(
            relationship=cls.relationships[0],
            source_type=cls.device_type,
            source_id=cls.devices[1].pk,
            destination_type=cls.vlan_type,
            destination_id=cls.vlans[1].pk,
        ).validated_save()
        RelationshipAssociation(
            relationship=cls.relationships[1],
            source_type=cls.vlan_type,
            source_id=cls.vlans[0].pk,
            destination_type=cls.device_type,
            destination_id=cls.devices[0].pk,
        ).validated_save()
        RelationshipAssociation(
            relationship=cls.relationships[1],
            source_type=cls.vlan_type,
            source_id=cls.vlans[1].pk,
            destination_type=cls.device_type,
            destination_id=cls.devices[1].pk,
        ).validated_save()
        RelationshipAssociation(
            relationship=cls.relationships[2],
            source_type=cls.device_type,
            source_id=cls.devices[0].pk,
            destination_type=cls.device_type,
            destination_id=cls.devices[1].pk,
        ).validated_save()
        RelationshipAssociation(
            relationship=cls.relationships[2],
            source_type=cls.device_type,
            source_id=cls.devices[1].pk,
            destination_type=cls.device_type,
            destination_id=cls.devices[2].pk,
        ).validated_save()

    def test_relationship(self):
        params = {"relationship": [self.relationships[0].key]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)

    def test_source_type(self):
        params = {"source_type": ["dcim.device", "dcim.interface"]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 4)

    def test_source_id(self):
        params = {"source_id": [self.devices[0].pk, self.devices[1].pk]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 4)

    def test_destination_type(self):
        params = {"destination_type": ["dcim.device", "dcim.interface"]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 4)

    def test_destination_id(self):
        params = {"destination_id": [self.devices[0].pk, self.devices[1].pk]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 3)

    def test_peer_id(self):
        params = {"peer_id": [self.devices[0].pk, self.devices[1].pk]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)
        params = {"peer_id": [self.devices[2].pk]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 1)


class RelationshipModelFilterSetTestCase(FilterTestCases.FilterTestCase):
    queryset = RelationshipAssociation.objects.all()
    filterset = RelationshipAssociationFilterSet

    @classmethod
    def setUpTestData(cls):
        cls.device_type = ContentType.objects.get_for_model(Device)
        cls.vlan_type = ContentType.objects.get_for_model(VLAN)
        cls.relationships = (
            Relationship(
                label="Device VLANs",
                key="device_vlans",
                type="many-to-many",
                source_type=cls.device_type,
                destination_type=cls.vlan_type,
            ),
            Relationship(
                label="Primary VLAN",
                key="primary_vlan",
                type="one-to-many",
                source_type=cls.vlan_type,
                destination_type=cls.device_type,
            ),
            Relationship(
                label="Device Peers",
                key="device_peers",
                type="symmetric-many-to-many",
                source_type=cls.device_type,
                destination_type=cls.device_type,
            ),
        )
        for relationship in cls.relationships:
            relationship.validated_save()

        manufacturer = Manufacturer.objects.first()
        devicetype = DeviceType.objects.create(manufacturer=manufacturer, model="Device Type 1")
        devicerole = Role.objects.get_for_model(Device).first()
        devicestatus = Status.objects.get_for_model(Device).first()
        location = Location.objects.filter(location_type=LocationType.objects.get(name="Campus")).first()
        cls.devices = (
            Device.objects.create(
                name="Device 1", device_type=devicetype, role=devicerole, status=devicestatus, location=location
            ),
            Device.objects.create(
                name="Device 2", device_type=devicetype, role=devicerole, status=devicestatus, location=location
            ),
            Device.objects.create(
                name="Device 3", device_type=devicetype, role=devicerole, status=devicestatus, location=location
            ),
        )
        vlan_status = Status.objects.get_for_model(VLAN).first()
        vlan_group = VLANGroup.objects.first()
        cls.vlans = (
            VLAN.objects.create(vid=1, name="VLAN 1", status=vlan_status, vlan_group=vlan_group),
            VLAN.objects.create(vid=2, name="VLAN 2", status=vlan_status, vlan_group=vlan_group),
            VLAN.objects.create(vid=3, name="VLAN 3", status=vlan_status, vlan_group=vlan_group),
        )
        cls.relationship_associations = (
            RelationshipAssociation(
                relationship=cls.relationships[0],
                source_type=cls.device_type,
                source_id=cls.devices[0].pk,
                destination_type=cls.vlan_type,
                destination_id=cls.vlans[0].pk,
            ),
            RelationshipAssociation(
                relationship=cls.relationships[0],
                source_type=cls.device_type,
                source_id=cls.devices[1].pk,
                destination_type=cls.vlan_type,
                destination_id=cls.vlans[1].pk,
            ),
            RelationshipAssociation(
                relationship=cls.relationships[1],
                source_type=cls.vlan_type,
                source_id=cls.vlans[0].pk,
                destination_type=cls.device_type,
                destination_id=cls.devices[0].pk,
            ),
            RelationshipAssociation(
                relationship=cls.relationships[1],
                source_type=cls.vlan_type,
                source_id=cls.vlans[0].pk,
                destination_type=cls.device_type,
                destination_id=cls.devices[1].pk,
            ),
            RelationshipAssociation(
                relationship=cls.relationships[1],
                source_type=cls.vlan_type,
                source_id=cls.vlans[0].pk,
                destination_type=cls.device_type,
                destination_id=cls.devices[2].pk,
            ),
            RelationshipAssociation(
                relationship=cls.relationships[2],
                source_type=cls.device_type,
                source_id=cls.devices[0].pk,
                destination_type=cls.device_type,
                destination_id=cls.devices[1].pk,
            ),
            RelationshipAssociation(
                relationship=cls.relationships[2],
                source_type=cls.device_type,
                source_id=cls.devices[0].pk,
                destination_type=cls.device_type,
                destination_id=cls.devices[2].pk,
            ),
            RelationshipAssociation(
                relationship=cls.relationships[2],
                source_type=cls.device_type,
                source_id=cls.devices[1].pk,
                destination_type=cls.device_type,
                destination_id=cls.devices[2].pk,
            ),
        )
        for relationship_association in cls.relationship_associations:
            relationship_association.validated_save()

    def test_one_to_many_source(self):
        self.queryset = Device.objects.all()
        self.filterset = DeviceFilterSet
        self.assertEqual(
            self.filterset({f"cr_{self.relationships[1].key}__source": [self.vlans[0].pk]}, self.queryset).qs.count(),
            3,
        )

    def test_one_to_many_destination(self):
        self.queryset = VLAN.objects.all()
        self.filterset = VLANFilterSet
        self.assertEqual(
            self.filterset(
                {f"cr_{self.relationships[1].key}__destination": [self.devices[0].pk, self.devices[1].pk]},
                self.queryset,
            ).qs.count(),
            1,
        )

    def test_many_to_many_source(self):
        self.queryset = VLAN.objects.all()
        self.filterset = VLANFilterSet
        self.assertEqual(
            self.filterset(
                {f"cr_{self.relationships[0].key}__source": [self.devices[0].pk, self.devices[1].pk]}, self.queryset
            ).qs.count(),
            2,
        )

    def test_many_to_many_destination(self):
        self.queryset = Device.objects.all()
        self.filterset = DeviceFilterSet
        self.assertEqual(
            self.filterset(
                {f"cr_{self.relationships[0].key}__destination": [self.vlans[0].pk, self.vlans[1].pk]}, self.queryset
            ).qs.count(),
            2,
        )

    def test_many_to_many_peer(self):
        self.queryset = Device.objects.all()
        self.filterset = DeviceFilterSet
        self.assertEqual(
            self.filterset(
                {f"cr_{self.relationships[2].key}__peer": [self.devices[0].pk, self.devices[1].pk]}, self.queryset
            ).qs.count(),
            3,
        )
        self.assertEqual(
            self.filterset({f"cr_{self.relationships[2].key}__peer": [self.devices[2].pk]}, self.queryset).qs.count(),
            2,
        )

    def test_combination(self):
        self.queryset = Device.objects.all()
        self.filterset = DeviceFilterSet
        self.assertEqual(
            self.filterset(
                {
                    f"cr_{self.relationships[2].key}__peer": [self.devices[0].pk, self.devices[1].pk],
                    f"cr_{self.relationships[0].key}__destination": [self.vlans[0].pk, self.vlans[1].pk],
                },
                self.queryset,
            ).qs.count(),
            2,
        )
        self.assertEqual(
            self.filterset(
                {
                    f"cr_{self.relationships[2].key}__peer": [self.devices[2].pk],
                    f"cr_{self.relationships[0].key}__destination": [self.vlans[0].pk, self.vlans[1].pk],
                },
                self.queryset,
            ).qs.count(),
            2,
        )

    def test_regression_distinct_2963(self):
        """
        Regression tests for issue #2963 to  address `AssertionError` error when combining filtering on
        relationships with concrete fields.

        Ref: https://github.com/nautobot/nautobot/issues/2963
        """
        self.queryset = Device.objects.all()
        self.filterset = DeviceFilterSet
        self.assertEqual(
            self.filterset(
                {
                    f"cr_{self.relationships[0].key}__destination": [self.vlans[0].pk, self.vlans[1].pk],
                    "manufacturer": ["manufacturer-1"],
                },
                self.queryset,
            ).qs.count(),
            2,
        )


class SecretTestCase(FilterTestCases.NameOnlyFilterTestCase):
    queryset = Secret.objects.all()
    filterset = SecretFilterSet

    @classmethod
    def setUpTestData(cls):
        secrets = (
            Secret(
                name="Secret 1",
                provider="environment-variable",
                parameters={"variable": "FILTER_TEST_1"},
            ),
            Secret(
                name="Secret 2",
                provider="environment-variable",
                parameters={"variable": "FILTER_TEST_2"},
            ),
            Secret(
                name="Secret 3",
                provider="text-file",
                parameters={"path": "/github-tokens/user/myusername.txt"},
            ),
        )
        for secret in secrets:
            secret.validated_save()
        secrets[0].tags.set(Tag.objects.get_for_model(Secret))
        secrets[1].tags.set(Tag.objects.get_for_model(Secret)[:3])

    def test_provider(self):
        params = {"provider": ["environment-variable"]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)

    def test_search(self):
        value = self.queryset.values_list("pk", flat=True)[0]
        params = {"q": value}
        self.assertEqual(self.filterset(params, self.queryset).qs.values_list("pk", flat=True)[0], value)


class SecretsGroupTestCase(FilterTestCases.NameOnlyFilterTestCase):
    queryset = SecretsGroup.objects.all()
    filterset = SecretsGroupFilterSet

    @classmethod
    def setUpTestData(cls):
        SecretsGroup.objects.create(name="Group 1")
        SecretsGroup.objects.create(name="Group 2")
        SecretsGroup.objects.create(name="Group 3")

    def test_search(self):
        value = self.queryset.values_list("pk", flat=True)[0]
        params = {"q": value}
        self.assertEqual(self.filterset(params, self.queryset).qs.values_list("pk", flat=True)[0], value)


class SecretsGroupAssociationTestCase(FilterTestCases.FilterTestCase):
    queryset = SecretsGroupAssociation.objects.all()
    filterset = SecretsGroupAssociationFilterSet

    generic_filter_tests = (["secrets_group", "secrets_group__id"],)

    @classmethod
    def setUpTestData(cls):
        cls.secrets = (
            Secret(
                name="Secret 1",
                provider="environment-variable",
                parameters={"variable": "FILTER_TEST_1"},
            ),
            Secret(
                name="Secret 2",
                provider="environment-variable",
                parameters={"variable": "FILTER_TEST_2"},
            ),
            Secret(
                name="Secret 3",
                provider="text-file",
                parameters={"path": "/github-tokens/user/myusername.txt"},
            ),
        )

        for secret in cls.secrets:
            secret.validated_save()

        cls.groups = (
            SecretsGroup.objects.create(name="Group 1"),
            SecretsGroup.objects.create(name="Group 2"),
            SecretsGroup.objects.create(name="Group 3"),
        )

        SecretsGroupAssociation.objects.create(
            secrets_group=cls.groups[0],
            secret=cls.secrets[0],
            access_type=SecretsGroupAccessTypeChoices.TYPE_GENERIC,
            secret_type=SecretsGroupSecretTypeChoices.TYPE_USERNAME,
        )
        SecretsGroupAssociation.objects.create(
            secrets_group=cls.groups[1],
            secret=cls.secrets[1],
            access_type=SecretsGroupAccessTypeChoices.TYPE_GENERIC,
            secret_type=SecretsGroupSecretTypeChoices.TYPE_PASSWORD,
        )
        SecretsGroupAssociation.objects.create(
            secrets_group=cls.groups[2],
            secret=cls.secrets[2],
            access_type=SecretsGroupAccessTypeChoices.TYPE_HTTP,
            secret_type=SecretsGroupSecretTypeChoices.TYPE_PASSWORD,
        )

    def test_secret(self):
        filter_params = [
            {"secret_id": [self.secrets[0].pk, self.secrets[1].pk]},
            {"secret": [self.secrets[0].name, self.secrets[1].pk]},
        ]
        for params in filter_params:
            self.assertQuerysetEqualAndNotEmpty(
                self.filterset(params, self.queryset).qs, self.queryset.filter(secret__in=self.secrets[:2]).distinct()
            )

    def test_access_type(self):
        params = {"access_type": [SecretsGroupAccessTypeChoices.TYPE_GENERIC]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)

    def test_secret_type(self):
        params = {"secret_type": [SecretsGroupSecretTypeChoices.TYPE_PASSWORD]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)


class StatusTestCase(FilterTestCases.NameOnlyFilterTestCase):
    queryset = Status.objects.all()
    filterset = StatusFilterSet

    def test_content_types(self):
        ct = ContentType.objects.get_for_model(Device)
        status_count = self.queryset.filter(content_types=ct).count()
        params = {"content_types": ["dcim.device"]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), status_count)

    def test_color(self):
        """Test the color search field."""
        params = {"color": [ColorChoices.COLOR_GREY]}
        self.assertQuerysetEqualAndNotEmpty(
            self.filterset(params, self.queryset).qs, Status.objects.filter(color=ColorChoices.COLOR_GREY)
        )

    def test_search(self):
        params = {"q": "active"}
        # TODO: Remove pylint disable after issue is resolved (see: https://github.com/PyCQA/pylint/issues/7381)
        # pylint: disable=unsupported-binary-operation
        q = Q(id__iexact="active") | Q(name__icontains="active")
        # pylint: enable=unsupported-binary-operation
        q |= Q(content_types__model__icontains="active")
        self.assertQuerysetEqualAndNotEmpty(
            self.filterset(params, self.queryset).qs,
            self.queryset.filter(q).distinct(),
        )
        value = self.queryset.first().pk
        params = {"q": value}
        self.assertQuerysetEqualAndNotEmpty(
            self.filterset(params, self.queryset).qs,
            self.queryset.filter(pk=value),
        )


class TagTestCase(FilterTestCases.NameOnlyFilterTestCase):
    queryset = Tag.objects.all()
    filterset = TagFilterSet

    @classmethod
    def setUpTestData(cls):
        cls.tags = Tag.objects.all()

    def test_color(self):
        params = {"color": [self.tags[0].color, self.tags[1].color]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)

    def test_content_types(self):
        params = {"content_types": ["dcim.location"]}
        filtered_data = self.filterset(params, self.queryset).qs
        self.assertQuerysetEqual(filtered_data, Tag.objects.get_for_model(Location))
        self.assertEqual(filtered_data[0], Tag.objects.get_for_model(Location)[0])

    def test_search(self):
        params = {"q": self.tags[0].name}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 1)
        value = self.queryset.values_list("pk", flat=True)[0]
        params = {"q": value}
        self.assertEqual(self.filterset(params, self.queryset).qs.values_list("pk", flat=True)[0], value)


class WebhookTestCase(FilterTestCases.FilterTestCase):
    queryset = Webhook.objects.all()
    filterset = WebhookFilterSet

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
        obj_type = ContentType.objects.get_for_model(Location)
        for webhook in webhooks:
            webhook.save()
            webhook.content_types.set([obj_type])

    def test_name(self):
        params = {"name": ["webhook-1"]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 1)

    def test_create(self):
        params = {"type_create": True}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 1)

    def test_update(self):
        params = {"type_update": True}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 1)

    def test_delete(self):
        params = {"type_delete": True}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 1)

    def test_enabled(self):
        params = {"enabled": True}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 3)

    def test_search(self):
        params = {"q": "webhook"}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 3)
        value = self.queryset.values_list("pk", flat=True)[0]
        params = {"q": value}
        self.assertEqual(self.filterset(params, self.queryset).qs.values_list("pk", flat=True)[0], value)


class RoleTestCase(FilterTestCases.NameOnlyFilterTestCase):
    queryset = Role.objects.all()
    filterset = RoleFilterSet

    def test_content_types(self):
        device_ct = ContentType.objects.get_for_model(Device)
        rack_ct = ContentType.objects.get_for_model(Rack)
        device_roles = self.queryset.filter(content_types=device_ct)
        params = {"content_types": ["dcim.device"]}
        self.assertQuerysetEqualAndNotEmpty(self.filterset(params, self.queryset).qs, device_roles)

        rack_roles = self.queryset.filter(content_types=rack_ct)
        params = {"content_types": ["dcim.rack"]}
        self.assertQuerysetEqualAndNotEmpty(self.filterset(params, self.queryset).qs, rack_roles)

    def test_color(self):
        """Test the color search field."""
        params = {"color": [ColorChoices.COLOR_AMBER]}
        self.assertQuerysetEqualAndNotEmpty(
            self.filterset(params, self.queryset).qs, Role.objects.filter(color=ColorChoices.COLOR_AMBER)
        )

    def test_weight(self):
        """Test the weight search field."""
        instance = self.queryset.filter(weight__isnull=False).first()
        params = {"weight": [instance.weight]}
        self.assertQuerysetEqualAndNotEmpty(
            self.filterset(params, self.queryset).qs, self.queryset.filter(weight=instance.weight)
        )

    def test_search(self):
        value = self.queryset.first().name
        params = {"q": value}
        self.assertQuerysetEqualAndNotEmpty(
            self.filterset(params, self.queryset).qs,
            self.queryset.filter(name=value).distinct(),
        )
        value = self.queryset.first().pk
        params = {"q": value}
        self.assertQuerysetEqualAndNotEmpty(
            self.filterset(params, self.queryset).qs,
            self.queryset.filter(pk=value),
        )
