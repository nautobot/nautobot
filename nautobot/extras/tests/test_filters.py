import uuid

from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.db.models import Q

from nautobot.dcim.filters import DeviceFilterSet
from nautobot.dcim.models import (
    Device,
    DeviceRole,
    DeviceType,
    Interface,
    Manufacturer,
    Platform,
    Rack,
    Region,
    Site,
)
from nautobot.extras.choices import (
    ObjectChangeActionChoices,
    SecretsGroupAccessTypeChoices,
    SecretsGroupSecretTypeChoices,
)
from nautobot.extras.constants import HTTP_CONTENT_TYPE_JSON
from nautobot.extras.filters import (
    ComputedFieldFilterSet,
    ConfigContextFilterSet,
    ContentTypeFilterSet,
    CustomLinkFilterSet,
    ExportTemplateFilterSet,
    GitRepositoryFilterSet,
    GraphQLQueryFilterSet,
    ImageAttachmentFilterSet,
    JobFilterSet,
    JobHookFilterSet,
    JobLogEntryFilterSet,
    ObjectChangeFilterSet,
    RelationshipAssociationFilterSet,
    RelationshipFilterSet,
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
    CustomLink,
    ExportTemplate,
    GitRepository,
    GraphQLQuery,
    ImageAttachment,
    Job,
    JobHook,
    JobLogEntry,
    JobResult,
    ObjectChange,
    Relationship,
    RelationshipAssociation,
    Secret,
    SecretsGroup,
    SecretsGroupAssociation,
    Status,
    Tag,
    Webhook,
)
from nautobot.ipam.filters import VLANFilterSet
from nautobot.ipam.models import IPAddress, VLAN
from nautobot.tenancy.models import Tenant, TenantGroup
from nautobot.utilities.choices import ColorChoices
from nautobot.utilities.testing import FilterTestCases
from nautobot.virtualization.models import Cluster, ClusterGroup, ClusterType

# Use the proper swappable User model
User = get_user_model()


class ComputedFieldTestCase(FilterTestCases.FilterTestCase):
    queryset = ComputedField.objects.all()
    filterset = ComputedFieldFilterSet

    @classmethod
    def setUpTestData(cls):
        ComputedField.objects.create(
            content_type=ContentType.objects.get_for_model(Site),
            slug="computed_field_one",
            label="Computed Field One",
            template="{{ obj.name }} is the name of this site.",
            fallback_value="An error occurred while rendering this template.",
            weight=100,
        )
        # Field whose template will raise a TemplateError
        ComputedField.objects.create(
            content_type=ContentType.objects.get_for_model(Site),
            slug="bad_computed_field",
            label="Bad Computed Field",
            template="{{ something_that_throws_an_err | not_a_real_filter }} bad data",
            fallback_value="This template has errored",
            weight=100,
        )
        # Field whose template will raise a TypeError
        ComputedField.objects.create(
            content_type=ContentType.objects.get_for_model(Site),
            slug="worse_computed_field",
            label="Worse Computed Field",
            template="{{ obj.images | list }}",
            fallback_value="Another template error",
            weight=200,
        )
        ComputedField.objects.create(
            content_type=ContentType.objects.get_for_model(Device),
            slug="device_computed_field",
            label="Device Computed Field",
            template="Hello, world.",
            fallback_value="This template has errored",
            weight=100,
        )

    def test_slug(self):
        params = {"slug": ["device_computed_field", "worse_computed_field"]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)

    def test_content_type(self):
        params = {"content_type": "dcim.site"}
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
        params = {"q": "site"}
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

        regions = Region.objects.all()[:3]
        sites = Site.objects.all()[:3]

        device_roles = (
            DeviceRole.objects.create(name="Device Role 1", slug="device-role-1"),
            DeviceRole.objects.create(name="Device Role 2", slug="device-role-2"),
            DeviceRole.objects.create(name="Device Role 3", slug="device-role-3"),
        )
        cls.device_roles = device_roles

        manufacturer = Manufacturer.objects.create(name="Manufacturer 1", slug="manufacturer-1")

        device_types = (
            DeviceType.objects.create(model="Device Type 1", slug="device-type-1", manufacturer=manufacturer),
            DeviceType.objects.create(model="Device Type 2", slug="device-type-2", manufacturer=manufacturer),
            DeviceType.objects.create(model="Device Type 3", slug="device-type-3", manufacturer=manufacturer),
        )
        cls.device_types = device_types

        platforms = (
            Platform.objects.create(name="Platform 1", slug="platform-1"),
            Platform.objects.create(name="Platform 2", slug="platform-2"),
            Platform.objects.create(name="Platform 3", slug="platform-3"),
        )
        cls.platforms = platforms

        cluster_groups = (
            ClusterGroup.objects.create(name="Cluster Group 1", slug="cluster-group-1"),
            ClusterGroup.objects.create(name="Cluster Group 2", slug="cluster-group-2"),
            ClusterGroup.objects.create(name="Cluster Group 3", slug="cluster-group-3"),
        )

        cluster_type = ClusterType.objects.create(name="Cluster Type 1", slug="cluster-type-1")
        clusters = (
            Cluster.objects.create(name="Cluster 1", type=cluster_type),
            Cluster.objects.create(name="Cluster 2", type=cluster_type),
            Cluster.objects.create(name="Cluster 3", type=cluster_type),
        )

        cls.tenant_groups = TenantGroup.objects.filter(tenants__isnull=True)[:3]

        cls.tenants = Tenant.objects.filter(group__isnull=True)[:3]

        for i in range(0, 3):
            is_active = bool(i % 2)
            c = ConfigContext.objects.create(
                name=f"Config Context {i + 1}",
                is_active=is_active,
                data='{"foo": 123}',
            )
            c.regions.set([regions[i]])
            c.sites.set([sites[i]])
            c.roles.set([device_roles[i]])
            c.device_types.set([device_types[i]])
            c.platforms.set([platforms[i]])
            c.cluster_groups.set([cluster_groups[i]])
            c.clusters.set([clusters[i]])
            c.tenant_groups.set([cls.tenant_groups[i]])
            c.tenants.set([cls.tenants[i]])

    def test_name(self):
        params = {"name": ["Config Context 1", "Config Context 2"]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)

    def test_is_active(self):
        params = {"is_active": True}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 1)
        params = {"is_active": False}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)

    def test_region(self):
        regions = Region.objects.all()[:2]
        params = {"region_id": [regions[0].pk, regions[1].pk]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)
        params = {"region": [regions[0].slug, regions[1].slug]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)

    def test_site(self):
        sites = Site.objects.all()[:2]
        params = {"site_id": [sites[0].pk, sites[1].pk]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)
        params = {"site": [sites[0].slug, sites[1].slug]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)

    def test_role(self):
        device_roles = self.device_roles[:2]
        params = {"role_id": [device_roles[0].pk, device_roles[1].pk]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), len(device_roles))
        params = {"role": [device_roles[0].slug, device_roles[1].slug]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), len(device_roles))

    def test_type(self):
        device_types = self.device_types[:2]
        params = {"device_type_id": [device_types[0].pk, device_types[1].pk]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), len(device_types))
        params = {"device_type": [device_types[0].slug, device_types[1].slug]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), len(device_types))

    def test_platform(self):
        platforms = self.platforms[:2]
        params = {"platform_id": [platforms[0].pk, platforms[1].pk]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), len(platforms))
        params = {"platform": [platforms[0].slug, platforms[1].slug]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), len(platforms))

    def test_cluster_group(self):
        cluster_groups = ClusterGroup.objects.all()[:2]
        params = {"cluster_group_id": [cluster_groups[0].pk, cluster_groups[1].pk]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)
        params = {"cluster_group": [cluster_groups[0].slug, cluster_groups[1].slug]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)

    def test_cluster(self):
        clusters = Cluster.objects.all()[:2]
        params = {"cluster_id": [clusters[0].pk, clusters[1].pk]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)

    def test_tenant_group(self):
        tenant_groups = self.tenant_groups[:2]
        params = {"tenant_group_id": [tenant_groups[0].pk, tenant_groups[1].pk]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)
        params = {"tenant_group": [tenant_groups[0].slug, tenant_groups[1].slug]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)

    def test_tenant_id(self):
        tenants = self.tenants[:2]
        params = {"tenant_id": [tenants[0].pk, tenants[1].pk]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)
        params = {"tenant": [tenants[0].slug, tenants[1].slug]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)

    def test_search(self):
        value = self.queryset.values_list("pk", flat=True)[0]
        params = {"q": value}
        self.assertEqual(self.filterset(params, self.queryset).qs.values_list("pk", flat=True)[0], value)


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


class CustomLinkTestCase(FilterTestCases.FilterTestCase):
    queryset = CustomLink.objects.all()
    filterset = CustomLinkFilterSet

    @classmethod
    def setUpTestData(cls):
        obj_type = ContentType.objects.get_for_model(Site)

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


class ExportTemplateTestCase(FilterTestCases.FilterTestCase):
    queryset = ExportTemplate.objects.all()
    filterset = ExportTemplateFilterSet

    @classmethod
    def setUpTestData(cls):

        content_types = ContentType.objects.filter(model__in=["site", "rack", "device"])

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
        params = {"content_type": ContentType.objects.get(model="site").pk}
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
        repos = (
            GitRepository(
                name="Repo 1",
                slug="repo-1",
                branch="main",
                provided_contents=[
                    "extras.configcontext",
                ],
                remote_url="https://example.com/repo1.git",
            ),
            GitRepository(
                name="Repo 2",
                slug="repo-2",
                branch="develop",
                provided_contents=[
                    "extras.configcontext",
                    "extras.job",
                ],
                remote_url="https://example.com/repo2.git",
            ),
            GitRepository(
                name="Repo 3",
                slug="repo-3",
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
            repo.save(trigger_resync=False)

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


class GraphQLTestCase(FilterTestCases.NameSlugFilterTestCase):
    queryset = GraphQLQuery.objects.all()
    filterset = GraphQLQueryFilterSet

    @classmethod
    def setUpTestData(cls):
        graphqlqueries = (
            GraphQLQuery(
                name="graphql-query-1",
                slug="graphql-query-1",
                query="{ query: sites {name} }",
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
query ($device: String!) {
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

        for query in graphqlqueries:
            query.clean()
            query.save()

    def test_query(self):
        params = {"query": ["sites"]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 3)


class ImageAttachmentTestCase(FilterTestCases.FilterTestCase):
    queryset = ImageAttachment.objects.all()
    filterset = ImageAttachmentFilterSet

    @classmethod
    def setUpTestData(cls):

        site_ct = ContentType.objects.get(app_label="dcim", model="site")
        rack_ct = ContentType.objects.get(app_label="dcim", model="rack")

        sites = Site.objects.all()[:2]

        racks = (
            Rack.objects.create(name="Rack 1", site=sites[0]),
            Rack.objects.create(name="Rack 2", site=sites[1]),
        )

        ImageAttachment.objects.create(
            content_type=site_ct,
            object_id=sites[0].pk,
            name="Image Attachment 1",
            image="http://example.com/image1.png",
            image_height=100,
            image_width=100,
        )
        ImageAttachment.objects.create(
            content_type=site_ct,
            object_id=sites[1].pk,
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
        params = {"content_type": "dcim.site"}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)

    def test_content_type_id_and_object_id(self):
        params = {
            "content_type_id": ContentType.objects.get(app_label="dcim", model="site").pk,
            "object_id": [Site.objects.first().pk],
        }
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 1)


class JobFilterSetTestCase(FilterTestCases.NameSlugFilterTestCase):
    queryset = Job.objects.all()
    filterset = JobFilterSet

    def test_grouping(self):
        params = {"grouping": ["test_file_upload_pass", "test_file_upload_fail"]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)

    def test_installed(self):
        params = {"job_class_name": "TestPass", "installed": True}
        self.assertTrue(self.filterset(params, self.queryset).qs.exists())

    def test_enabled(self):
        params = {"job_class_name": "TestPass", "enabled": False}
        self.assertTrue(self.filterset(params, self.queryset).qs.exists())

    def test_commit_default(self):
        params = {"commit_default": False}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 0)

    def test_hidden(self):
        params = {"hidden": True}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 1)

    def test_read_only(self):
        params = {"read_only": True}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 3)

    def test_approval_required(self):
        params = {"approval_required": True}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 0)

    def test_search(self):
        params = {"q": "file"}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 3)
        value = self.queryset.values_list("pk", flat=True)[0]
        params = {"q": value}
        self.assertEqual(self.filterset(params, self.queryset).qs.values_list("pk", flat=True)[0], value)

    def test_is_job_hook_receiver(self):
        params = {"is_job_hook_receiver": True}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 4)


class JobHookFilterSetTestCase(FilterTestCases.NameSlugFilterTestCase):
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
        params = {"job": [jobs[0].slug, jobs[1].pk]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)

    def test_slug(self):
        params = {"slug": ["jobhook1", "jobhook2"]}
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


class JobLogEntryTestCase(FilterTestCases.FilterTestCase):
    queryset = JobLogEntry.objects.all()
    filterset = JobLogEntryFilterSet

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

    def test_log_level(self):
        params = {"log_level": "success"}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 1)

    def test_grouping(self):
        params = {"grouping": ["run"]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 4)

    def test_message(self):
        params = {"message": ["I am a success log."]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 1)

    def test_search(self):
        params = {"q": "run"}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 4)
        params = {"q": "warning log"}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 1)
        params = {"q": "success"}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 1)


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

        site = Site.objects.first()
        ipaddress = IPAddress.objects.create(address="192.0.2.1/24")

        ObjectChange.objects.create(
            user=users[0],
            user_name=users[0].username,
            request_id=uuid.uuid4(),
            action=ObjectChangeActionChoices.ACTION_CREATE,
            changed_object=site,
            object_repr=str(site),
            object_data={"name": site.name, "slug": site.slug},
        )
        ObjectChange.objects.create(
            user=users[0],
            user_name=users[0].username,
            request_id=uuid.uuid4(),
            action=ObjectChangeActionChoices.ACTION_UPDATE,
            changed_object=site,
            object_repr=str(site),
            object_data={"name": site.name, "slug": site.slug},
        )
        ObjectChange.objects.create(
            user=users[1],
            user_name=users[1].username,
            request_id=uuid.uuid4(),
            action=ObjectChangeActionChoices.ACTION_DELETE,
            changed_object=site,
            object_repr=str(site),
            object_data={"name": site.name, "slug": site.slug},
        )
        ObjectChange.objects.create(
            user=users[1],
            user_name=users[1].username,
            request_id=uuid.uuid4(),
            action=ObjectChangeActionChoices.ACTION_CREATE,
            changed_object=ipaddress,
            object_repr=str(ipaddress),
            object_data={"address": str(ipaddress.address), "status": ipaddress.status},
        )
        ObjectChange.objects.create(
            user=users[2],
            user_name=users[2].username,
            request_id=uuid.uuid4(),
            action=ObjectChangeActionChoices.ACTION_UPDATE,
            changed_object=ipaddress,
            object_repr=str(ipaddress),
            object_data={"address": str(ipaddress.address), "status": ipaddress.status},
        )
        ObjectChange.objects.create(
            user=users[2],
            user_name=users[2].username,
            request_id=uuid.uuid4(),
            action=ObjectChangeActionChoices.ACTION_DELETE,
            changed_object=ipaddress,
            object_repr=str(ipaddress),
            object_data={"address": str(ipaddress.address), "status": ipaddress.status},
        )

    def test_user(self):
        params = {"user_id": User.objects.filter(username__in=["user1", "user2"]).values_list("pk", flat=True)}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 4)
        params = {"user": ["user1", "user2"]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 4)

    def test_user_name(self):
        params = {"user_name": ["user1", "user2"]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 4)

    def test_changed_object_type(self):
        params = {"changed_object_type": "dcim.site"}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 3)

    def test_changed_object_type_id(self):
        params = {"changed_object_type_id": ContentType.objects.get(app_label="dcim", model="site").pk}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 3)

    def test_search(self):
        value = self.queryset.values_list("pk", flat=True)[0]
        params = {"q": value}
        self.assertEqual(self.filterset(params, self.queryset).qs.values_list("pk", flat=True)[0], value)


class RelationshipTestCase(FilterTestCases.NameSlugFilterTestCase):
    queryset = Relationship.objects.all()
    filterset = RelationshipFilterSet

    @classmethod
    def setUpTestData(cls):
        device_type = ContentType.objects.get_for_model(Device)
        interface_type = ContentType.objects.get_for_model(Interface)
        vlan_type = ContentType.objects.get_for_model(VLAN)

        Relationship(
            name="Device VLANs",
            slug="device-vlans",
            type="many-to-many",
            source_type=device_type,
            destination_type=vlan_type,
        ).validated_save()
        Relationship(
            name="Primary VLAN",
            slug="primary-vlan",
            type="one-to-many",
            source_type=vlan_type,
            destination_type=device_type,
        ).validated_save()
        Relationship(
            name="Primary Interface",
            slug="primary-interface",
            type="one-to-one",
            source_type=device_type,
            destination_type=interface_type,
        ).validated_save()

    def test_type(self):
        params = {"type": "one-to-many"}
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
                name="Device VLANs",
                slug="device-vlans",
                type="many-to-many",
                source_type=cls.device_type,
                destination_type=cls.vlan_type,
            ),
            Relationship(
                name="Primary VLAN",
                slug="primary-vlan",
                type="one-to-many",
                source_type=cls.vlan_type,
                destination_type=cls.device_type,
            ),
            Relationship(
                name="Device Device",
                slug="symmetric-device-device",
                type="symmetric-many-to-many",
                source_type=cls.device_type,
                destination_type=cls.device_type,
            ),
        )
        for relationship in cls.relationships:
            relationship.validated_save()

        manufacturer = Manufacturer.objects.create(name="Manufacturer 1", slug="manufacturer-1")
        devicetype = DeviceType.objects.create(manufacturer=manufacturer, model="Device Type 1", slug="device-type-1")
        devicerole = DeviceRole.objects.create(name="Device Role 1", slug="device-role-1")
        site = Site.objects.first()
        cls.devices = (
            Device.objects.create(name="Device 1", device_type=devicetype, device_role=devicerole, site=site),
            Device.objects.create(name="Device 2", device_type=devicetype, device_role=devicerole, site=site),
            Device.objects.create(name="Device 3", device_type=devicetype, device_role=devicerole, site=site),
        )
        cls.vlans = (
            VLAN.objects.create(vid=1, name="VLAN 1"),
            VLAN.objects.create(vid=2, name="VLAN 2"),
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
        params = {"relationship": [self.relationships[0].slug]}
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
                name="Device VLANs",
                slug="device-vlans",
                type="many-to-many",
                source_type=cls.device_type,
                destination_type=cls.vlan_type,
            ),
            Relationship(
                name="Primary VLAN",
                slug="primary-vlan",
                type="one-to-many",
                source_type=cls.vlan_type,
                destination_type=cls.device_type,
            ),
            Relationship(
                name="Device Peers",
                slug="device-peers",
                type="symmetric-many-to-many",
                source_type=cls.device_type,
                destination_type=cls.device_type,
            ),
        )
        for relationship in cls.relationships:
            relationship.validated_save()

        manufacturer = Manufacturer.objects.create(name="Manufacturer 1", slug="manufacturer-1")
        devicetype = DeviceType.objects.create(manufacturer=manufacturer, model="Device Type 1", slug="device-type-1")
        devicerole = DeviceRole.objects.create(name="Device Role 1", slug="device-role-1")
        site = Site.objects.first()
        cls.devices = (
            Device.objects.create(name="Device 1", device_type=devicetype, device_role=devicerole, site=site),
            Device.objects.create(name="Device 2", device_type=devicetype, device_role=devicerole, site=site),
            Device.objects.create(name="Device 3", device_type=devicetype, device_role=devicerole, site=site),
        )
        cls.vlans = (
            VLAN.objects.create(vid=1, name="VLAN 1"),
            VLAN.objects.create(vid=2, name="VLAN 2"),
            VLAN.objects.create(vid=3, name="VLAN 3"),
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
            self.filterset({f"cr_{self.relationships[1].slug}__source": [self.vlans[0].pk]}, self.queryset).qs.count(),
            3,
        )

    def test_one_to_many_destination(self):
        self.queryset = VLAN.objects.all()
        self.filterset = VLANFilterSet
        self.assertEqual(
            self.filterset(
                {f"cr_{self.relationships[1].slug}__destination": [self.devices[0].pk, self.devices[1].pk]},
                self.queryset,
            ).qs.count(),
            1,
        )

    def test_many_to_many_source(self):
        self.queryset = VLAN.objects.all()
        self.filterset = VLANFilterSet
        self.assertEqual(
            self.filterset(
                {f"cr_{self.relationships[0].slug}__source": [self.devices[0].pk, self.devices[1].pk]}, self.queryset
            ).qs.count(),
            2,
        )

    def test_many_to_many_destination(self):
        self.queryset = Device.objects.all()
        self.filterset = DeviceFilterSet
        self.assertEqual(
            self.filterset(
                {f"cr_{self.relationships[0].slug}__destination": [self.vlans[0].pk, self.vlans[1].pk]}, self.queryset
            ).qs.count(),
            2,
        )

    def test_many_to_many_peer(self):
        self.queryset = Device.objects.all()
        self.filterset = DeviceFilterSet
        self.assertEqual(
            self.filterset(
                {f"cr_{self.relationships[2].slug}__peer": [self.devices[0].pk, self.devices[1].pk]}, self.queryset
            ).qs.count(),
            3,
        )
        self.assertEqual(
            self.filterset({f"cr_{self.relationships[2].slug}__peer": [self.devices[2].pk]}, self.queryset).qs.count(),
            2,
        )

    def test_combination(self):
        self.queryset = Device.objects.all()
        self.filterset = DeviceFilterSet
        self.assertEqual(
            self.filterset(
                {
                    f"cr_{self.relationships[2].slug}__peer": [self.devices[0].pk, self.devices[1].pk],
                    f"cr_{self.relationships[0].slug}__destination": [self.vlans[0].pk, self.vlans[1].pk],
                },
                self.queryset,
            ).qs.count(),
            2,
        )
        self.assertEqual(
            self.filterset(
                {
                    f"cr_{self.relationships[2].slug}__peer": [self.devices[2].pk],
                    f"cr_{self.relationships[0].slug}__destination": [self.vlans[0].pk, self.vlans[1].pk],
                },
                self.queryset,
            ).qs.count(),
            2,
        )


class SecretTestCase(FilterTestCases.NameSlugFilterTestCase):
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

    def test_provider(self):
        params = {"provider": ["environment-variable"]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)

    def test_search(self):
        value = self.queryset.values_list("pk", flat=True)[0]
        params = {"q": value}
        self.assertEqual(self.filterset(params, self.queryset).qs.values_list("pk", flat=True)[0], value)


class SecretsGroupTestCase(FilterTestCases.NameSlugFilterTestCase):
    queryset = SecretsGroup.objects.all()
    filterset = SecretsGroupFilterSet

    @classmethod
    def setUpTestData(cls):
        SecretsGroup.objects.create(name="Group 1", slug="group-1")
        SecretsGroup.objects.create(name="Group 2", slug="group-2")
        SecretsGroup.objects.create(name="Group 3", slug="group-3")

    def test_search(self):
        value = self.queryset.values_list("pk", flat=True)[0]
        params = {"q": value}
        self.assertEqual(self.filterset(params, self.queryset).qs.values_list("pk", flat=True)[0], value)


class SecretsGroupAssociationTestCase(FilterTestCases.FilterTestCase):
    queryset = SecretsGroupAssociation.objects.all()
    filterset = SecretsGroupAssociationFilterSet

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
            SecretsGroup.objects.create(name="Group 1", slug="group-1"),
            SecretsGroup.objects.create(name="Group 2", slug="group-2"),
            SecretsGroup.objects.create(name="Group 3", slug="group-3"),
        )

        SecretsGroupAssociation.objects.create(
            group=cls.groups[0],
            secret=cls.secrets[0],
            access_type=SecretsGroupAccessTypeChoices.TYPE_GENERIC,
            secret_type=SecretsGroupSecretTypeChoices.TYPE_USERNAME,
        )
        SecretsGroupAssociation.objects.create(
            group=cls.groups[1],
            secret=cls.secrets[1],
            access_type=SecretsGroupAccessTypeChoices.TYPE_GENERIC,
            secret_type=SecretsGroupSecretTypeChoices.TYPE_PASSWORD,
        )
        SecretsGroupAssociation.objects.create(
            group=cls.groups[2],
            secret=cls.secrets[2],
            access_type=SecretsGroupAccessTypeChoices.TYPE_HTTP,
            secret_type=SecretsGroupSecretTypeChoices.TYPE_PASSWORD,
        )

    def test_group(self):
        params = {"group_id": [self.groups[0].pk, self.groups[1].pk]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)
        params = {"group": [self.groups[0].slug, self.groups[1].slug]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)

    def test_secret(self):
        params = {"secret_id": [self.secrets[0].pk, self.secrets[1].pk]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)
        params = {"secret": [self.secrets[0].slug, self.secrets[1].slug]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)

    def test_access_type(self):
        params = {"access_type": [SecretsGroupAccessTypeChoices.TYPE_GENERIC]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)

    def test_secret_type(self):
        params = {"secret_type": [SecretsGroupSecretTypeChoices.TYPE_PASSWORD]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)


class StatusTestCase(FilterTestCases.NameSlugFilterTestCase):
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
        # This current expected count may change as more `Status` objects are
        # imported by way of `extras.management.create_custom_statuses`. If as
        # these objects are imported, and this test fails, this number will need
        # to be adjusted.
        expected_count = 4
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), expected_count)

    def test_search(self):
        params = {"q": "active"}
        q = Q(id__iexact="active") | Q(name__icontains="active") | Q(slug__icontains="active")
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


class TagTestCase(FilterTestCases.NameSlugFilterTestCase):
    queryset = Tag.objects.all()
    filterset = TagFilterSet

    @classmethod
    def setUpTestData(cls):
        cls.tags = Tag.objects.all()

    def test_color(self):
        params = {"color": [self.tags[0].color, self.tags[1].color]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)

    def test_content_types(self):
        params = {"content_types": ["dcim.site"]}
        filtered_data = self.filterset(params, self.queryset).qs
        self.assertQuerysetEqual(filtered_data, Tag.objects.get_for_model(Site))
        self.assertEqual(filtered_data[0], Tag.objects.get_for_model(Site)[0])

    def test_search(self):
        params = {"q": self.tags[0].slug}
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
        obj_type = ContentType.objects.get_for_model(Site)
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
