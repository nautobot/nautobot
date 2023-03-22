from django.db.models import Q

from nautobot.core.testing import FilterTestCases
from nautobot.dcim.choices import InterfaceModeChoices
from nautobot.dcim.models import Device, DeviceType, Location, LocationType, Manufacturer, Platform
from nautobot.extras.models import Role, Status, Tag
from nautobot.ipam.choices import ServiceProtocolChoices
from nautobot.ipam.models import IPAddress, VLAN, Service
from nautobot.tenancy.models import Tenant
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
            Cluster.objects.create(name="Cluster 1", cluster_type=cluster_types[0]),
            Cluster.objects.create(name="Cluster 2", cluster_type=cluster_types[1]),
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
            Cluster.objects.create(name="Cluster 1", cluster_type=cluster_types[0], cluster_group=cluster_groups[0]),
            Cluster.objects.create(name="Cluster 2", cluster_type=cluster_types[1], cluster_group=cluster_groups[1]),
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

        location_type_1 = LocationType.objects.get(name="Campus")
        location_type_2 = LocationType.objects.get(name="Building")
        cls.locations = (
            Location.objects.create(name="Location 1", location_type=location_type_1),
            Location.objects.create(name="Location 2", location_type=location_type_2),
            Location.objects.create(name="Location 3", location_type=location_type_2),
        )
        cls.locations[1].parent = cls.locations[0]

        tenants = Tenant.objects.filter(tenant_group__isnull=False)[:3]

        clusters = (
            Cluster.objects.create(
                name="Cluster 1",
                cluster_type=cluster_types[0],
                cluster_group=cluster_groups[0],
                location=cls.locations[0],
                tenant=tenants[0],
                comments="This is cluster 1",
            ),
            Cluster.objects.create(
                name="Cluster 2",
                cluster_type=cluster_types[1],
                cluster_group=cluster_groups[1],
                location=cls.locations[1],
                tenant=tenants[1],
                comments="This is cluster 2",
            ),
            Cluster.objects.create(
                name="Cluster 3",
                cluster_type=cluster_types[2],
                cluster_group=cluster_groups[2],
                location=cls.locations[2],
                tenant=tenants[2],
                comments="This is cluster 3",
            ),
        )

        manufacturer = Manufacturer.objects.create(name="Manufacturer 1", slug="manufacturer-1")
        devicetype = DeviceType.objects.create(manufacturer=manufacturer, model="Device Type", slug="device-type")
        devicerole = Role.objects.get_for_model(Device).first()

        cls.device = Device.objects.create(
            name="Device 1", device_type=devicetype, role=devicerole, location=cls.locations[0], cluster=clusters[0]
        )

        cls.virtualmachine = VirtualMachine.objects.create(name="Virtual Machine 1", cluster=clusters[1])

        clusters[0].tags.set(Tag.objects.get_for_model(Cluster))
        clusters[1].tags.set(Tag.objects.get_for_model(Cluster)[:3])

    def test_name(self):
        params = {"name": ["Cluster 1", "Cluster 2"]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)

    def test_comments(self):
        params = {"comments": ["This is cluster 1", "This is cluster 2"]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)

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

    def test_location(self):
        params = {"location": [self.locations[0].pk, self.locations[1].pk]}
        self.assertQuerysetEqual(
            self.filterset(params, self.queryset).qs, self.queryset.filter(location__in=params["location"])
        )
        params = {"location": [self.locations[0].slug, self.locations[1].slug]}
        self.assertQuerysetEqual(
            self.filterset(params, self.queryset).qs, self.queryset.filter(location__slug__in=params["location"])
        )

    def test_cluster_group(self):
        cluster_groups = list(ClusterGroup.objects.all()[:2])
        filter_params = [
            {"cluster_group_id": [cluster_groups[0].pk, cluster_groups[1].pk]},
            {"cluster_group": [cluster_groups[0].pk, cluster_groups[1].slug]},
        ]
        for params in filter_params:
            self.assertQuerysetEqualAndNotEmpty(
                self.filterset(params, self.queryset).qs,
                self.queryset.filter(cluster_group__in=cluster_groups).distinct(),
            )

    def test_cluster_type(self):
        cluster_types = list(ClusterType.objects.all()[:2])
        filter_params = [
            {"cluster_type_id": [cluster_types[0].pk, cluster_types[1].pk]},
            {"cluster_type": [cluster_types[0].pk, cluster_types[1].slug]},
        ]
        for params in filter_params:
            self.assertQuerysetEqualAndNotEmpty(
                self.filterset(params, self.queryset).qs,
                self.queryset.filter(cluster_type__in=cluster_types).distinct(),
            )

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

        location_type_1 = LocationType.objects.get(name="Campus")
        location_type_2 = LocationType.objects.get(name="Building")
        cls.locations = (
            Location.objects.create(name="Location 1", location_type=location_type_1),
            Location.objects.create(name="Location 2", location_type=location_type_2),
            Location.objects.create(name="Location 3", location_type=location_type_2),
        )
        cls.locations[1].parent = cls.locations[0]

        clusters = (
            Cluster.objects.create(
                name="Cluster 1",
                cluster_type=cluster_types[0],
                cluster_group=cluster_groups[0],
                location=cls.locations[0],
            ),
            Cluster.objects.create(
                name="Cluster 2",
                cluster_type=cluster_types[1],
                cluster_group=cluster_groups[1],
                location=cls.locations[1],
            ),
            Cluster.objects.create(
                name="Cluster 3",
                cluster_type=cluster_types[2],
                cluster_group=cluster_groups[2],
                location=cls.locations[2],
            ),
        )

        platforms = (
            Platform.objects.create(name="Platform 1", slug="platform-1"),
            Platform.objects.create(name="Platform 2", slug="platform-2"),
            Platform.objects.create(name="Platform 3", slug="platform-3"),
        )
        cls.platforms = platforms

        roles = Role.objects.get_for_model(VirtualMachine)
        cls.roles = roles

        tenants = Tenant.objects.filter(tenant_group__isnull=False)[:3]

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
                local_config_context_data={"foo": 123},
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
            VirtualMachine.objects.create(
                name="Virtual Machine 4",
                cluster=clusters[2],
                platform=platforms[2],
                role=roles[2],
                tenant=tenants[2],
                status=status_map["offline"],
                vcpus=3,
                memory=3,
                disk=3,
                comments="This is VM 4",
            ),
            VirtualMachine.objects.create(
                name="Virtual Machine 5",
                cluster=clusters[2],
                platform=platforms[2],
                role=roles[2],
                tenant=tenants[2],
                status=status_map["offline"],
                vcpus=3,
                memory=3,
                disk=3,
                comments="This is VM 5",
            ),
            VirtualMachine.objects.create(
                name="Virtual Machine 6",
                cluster=clusters[2],
                platform=platforms[2],
                role=roles[2],
                tenant=tenants[2],
                status=status_map["offline"],
                vcpus=3,
                memory=3,
                disk=3,
                comments="This is VM 6",
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
            IPAddress.objects.create(address="192.0.2.1/24"),
            IPAddress.objects.create(address="fe80::8ef:3eff:fe4c:3895/24"),
        )
        cls.interfaces[0].add_ip_addresses(cls.ipaddresses[0])
        cls.interfaces[1].add_ip_addresses(cls.ipaddresses[1])

        VirtualMachine.objects.filter(pk=vms[0].pk).update(primary_ip4=cls.ipaddresses[0])
        VirtualMachine.objects.filter(pk=vms[1].pk).update(primary_ip6=cls.ipaddresses[1])

        vms[0].tags.set(Tag.objects.get_for_model(VirtualMachine))
        vms[1].tags.set(Tag.objects.get_for_model(VirtualMachine)[:3])

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
        params = {"services": [self.services[0].pk, self.services[1].name]}
        self.assertQuerysetEqualAndNotEmpty(
            self.filterset(params, self.queryset).qs,
            self.queryset.filter(services__in=[self.services[0].pk, self.services[1].pk]),
        )

    def test_interfaces(self):
        params = {"interfaces": [self.interfaces[0].pk, self.interfaces[1].pk]}
        self.assertQuerysetEqualAndNotEmpty(
            self.filterset(params, self.queryset).qs,
            self.queryset.filter(interfaces__in=[self.interfaces[0].pk, self.interfaces[1].pk]),
        )

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
        groups = list(ClusterGroup.objects.all()[:2])
        filter_params = [
            {"cluster_group_id": [groups[0].pk, groups[1].pk]},
            {"cluster_group": [groups[0].pk, groups[1].slug]},
        ]
        for params in filter_params:
            self.assertQuerysetEqualAndNotEmpty(
                self.filterset(params, self.queryset).qs,
                self.queryset.filter(cluster__cluster_group__in=groups).distinct(),
            )

    def test_cluster_type(self):
        types = list(ClusterType.objects.all()[:2])
        filter_params = [
            {"cluster_type_id": [types[0].pk, types[1].pk]},
            {"cluster_type": [types[0].pk, types[1].slug]},
        ]
        for params in filter_params:
            self.assertQuerysetEqualAndNotEmpty(
                self.filterset(params, self.queryset).qs,
                self.queryset.filter(cluster__cluster_type__in=types).distinct(),
            )

    def test_cluster(self):
        clusters = Cluster.objects.all()[:2]
        params = {"cluster_id": [clusters[0].pk, clusters[1].pk]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)
        # 2.0 TODO: 'cluster' should match on name (This should be solved in FilterSet refactors)
        # params = {'cluster': [clusters[0].name, clusters[1].name]}
        # self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)

    def test_location(self):
        params = {"location": [self.locations[0].pk, self.locations[1].pk]}
        self.assertQuerysetEqual(
            self.filterset(params, self.queryset).qs, self.queryset.filter(cluster__location__in=params["location"])
        )
        params = {"location": [self.locations[0].slug, self.locations[1].slug]}
        self.assertQuerysetEqual(
            self.filterset(params, self.queryset).qs,
            self.queryset.filter(cluster__location__slug__in=params["location"]),
        )

    def test_role(self):
        roles = self.roles[:2]
        params = {"role": [roles[0].pk, roles[1].slug]}
        self.assertQuerysetEqualAndNotEmpty(
            self.filterset(params, self.queryset).qs, self.queryset.filter(role__in=[roles[0], roles[1]])
        )

    def test_platform(self):
        platforms = self.platforms[:2]
        filter_params = [
            {"platform_id": [platforms[0].pk, platforms[1].pk]},
            {"platform": [platforms[0].pk, platforms[1].slug]},
        ]
        for params in filter_params:
            self.assertQuerysetEqualAndNotEmpty(
                self.filterset(params, self.queryset).qs, self.queryset.filter(platform__in=platforms).distinct()
            )

    def test_mac_address(self):
        params = {"mac_address": ["00-00-00-00-00-01", "00-00-00-00-00-02"]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)

    def test_has_primary_ip(self):
        params = {"has_primary_ip": "true"}
        self.assertQuerysetEqualAndNotEmpty(
            self.filterset(params, self.queryset).qs,
            self.queryset.exclude(primary_ip4__isnull=True, primary_ip6__isnull=True),
        )
        params = {"has_primary_ip": "false"}
        self.assertQuerysetEqualAndNotEmpty(
            self.filterset(params, self.queryset).qs,
            self.queryset.filter(primary_ip4__isnull=True, primary_ip6__isnull=True),
        )

    def test_local_config_context_data(self):
        params = {"local_config_context_data": "true"}
        self.assertQuerysetEqualAndNotEmpty(
            self.filterset(params, self.queryset).qs,
            self.queryset.filter(local_config_context_data__isnull=False),
        )
        params = {"local_config_context_data": "false"}
        self.assertQuerysetEqualAndNotEmpty(
            self.filterset(params, self.queryset).qs,
            self.queryset.filter(local_config_context_data__isnull=True),
        )

    def test_search(self):
        value = self.queryset.values_list("pk", flat=True)[0]
        params = {"q": value}
        self.assertEqual(self.filterset(params, self.queryset).qs.values_list("pk", flat=True)[0], value)


class VMInterfaceTestCase(FilterTestCases.FilterTestCase):
    queryset = VMInterface.objects.all()
    filterset = VMInterfaceFilterSet

    generic_filter_tests = (
        ["bridge"],
        ["bridged_interfaces"],
        ["child_interfaces"],
        ["cluster_id", "virtual_machine__cluster__id"],
        ["cluster", "virtual_machine__cluster__name"],
        ["description"],
        ["mac_address"],
        ["mtu"],
        ["name"],
        ["parent_interface"],
        ["status", "status__slug"],
        ["tagged_vlans", "tagged_vlans__pk"],
        ["tagged_vlans", "tagged_vlans__vid"],
        ["untagged_vlan", "untagged_vlan__pk"],
        ["untagged_vlan", "untagged_vlan__vid"],
        ["virtual_machine", "virtual_machine__name"],
        ["virtual_machine_id", "virtual_machine__id"],
    )

    @classmethod
    def setUpTestData(cls):

        cluster_types = (
            ClusterType.objects.create(name="Cluster Type 1", slug="cluster-type-1"),
            ClusterType.objects.create(name="Cluster Type 2", slug="cluster-type-2"),
            ClusterType.objects.create(name="Cluster Type 3", slug="cluster-type-3"),
        )

        clusters = (
            Cluster.objects.create(name="Cluster 1", cluster_type=cluster_types[0]),
            Cluster.objects.create(name="Cluster 2", cluster_type=cluster_types[1]),
            Cluster.objects.create(name="Cluster 3", cluster_type=cluster_types[2]),
        )

        vms = (
            VirtualMachine.objects.create(name="Virtual Machine 1", cluster=clusters[0]),
            VirtualMachine.objects.create(name="Virtual Machine 2", cluster=clusters[1]),
            VirtualMachine.objects.create(name="Virtual Machine 3", cluster=clusters[2]),
        )

        statuses = Status.objects.get_for_model(VMInterface)

        vlans = VLAN.objects.filter(location=None)[:2]
        cls.vlan1 = vlans[0]
        cls.vlan2 = vlans[1]

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
        child_interfaces = (
            VMInterface.objects.create(
                virtual_machine=vms[0],
                bridge=vminterfaces[0],
                parent_interface=vminterfaces[0],
                name="Interface 4",
                enabled=False,
                mtu=300,
                mac_address="00-00-00-00-00-04",
                status=statuses.get(slug="planned"),
                description="This is a description of Interface4",
                mode=InterfaceModeChoices.MODE_TAGGED,
            ),
            VMInterface.objects.create(
                virtual_machine=vms[1],
                bridge=vminterfaces[1],
                parent_interface=vminterfaces[1],
                name="Interface 5",
                enabled=False,
                mtu=300,
                mac_address="00-00-00-00-00-05",
                status=statuses.get(slug="maintenance"),
                description="This is a description of Interface5",
                mode=InterfaceModeChoices.MODE_TAGGED_ALL,
            ),
        )

        child_interfaces[0].tagged_vlans.add(cls.vlan1)
        vminterfaces[2].tagged_vlans.add(cls.vlan2)

        # Assign primary IPs for filtering
        ip_address4 = IPAddress.objects.ip_family(4).first()
        vminterfaces[0].add_ip_addresses(ip_address4)
        ip_address4.validated_save()
        ip_address6 = IPAddress.objects.ip_family(6).first()
        vminterfaces[1].add_ip_addresses(ip_address6)
        ip_address6.validated_save()

        vminterfaces[0].tags.set(Tag.objects.get_for_model(VMInterface))
        vminterfaces[1].tags.set(Tag.objects.get_for_model(VMInterface)[:3])

    def test_mode(self):
        params = {"mode": [InterfaceModeChoices.MODE_ACCESS]}
        self.assertQuerysetEqualAndNotEmpty(
            self.filterset(params, self.queryset).qs,
            self.queryset.filter(mode=InterfaceModeChoices.MODE_ACCESS),
        )

    def test_ip_addresses(self):
        ipaddresses = list(IPAddress.objects.filter(vm_interfaces__isnull=False)[:2])
        params = {"ip_addresses": [ipaddresses[0].address, ipaddresses[1].id]}
        self.assertQuerysetEqualAndNotEmpty(
            self.filterset(params, self.queryset).qs,
            self.queryset.filter(ip_addresses__in=ipaddresses),
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

    def test_search(self):
        value = self.queryset.first().pk
        params = {"q": value}
        q = Q(id__iexact=str(value)) | Q(name__icontains=value)
        self.assertQuerysetEqualAndNotEmpty(
            self.filterset(params, self.queryset).qs,
            self.queryset.filter(q),
        )
