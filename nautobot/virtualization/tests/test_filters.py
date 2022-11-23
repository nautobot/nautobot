from django.contrib.contenttypes.models import ContentType
from django.db.models import Q

from nautobot.dcim.choices import InterfaceModeChoices
from nautobot.dcim.models import Device, DeviceRole, DeviceType, Manufacturer, Platform, Region, Site
from nautobot.extras.models import Status, Tag
from nautobot.ipam.choices import ServiceProtocolChoices
from nautobot.ipam.models import IPAddress, VLAN, Service
from nautobot.tenancy.models import Tenant
from nautobot.utilities.testing import FilterTestCases
from nautobot.utilities.utils import flatten_iterable
from nautobot.virtualization.filters import (
    ClusterTypeFilterSet,
    ClusterGroupFilterSet,
    ClusterFilterSet,
    VirtualMachineFilterSet,
    VMInterfaceFilterSet,
)
from nautobot.virtualization.models import (
    Cluster,
    ClusterGroup,
    ClusterType,
    VirtualMachine,
    VMInterface,
)


class ClusterTypeTestCase(FilterTestCases.NameSlugFilterTestCase):
    queryset = ClusterType.objects.all()
    filterset = ClusterTypeFilterSet

    @classmethod
    def setUpTestData(cls):

        cluster_types = (
            ClusterType.objects.create(name="Cluster Type 1", slug="cluster-type-1", description="A"),
            ClusterType.objects.create(name="Cluster Type 2", slug="cluster-type-2", description="B"),
            ClusterType.objects.create(name="Cluster Type 3", slug="cluster-type-3", description="C"),
        )

        cls.clusters = [
            Cluster.objects.create(name="Cluster 1", type=cluster_types[0]),
            Cluster.objects.create(name="Cluster 2", type=cluster_types[1]),
        ]

    def test_description(self):
        params = {"description": ["A", "B"]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)

    def test_clusters(self):
        with self.subTest("Clusters"):
            params = {"clusters": [self.clusters[0].pk, self.clusters[1].name]}
            self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)

        with self.subTest("Has Clusters"):
            params = {"has_clusters": True}
            self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)

            params = {"has_clusters": False}
            self.assertEqual(self.filterset(params, self.queryset).qs.count(), 1)


class ClusterGroupTestCase(FilterTestCases.NameSlugFilterTestCase):
    queryset = ClusterGroup.objects.all()
    filterset = ClusterGroupFilterSet

    @classmethod
    def setUpTestData(cls):

        cluster_groups = (
            ClusterGroup.objects.create(name="Cluster Group 1", slug="cluster-group-1", description="A"),
            ClusterGroup.objects.create(name="Cluster Group 2", slug="cluster-group-2", description="B"),
            ClusterGroup.objects.create(name="Cluster Group 3", slug="cluster-group-3", description="C"),
        )

        cluster_types = (
            ClusterType.objects.create(name="Cluster Type 1", slug="cluster-type-1"),
            ClusterType.objects.create(name="Cluster Type 2", slug="cluster-type-2"),
        )

        cls.clusters = (
            Cluster.objects.create(name="Cluster 1", type=cluster_types[0], group=cluster_groups[0]),
            Cluster.objects.create(name="Cluster 2", type=cluster_types[1], group=cluster_groups[1]),
        )

    def test_description(self):
        params = {"description": ["A", "B"]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)

    def test_clusters(self):
        with self.subTest("Clusters"):
            params = {"clusters": [self.clusters[0].pk, self.clusters[1].name]}
            self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)

        with self.subTest("Has Clusters"):
            params = {"has_clusters": True}
            self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)

            params = {"has_clusters": False}
            self.assertEqual(self.filterset(params, self.queryset).qs.count(), 1)


class ClusterTestCase(FilterTestCases.FilterTestCase, FilterTestCases.TenancyFilterTestCaseMixin):
    queryset = Cluster.objects.all()
    filterset = ClusterFilterSet
    tenancy_related_name = "clusters"

    @classmethod
    def setUpTestData(cls):

        cluster_types = (
            ClusterType.objects.create(name="Cluster Type 1", slug="cluster-type-1"),
            ClusterType.objects.create(name="Cluster Type 2", slug="cluster-type-2"),
            ClusterType.objects.create(name="Cluster Type 3", slug="cluster-type-3"),
        )

        cluster_groups = (
            ClusterGroup.objects.create(name="Cluster Group 1", slug="cluster-group-1"),
            ClusterGroup.objects.create(name="Cluster Group 2", slug="cluster-group-2"),
            ClusterGroup.objects.create(name="Cluster Group 3", slug="cluster-group-3"),
        )

        cls.regions = Region.objects.filter(sites__isnull=False)[:3]

        cls.sites = (
            Site.objects.filter(region=cls.regions[0]).first(),
            Site.objects.filter(region=cls.regions[1]).first(),
            Site.objects.filter(region=cls.regions[2]).first(),
        )

        tenants = Tenant.objects.filter(group__isnull=False)[:3]

        clusters = (
            Cluster.objects.create(
                name="Cluster 1",
                type=cluster_types[0],
                group=cluster_groups[0],
                site=cls.sites[0],
                tenant=tenants[0],
                comments="This is cluster 1",
            ),
            Cluster.objects.create(
                name="Cluster 2",
                type=cluster_types[1],
                group=cluster_groups[1],
                site=cls.sites[1],
                tenant=tenants[1],
                comments="This is cluster 2",
            ),
            Cluster.objects.create(
                name="Cluster 3",
                type=cluster_types[2],
                group=cluster_groups[2],
                site=cls.sites[2],
                tenant=tenants[2],
                comments="This is cluster 3",
            ),
        )

        manufacturer = Manufacturer.objects.create(name="Manufacturer 1", slug="manufacturer-1")
        devicetype = DeviceType.objects.create(manufacturer=manufacturer, model="Device Type", slug="device-type")
        devicerole = DeviceRole.objects.create(name="Device Role", slug="device-role", color="ff0000")

        cls.device = Device.objects.create(
            name="Device 1", device_type=devicetype, device_role=devicerole, site=cls.sites[0], cluster=clusters[0]
        )

        cls.virtualmachine = VirtualMachine.objects.create(name="Virtual Machine 1", cluster=clusters[1])

        cls.tag = Tag.objects.get_for_model(Cluster).first()
        clusters[0].tags.add(cls.tag)
        clusters[1].tags.add(cls.tag)

    def test_name(self):
        params = {"name": ["Cluster 1", "Cluster 2"]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)

    def test_comments(self):
        params = {"comments": ["This is cluster 1", "This is cluster 2"]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)

    def test_tags(self):
        params = {"tag": [self.tag.slug]}
        self.assertQuerysetEqual(self.filterset(params, self.queryset).qs, self.queryset.filter(tags=self.tag))

    def test_device(self):
        with self.subTest("Devices"):
            params = {"devices": [self.device.pk, self.device.name]}
            self.assertEqual(self.filterset(params, self.queryset).qs.count(), 1)

        with self.subTest("Has Devices"):
            params = {"has_devices": True}
            self.assertEqual(self.filterset(params, self.queryset).qs.count(), 1)

            params = {"has_devices": False}
            self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)

    def test_virtual_machines(self):
        with self.subTest("Virtual Machines"):
            params = {"virtual_machines": [self.virtualmachine.pk, self.virtualmachine.name]}
            self.assertEqual(self.filterset(params, self.queryset).qs.count(), 1)

        with self.subTest("Has Virtual Machines"):
            params = {"has_virtual_machines": True}
            self.assertEqual(self.filterset(params, self.queryset).qs.count(), 1)

            params = {"has_virtual_machines": False}
            self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)

    def test_region(self):
        filter_parent_regions = self.regions[:2]
        nested_regions = list(
            set(flatten_iterable(map(lambda r: r.get_descendants(include_self=True), filter_parent_regions)))
        )
        params = {"region_id": [filter_parent_regions[0].pk, filter_parent_regions[1].pk]}
        self.assertQuerysetEqual(
            self.filterset(params, self.queryset).qs, self.queryset.filter(site__region__in=nested_regions)
        )
        params = {"region": [filter_parent_regions[0].slug, filter_parent_regions[1].slug]}
        self.assertQuerysetEqual(
            self.filterset(params, self.queryset).qs, self.queryset.filter(site__region__in=nested_regions)
        )

    def test_site(self):
        sites = list(self.sites[:2])
        params = {"site_id": [sites[0].pk, sites[1].pk]}
        self.assertQuerysetEqual(self.filterset(params, self.queryset).qs, self.queryset.filter(site__in=sites))
        params = {"site": [sites[0].slug, sites[1].slug]}
        self.assertQuerysetEqual(self.filterset(params, self.queryset).qs, self.queryset.filter(site__in=sites))

    def test_group(self):
        groups = ClusterGroup.objects.all()[:2]
        params = {"group_id": [groups[0].pk, groups[1].pk]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)
        params = {"group": [groups[0].slug, groups[1].slug]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)

    def test_type(self):
        types = ClusterType.objects.all()[:2]
        params = {"type_id": [types[0].pk, types[1].pk]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)
        params = {"type": [types[0].slug, types[1].slug]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)

    def test_search(self):
        value = self.queryset.values_list("pk", flat=True)[0]
        params = {"q": value}
        self.assertEqual(self.filterset(params, self.queryset).qs.values_list("pk", flat=True)[0], value)


class VirtualMachineTestCase(FilterTestCases.FilterTestCase, FilterTestCases.TenancyFilterTestCaseMixin):
    queryset = VirtualMachine.objects.all()
    filterset = VirtualMachineFilterSet
    tenancy_related_name = "virtual_machines"

    @classmethod
    def setUpTestData(cls):

        cluster_types = (
            ClusterType.objects.create(name="Cluster Type 1", slug="cluster-type-1"),
            ClusterType.objects.create(name="Cluster Type 2", slug="cluster-type-2"),
            ClusterType.objects.create(name="Cluster Type 3", slug="cluster-type-3"),
        )

        cluster_groups = (
            ClusterGroup.objects.create(name="Cluster Group 1", slug="cluster-group-1"),
            ClusterGroup.objects.create(name="Cluster Group 2", slug="cluster-group-2"),
            ClusterGroup.objects.create(name="Cluster Group 3", slug="cluster-group-3"),
        )

        cls.regions = Region.objects.filter(sites__isnull=False)[:3]

        cls.sites = (
            Site.objects.filter(region=cls.regions[0]).first(),
            Site.objects.filter(region=cls.regions[1]).first(),
            Site.objects.filter(region=cls.regions[2]).first(),
        )

        clusters = (
            Cluster.objects.create(
                name="Cluster 1",
                type=cluster_types[0],
                group=cluster_groups[0],
                site=cls.sites[0],
            ),
            Cluster.objects.create(
                name="Cluster 2",
                type=cluster_types[1],
                group=cluster_groups[1],
                site=cls.sites[1],
            ),
            Cluster.objects.create(
                name="Cluster 3",
                type=cluster_types[2],
                group=cluster_groups[2],
                site=cls.sites[2],
            ),
        )

        platforms = (
            Platform.objects.create(name="Platform 1", slug="platform-1"),
            Platform.objects.create(name="Platform 2", slug="platform-2"),
            Platform.objects.create(name="Platform 3", slug="platform-3"),
        )
        cls.platforms = platforms

        roles = (
            DeviceRole.objects.create(name="Device Role 1", slug="device-role-1"),
            DeviceRole.objects.create(name="Device Role 2", slug="device-role-2"),
            DeviceRole.objects.create(name="Device Role 3", slug="device-role-3"),
        )
        cls.roles = roles

        tenants = Tenant.objects.filter(group__isnull=False)[:3]

        statuses = Status.objects.get_for_model(VirtualMachine)
        status_map = {s.slug: s for s in statuses.all()}

        vms = (
            VirtualMachine.objects.create(
                name="Virtual Machine 1",
                cluster=clusters[0],
                platform=platforms[0],
                role=roles[0],
                tenant=tenants[0],
                status=status_map["active"],
                vcpus=1,
                memory=1,
                disk=1,
                local_context_data={"foo": 123},
                comments="This is VM 1",
            ),
            VirtualMachine.objects.create(
                name="Virtual Machine 2",
                cluster=clusters[1],
                platform=platforms[1],
                role=roles[1],
                tenant=tenants[1],
                status=status_map["staged"],
                vcpus=2,
                memory=2,
                disk=2,
                comments="This is VM 2",
            ),
            VirtualMachine.objects.create(
                name="Virtual Machine 3",
                cluster=clusters[2],
                platform=platforms[2],
                role=roles[2],
                tenant=tenants[2],
                status=status_map["offline"],
                vcpus=3,
                memory=3,
                disk=3,
                comments="This is VM 3",
            ),
        )

        cls.interfaces = (
            VMInterface.objects.create(
                virtual_machine=vms[0],
                name="Interface 1",
                mac_address="00-00-00-00-00-01",
            ),
            VMInterface.objects.create(
                virtual_machine=vms[1],
                name="Interface 2",
                mac_address="00-00-00-00-00-02",
            ),
            VMInterface.objects.create(
                virtual_machine=vms[2],
                name="Interface 3",
                mac_address="00-00-00-00-00-03",
            ),
        )

        cls.services = (
            Service.objects.create(
                virtual_machine=vms[1],
                name="Service 1",
                protocol=ServiceProtocolChoices.PROTOCOL_UDP,
                ports=[2003],
            ),
            Service.objects.create(
                virtual_machine=vms[2],
                name="Service 2",
                protocol=ServiceProtocolChoices.PROTOCOL_UDP,
                ports=[2002],
            ),
        )

        # Assign primary IPs for filtering
        cls.ipaddresses = (
            IPAddress.objects.create(address="192.0.2.1/24", assigned_object=cls.interfaces[0]),
            IPAddress.objects.create(address="fe80::8ef:3eff:fe4c:3895/24", assigned_object=cls.interfaces[1]),
        )

        VirtualMachine.objects.filter(pk=vms[0].pk).update(primary_ip4=cls.ipaddresses[0])
        VirtualMachine.objects.filter(pk=vms[1].pk).update(primary_ip6=cls.ipaddresses[1])

        cls.tag = Tag.objects.get_for_model(VirtualMachine).first()
        vms[0].tags.add(cls.tag)
        vms[1].tags.add(cls.tag)

    def test_name(self):
        params = {"name": ["Virtual Machine 1", "Virtual Machine 2"]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)

    def test_comments(self):
        params = {"comments": ["This is VM 1", "This is VM 2"]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)

    def test_primary_ip4(self):
        params = {"primary_ip4": ["192.0.2.1/24", self.ipaddresses[0].pk]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 1)

    def test_primary_ip6(self):
        params = {"primary_ip6": ["fe80::8ef:3eff:fe4c:3895/24", self.ipaddresses[1].pk]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 1)

    def test_services(self):
        with self.subTest("Services"):
            params = {"services": [self.services[0].pk, self.services[1].name]}
            self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)

        with self.subTest("Has Services"):
            params = {"has_services": True}
            self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)

            params = {"has_services": False}
            self.assertEqual(self.filterset(params, self.queryset).qs.count(), 1)

    def test_interfaces(self):
        with self.subTest("Interfaces"):
            params = {"interfaces": [self.interfaces[0].pk, self.interfaces[1].pk]}
            self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)

        with self.subTest("Has Interfaces"):
            params = {"has_interfaces": True}
            self.assertEqual(self.filterset(params, self.queryset).qs.count(), 3)

            params = {"has_interfaces": False}
            self.assertEqual(self.filterset(params, self.queryset).qs.count(), 0)

    def test_tags(self):
        params = {"tag": [self.tag.slug]}
        self.assertQuerysetEqual(self.filterset(params, self.queryset).qs, self.queryset.filter(tags=self.tag))

    def test_vcpus(self):
        params = {"vcpus": [1, 2]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)

    def test_memory(self):
        params = {"memory": [1, 2]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)

    def test_disk(self):
        params = {"disk": [1, 2]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)

    def test_status(self):
        params = {"status": ["active", "staged"]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)

    def test_cluster_group(self):
        groups = ClusterGroup.objects.all()[:2]
        params = {"cluster_group_id": [groups[0].pk, groups[1].pk]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)
        params = {"cluster_group": [groups[0].slug, groups[1].slug]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)

    def test_cluster_type(self):
        types = ClusterType.objects.all()[:2]
        params = {"cluster_type_id": [types[0].pk, types[1].pk]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)
        params = {"cluster_type": [types[0].slug, types[1].slug]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)

    def test_cluster(self):
        clusters = Cluster.objects.all()[:2]
        params = {"cluster_id": [clusters[0].pk, clusters[1].pk]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)
        # 2.0 TODO: 'cluster' should match on name (This should be solved in FilterSet refactors)
        # params = {'cluster': [clusters[0].name, clusters[1].name]}
        # self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)

    def test_region(self):
        filter_parent_regions = self.regions[:2]
        nested_regions = list(
            set(flatten_iterable(map(lambda r: r.get_descendants(include_self=True), filter_parent_regions)))
        )
        params = {"region_id": [filter_parent_regions[0].pk, filter_parent_regions[1].pk]}
        self.assertQuerysetEqual(
            self.filterset(params, self.queryset).qs, self.queryset.filter(cluster__site__region__in=nested_regions)
        )
        params = {"region": [filter_parent_regions[0].slug, filter_parent_regions[1].slug]}
        self.assertQuerysetEqual(
            self.filterset(params, self.queryset).qs, self.queryset.filter(cluster__site__region__in=nested_regions)
        )

    def test_site(self):
        sites = list(self.sites[:2])
        params = {"site_id": [sites[0].pk, sites[1].pk]}
        self.assertQuerysetEqual(
            self.filterset(params, self.queryset).qs, self.queryset.filter(cluster__site__in=sites)
        )
        params = {"site": [sites[0].slug, sites[1].slug]}
        self.assertQuerysetEqual(
            self.filterset(params, self.queryset).qs, self.queryset.filter(cluster__site__in=sites)
        )

    def test_role(self):
        roles = self.roles[:2]
        params = {"role_id": [roles[0].pk, roles[1].pk]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), len(roles))
        params = {"role": [roles[0].slug, roles[1].slug]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), len(roles))

    def test_platform(self):
        platforms = self.platforms[:2]
        params = {"platform_id": [platforms[0].pk, platforms[1].pk]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), len(platforms))
        params = {"platform": [platforms[0].slug, platforms[1].slug]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), len(platforms))

    def test_mac_address(self):
        params = {"mac_address": ["00-00-00-00-00-01", "00-00-00-00-00-02"]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)

    def test_has_primary_ip(self):
        params = {"has_primary_ip": "true"}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)
        params = {"has_primary_ip": "false"}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 1)

    def test_local_context_data(self):
        params = {"local_context_data": "true"}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 1)
        params = {"local_context_data": "false"}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)

    def test_search(self):
        value = self.queryset.values_list("pk", flat=True)[0]
        params = {"q": value}
        self.assertEqual(self.filterset(params, self.queryset).qs.values_list("pk", flat=True)[0], value)


class VMInterfaceTestCase(FilterTestCases.FilterTestCase):
    queryset = VMInterface.objects.all()
    filterset = VMInterfaceFilterSet

    @classmethod
    def setUpTestData(cls):

        cluster_types = (
            ClusterType.objects.create(name="Cluster Type 1", slug="cluster-type-1"),
            ClusterType.objects.create(name="Cluster Type 2", slug="cluster-type-2"),
            ClusterType.objects.create(name="Cluster Type 3", slug="cluster-type-3"),
        )

        clusters = (
            Cluster.objects.create(name="Cluster 1", type=cluster_types[0]),
            Cluster.objects.create(name="Cluster 2", type=cluster_types[1]),
            Cluster.objects.create(name="Cluster 3", type=cluster_types[2]),
        )

        vms = (
            VirtualMachine.objects.create(name="Virtual Machine 1", cluster=clusters[0]),
            VirtualMachine.objects.create(name="Virtual Machine 2", cluster=clusters[1]),
            VirtualMachine.objects.create(name="Virtual Machine 3", cluster=clusters[2]),
        )

        statuses = Status.objects.get_for_model(VMInterface)

        cls.vlan1 = VLAN.objects.first()
        cls.vlan2 = VLAN.objects.last()

        vminterfaces = (
            VMInterface.objects.create(
                virtual_machine=vms[0],
                name="Interface 1",
                enabled=True,
                mtu=100,
                mac_address="00-00-00-00-00-01",
                status=statuses.get(slug="active"),
                description="This is a description of Interface1",
                mode=InterfaceModeChoices.MODE_ACCESS,
                untagged_vlan=cls.vlan1,
            ),
            VMInterface.objects.create(
                virtual_machine=vms[1],
                name="Interface 2",
                enabled=True,
                mtu=200,
                mac_address="00-00-00-00-00-02",
                status=statuses.get(slug="active"),
                description="This is a description of Interface2",
                mode=InterfaceModeChoices.MODE_ACCESS,
                untagged_vlan=cls.vlan2,
            ),
            VMInterface.objects.create(
                virtual_machine=vms[2],
                name="Interface 3",
                enabled=False,
                mtu=300,
                mac_address="00-00-00-00-00-03",
                status=statuses.get(slug="planned"),
                description="This is a description of Interface3",
                mode=InterfaceModeChoices.MODE_TAGGED,
            ),
        )

        vminterfaces[2].tagged_vlans.add(cls.vlan2)

        # Assign primary IPs for filtering
        ip_address4 = IPAddress.objects.ip_family(4).first()
        ip_address4.assigned_object = vminterfaces[0]
        ip_address4.validated_save()
        ip_address6 = IPAddress.objects.ip_family(6).first()
        ip_address6.assigned_object = vminterfaces[1]
        ip_address6.validated_save()

        cls.tag = Tag.objects.get_for_model(VMInterface).first()
        vminterfaces[0].tags.add(cls.tag)
        vminterfaces[1].tags.add(cls.tag)

    def test_name(self):
        params = {"name": ["Interface 1", "Interface 2"]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)

    def test_description(self):
        params = {"description": ["This is a description of Interface3", "This is a description of Interface2"]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)

    def test_tags(self):
        params = {"tag": [self.tag.slug]}
        self.assertQuerysetEqual(self.filterset(params, self.queryset).qs, self.queryset.filter(tags=self.tag))

    def test_tagged_vlans(self):
        with self.subTest("Tagged VLANs"):
            params = {"tagged_vlans": [self.vlan1.pk, self.vlan2.vid]}
            self.assertEqual(self.filterset(params, self.queryset).qs.count(), 1)

        with self.subTest("Has Tagged VLANs"):
            params = {"has_tagged_vlans": False}
            self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)

            params = {"has_tagged_vlans": True}
            self.assertEqual(self.filterset(params, self.queryset).qs.count(), 1)

    def test_untagged_vlan(self):
        params = {"untagged_vlan": [self.vlan1.pk, self.vlan2.vid]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)

    def test_mode(self):
        params = {"mode": [InterfaceModeChoices.MODE_ACCESS, InterfaceModeChoices.MODE_TAGGED]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 3)

    def test_ip_addresses(self):
        with self.subTest("Primary Addresses"):
            vminterface_ct = ContentType.objects.get_for_model(VMInterface)
            ipaddresses = list(
                IPAddress.objects.filter(assigned_object_id__isnull=False, assigned_object_type=vminterface_ct)[:2]
            )
            params = {"ip_addresses": [ipaddresses[0].address, ipaddresses[1].id]}
            self.assertQuerysetEqualAndNotEmpty(
                self.filterset(params, self.queryset).qs,
                self.queryset.filter(ip_addresses__in=ipaddresses),
            )

        with self.subTest("Has Primary Addresses"):
            params = {"has_ip_addresses": False}
            self.assertQuerysetEqualAndNotEmpty(
                self.filterset(params, self.queryset).qs,
                self.queryset.filter(ip_addresses__isnull=True),
            )

            params = {"has_ip_addresses": True}
            self.assertQuerysetEqualAndNotEmpty(
                self.filterset(params, self.queryset).qs,
                self.queryset.filter(ip_addresses__isnull=False),
            )

    def test_assigned_to_interface(self):
        params = {"enabled": "true"}
        self.assertQuerysetEqualAndNotEmpty(
            self.filterset(params, self.queryset).qs,
            self.queryset.filter(enabled=True),
        )
        params = {"enabled": "false"}
        self.assertQuerysetEqualAndNotEmpty(
            self.filterset(params, self.queryset).qs,
            self.queryset.filter(enabled=False),
        )

    def test_parent(self):
        # Create child interfaces
        parent_interface = VMInterface.objects.first()
        child_interfaces = (
            VMInterface(
                virtual_machine=parent_interface.virtual_machine, name="Child 1", parent_interface=parent_interface
            ),
            VMInterface(
                virtual_machine=parent_interface.virtual_machine, name="Child 2", parent_interface=parent_interface
            ),
            VMInterface(
                virtual_machine=parent_interface.virtual_machine, name="Child 3", parent_interface=parent_interface
            ),
        )
        VMInterface.objects.bulk_create(child_interfaces)
        params = {"parent_interface": [parent_interface.pk, parent_interface.name]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 3)

    def test_child(self):
        # Create child interfaces
        parent_interface = VMInterface.objects.first()
        child_interfaces = (
            VMInterface(
                virtual_machine=parent_interface.virtual_machine, name="Child 1", parent_interface=parent_interface
            ),
            VMInterface(
                virtual_machine=parent_interface.virtual_machine, name="Child 2", parent_interface=parent_interface
            ),
            VMInterface(
                virtual_machine=parent_interface.virtual_machine, name="Child 3", parent_interface=parent_interface
            ),
        )
        VMInterface.objects.bulk_create(child_interfaces)
        with self.subTest("Child Interfaces"):
            params = {"child_interfaces": [child_interfaces[0].pk, child_interfaces[1].name]}
            self.assertEqual(self.filterset(params, self.queryset).qs.count(), 1)

        with self.subTest("Has child Interfaces"):
            params = {"has_child_interfaces": True}
            self.assertEqual(self.filterset(params, self.queryset).qs.count(), 1)

            params = {"has_child_interfaces": False}
            self.assertEqual(self.filterset(params, self.queryset).qs.count(), 5)

    def test_bridge(self):
        # Create bridged interfaces
        bridge_interface = VMInterface.objects.first()
        bridged_interfaces = (
            VMInterface(virtual_machine=bridge_interface.virtual_machine, name="Bridged 1", bridge=bridge_interface),
            VMInterface(virtual_machine=bridge_interface.virtual_machine, name="Bridged 2", bridge=bridge_interface),
            VMInterface(virtual_machine=bridge_interface.virtual_machine, name="Bridged 3", bridge=bridge_interface),
        )
        VMInterface.objects.bulk_create(bridged_interfaces)

        params = {"bridge": [bridge_interface.pk, bridge_interface.name]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 3)

    def test_bridged_interfaces(self):
        # Create bridged interfaces
        bridge_interface = VMInterface.objects.first()
        bridged_interfaces = (
            VMInterface(virtual_machine=bridge_interface.virtual_machine, name="Bridged 1", bridge=bridge_interface),
            VMInterface(virtual_machine=bridge_interface.virtual_machine, name="Bridged 2", bridge=bridge_interface),
            VMInterface(virtual_machine=bridge_interface.virtual_machine, name="Bridged 3", bridge=bridge_interface),
        )
        VMInterface.objects.bulk_create(bridged_interfaces)

        with self.subTest("Bridged Interfaces"):
            params = {"bridged_interfaces": [bridged_interfaces[0].pk, bridged_interfaces[1].name]}
            self.assertEqual(self.filterset(params, self.queryset).qs.count(), 1)

        with self.subTest("Has Bridged Interfaces"):
            params = {"has_bridged_interfaces": True}
            self.assertEqual(self.filterset(params, self.queryset).qs.count(), 1)

            params = {"has_bridged_interfaces": False}
            self.assertEqual(self.filterset(params, self.queryset).qs.count(), 5)

    def test_mtu(self):
        params = {"mtu": [100, 200]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)

    def test_virtual_machine(self):
        vms = VirtualMachine.objects.all()[:2]
        params = {"virtual_machine_id": [vms[0].pk, vms[1].pk]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)
        params = {"virtual_machine": [vms[0].name, vms[1].name]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)

    def test_mac_address(self):
        params = {"mac_address": ["00-00-00-00-00-01", "00-00-00-00-00-02"]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)

    def test_status(self):
        params = {"status": ["active"]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)

    def test_search(self):
        value = self.queryset.first().pk
        params = {"q": value}
        q = Q(id__iexact=str(value)) | Q(name__icontains=value)
        self.assertQuerysetEqualAndNotEmpty(
            self.filterset(params, self.queryset).qs,
            self.queryset.filter(q),
        )
