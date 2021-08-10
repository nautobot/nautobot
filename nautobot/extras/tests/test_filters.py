import uuid

from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.test import TestCase

from nautobot.dcim.models import Device, DeviceRole, DeviceType, Interface, Manufacturer, Platform, Rack, Region, Site
from nautobot.extras.choices import ObjectChangeActionChoices
from nautobot.extras.constants import *
from nautobot.extras.filters import *
from nautobot.extras.models import (
    ConfigContext,
    CustomLink,
    ExportTemplate,
    GraphQLQuery,
    ImageAttachment,
    ObjectChange,
    Relationship,
    RelationshipAssociation,
    Tag,
    Status,
    Webhook,
)
from nautobot.ipam.models import IPAddress, VLAN
from nautobot.tenancy.models import Tenant, TenantGroup
from nautobot.utilities.choices import ColorChoices
from nautobot.virtualization.models import Cluster, ClusterGroup, ClusterType


# Use the proper swappable User model
User = get_user_model()


class ExportTemplateTestCase(TestCase):
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

    def test_id(self):
        params = {"id": self.queryset.values_list("pk", flat=True)[:2]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)

    def test_name(self):
        params = {"name": ["Export Template 1", "Export Template 2"]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)

    def test_content_type(self):
        params = {"content_type": ContentType.objects.get(model="site").pk}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 1)

    def test_search(self):
        params = {"q": "export"}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 3)


class ImageAttachmentTestCase(TestCase):
    queryset = ImageAttachment.objects.all()
    filterset = ImageAttachmentFilterSet

    @classmethod
    def setUpTestData(cls):

        site_ct = ContentType.objects.get(app_label="dcim", model="site")
        rack_ct = ContentType.objects.get(app_label="dcim", model="rack")

        sites = (
            Site.objects.create(name="Site 1", slug="site-1"),
            Site.objects.create(name="Site 2", slug="site-2"),
        )

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
        ),
        ImageAttachment.objects.create(
            content_type=site_ct,
            object_id=sites[1].pk,
            name="Image Attachment 2",
            image="http://example.com/image2.png",
            image_height=100,
            image_width=100,
        ),
        ImageAttachment.objects.create(
            content_type=rack_ct,
            object_id=racks[0].pk,
            name="Image Attachment 3",
            image="http://example.com/image3.png",
            image_height=100,
            image_width=100,
        ),
        ImageAttachment.objects.create(
            content_type=rack_ct,
            object_id=racks[1].pk,
            name="Image Attachment 4",
            image="http://example.com/image4.png",
            image_height=100,
            image_width=100,
        )

    def test_id(self):
        params = {"id": self.queryset.values_list("pk", flat=True)[:2]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)

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


class ConfigContextTestCase(TestCase):
    queryset = ConfigContext.objects.all()
    filterset = ConfigContextFilterSet

    @classmethod
    def setUpTestData(cls):

        regions = (
            Region.objects.create(name="Test Region 1", slug="test-region-1"),
            Region.objects.create(name="Test Region 2", slug="test-region-2"),
            Region.objects.create(name="Test Region 3", slug="test-region-3"),
        )

        sites = (
            Site.objects.create(name="Test Site 1", slug="test-site-1"),
            Site.objects.create(name="Test Site 2", slug="test-site-2"),
            Site.objects.create(name="Test Site 3", slug="test-site-3"),
        )

        device_roles = (
            DeviceRole.objects.create(name="Device Role 1", slug="device-role-1"),
            DeviceRole.objects.create(name="Device Role 2", slug="device-role-2"),
            DeviceRole.objects.create(name="Device Role 3", slug="device-role-3"),
        )

        manufacturer = Manufacturer.objects.create(name="Manufacturer 1", slug="manufacturer-1")

        device_types = (
            DeviceType.objects.create(model="Device Type 1", slug="device-type-1", manufacturer=manufacturer),
            DeviceType.objects.create(model="Device Type 2", slug="device-type-2", manufacturer=manufacturer),
            DeviceType.objects.create(model="Device Type 3", slug="device-type-3", manufacturer=manufacturer),
        )

        platforms = (
            Platform.objects.create(name="Platform 1", slug="platform-1"),
            Platform.objects.create(name="Platform 2", slug="platform-2"),
            Platform.objects.create(name="Platform 3", slug="platform-3"),
        )

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

        tenant_groups = (
            TenantGroup.objects.create(name="Tenant Group 1", slug="tenant-group-1"),
            TenantGroup.objects.create(name="Tenant Group 2", slug="tenant-group-2"),
            TenantGroup.objects.create(name="Tenant Group 3", slug="tenant-group-3"),
        )

        tenants = (
            Tenant.objects.create(name="Tenant 1", slug="tenant-1"),
            Tenant.objects.create(name="Tenant 2", slug="tenant-2"),
            Tenant.objects.create(name="Tenant 3", slug="tenant-3"),
        )

        for i in range(0, 3):
            is_active = bool(i % 2)
            c = ConfigContext.objects.create(
                name="Config Context {}".format(i + 1),
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
            c.tenant_groups.set([tenant_groups[i]])
            c.tenants.set([tenants[i]])

    def test_id(self):
        params = {"id": self.queryset.values_list("pk", flat=True)[:2]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)

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
        device_roles = DeviceRole.objects.all()[:2]
        params = {"role_id": [device_roles[0].pk, device_roles[1].pk]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)
        params = {"role": [device_roles[0].slug, device_roles[1].slug]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)

    def test_type(self):
        device_types = DeviceType.objects.all()[:2]
        params = {"device_type_id": [device_types[0].pk, device_types[1].pk]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)
        params = {"device_type": [device_types[0].slug, device_types[1].slug]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)

    def test_platform(self):
        platforms = Platform.objects.all()[:2]
        params = {"platform_id": [platforms[0].pk, platforms[1].pk]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)
        params = {"platform": [platforms[0].slug, platforms[1].slug]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)

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
        tenant_groups = TenantGroup.objects.all()[:2]
        params = {"tenant_group_id": [tenant_groups[0].pk, tenant_groups[1].pk]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)
        params = {"tenant_group": [tenant_groups[0].slug, tenant_groups[1].slug]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)

    def test_tenant_(self):
        tenants = Tenant.objects.all()[:2]
        params = {"tenant_id": [tenants[0].pk, tenants[1].pk]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)
        params = {"tenant": [tenants[0].slug, tenants[1].slug]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)


class RelationshipTestCase(TestCase):
    queryset = Relationship.objects.all()
    filterset = RelationshipFilterSet

    @classmethod
    def setUpTestData(cls):
        device_type = ContentType.objects.get_for_model(Device)
        interface_type = ContentType.objects.get_for_model(Interface)
        vlan_type = ContentType.objects.get_for_model(VLAN)

        Relationship.objects.create(
            name="Device VLANs",
            slug="device-vlans",
            type="many-to-many",
            source_type=device_type,
            destination_type=vlan_type,
        )
        Relationship.objects.create(
            name="Primary VLAN",
            slug="primary-vlan",
            type="one-to-many",
            source_type=vlan_type,
            destination_type=device_type,
        )
        Relationship.objects.create(
            name="Primary Interface",
            slug="primary-interface",
            type="one-to-one",
            source_type=device_type,
            destination_type=interface_type,
        )

    def test_id(self):
        params = {"id": self.queryset.values_list("pk", flat=True)[:2]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)

    def test_name(self):
        params = {"name": ["Primary VLAN", "Primary Interface"]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)

    def test_type(self):
        params = {"type": "one-to-many"}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 1)

    def test_source_type(self):
        params = {"source_type": ["dcim.device"]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)

    def test_destination_type(self):
        params = {"destination_type": ["ipam.vlan", "dcim.interface"]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)


class RelationshipAssociationTestCase(TestCase):
    queryset = RelationshipAssociation.objects.all()
    filterset = RelationshipAssociationFilterSet

    @classmethod
    def setUpTestData(cls):
        cls.device_type = ContentType.objects.get_for_model(Device)
        cls.vlan_type = ContentType.objects.get_for_model(VLAN)

        cls.relationships = (
            Relationship.objects.create(
                name="Device VLANs",
                slug="device-vlans",
                type="many-to-many",
                source_type=cls.device_type,
                destination_type=cls.vlan_type,
            ),
            Relationship.objects.create(
                name="Primary VLAN",
                slug="primary-vlan",
                type="one-to-many",
                source_type=cls.vlan_type,
                destination_type=cls.device_type,
            ),
        )

        manufacturer = Manufacturer.objects.create(name="Manufacturer 1", slug="manufacturer-1")
        devicetype = DeviceType.objects.create(manufacturer=manufacturer, model="Device Type 1", slug="device-type-1")
        devicerole = DeviceRole.objects.create(name="Device Role 1", slug="device-role-1")
        site = Site.objects.create(name="Site 1", slug="site-1")
        cls.devices = (
            Device.objects.create(name="Device 1", device_type=devicetype, device_role=devicerole, site=site),
            Device.objects.create(name="Device 2", device_type=devicetype, device_role=devicerole, site=site),
        )
        cls.vlans = (
            VLAN.objects.create(vid=1, name="VLAN 1"),
            VLAN.objects.create(vid=2, name="VLAN 2"),
        )

        RelationshipAssociation.objects.create(
            relationship=cls.relationships[0],
            source_type=cls.device_type,
            source_id=cls.devices[0].pk,
            destination_type=cls.vlan_type,
            destination_id=cls.vlans[0].pk,
        )
        RelationshipAssociation.objects.create(
            relationship=cls.relationships[0],
            source_type=cls.device_type,
            source_id=cls.devices[1].pk,
            destination_type=cls.vlan_type,
            destination_id=cls.vlans[1].pk,
        )
        RelationshipAssociation.objects.create(
            relationship=cls.relationships[1],
            source_type=cls.vlan_type,
            source_id=cls.vlans[0].pk,
            destination_type=cls.device_type,
            destination_id=cls.devices[0].pk,
        )
        RelationshipAssociation.objects.create(
            relationship=cls.relationships[1],
            source_type=cls.vlan_type,
            source_id=cls.vlans[1].pk,
            destination_type=cls.device_type,
            destination_id=cls.devices[1].pk,
        )

    def test_id(self):
        params = {"id": self.queryset.values_list("pk", flat=True)[:2]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)

    def test_relationship(self):
        params = {"relationship": [self.relationships[0].slug]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)

    def test_source_type(self):
        params = {"source_type": ["dcim.device", "dcim.interface"]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)

    def test_source_id(self):
        params = {"source_id": [self.devices[0].pk, self.devices[1].pk]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)

    def test_destination_type(self):
        params = {"destination_type": ["dcim.device", "dcim.interface"]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)

    def test_destination_id(self):
        params = {"destination_id": [self.devices[0].pk, self.devices[1].pk]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)


class TagTestCase(TestCase):
    queryset = Tag.objects.all()
    filterset = TagFilterSet

    @classmethod
    def setUpTestData(cls):

        Tag.objects.create(name="Tag 1", slug="tag-1", color="ff0000")
        Tag.objects.create(name="Tag 2", slug="tag-2", color="00ff00")
        Tag.objects.create(name="Tag 3", slug="tag-3", color="0000ff")

    def test_id(self):
        params = {"id": self.queryset.values_list("pk", flat=True)[:2]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)

    def test_name(self):
        params = {"name": ["Tag 1", "Tag 2"]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)

    def test_slug(self):
        params = {"slug": ["tag-1", "tag-2"]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)

    def test_color(self):
        params = {"color": ["ff0000", "00ff00"]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)


class ObjectChangeTestCase(TestCase):
    queryset = ObjectChange.objects.all()
    filterset = ObjectChangeFilterSet

    @classmethod
    def setUpTestData(cls):
        users = (
            User.objects.create(username="user1"),
            User.objects.create(username="user2"),
            User.objects.create(username="user3"),
        )

        site = Site.objects.create(name="Test Site 1", slug="test-site-1")
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

    def test_id(self):
        params = {"id": self.queryset.values_list("pk", flat=True)[:3]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 3)

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


class CustomLinkTestCase(TestCase):
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


class WebhookTestCase(TestCase):
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


class StatusTestCase(TestCase):
    queryset = Status.objects.all()
    filterset = StatusFilterSet

    @classmethod
    def setUpTestData(cls):
        """
        Since many `Status` objects are created as part of data migrations, we're
        testing against those. If this seems magical, it's because they are
        imported from `ChoiceSet` enum objects.

        This method is defined just so it's clear that there is no need to
        create test data for this test case.

        See `extras.management.create_custom_statuses` for context.
        """

    def test_id(self):
        params = {"id": self.queryset.values_list("pk", flat=True)[:2]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)

    def test_name(self):
        params = {"name": ["Active", "Offline"]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)

    def test_slug(self):
        params = {"slug": ["active", "offline"]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)

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
        expected_count = 3
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), expected_count)

    def test_search(self):
        params = {"q": "active"}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 1)


class GraphQLTestCase(TestCase):
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

    def test_name(self):
        params = {"name": ["graphql-query-1"]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 1)

    def test_slug(self):
        params = {"slug": ["graphql-query-2"]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 1)

    def test_query(self):
        params = {"query": ["sites"]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 3)
