from datetime import datetime
import uuid
from zoneinfo import ZoneInfo

from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings, RequestFactory
from django.utils.timezone import now

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
    DynamicGroupTypeChoices,
    JobExecutionType,
    JobQueueTypeChoices,
    JobResultStatusChoices,
    MetadataTypeDataTypeChoices,
    ObjectChangeActionChoices,
    SecretsGroupAccessTypeChoices,
    SecretsGroupSecretTypeChoices,
)
from nautobot.extras.constants import HTTP_CONTENT_TYPE_JSON
from nautobot.extras.filters import (
    ComputedFieldFilterSet,
    ConfigContextFilterSet,
    ContactAssociationFilterSet,
    ContactFilterSet,
    ContentTypeFilterSet,
    CustomFieldChoiceFilterSet,
    CustomLinkFilterSet,
    ExportTemplateFilterSet,
    ExternalIntegrationFilterSet,
    FileProxyFilterSet,
    GitRepositoryFilterSet,
    GraphQLQueryFilterSet,
    ImageAttachmentFilterSet,
    JobButtonFilterSet,
    JobFilterSet,
    JobHookFilterSet,
    JobLogEntryFilterSet,
    JobQueueAssignmentFilterSet,
    JobQueueFilterSet,
    JobResultFilterSet,
    MetadataChoiceFilterSet,
    MetadataTypeFilterSet,
    ObjectChangeFilterSet,
    ObjectMetadataFilterSet,
    RelationshipAssociationFilterSet,
    RelationshipFilterSet,
    RoleFilterSet,
    SavedViewFilterSet,
    SecretFilterSet,
    SecretsGroupAssociationFilterSet,
    SecretsGroupFilterSet,
    StaticGroupAssociationFilterSet,
    StatusFilterSet,
    TagFilterSet,
    TeamFilterSet,
    WebhookFilterSet,
)
from nautobot.extras.models import (
    ComputedField,
    ConfigContext,
    Contact,
    ContactAssociation,
    CustomField,
    CustomFieldChoice,
    CustomLink,
    DynamicGroup,
    ExportTemplate,
    ExternalIntegration,
    FileProxy,
    GitRepository,
    GraphQLQuery,
    ImageAttachment,
    Job,
    JobButton,
    JobHook,
    JobLogEntry,
    JobQueue,
    JobQueueAssignment,
    JobResult,
    MetadataChoice,
    MetadataType,
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
    Webhook,
)
from nautobot.extras.tests.constants import BIG_GRAPHQL_DEVICE_QUERY
from nautobot.ipam.filters import VLANFilterSet
from nautobot.ipam.models import IPAddress, Namespace, Prefix, VLAN, VLANGroup
from nautobot.tenancy.models import Tenant, TenantGroup
from nautobot.users.factory import UserFactory
from nautobot.virtualization.models import Cluster, ClusterGroup, ClusterType

# Use the proper swappable User model
User = get_user_model()


class ComputedFieldTestCase(FilterTestCases.FilterTestCase):
    queryset = ComputedField.objects.all()
    filterset = ComputedFieldFilterSet
    generic_filter_tests = (
        ("fallback_value",),
        ("key",),
        ("template",),
        ("weight",),
    )

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
            weight=300,
        )

    def test_content_type(self):
        params = {"content_type": "dcim.location"}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 3)
        params = {"content_type__n": "dcim.location"}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 1)


class ConfigContextTestCase(FilterTestCases.FilterTestCase):
    queryset = ConfigContext.objects.all()
    filterset = ConfigContextFilterSet
    generic_filter_tests = (
        ("cluster_id", "clusters__id"),
        ("cluster_group", "cluster_groups__id"),
        ("cluster_group", "cluster_groups__name"),
        ("cluster_group_id", "cluster_groups__id"),
        ("device_type", "device_types__id"),
        ("device_type", "device_types__model"),
        ("device_type_id", "device_types__id"),
        ("name",),
        ("platform", "platforms__id"),
        ("platform", "platforms__name"),
        ("platform_id", "platforms__id"),
        ("role", "roles__id"),
        ("role", "roles__name"),
        ("tenant", "tenants__id"),
        ("tenant", "tenants__name"),
        ("tenant_id", "tenants__id"),
        ("tenant_group", "tenant_groups__id"),
        ("tenant_group", "tenant_groups__name"),
        ("tenant_group_id", "tenant_groups__id"),
    )

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
    generic_filter_tests = (
        ("app_label",),
        ("model",),
    )
    user_permissions = [
        "dcim.add_location",
        "extras.change_status",
        "ipam.delete_prefix",
        "tenancy.view_tenant",
    ]

    def setUp(self):
        super().setUp()
        self.factory = RequestFactory(SERVER_NAME="nautobot.example.com")

    def test_can_add(self):
        # With no request user, can't add anything
        params = {"can_add": True}
        self.assertQuerysetEqual(self.filterset(params, self.queryset).qs, self.queryset.none())
        params = {"can_add": False}
        self.assertQuerysetEqual(self.filterset(params, self.queryset).qs, self.queryset)
        # With user, filter by permissions
        request = self.factory.get("/api/extras/content-types/")
        request.user = self.user
        params = {"can_add": True}
        self.assertQuerysetEqual(
            self.filterset(params, self.queryset, request=request).qs,
            self.queryset.filter(app_label="dcim", model="location"),
        )
        params = {"can_add": False}
        self.assertQuerysetEqual(
            self.filterset(params, self.queryset, request=request).qs,
            self.queryset.exclude(app_label="dcim", model="location"),
        )

    def test_can_change(self):
        # With no request user, can't change anything
        params = {"can_change": True}
        self.assertQuerysetEqual(self.filterset(params, self.queryset).qs, self.queryset.none())
        params = {"can_change": False}
        self.assertQuerysetEqual(self.filterset(params, self.queryset).qs, self.queryset)
        # With user, filter by permissions
        request = self.factory.get("/api/extras/content-types/")
        request.user = self.user
        params = {"can_change": True}
        self.assertQuerysetEqual(
            self.filterset(params, self.queryset, request=request).qs,
            self.queryset.filter(app_label="extras", model="status"),
        )
        params = {"can_change": False}
        self.assertQuerysetEqual(
            self.filterset(params, self.queryset, request=request).qs,
            self.queryset.exclude(app_label="extras", model="status"),
        )

    def test_can_delete(self):
        # With no request user, can't delete anything
        params = {"can_delete": True}
        self.assertQuerysetEqual(self.filterset(params, self.queryset).qs, self.queryset.none())
        params = {"can_delete": False}
        self.assertQuerysetEqual(self.filterset(params, self.queryset).qs, self.queryset)
        # With user, filter by permissions
        request = self.factory.get("/api/extras/content-types/")
        request.user = self.user
        params = {"can_delete": True}
        self.assertQuerysetEqual(
            self.filterset(params, self.queryset, request=request).qs,
            self.queryset.filter(app_label="ipam", model="prefix"),
        )
        params = {"can_delete": False}
        self.assertQuerysetEqual(
            self.filterset(params, self.queryset, request=request).qs,
            self.queryset.exclude(app_label="ipam", model="prefix"),
        )

    def test_can_view(self):
        # With no request user, can't view anything
        params = {"can_view": True}
        self.assertQuerysetEqual(self.filterset(params, self.queryset).qs, self.queryset.none())
        params = {"can_view": False}
        self.assertQuerysetEqual(self.filterset(params, self.queryset).qs, self.queryset)
        # With user, filter by permissions
        request = self.factory.get("/api/extras/content-types/")
        request.user = self.user
        params = {"can_view": True}
        self.assertQuerysetEqual(
            self.filterset(params, self.queryset, request=request).qs,
            self.queryset.filter(app_label="tenancy", model="tenant"),
        )
        params = {"can_view": False}
        self.assertQuerysetEqual(
            self.filterset(params, self.queryset, request=request).qs,
            self.queryset.exclude(app_label="tenancy", model="tenant"),
        )


class ContactAndTeamFilterSetTestCaseMixin:
    """Mixin class to test common filters to both Contact and Team filter sets."""

    def test_similar_to_location_data(self):
        """Complex test to test the complex `similar_to_location_data` method filter."""
        ContactAssociation.objects.all().delete()
        ObjectMetadata.objects.all().delete()
        self.queryset.delete()
        location_type = LocationType.objects.filter(parent__isnull=True).first()
        location_status = Status.objects.get_for_model(Location).first()
        test_locations = (
            Location.objects.create(
                location_type=location_type,
                name="Filter Test Location 0",
                status=location_status,
                contact_name="match 0",
            ),
            Location.objects.create(
                location_type=location_type,
                name="Filter Test Location 1",
                status=location_status,
                contact_email="Test email for location 1 and 2",
            ),
            Location.objects.create(
                location_type=location_type,
                name="Filter Test Location 2",
                status=location_status,
                contact_email="TEST EMAIL FOR LOCATION 1 AND 2",
                contact_phone="Test phone for location 2 and 3",
            ),
            Location.objects.create(
                location_type=location_type,
                name="Filter Test Location 3",
                status=location_status,
                contact_phone="Test phone for location 2 and 3",
            ),
            Location.objects.create(
                location_type=location_type,
                name="Filter Test Location 4",
                status=location_status,
                contact_name="Hopefully this doesn't match any random factory data",
                contact_email="Hopefully this doesn't match any random factory data",
                contact_phone="Hopefully this doesn't match any random factory data",
                physical_address="Hopefully this doesn't match any random factory data",
                shipping_address="Hopefully this doesn't match any random factory data",
            ),
        )

        self.queryset.create(name="match 0")
        self.queryset.create(name="match 1 and 2", email="Test email for location 1 and 2")
        self.queryset.create(name="match 2 and 3", phone="Test phone for location 2 and 3")

        # These subtests are confusing because we're trying to test the NaturalKeyOrPKMultipleChoiceFilter
        # behavior while also testing the `similar_to_location_data` method filter behavior.
        with self.subTest("Test name match"):
            params = {"similar_to_location_data": [test_locations[0].pk]}
            self.assertQuerysetEqualAndNotEmpty(
                self.filterset(params, self.queryset).qs,
                self.queryset.filter(name__in=["match 0"]),
            )
        with self.subTest("Test email match"):
            params = {"similar_to_location_data": [test_locations[1].pk]}
            self.assertQuerysetEqualAndNotEmpty(
                self.filterset(params, self.queryset).qs,
                self.queryset.filter(name__in=["match 1 and 2"]),
            )
        with self.subTest("Test phone match"):
            params = {"similar_to_location_data": [test_locations[2].pk]}
            self.assertQuerysetEqualAndNotEmpty(
                self.filterset(params, self.queryset).qs,
                self.queryset.filter(name__in=["match 1 and 2", "match 2 and 3"]),
            )
        with self.subTest("Test email and phone match"):
            params = {"similar_to_location_data": [test_locations[1].pk, test_locations[3].name]}
            self.assertQuerysetEqualAndNotEmpty(
                self.filterset(params, self.queryset).qs,
                self.queryset.filter(name__in=["match 1 and 2", "match 2 and 3"]),
            )
        with self.subTest("Test no match"):
            params = {"similar_to_location_data": [test_locations[4].pk]}
            self.assertFalse(self.filterset(params, self.queryset).qs.exists())
            params = {"similar_to_location_data": [test_locations[4].name]}
            self.assertFalse(self.filterset(params, self.queryset).qs.exists())


class ContactFilterSetTestCase(ContactAndTeamFilterSetTestCaseMixin, FilterTestCases.FilterTestCase):
    queryset = Contact.objects.all()
    filterset = ContactFilterSet

    generic_filter_tests = (
        ["name"],
        ["phone"],
        ["email"],
        ["address"],
        ["comments"],
    )


class ContactAssociationFilterSetTestCase(FilterTestCases.FilterTestCase):
    queryset = ContactAssociation.objects.all()
    filterset = ContactAssociationFilterSet

    generic_filter_tests = (
        ["status", "status__id"],
        ["status", "status__name"],
        ["contact", "contact__id"],
        ["contact", "contact__name"],
        ["team", "team__id"],
        ["team", "team__name"],
        ["role", "role__id"],
        ["role", "role__name"],
    )

    @classmethod
    def setUpTestData(cls):
        roles = Role.objects.get_for_model(ContactAssociation)
        statuses = Status.objects.get_for_model(ContactAssociation)
        ip_addresses = IPAddress.objects.all()
        locations = Location.objects.all()

        cls.location_ct = ContentType.objects.get_for_model(Location)
        ipaddress_ct = ContentType.objects.get_for_model(IPAddress)

        ContactAssociation.objects.create(
            contact=Contact.objects.first(),
            associated_object_type=ipaddress_ct,
            associated_object_id=ip_addresses[0].pk,
            role=roles[2],
            status=statuses[1],
        )
        ContactAssociation.objects.create(
            contact=Contact.objects.last(),
            associated_object_type=ipaddress_ct,
            associated_object_id=ip_addresses[1].pk,
            role=roles[1],
            status=statuses[2],
        )
        ContactAssociation.objects.create(
            team=Team.objects.first(),
            associated_object_type=cls.location_ct,
            associated_object_id=locations[0].pk,
            role=roles[3],
            status=statuses[0],
        )
        ContactAssociation.objects.create(
            team=Team.objects.last(),
            associated_object_type=cls.location_ct,
            associated_object_id=locations[1].pk,
            role=roles[0],
            status=statuses[1],
        )

    def test_associated_object_type(self):
        params = {"associated_object_type": "dcim.location"}
        self.assertEqual(
            self.filterset(params, self.queryset).qs.count(),
            ContactAssociation.objects.filter(associated_object_type=self.location_ct).count(),
        )

        params = {"associated_object_type": self.location_ct.pk}
        self.assertEqual(
            self.filterset(params, self.queryset).qs.count(),
            ContactAssociation.objects.filter(associated_object_type=self.location_ct).count(),
        )


class CustomLinkTestCase(FilterTestCases.FilterTestCase):
    queryset = CustomLink.objects.all()
    filterset = CustomLinkFilterSet
    generic_filter_tests = (
        # ("button_class",),  # TODO
        # ("group_name",),  # TODO
        ("name",),
        ("target_url",),
        ("text",),
        ("weight",),
    )

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
            weight=200,
            button_class="default",
            new_window=False,
        )
        CustomLink.objects.create(
            content_type=obj_type,
            name="customlink-3",
            text="customlink text 3",
            target_url="http://customlink3.com",
            weight=300,
            button_class="default",
            new_window=False,
        )


class CustomFieldChoiceTestCase(FilterTestCases.FilterTestCase):
    queryset = CustomFieldChoice.objects.all()
    filterset = CustomFieldChoiceFilterSet
    generic_filter_tests = (
        ("custom_field", "custom_field__key"),
        ("custom_field", "custom_field__id"),
        ("value",),
        ("weight",),
    )

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

        for i, val in enumerate(["Value 1", "Value 2", "Value 3"]):
            CustomFieldChoice.objects.create(custom_field=fields[i], value=val, weight=100 * i)


class ExportTemplateTestCase(FilterTestCases.FilterTestCase):
    queryset = ExportTemplate.objects.all()
    filterset = ExportTemplateFilterSet
    generic_filter_tests = (("name",),)

    @classmethod
    def setUpTestData(cls):
        content_types = ContentType.objects.filter(model__in=["location", "rack", "device"])
        repo = GitRepository.objects.create(
            name="Test Git Repository",
            slug="test_git_repo",
            remote_url="http://localhost/git.git",
        )
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
            owner=repo,
        )

    def test_content_type(self):
        params = {"content_type": ContentType.objects.get(model="location").pk}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 1)
        params = {"content_type__n": ContentType.objects.get(model="location").pk}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)


class FileProxyTestCase(FilterTestCases.FilterTestCase):
    queryset = FileProxy.objects.all()
    filterset = FileProxyFilterSet

    generic_filter_tests = (
        ["job", "job_result__job_model__id"],
        ["job", "job_result__job_model__name"],
        ["job_result_id"],
        ["name"],
        ["uploaded_at"],
    )

    @classmethod
    def setUpTestData(cls):
        jobs = Job.objects.all()[:3]
        job_results = (JobResult.objects.create(job_model=job) for job in jobs)
        for i, job_result in enumerate(job_results):
            FileProxy.objects.create(
                name=f"File {i}.txt", file=SimpleUploadedFile(name=f"File {i}.txt", content=b""), job_result=job_result
            )


class ExternalIntegrationTestCase(FilterTestCases.FilterTestCase):
    queryset = ExternalIntegration.objects.all()
    filterset = ExternalIntegrationFilterSet

    generic_filter_tests = (
        ["name"],
        ["remote_url"],
        ["timeout"],
        ["secrets_group", "secrets_group__id"],
        ["secrets_group", "secrets_group__name"],
        ["http_method"],
    )

    @classmethod
    def setUpTestData(cls):
        secrets_groups = (
            SecretsGroup.objects.create(name="Secrets Group 1"),
            SecretsGroup.objects.create(name="Secrets Group 2"),
        )
        external_integrations = list(ExternalIntegration.objects.all()[:2])
        external_integrations[0].secrets_group = secrets_groups[0]
        external_integrations[1].secrets_group = secrets_groups[1]
        for ei in external_integrations:
            ei.validated_save()

    def test_verify_ssl(self):
        params = {"verify_ssl": True}
        self.assertQuerysetEqualAndNotEmpty(
            self.filterset(params, self.queryset).qs, self.queryset.filter(verify_ssl=True)
        )
        params = {"verify_ssl": False}
        self.assertQuerysetEqualAndNotEmpty(
            self.filterset(params, self.queryset).qs, self.queryset.filter(verify_ssl=False)
        )


class GitRepositoryTestCase(FilterTestCases.FilterTestCase):
    queryset = GitRepository.objects.all()
    filterset = GitRepositoryFilterSet
    generic_filter_tests = (
        ("branch",),
        ("name",),
        # ("provided_contents",),  # TODO
        ("remote_url",),
        ("secrets_group", "secrets_group__id"),
        ("secrets_group", "secrets_group__name"),
        ("secrets_group_id", "secrets_group__id"),
        ("slug",),
    )

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

    def test_provided_contents(self):
        params = {"provided_contents": ["extras.exporttemplate"]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 1)
        params = {"provided_contents": ["extras.job"]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)


class GraphQLTestCase(FilterTestCases.FilterTestCase):
    queryset = GraphQLQuery.objects.all()
    filterset = GraphQLQueryFilterSet
    generic_filter_tests = (("name",),)
    # skip testing "query" attribute for generic q filter test as it's not trivially modifiable
    exclude_q_filter_predicates = ["query"]

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
    generic_filter_tests = (("name",),)

    @classmethod
    def setUpTestData(cls):
        location_ct = ContentType.objects.get(app_label="dcim", model="location")
        rack_ct = ContentType.objects.get(app_label="dcim", model="rack")

        cls.locations = Location.objects.filter(location_type=LocationType.objects.get(name="Campus"))[:2]

        rack_status = Status.objects.get_for_model(Rack).first()
        racks = (
            Rack.objects.create(name="Rack 1", location=cls.locations[0], status=rack_status),
            Rack.objects.create(name="Rack 2", location=cls.locations[1], status=rack_status),
        )

        ImageAttachment.objects.create(
            content_type=location_ct,
            object_id=cls.locations[0].pk,
            name="Image Attachment 1",
            image="http://example.com/image1.png",
            image_height=100,
            image_width=100,
        )
        ImageAttachment.objects.create(
            content_type=location_ct,
            object_id=cls.locations[1].pk,
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

    def test_content_type(self):
        params = {"content_type": "dcim.location"}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)
        params = {"content_type__n": "dcim.location"}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)

    def test_content_type_id_and_object_id(self):
        params = {
            "content_type_id": ContentType.objects.get(app_label="dcim", model="location").pk,
            "object_id": [self.locations[0].pk],
        }
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 1)


class JobFilterSetTestCase(FilterTestCases.FilterTestCase):
    queryset = Job.objects.all()
    filterset = JobFilterSet
    generic_filter_tests = (
        ("grouping",),
        ("job_class_name",),
        ("job_queues", "job_queues__id"),
        ("job_queues", "job_queues__name"),
        ("module_name",),
        ("name",),
    )

    @classmethod
    def setUpTestData(cls):
        Job.objects.first().tags.set(Tag.objects.get_for_model(Job))
        Job.objects.last().tags.set(Tag.objects.get_for_model(Job)[:3])

    def test_installed(self):
        params = {"job_class_name": "TestPassJob", "installed": True}
        self.assertTrue(self.filterset(params, self.queryset).qs.exists())

    def test_enabled(self):
        params = {"job_class_name": "TestPassJob", "enabled": False}
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

    def test_is_job_hook_receiver(self):
        params = {"is_job_hook_receiver": True}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 4)


class JobQueueFilterSetTestCase(FilterTestCases.FilterTestCase, FilterTestCases.TenancyFilterTestCaseMixin):
    queryset = JobQueue.objects.all()
    filterset = JobQueueFilterSet
    tenancy_related_name = "job_queues"
    generic_filter_tests = [
        ["name"],
    ]

    @classmethod
    def setUpTestData(cls):
        # create some job queues that do not have jobs attached to them
        # for has_jobs boolean filter
        JobQueue.objects.create(
            name="Empty Job Queue 1",
            queue_type=JobQueueTypeChoices.TYPE_KUBERNETES,
        )
        JobQueue.objects.create(name="Empty Job Queue 2", queue_type=JobQueueTypeChoices.TYPE_CELERY)
        JobQueue.objects.create(
            name="Empty Job Queue 3",
            queue_type=JobQueueTypeChoices.TYPE_KUBERNETES,
        )
        JobQueue.objects.create(
            name="Empty Job Queue 4",
            queue_type=JobQueueTypeChoices.TYPE_KUBERNETES,
        )

    def test_queue_type(self):
        # we cannot add this test to self.generic_filter_tests because JobQueueTypeChoices only has two values.
        # self.generic_filter_tests needs at least three.
        params = {"queue_type": [JobQueueTypeChoices.TYPE_CELERY]}
        self.assertQuerysetEqualAndNotEmpty(
            self.filterset(params, self.queryset).qs, self.queryset.filter(queue_type=JobQueueTypeChoices.TYPE_CELERY)
        )
        params = {"queue_type": [JobQueueTypeChoices.TYPE_KUBERNETES]}
        self.assertQuerysetEqualAndNotEmpty(
            self.filterset(params, self.queryset).qs,
            self.queryset.filter(queue_type=JobQueueTypeChoices.TYPE_KUBERNETES),
        )


class JobQueueAssignmentFilterSetTestCase(FilterTestCases.FilterTestCase):
    queryset = JobQueueAssignment.objects.all()
    filterset = JobQueueAssignmentFilterSet
    generic_filter_tests = [
        ("job", "job__id"),
        ("job", "job__name"),
        ("job_queue", "job_queue__id"),
        ("job_queue", "job_queue__name"),
    ]


class JobResultFilterSetTestCase(FilterTestCases.FilterTestCase):
    queryset = JobResult.objects.all()
    filterset = JobResultFilterSet
    generic_filter_tests = (
        ("date_created",),
        ("date_started",),
        ("date_done",),
        ("job_model", "job_model__id"),
        ("job_model", "job_model__name"),
        ("job_model_id", "job_model__id"),
        ("name",),
        ("status",),
    )

    @classmethod
    def setUpTestData(cls):
        jobs = Job.objects.all()[:3]
        cls.jobs = jobs
        user = User.objects.create(username="user1", is_active=True)
        job_model = Job.objects.get_for_class_path("pass_job.TestPassJob")
        scheduled_jobs = [
            ScheduledJob.objects.create(
                name="test1",
                task="pass_job.TestPassJob",
                job_model=job_model,
                interval=JobExecutionType.TYPE_IMMEDIATELY,
                user=user,
                approval_required=True,
                start_time=now(),
            ),
            ScheduledJob.objects.create(
                name="test2",
                task="pass_job.TestPassJob",
                job_model=job_model,
                interval=JobExecutionType.TYPE_DAILY,
                user=user,
                approval_required=True,
                start_time=datetime(2020, 1, 23, 12, 34, 56, tzinfo=ZoneInfo("America/New_York")),
                time_zone=ZoneInfo("America/New_York"),
            ),
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
            ),
        ]
        cls.scheduled_jobs = scheduled_jobs
        user = UserFactory.create()
        for idx, job in enumerate(jobs):
            JobResult.objects.create(
                job_model=job,
                name=job.class_path,
                user=user,
                status=JobResultStatusChoices.STATUS_STARTED,
                scheduled_job=scheduled_jobs[idx],
            )

    def test_scheduled_job(self):
        scheduled_jobs = list(self.scheduled_jobs[:2])
        filter_params = [
            {"scheduled_job": [scheduled_jobs[0].pk, scheduled_jobs[1].name]},
        ]
        for params in filter_params:
            self.assertQuerysetEqualAndNotEmpty(
                self.filterset(params, self.queryset).qs,
                self.queryset.filter(scheduled_job__in=scheduled_jobs).distinct(),
            )


class JobHookFilterSetTestCase(FilterTestCases.FilterTestCase):
    queryset = JobHook.objects.all()
    filterset = JobHookFilterSet
    generic_filter_tests = (
        ("job", "job__id"),
        ("job", "job__name"),
        ("name",),
    )

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

    def test_content_types(self):
        params = {"content_types": ["dcim.devicetype"]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)
        params = {"content_types__n": ["dcim.devicetype"]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 1)

    def test_enabled(self):
        params = {"enabled": True}
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


class JobButtonFilterTestCase(FilterTestCases.FilterTestCase):
    queryset = JobButton.objects.all()
    filterset = JobButtonFilterSet
    generic_filter_tests = (
        # ("job", "job__id"),  # TODO: not enough distinct values for generic test
        # ("job", "job__name"),  # TODO: not enough distinct values for generic test
        ("name",),
        ("text",),
        ("weight",),
    )

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


class JobLogEntryTestCase(FilterTestCases.FilterTestCase):
    queryset = JobLogEntry.objects.all()
    filterset = JobLogEntryFilterSet
    generic_filter_tests = (
        ("grouping",),
        ("log_level",),
        ("message",),
    )

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


class MetadataChoiceTestCase(FilterTestCases.FilterTestCase):
    queryset = MetadataChoice.objects.all()
    filterset = MetadataChoiceFilterSet
    generic_filter_tests = (
        ["metadata_type", "metadata_type__name"],
        ["metadata_type", "metadata_type__id"],
        ["value"],
        ["weight"],
    )


class MetadataTypeTestCase(FilterTestCases.FilterTestCase):
    queryset = MetadataType.objects.all()
    filterset = MetadataTypeFilterSet
    generic_filter_tests = (
        ["name"],
        ["description"],
        ["data_type"],
    )

    def test_content_types(self):
        device_ct = ContentType.objects.get_for_model(Device)
        rack_ct = ContentType.objects.get_for_model(Rack)
        mdts = self.queryset.filter(content_types=device_ct).filter(content_types=rack_ct).distinct()
        params = {"content_types": ["dcim.device", "dcim.rack"]}
        self.assertQuerysetEqualAndNotEmpty(self.filterset(params, self.queryset).qs, mdts)


class ObjectChangeTestCase(FilterTestCases.FilterTestCase):
    queryset = ObjectChange.objects.all()
    filterset = ObjectChangeFilterSet
    generic_filter_tests = (
        ("user", "user__id"),
        ("user", "user__username"),
        ("user_id", "user__id"),
        ("user_name",),
    )

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

    def test_changed_object_type(self):
        params = {"changed_object_type": "dcim.location"}
        self.assertQuerysetEqualAndNotEmpty(
            self.filterset(params, self.queryset).qs,
            self.queryset.filter(changed_object_type=ContentType.objects.get_for_model(Location)),
        )

    def test_changed_object_type_id(self):
        params = {"changed_object_type_id": ContentType.objects.get(app_label="dcim", model="location").pk}
        self.assertQuerysetEqualAndNotEmpty(
            self.filterset(params, self.queryset).qs,
            self.queryset.filter(changed_object_type=ContentType.objects.get_for_model(Location)),
        )


class ObjectMetadataTestCase(FilterTestCases.FilterTestCase):
    queryset = ObjectMetadata.objects.all()
    filterset = ObjectMetadataFilterSet
    generic_filter_tests = (
        ["contact", "contact__name"],
        ["contact", "contact__id"],
        ["team", "team__name"],
        ["team", "team__id"],
        ["metadata_type", "metadata_type__name"],
        ["metadata_type", "metadata_type__id"],
    )

    @classmethod
    def setUpTestData(cls):
        mdt = MetadataType.objects.create(
            name="Contact/Team Metadata Type", data_type=MetadataTypeDataTypeChoices.TYPE_CONTACT_TEAM
        )
        contacts = Contact.objects.all()
        teams = Team.objects.all()
        mdt.content_types.set(list(ContentType.objects.values_list("pk", flat=True)))
        ObjectMetadata.objects.create(
            metadata_type=mdt,
            contact=contacts[0],
            scoped_fields=["parent"],
            assigned_object_type=ContentType.objects.get_for_model(IPAddress),
            assigned_object_id=IPAddress.objects.first().pk,
        )
        ObjectMetadata.objects.create(
            metadata_type=mdt,
            contact=contacts[1],
            scoped_fields=["status"],
            assigned_object_type=ContentType.objects.get_for_model(IPAddress),
            assigned_object_id=IPAddress.objects.first().pk,
        )
        ObjectMetadata.objects.create(
            metadata_type=mdt,
            contact=contacts[2],
            scoped_fields=["namespace"],
            assigned_object_type=ContentType.objects.get_for_model(IPAddress),
            assigned_object_id=IPAddress.objects.first().pk,
        )
        ObjectMetadata.objects.create(
            metadata_type=mdt,
            team=teams[0],
            scoped_fields=["device_type"],
            assigned_object_type=ContentType.objects.get_for_model(Device),
            assigned_object_id=Device.objects.first().pk,
        )
        ObjectMetadata.objects.create(
            metadata_type=mdt,
            team=teams[1],
            scoped_fields=["status"],
            assigned_object_type=ContentType.objects.get_for_model(Device),
            assigned_object_id=Device.objects.first().pk,
        )
        ObjectMetadata.objects.create(
            metadata_type=mdt,
            team=teams[2],
            scoped_fields=["name"],
            assigned_object_type=ContentType.objects.get_for_model(Device),
            assigned_object_id=Device.objects.first().pk,
        )

    def test_assigned_object_type(self):
        ct_1_pk, ct_2_pk = self.queryset.values_list("assigned_object_type", flat=True)[:2]
        ct_1 = ContentType.objects.get(pk=ct_1_pk)
        ct_2 = ContentType.objects.get(pk=ct_2_pk)
        oms = self.queryset.filter(assigned_object_type=ct_1_pk).distinct()
        params = {"assigned_object_type": [f"{ct_1.app_label}.{ct_1.model}"]}
        self.assertQuerysetEqualAndNotEmpty(self.filterset(params, self.queryset).qs, oms)
        oms = self.queryset.filter(assigned_object_type=ct_2_pk).distinct()
        params = {"assigned_object_type": [f"{ct_2.app_label}.{ct_2.model}"]}
        self.assertQuerysetEqualAndNotEmpty(self.filterset(params, self.queryset).qs, oms)


class RelationshipTestCase(FilterTestCases.FilterTestCase):
    queryset = Relationship.objects.all()
    filterset = RelationshipFilterSet
    generic_filter_tests = (
        ("key",),
        ("label",),
        ("type",),
    )

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

    def test_source_type(self):
        params = {"source_type": ["dcim.device"]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)

    def test_destination_type(self):
        params = {"destination_type": ["ipam.vlan", "dcim.interface"]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)


class RelationshipAssociationFilterSetTestCase(FilterTestCases.FilterTestCase):
    queryset = RelationshipAssociation.objects.all()
    filterset = RelationshipAssociationFilterSet
    generic_filter_tests = (
        ("destination_id",),
        # ("relationship", "relationship__id"),  # TODO?
        ("relationship", "relationship__key"),
        ("source_id",),
    )

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
        vlan_group = VLANGroup.objects.create(name="Test VLANGroup 1")
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

    def test_source_type(self):
        params = {"source_type": ["dcim.device", "dcim.interface"]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 5)

    def test_destination_type(self):
        params = {"destination_type": ["dcim.device", "dcim.interface"]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 6)

    def test_peer_id(self):
        params = {"peer_id": [self.devices[0].pk, self.devices[1].pk]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 3)
        params = {"peer_id": [self.devices[2].pk]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)

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


class SavedViewTestCase(FilterTestCases.FilterTestCase):
    queryset = SavedView.objects.all()
    filterset = SavedViewFilterSet

    generic_filter_tests = (
        ["owner", "owner__id"],
        ["owner", "owner__username"],
        ["name"],
        ["view"],
    )

    @classmethod
    def setUpTestData(cls):
        user = User.objects.create(username="User1", is_active=True)
        SavedView.objects.create(
            name="Global default View", owner=user, view="dcim:location_list", is_global_default=True
        )

    def test_is_shared(self):
        params = {"is_shared": True}
        self.assertQuerysetEqualAndNotEmpty(
            self.filterset(params, self.queryset).qs, self.queryset.filter(is_shared=True)
        )

    def test_is_global_default(self):
        params = {"is_global_default": True}
        self.assertQuerysetEqualAndNotEmpty(
            self.filterset(params, self.queryset).qs, self.queryset.filter(is_global_default=True)
        )


class SecretTestCase(FilterTestCases.FilterTestCase):
    queryset = Secret.objects.all()
    filterset = SecretFilterSet
    generic_filter_tests = (
        ("created",),
        ("last_updated",),
        ("name",),
        ("tags", "tags__id"),
        ("tags", "tags__name"),
    )

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


class SecretsGroupTestCase(FilterTestCases.FilterTestCase):
    queryset = SecretsGroup.objects.all()
    filterset = SecretsGroupFilterSet
    generic_filter_tests = (
        ("created",),
        ("last_updated",),
        ("name",),
    )

    @classmethod
    def setUpTestData(cls):
        SecretsGroup.objects.create(name="Group 1")
        SecretsGroup.objects.create(name="Group 2")
        SecretsGroup.objects.create(name="Group 3")


class SecretsGroupAssociationTestCase(FilterTestCases.FilterTestCase):
    queryset = SecretsGroupAssociation.objects.all()
    filterset = SecretsGroupAssociationFilterSet

    generic_filter_tests = (
        ("secret", "secret__id"),
        ("secret", "secret__name"),
        ("secret_id", "secret__id"),
        ("secrets_group", "secrets_group__id"),
        ("secrets_group", "secrets_group__name"),
    )

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

    def test_access_type(self):
        params = {"access_type": [SecretsGroupAccessTypeChoices.TYPE_GENERIC]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)

    def test_secret_type(self):
        params = {"secret_type": [SecretsGroupSecretTypeChoices.TYPE_PASSWORD]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)


class StaticGroupAssociationTestCase(FilterTestCases.FilterTestCase):
    queryset = StaticGroupAssociation.objects.all()
    filterset = StaticGroupAssociationFilterSet

    generic_filter_tests = (
        ["dynamic_group", "dynamic_group__id"],
        ["dynamic_group", "dynamic_group__name"],
        ["associated_object_id"],
    )

    def test_associated_object_type(self):
        ct = (
            DynamicGroup.objects.filter(
                static_group_associations__isnull=False,
                group_type=DynamicGroupTypeChoices.TYPE_STATIC,
            )
            .first()
            .content_type
        )
        params = {"associated_object_type": [ct.model_class()._meta.label_lower]}
        self.assertQuerysetEqualAndNotEmpty(
            self.filterset(params, self.queryset).qs,
            StaticGroupAssociation.objects.filter(associated_object_type=ct),
            ordered=False,
        )


class StatusTestCase(FilterTestCases.FilterTestCase):
    queryset = Status.objects.all()
    filterset = StatusFilterSet
    generic_filter_tests = (
        ("color",),
        ("name",),
    )

    def test_content_types(self):
        ct = ContentType.objects.get_for_model(Device)
        status_count = self.queryset.filter(content_types=ct).count()
        params = {"content_types": ["dcim.device"]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), status_count)


class TagTestCase(FilterTestCases.FilterTestCase):
    queryset = Tag.objects.all()
    filterset = TagFilterSet
    generic_filter_tests = (
        ("color",),
        ("name",),
    )

    @classmethod
    def setUpTestData(cls):
        cls.tags = Tag.objects.all()

    def test_content_types(self):
        params = {"content_types": ["dcim.location"]}
        filtered_data = self.filterset(params, self.queryset).qs
        self.assertQuerysetEqual(filtered_data, Tag.objects.get_for_model(Location))
        self.assertEqual(filtered_data[0], Tag.objects.get_for_model(Location)[0])


class TeamFilterSetTestCase(ContactAndTeamFilterSetTestCaseMixin, FilterTestCases.FilterTestCase):
    queryset = Team.objects.all()
    filterset = TeamFilterSet

    generic_filter_tests = (
        ["name"],
        ["phone"],
        ["email"],
        ["address"],
        ["comments"],
    )


class WebhookTestCase(FilterTestCases.FilterTestCase):
    queryset = Webhook.objects.all()
    filterset = WebhookFilterSet
    generic_filter_tests = (
        ("name",),
        ("payload_url",),
    )

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


class RoleTestCase(FilterTestCases.FilterTestCase):
    queryset = Role.objects.all()
    filterset = RoleFilterSet
    generic_filter_tests = (
        ("color",),
        ("name",),
        ("weight",),
    )

    def test_content_types(self):
        device_ct = ContentType.objects.get_for_model(Device)
        rack_ct = ContentType.objects.get_for_model(Rack)
        device_roles = self.queryset.filter(content_types__in=[device_ct, rack_ct]).distinct()
        params = {"content_types": ["dcim.device", "dcim.rack"]}
        self.assertQuerysetEqualAndNotEmpty(self.filterset(params, self.queryset).qs, device_roles)

        rack_roles = self.queryset.filter(content_types=rack_ct)
        params = {"content_types": ["dcim.rack"]}
        self.assertQuerysetEqualAndNotEmpty(self.filterset(params, self.queryset).qs, rack_roles)
