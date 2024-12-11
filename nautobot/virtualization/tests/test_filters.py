from nautobot.core.testing import FilterTestCases
from nautobot.dcim.choices import InterfaceModeChoices
from nautobot.dcim.models import Device, DeviceType, Location, LocationType, Manufacturer, Platform, SoftwareVersion
from nautobot.extras.models import Role, Status, Tag
from nautobot.ipam.choices import ServiceProtocolChoices
from nautobot.ipam.models import IPAddress, Namespace, Prefix, Service, VLAN
from nautobot.tenancy.models import Tenant
from nautobot.virtualization.filters import (
    ClusterFilterSet,
    ClusterGroupFilterSet,
    ClusterTypeFilterSet,
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


class ClusterTypeTestCase(FilterTestCases.FilterTestCase):
    queryset = ClusterType.objects.all()
    filterset = ClusterTypeFilterSet
    generic_filter_tests = (
        ("description",),
        ("name",),
    )

    @classmethod
    def setUpTestData(cls):
        cluster_types = (
            ClusterType.objects.create(name="Cluster Type 1", description="A"),
            ClusterType.objects.create(name="Cluster Type 2", description="B"),
            ClusterType.objects.create(name="Cluster Type 3", description="C"),
        )

        cls.clusters = [
            Cluster.objects.create(name="Cluster 1", cluster_type=cluster_types[0]),
            Cluster.objects.create(name="Cluster 2", cluster_type=cluster_types[1]),
        ]

    def test_clusters(self):
        with self.subTest("Clusters"):
            params = {"clusters": [self.clusters[0].pk, self.clusters[1].name]}
            self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)


class ClusterGroupTestCase(FilterTestCases.FilterTestCase):
    queryset = ClusterGroup.objects.all()
    filterset = ClusterGroupFilterSet
    generic_filter_tests = (
        ("description",),
        ("name",),
    )

    @classmethod
    def setUpTestData(cls):
        cluster_groups = (
            ClusterGroup.objects.create(name="Cluster Group 1", description="A"),
            ClusterGroup.objects.create(name="Cluster Group 2", description="B"),
            ClusterGroup.objects.create(name="Cluster Group 3", description="C"),
        )

        cluster_types = (
            ClusterType.objects.create(name="Cluster Type 1", description="A"),
            ClusterType.objects.create(name="Cluster Type 2", description="B"),
            ClusterType.objects.create(name="Cluster Type 3", description="C"),
        )

        cls.clusters = (
            Cluster.objects.create(name="Cluster 1", cluster_type=cluster_types[0], cluster_group=cluster_groups[0]),
            Cluster.objects.create(name="Cluster 2", cluster_type=cluster_types[1], cluster_group=cluster_groups[1]),
        )

    def test_clusters(self):
        with self.subTest("Clusters"):
            params = {"clusters": [self.clusters[0].pk, self.clusters[1].name]}
            self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)


class ClusterTestCase(FilterTestCases.FilterTestCase, FilterTestCases.TenancyFilterTestCaseMixin):
    queryset = Cluster.objects.all()
    filterset = ClusterFilterSet
    tenancy_related_name = "clusters"
    generic_filter_tests = (
        ("cluster_group", "cluster_group__id"),
        ("cluster_group", "cluster_group__name"),
        ("cluster_group_id", "cluster_group__id"),
        ("cluster_type", "cluster_type__id"),
        ("cluster_type", "cluster_type__name"),
        ("cluster_type_id", "cluster_type__id"),
        ("comments",),
        # ("devices", "devices__id"),  # TODO: not enough distinct devices at present
        # ("devices", "devices__name"),  # TODO: not enough distinct devices at present
        # ("location", "location__id"),  # TODO
        # ("location", "location__name"),  # TODO
        ("name",),
        # ("virtual_machines", "virtual_machines__id"),  # TODO: not enough distinct VMs at present
        # ("virtual_machines", "virtual_machines__name"),  # TODO: not enough distinct VMs at present
    )

    @classmethod
    def setUpTestData(cls):
        cluster_types = (
            ClusterType.objects.create(name="Cluster Type 1", description="A"),
            ClusterType.objects.create(name="Cluster Type 2", description="B"),
            ClusterType.objects.create(name="Cluster Type 3", description="C"),
        )

        cluster_groups = (
            ClusterGroup.objects.create(name="Cluster Group 1", description="A"),
            ClusterGroup.objects.create(name="Cluster Group 2", description="B"),
            ClusterGroup.objects.create(name="Cluster Group 3", description="C"),
        )

        location_type_1 = LocationType.objects.get(name="Campus")
        location_type_2 = LocationType.objects.get(name="Building")
        location_status = Status.objects.get_for_model(Location).first()
        cls.locations = (
            Location(name="Location 1", location_type=location_type_1, status=location_status),
            Location(name="Location 2", location_type=location_type_2, status=location_status),
            Location(name="Location 3", location_type=location_type_1, status=location_status),
        )
        cls.locations[1].parent = cls.locations[0]
        for location in cls.locations:
            location.validated_save()

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

        manufacturer = Manufacturer.objects.first()
        devicetype = DeviceType.objects.create(manufacturer=manufacturer, model="Device Type")
        devicerole = Role.objects.get_for_model(Device).first()
        devicestatus = Status.objects.get_for_model(Device).first()

        cls.device = Device.objects.create(
            name="Device 1",
            device_type=devicetype,
            role=devicerole,
            status=devicestatus,
            location=cls.locations[0],
            cluster=clusters[0],
        )

        vm_status = Status.objects.get_for_model(VirtualMachine).first()
        cls.virtualmachine = VirtualMachine.objects.create(
            name="Virtual Machine 1", cluster=clusters[1], status=vm_status
        )

        clusters[0].tags.set(Tag.objects.get_for_model(Cluster))
        clusters[1].tags.set(Tag.objects.get_for_model(Cluster)[:3])

    def test_device(self):
        with self.subTest("Devices"):
            params = {"devices": [self.device.pk, self.device.name]}
            self.assertEqual(self.filterset(params, self.queryset).qs.count(), 1)

    def test_virtual_machines(self):
        with self.subTest("Virtual Machines"):
            params = {"virtual_machines": [self.virtualmachine.pk, self.virtualmachine.name]}
            self.assertEqual(self.filterset(params, self.queryset).qs.count(), 1)

    def test_location(self):
        params = {"location": [self.locations[0].pk, self.locations[1].pk]}
        self.assertQuerysetEqual(
            self.filterset(params, self.queryset).qs, self.queryset.filter(location__in=params["location"])
        )
        params = {"location": [self.locations[0].name, self.locations[1].name]}
        self.assertQuerysetEqual(
            self.filterset(params, self.queryset).qs, self.queryset.filter(location__name__in=params["location"])
        )


class VirtualMachineTestCase(FilterTestCases.FilterTestCase, FilterTestCases.TenancyFilterTestCaseMixin):
    queryset = VirtualMachine.objects.all()
    filterset = VirtualMachineFilterSet
    tenancy_related_name = "virtual_machines"

    generic_filter_tests = (
        ["ip_addresses", "interfaces__ip_addresses__id"],
        ("cluster", "cluster__id"),
        ("cluster", "cluster__name"),
        ("cluster_group", "cluster__cluster_group__id"),
        ("cluster_group", "cluster__cluster_group__name"),
        ("cluster_group_id", "cluster__cluster_group__id"),
        ("cluster_id", "cluster__id"),
        ("cluster_type", "cluster__cluster_type__id"),
        ("cluster_type", "cluster__cluster_type__name"),
        ("cluster_type_id", "cluster__cluster_type__id"),
        ("comments",),
        ("disk",),
        ("interfaces", "interfaces__id"),
        ("location", "cluster__location__id"),
        ("location", "cluster__location__name"),
        ("mac_address", "interfaces__mac_address"),
        ("memory",),
        ("name",),
        ("platform", "platform__id"),
        ("platform", "platform__name"),
        ("platform_id", "platform__id"),
        ("role", "role__id"),
        ("role", "role__name"),
        ("services", "services__id"),
        ("services", "services__name"),
        ("software_image_files", "software_image_files__id"),
        ("software_image_files", "software_image_files__image_file_name"),
        ("software_version", "software_version__id"),
        ("software_version", "software_version__version"),
        ("status", "status__id"),
        ("status", "status__name"),
        ("vcpus",),
    )

    @classmethod
    def setUpTestData(cls):
        cluster_types = (
            ClusterType.objects.create(name="Cluster Type 1", description="A"),
            ClusterType.objects.create(name="Cluster Type 2", description="B"),
            ClusterType.objects.create(name="Cluster Type 3", description="C"),
        )

        cluster_groups = (
            ClusterGroup.objects.create(name="Cluster Group 1", description="A"),
            ClusterGroup.objects.create(name="Cluster Group 2", description="B"),
            ClusterGroup.objects.create(name="Cluster Group 3", description="C"),
        )

        location_type_1 = LocationType.objects.get(name="Campus")
        location_type_2 = LocationType.objects.get(name="Building")
        location_status = Status.objects.get_for_model(Location).first()
        cls.locations = (
            Location(name="Location 1", location_type=location_type_1, status=location_status),
            Location(name="Location 2", location_type=location_type_2, status=location_status),
            Location(name="Location 3", location_type=location_type_1, status=location_status),
        )
        cls.locations[1].parent = cls.locations[0]
        for location in cls.locations:
            location.validated_save()

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

        platforms = Platform.objects.all()[:3]
        cls.platforms = platforms

        roles = Role.objects.get_for_model(VirtualMachine)
        cls.roles = roles

        cls.software_versions = SoftwareVersion.objects.filter(software_image_files__isnull=False)[:3]

        tenants = Tenant.objects.filter(tenant_group__isnull=False)[:3]

        cls.statuses = Status.objects.get_for_model(VirtualMachine)

        vms = (
            VirtualMachine.objects.create(
                name="Virtual Machine 1",
                cluster=clusters[0],
                platform=platforms[0],
                role=roles[0],
                tenant=tenants[0],
                status=cls.statuses[0],
                vcpus=1,
                memory=1,
                disk=1,
                local_config_context_data={"foo": 123},
                comments="This is VM 1",
                software_version=cls.software_versions[0],
            ),
            VirtualMachine.objects.create(
                name="Virtual Machine 2",
                cluster=clusters[1],
                platform=platforms[1],
                role=roles[1],
                tenant=tenants[1],
                status=cls.statuses[2],
                vcpus=2,
                memory=2,
                disk=2,
                comments="This is VM 2",
                software_version=cls.software_versions[1],
            ),
            VirtualMachine.objects.create(
                name="Virtual Machine 3",
                cluster=clusters[2],
                platform=platforms[2],
                role=roles[2],
                tenant=tenants[2],
                status=cls.statuses[1],
                vcpus=3,
                memory=3,
                disk=3,
                comments="This is VM 3",
                software_version=cls.software_versions[2],
            ),
            VirtualMachine.objects.create(
                name="Virtual Machine 4",
                cluster=clusters[2],
                platform=platforms[2],
                role=roles[2],
                tenant=tenants[2],
                status=cls.statuses[1],
                vcpus=3,
                memory=3,
                disk=3,
                comments="This is VM 4",
                software_version=None,
            ),
            VirtualMachine.objects.create(
                name="Virtual Machine 5",
                cluster=clusters[2],
                platform=platforms[2],
                role=roles[2],
                tenant=tenants[2],
                status=cls.statuses[1],
                vcpus=3,
                memory=3,
                disk=3,
                comments="This is VM 5",
                software_version=None,
            ),
            VirtualMachine.objects.create(
                name="Virtual Machine 6",
                cluster=clusters[2],
                platform=platforms[2],
                role=roles[2],
                tenant=tenants[2],
                status=cls.statuses[1],
                vcpus=3,
                memory=3,
                disk=3,
                comments="This is VM 6",
                software_version=cls.software_versions[1],
            ),
        )
        vms[0].software_image_files.set(cls.software_versions[1].software_image_files.all())
        vms[1].software_image_files.set(cls.software_versions[0].software_image_files.all())

        int_status = Status.objects.get_for_model(VMInterface).first()
        int_role = Role.objects.get_for_model(VMInterface).first()
        cls.interfaces = (
            VMInterface.objects.create(
                virtual_machine=vms[0],
                name="Interface 1",
                mac_address="00-00-00-00-00-01",
                status=int_status,
                role=int_role,
            ),
            VMInterface.objects.create(
                virtual_machine=vms[1],
                name="Interface 2",
                mac_address="00-00-00-00-00-02",
                status=int_status,
                role=int_role,
            ),
            VMInterface.objects.create(
                virtual_machine=vms[2],
                name="Interface 3",
                mac_address="00-00-00-00-00-03",
                status=int_status,
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

        cls.namespace = Namespace.objects.first()
        cls.prefix_status = Status.objects.get_for_model(Prefix).first()
        cls.ipadd_status = Status.objects.get_for_model(IPAddress).first()
        cls.prefix4 = Prefix.objects.create(prefix="192.0.2.0/24", namespace=cls.namespace, status=cls.prefix_status)
        cls.prefix6 = Prefix.objects.create(
            prefix="fe80::8ef:3eff:fe4c:3895/24", namespace=cls.namespace, status=cls.prefix_status
        )
        # Assign primary IPs for filtering
        cls.ipaddresses = (
            IPAddress.objects.create(address="192.0.2.1/24", namespace=cls.namespace, status=cls.ipadd_status),
            IPAddress.objects.create(
                address="fe80::8ef:3eff:fe4c:3895/24", namespace=cls.namespace, status=cls.ipadd_status
            ),
        )
        cls.interfaces[0].add_ip_addresses(cls.ipaddresses[0])
        cls.interfaces[1].add_ip_addresses(cls.ipaddresses[1])

        VirtualMachine.objects.filter(pk=vms[0].pk).update(primary_ip4=cls.ipaddresses[0])
        VirtualMachine.objects.filter(pk=vms[1].pk).update(primary_ip6=cls.ipaddresses[1])

        vms[0].tags.set(Tag.objects.get_for_model(VirtualMachine))
        vms[1].tags.set(Tag.objects.get_for_model(VirtualMachine)[:3])

    def test_filters_generic(self):
        # Assign more than 2 different software versions to VirtualMachine before we test generic filters
        software_versions = list(SoftwareVersion.objects.all())
        virtual_machines = list(VirtualMachine.objects.all())
        for i in range(4):
            virtual_machines[i].software_version = software_versions[i]
            virtual_machines[i].save()
        return super().test_filters_generic()

    def test_name(self):
        params = {"name": ["Virtual Machine 1", "Virtual Machine 2"]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)

    def test_comments(self):
        params = {"comments": ["This is VM 1", "This is VM 2"]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)

    def test_ip_addresses(self):
        ipaddresses = list(IPAddress.objects.filter(vm_interfaces__isnull=False)[:2])
        params = {"ip_addresses": [ipaddresses[0].address, ipaddresses[1].id]}
        self.assertQuerysetEqualAndNotEmpty(
            self.filterset(params, self.queryset).qs,
            self.queryset.filter(interfaces__ip_addresses__in=ipaddresses).distinct(),
        )

    def test_primary_ip4(self):
        params = {"primary_ip4": ["192.0.2.1/24", self.ipaddresses[0].pk]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 1)

    def test_primary_ip6(self):
        params = {"primary_ip6": ["fe80::8ef:3eff:fe4c:3895/24", self.ipaddresses[1].pk]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 1)

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
        ("role", "role__id"),
        ("role", "role__name"),
        ["parent_interface"],
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
            ClusterType.objects.create(name="Cluster Type 1", description="A"),
            ClusterType.objects.create(name="Cluster Type 2", description="B"),
            ClusterType.objects.create(name="Cluster Type 3", description="C"),
        )

        clusters = (
            Cluster.objects.create(name="Cluster 1", cluster_type=cluster_types[0]),
            Cluster.objects.create(name="Cluster 2", cluster_type=cluster_types[1]),
            Cluster.objects.create(name="Cluster 3", cluster_type=cluster_types[2]),
        )

        vm_status = Status.objects.get_for_model(VirtualMachine).first()
        vms = (
            VirtualMachine.objects.create(name="Virtual Machine 1", cluster=clusters[0], status=vm_status),
            VirtualMachine.objects.create(name="Virtual Machine 2", cluster=clusters[1], status=vm_status),
            VirtualMachine.objects.create(name="Virtual Machine 3", cluster=clusters[2], status=vm_status),
        )

        statuses = Status.objects.get_for_model(VMInterface)
        roles = Role.objects.get_for_model(VMInterface)

        vlans = VLAN.objects.filter()[:2]
        vlans[0].locations.clear()
        vlans[1].locations.clear()

        cls.vlan1 = vlans[0]
        cls.vlan2 = vlans[1]

        vminterfaces = (
            VMInterface.objects.create(
                virtual_machine=vms[0],
                name="Interface 1",
                enabled=True,
                mtu=100,
                mac_address="00-00-00-00-00-01",
                role=roles[0],
                status=statuses[0],
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
                role=roles[1],
                status=statuses[0],
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
                status=statuses[1],
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
                role=roles[0],
                status=statuses[1],
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
                role=roles[1],
                status=statuses[2],
                description="This is a description of Interface5",
                mode=InterfaceModeChoices.MODE_TAGGED_ALL,
            ),
        )

        child_interfaces[0].tagged_vlans.add(cls.vlan1)
        vminterfaces[2].tagged_vlans.add(cls.vlan2)

        # Assign primary IPs for filtering
        ip_address4 = IPAddress.objects.filter(ip_version=4).first()
        vminterfaces[0].add_ip_addresses(ip_address4)
        ip_address4.validated_save()
        ip_address6 = IPAddress.objects.filter(ip_version=6).first()
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
