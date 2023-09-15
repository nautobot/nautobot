from django.contrib.contenttypes.models import ContentType
from django.db.models import Q

from nautobot.core.testing import TestCase, FilterTestCases
from nautobot.dcim.choices import InterfaceTypeChoices
from nautobot.dcim.models import (
    Device,
    DeviceType,
    Interface,
    Location,
    LocationType,
    Manufacturer,
)
from nautobot.extras.models import Role, Status, Tag
from nautobot.ipam.choices import PrefixTypeChoices, ServiceProtocolChoices
from nautobot.ipam.filters import (
    IPAddressFilterSet,
    IPAddressToInterfaceFilterSet,
    PrefixFilterSet,
    RIRFilterSet,
    RouteTargetFilterSet,
    ServiceFilterSet,
    VLANFilterSet,
    VLANGroupFilterSet,
    VRFFilterSet,
)
from nautobot.ipam.models import (
    IPAddress,
    IPAddressToInterface,
    Prefix,
    RIR,
    RouteTarget,
    Service,
    VLAN,
    VLANGroup,
    VRF,
    Namespace,
)
from nautobot.tenancy.models import Tenant
from nautobot.virtualization.models import (
    Cluster,
    ClusterType,
    VirtualMachine,
    VMInterface,
)


class VRFTestCase(FilterTestCases.FilterTestCase, FilterTestCases.TenancyFilterTestCaseMixin):
    """VRF Filterset tests

    Test cases for `VRFFilterset`

    Note:
        All assertQuerySetEqual() calls here must use ordered=False, because order_by=["name", "rd"]
        but name is not globally unique and rd can be null, so relative ordering of VRFs with identical
        name and null rd is not guaranteed.
    """

    queryset = VRF.objects.all()
    filterset = VRFFilterSet
    tenancy_related_name = "vrfs"

    @classmethod
    def setUpTestData(cls):
        instance = cls.queryset.first()
        instance.tags.set(Tag.objects.all()[:2])

    def test_name(self):
        names = list(self.queryset.values_list("name", flat=True))[:2]
        params = {"name": names}
        self.assertQuerysetEqual(self.filterset(params, self.queryset).qs, self.queryset.filter(name__in=names))

    def test_rd(self):
        vrfs = self.queryset.filter(rd__isnull=False)[:2]
        params = {"rd": [vrfs[0].rd, vrfs[1].rd]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)

    def test_import_targets(self):
        route_targets = list(RouteTarget.objects.filter(importing_vrfs__isnull=False).distinct())[:2]
        params = {"import_targets": [route_targets[0].pk, route_targets[1].name]}
        self.assertQuerysetEqualAndNotEmpty(
            self.filterset(params, self.queryset).qs,
            self.queryset.filter(import_targets__in=route_targets).distinct(),
            ordered=False,
        )

    def test_export_targets(self):
        route_targets = list(RouteTarget.objects.filter(exporting_vrfs__isnull=False).distinct())[:2]
        params = {"export_targets": [route_targets[0].pk, route_targets[1].name]}
        self.assertQuerysetEqualAndNotEmpty(
            self.filterset(params, self.queryset).qs,
            self.queryset.filter(export_targets__in=route_targets).distinct(),
            ordered=False,
        )

    def test_search(self):
        value = self.queryset.values_list("pk", flat=True)[0]
        params = {"q": value}
        self.assertEqual(self.filterset(params, self.queryset).qs.values_list("pk", flat=True)[0], value)


class RouteTargetTestCase(FilterTestCases.FilterTestCase, FilterTestCases.TenancyFilterTestCaseMixin):
    queryset = RouteTarget.objects.all()
    filterset = RouteTargetFilterSet
    tenancy_related_name = "route_targets"

    @classmethod
    def setUpTestData(cls):
        instance = cls.queryset.first()
        instance.tags.set(Tag.objects.all()[:2])

    def test_name(self):
        params = {"name": [self.queryset[0].name, self.queryset[1].name, self.queryset[2].name]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 3)

    def test_importing_vrfs(self):
        vrfs = list(VRF.objects.filter(import_targets__isnull=False, rd__isnull=False).distinct())[:2]
        params = {"importing_vrfs": [vrfs[0].pk, vrfs[1].rd]}
        self.assertQuerysetEqualAndNotEmpty(
            self.filterset(params, self.queryset).qs, self.queryset.filter(importing_vrfs__in=vrfs).distinct()
        )

    def test_exporting_vrfs(self):
        vrfs = list(VRF.objects.filter(export_targets__isnull=False, rd__isnull=False).distinct())[:2]
        params = {"exporting_vrfs": [vrfs[0].pk, vrfs[1].rd]}
        self.assertQuerysetEqualAndNotEmpty(
            self.filterset(params, self.queryset).qs, self.queryset.filter(exporting_vrfs__in=vrfs).distinct()
        )

    def test_search(self):
        value = self.queryset.values_list("pk", flat=True)[0]
        params = {"q": value}
        self.assertEqual(self.filterset(params, self.queryset).qs.values_list("pk", flat=True)[0], value)


class RIRTestCase(FilterTestCases.NameOnlyFilterTestCase):
    queryset = RIR.objects.all()
    filterset = RIRFilterSet

    def test_description(self):
        descriptions = self.queryset.exclude(description="").values_list("description", flat=True)[:2]
        params = {"description": list(descriptions)}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)

    def test_is_private(self):
        params = {"is_private": "true"}
        self.assertQuerysetEqual(self.filterset(params, self.queryset).qs, self.queryset.filter(is_private=True))
        params = {"is_private": "false"}
        self.assertQuerysetEqual(self.filterset(params, self.queryset).qs, self.queryset.filter(is_private=False))


class PrefixTestCase(FilterTestCases.FilterTestCase, FilterTestCases.TenancyFilterTestCaseMixin):
    """Generic filter test case for tests that can use randomized factory data.

    For testing prefix filters with custom test data use PrefixFilterCustomDataTestCase.
    """

    queryset = Prefix.objects.all()
    filterset = PrefixFilterSet
    tenancy_related_name = "prefixes"
    generic_filter_tests = (
        ["date_allocated"],
        ["prefix_length"],
        ["rir", "rir__id"],
        ["rir", "rir__name"],
        ["role", "role__id"],
        ["role", "role__name"],
        ["status", "status__name"],
        ["type"],
    )

    def test_search(self):
        prefixes = Prefix.objects.all()[:2]
        test_values = [
            prefixes[0].cidr_str,
            str(prefixes[0].network),
            str(prefixes[1].network),
        ]
        for value in test_values:
            params = {"q": value}
            count = self.queryset.string_search(value).count()
            self.assertEqual(self.filterset(params, self.queryset).qs.count(), count)

    def test_ip_version(self):
        params = {"ip_version": "6"}
        ipv6_prefixes = self.queryset.filter(ip_version=6)
        self.assertQuerysetEqualAndNotEmpty(self.filterset(params, self.queryset).qs, ipv6_prefixes)
        params = {"ip_version": "4"}
        ipv4_prefixes = self.queryset.filter(ip_version=4)
        self.assertQuerysetEqualAndNotEmpty(self.filterset(params, self.queryset).qs, ipv4_prefixes)
        params = {"ip_version": ""}
        all_prefixes = self.queryset.all()
        self.assertQuerysetEqualAndNotEmpty(self.filterset(params, self.queryset).qs, all_prefixes)


class PrefixFilterCustomDataTestCase(TestCase):
    """Filter test case that requires clearing out factory data and building specific test data."""

    queryset = Prefix.objects.all()
    filterset = PrefixFilterSet

    @classmethod
    def setUpTestData(cls):
        IPAddress.objects.all().delete()
        Prefix.objects.update(parent=None)
        Prefix.objects.all().delete()

        cls.namespace = Namespace.objects.create(name="Prefix Test Case Namespace")
        prefix_status = Status.objects.get_for_model(Prefix).first()

        Prefix.objects.create(
            prefix="10.0.0.0/16",
            namespace=cls.namespace,
            type=PrefixTypeChoices.TYPE_CONTAINER,
            status=prefix_status,
        )
        Prefix.objects.create(
            prefix="10.0.1.0/24",
            namespace=cls.namespace,
            type=PrefixTypeChoices.TYPE_CONTAINER,
            status=prefix_status,
        )
        Prefix.objects.create(
            prefix="10.0.1.2/31",
            namespace=cls.namespace,
            type=PrefixTypeChoices.TYPE_NETWORK,
            status=prefix_status,
        )
        Prefix.objects.create(
            prefix="10.0.1.4/31",
            namespace=cls.namespace,
            type=PrefixTypeChoices.TYPE_NETWORK,
            status=prefix_status,
        )
        Prefix.objects.create(prefix="2.2.2.2/31", namespace=cls.namespace, status=prefix_status)
        Prefix.objects.create(prefix="4.4.4.4/31", namespace=cls.namespace, status=prefix_status)

        Prefix.objects.create(
            prefix="2001:db8::/32",
            namespace=cls.namespace,
            type=PrefixTypeChoices.TYPE_CONTAINER,
            status=prefix_status,
        )
        Prefix.objects.create(
            prefix="2001:db8:0:1::/64",
            namespace=cls.namespace,
            type=PrefixTypeChoices.TYPE_NETWORK,
            status=prefix_status,
        )
        Prefix.objects.create(
            prefix="2001:db8:0:2::/64",
            namespace=cls.namespace,
            type=PrefixTypeChoices.TYPE_NETWORK,
            status=prefix_status,
        )
        Prefix.objects.create(
            prefix="2001:db8:0:2::/65",
            namespace=cls.namespace,
            type=PrefixTypeChoices.TYPE_POOL,
            status=prefix_status,
        )
        Prefix.objects.create(prefix="abcd::/32", namespace=cls.namespace, status=prefix_status)

    def test_search(self):
        prefixes = Prefix.objects.all()[:2]
        test_values = [
            prefixes[0].cidr_str,
            str(prefixes[0].network),
            str(prefixes[1].network),
        ]
        for value in test_values:
            params = {"q": value}
            count = self.queryset.string_search(value).count()
            self.assertEqual(self.filterset(params, self.queryset).qs.count(), count)

    def test_parent(self):
        parent4 = Prefix.objects.get(prefix="10.0.0.0/16", namespace=self.namespace)
        params = {"parent": [str(parent4.pk)]}
        self.assertQuerysetEqualAndNotEmpty(
            self.filterset(params, self.queryset).qs, self.queryset.filter(parent=parent4)
        )
        parent6 = Prefix.objects.get(prefix="2001:db8::/32", namespace=self.namespace)
        params = {"parent": [str(parent6.pk)]}
        self.assertQuerysetEqualAndNotEmpty(
            self.filterset(params, self.queryset).qs, self.queryset.filter(parent=parent6)
        )

    def test_ip_version(self):
        params = {"ip_version": "6"}
        ipv6_prefixes = self.queryset.filter(ip_version=6)
        self.assertQuerysetEqualAndNotEmpty(self.filterset(params, self.queryset).qs, ipv6_prefixes)
        params = {"ip_version": "4"}
        ipv4_prefixes = self.queryset.filter(ip_version=4)
        self.assertQuerysetEqualAndNotEmpty(self.filterset(params, self.queryset).qs, ipv4_prefixes)
        params = {"ip_version": ""}
        all_prefixes = self.queryset.all()
        self.assertQuerysetEqualAndNotEmpty(self.filterset(params, self.queryset).qs, all_prefixes)

    def test_within(self):
        matches = Prefix.objects.filter(network__in=["10.0.1.0", "10.0.1.2", "10.0.1.4"])
        params = {"within": "10.0.0.0/16"}
        self.assertQuerysetEqualAndNotEmpty(self.filterset(params, self.queryset).qs, matches)

    def test_within_include(self):
        matches = self.queryset.filter(network__in=["10.0.0.0", "10.0.1.0", "10.0.1.2", "10.0.1.4"])
        params = {"within_include": "10.0.0.0/16"}
        self.assertQuerysetEqualAndNotEmpty(self.filterset(params, self.queryset).qs, matches)

    def test_contains(self):
        matches_ipv4 = self.queryset.filter(network__in=["10.0.0.0", "10.0.1.0"])
        matches_ipv6 = self.queryset.filter(network__in=["2001:db8::", "2001:db8:0:1::"])
        params = {"contains": "10.0.1.0/24"}
        self.assertQuerysetEqualAndNotEmpty(self.filterset(params, self.queryset).qs, matches_ipv4)
        params = {"contains": "2001:db8:0:1::/64"}
        self.assertQuerysetEqualAndNotEmpty(self.filterset(params, self.queryset).qs, matches_ipv6)

    def test_vrfs(self):
        prefixes = self.queryset[:2]
        vrfs = (
            VRF.objects.create(name="VRF 1", rd="65000:100", namespace=self.namespace),
            VRF.objects.create(name="VRF 2", rd="65000:200", namespace=self.namespace),
        )
        prefixes[0].vrfs.add(vrfs[0])
        prefixes[0].vrfs.add(vrfs[1])
        prefixes[1].vrfs.add(vrfs[0])
        prefixes[1].vrfs.add(vrfs[1])
        params = {"vrfs": [vrfs[0].pk, vrfs[1].pk]}
        self.assertQuerysetEqualAndNotEmpty(
            self.filterset(params, self.queryset).qs,
            self.queryset.filter(vrfs__in=vrfs).distinct(),
        )
        params = {"vrfs": [vrfs[0].pk, vrfs[1].rd]}
        self.assertQuerysetEqualAndNotEmpty(
            self.filterset(params, self.queryset).qs,
            self.queryset.filter(vrfs__in=vrfs).distinct(),
        )

    def test_present_in_vrf(self):
        test_prefixes = list(self.queryset[:3])
        VRF.objects.all().delete()
        RouteTarget.objects.all().delete()
        route_targets = (
            RouteTarget.objects.create(name="65000:100"),
            RouteTarget.objects.create(name="65000:200"),
            RouteTarget.objects.create(name="65000:300"),
        )
        vrfs = (
            VRF.objects.create(name="VRF 1", rd="65000:100", namespace=self.namespace),
            VRF.objects.create(name="VRF 2", rd="65000:200", namespace=self.namespace),
            VRF.objects.create(name="VRF 3", rd="65000:300", namespace=self.namespace),
        )
        vrfs[0].import_targets.add(route_targets[0], route_targets[1], route_targets[2])
        vrfs[1].export_targets.add(route_targets[1])
        vrfs[2].export_targets.add(route_targets[2])
        test_prefixes[0].vrfs.add(vrfs[0], vrfs[1])
        test_prefixes[1].vrfs.add(vrfs[0], vrfs[1])
        test_prefixes[2].vrfs.add(vrfs[0], vrfs[1])
        self.assertQuerysetEqualAndNotEmpty(
            self.filterset({"present_in_vrf_id": vrfs[0].pk}, self.queryset).qs,
            self.queryset.filter(Q(vrfs=vrfs[0]) | Q(vrfs__export_targets__in=vrfs[0].import_targets.all())).distinct(),
        )
        self.assertQuerysetEqualAndNotEmpty(
            self.filterset({"present_in_vrf_id": vrfs[1].pk}, self.queryset).qs,
            self.queryset.filter(Q(vrfs=vrfs[1]) | Q(vrfs__export_targets__in=vrfs[1].import_targets.all())).distinct(),
        )
        self.assertQuerysetEqualAndNotEmpty(
            self.filterset({"present_in_vrf": vrfs[0].rd}, self.queryset).qs,
            self.queryset.filter(Q(vrfs=vrfs[0]) | Q(vrfs__export_targets__in=vrfs[0].import_targets.all())).distinct(),
        )
        self.assertQuerysetEqualAndNotEmpty(
            self.filterset({"present_in_vrf": vrfs[1].rd}, self.queryset).qs,
            self.queryset.filter(Q(vrfs=vrfs[1]) | Q(vrfs__export_targets__in=vrfs[1].import_targets.all())).distinct(),
        )

    def test_location(self):
        location_type_1 = LocationType.objects.get(name="Campus")
        location_type_2 = LocationType.objects.get(name="Building")
        loc_status = Status.objects.get_for_model(Location).first()
        test_locations = (
            Location.objects.create(name="Location 1", location_type=location_type_1, status=loc_status),
            Location.objects.create(name="Location 2", location_type=location_type_2, status=loc_status),
            Location.objects.create(name="Location 3", location_type=location_type_2, status=loc_status),
        )
        test_locations[1].parent = test_locations[0]
        test_prefixes = list(self.queryset[:3])
        test_prefixes[0].location = test_locations[0]
        test_prefixes[1].location = test_locations[1]
        test_prefixes[2].location = test_locations[2]
        self.queryset.bulk_update(test_prefixes, ["location"])

        params = {"location": [test_locations[0].pk, test_locations[1].pk]}
        self.assertQuerysetEqualAndNotEmpty(
            self.filterset(params, self.queryset).qs,
            self.queryset.filter(location__in=params["location"]),
        )
        params = {"location": [test_locations[0].name, test_locations[1].name]}
        self.assertQuerysetEqualAndNotEmpty(
            self.filterset(params, self.queryset).qs,
            self.queryset.filter(location__name__in=params["location"]),
        )

    def test_vlan(self):
        vlans = list(VLAN.objects.all()[:2])
        test_prefixes = list(self.queryset[:3])
        test_prefixes[0].vlan = vlans[0]
        test_prefixes[1].vlan = vlans[1]
        test_prefixes[2].vlan = vlans[1]
        self.queryset.bulk_update(test_prefixes, ["vlan"])

        params = {"vlan_id": [vlans[0].pk, vlans[1].pk]}
        self.assertQuerysetEqualAndNotEmpty(
            self.filterset(params, self.queryset).qs, self.queryset.filter(vlan__in=vlans)
        )
        params = {"vlan_vid": [vlans[0].vid, vlans[1].vid]}
        self.assertQuerysetEqualAndNotEmpty(
            self.filterset(params, self.queryset).qs, self.queryset.filter(vlan__vid__in=[vlans[0].vid, vlans[1].vid])
        )


class IPAddressTestCase(FilterTestCases.FilterTestCase, FilterTestCases.TenancyFilterTestCaseMixin):
    queryset = IPAddress.objects.all()
    filterset = IPAddressFilterSet
    tenancy_related_name = "ip_addresses"

    @classmethod
    def setUpTestData(cls):
        # Create some VRFs that belong to the same Namespace and have an rd
        cls.namespace = Namespace.objects.create(name="IP Address Test Case Namespace")
        VRF.objects.create(name="VRF 1", rd="65000:100", namespace=cls.namespace)
        VRF.objects.create(name="VRF 2", rd="65000:200", namespace=cls.namespace)
        VRF.objects.create(name="VRF 3", rd="65000:300", namespace=cls.namespace)
        # Create some VRFs without an rd
        VRF.objects.create(name="VRF 4", namespace=cls.namespace)
        VRF.objects.create(name="VRF 5", namespace=cls.namespace)
        VRF.objects.create(name="VRF 6", namespace=cls.namespace)
        vrfs = VRF.objects.filter(namespace=cls.namespace, rd__isnull=False)
        assert len(vrfs) == 3, f"This Namespace {cls.namespace} does not contain enough VRFs."

        cls.interface_ct = ContentType.objects.get_for_model(Interface)
        cls.vm_interface_ct = ContentType.objects.get_for_model(VMInterface)

        location = Location.objects.filter(location_type=LocationType.objects.get(name="Campus")).first()
        manufacturer = Manufacturer.objects.first()
        device_type = DeviceType.objects.create(manufacturer=manufacturer, model="Device Type 1")
        device_role = Role.objects.get_for_model(Device).first()
        device_status = Status.objects.get_for_model(Device).first()

        devices = (
            Device.objects.create(
                device_type=device_type,
                name="Device 1",
                location=location,
                role=device_role,
                status=device_status,
            ),
            Device.objects.create(
                device_type=device_type,
                name="Device 2",
                location=location,
                role=device_role,
                status=device_status,
            ),
            Device.objects.create(
                device_type=device_type,
                name="Device 3",
                location=location,
                role=device_role,
                status=device_status,
            ),
        )

        interface_status = Status.objects.get_for_model(Interface).first()
        interfaces = (
            Interface.objects.create(
                device=devices[0],
                name="Interface 1",
                status=interface_status,
            ),
            Interface.objects.create(
                device=devices[1],
                name="Interface 2",
                status=interface_status,
            ),
            Interface.objects.create(
                device=devices[2],
                name="Interface 3",
                status=interface_status,
            ),
        )

        clustertype = ClusterType.objects.create(name="Cluster Type 1")
        cluster = Cluster.objects.create(cluster_type=clustertype, name="Cluster 1")

        vm_status = Status.objects.get_for_model(VirtualMachine).first()
        virtual_machines = (
            VirtualMachine.objects.create(name="Virtual Machine 1", cluster=cluster, status=vm_status),
            VirtualMachine.objects.create(name="Virtual Machine 2", cluster=cluster, status=vm_status),
            VirtualMachine.objects.create(name="Virtual Machine 3", cluster=cluster, status=vm_status),
        )

        vmint_status = Status.objects.get_for_model(VMInterface).first()
        vminterfaces = (
            VMInterface.objects.create(virtual_machine=virtual_machines[0], name="Interface 1", status=vmint_status),
            VMInterface.objects.create(virtual_machine=virtual_machines[1], name="Interface 2", status=vmint_status),
            VMInterface.objects.create(virtual_machine=virtual_machines[2], name="Interface 3", status=vmint_status),
        )

        tenants = Tenant.objects.filter(tenant_group__isnull=False)[:3]

        statuses = Status.objects.get_for_model(IPAddress)
        prefix_status = Status.objects.get_for_model(Prefix).first()
        roles = Role.objects.get_for_model(IPAddress)
        cls.prefix4 = Prefix.objects.create(prefix="10.0.0.0/8", namespace=cls.namespace, status=prefix_status)
        cls.prefix6 = Prefix.objects.create(prefix="2001:db8::/64", namespace=cls.namespace, status=prefix_status)
        # Add some prefixes to VRFs so that we have enough qualified vrfs in test_vrf().
        vrfs[0].prefixes.add(cls.prefix4)
        vrfs[0].prefixes.add(cls.prefix6)
        vrfs[1].prefixes.add(cls.prefix4)
        vrfs[1].prefixes.add(cls.prefix6)
        vrfs[2].prefixes.add(cls.prefix4)
        vrfs[2].prefixes.add(cls.prefix6)
        cls.ipv4_address = IPAddress.objects.create(
            address="10.0.0.1/24",
            tenant=None,
            status=statuses[0],
            dns_name="ipaddress-a",
            namespace=cls.namespace,
        )
        ip0 = IPAddress.objects.create(
            address="10.0.0.2/24",
            tenant=tenants[0],
            status=statuses[0],
            dns_name="ipaddress-b",
            namespace=cls.namespace,
        )
        interfaces[0].add_ip_addresses(ip0)
        ip1 = IPAddress.objects.create(
            address="10.0.0.3/24",
            tenant=tenants[1],
            status=statuses[2],
            role=roles[0],
            dns_name="ipaddress-c",
            namespace=cls.namespace,
        )
        interfaces[1].add_ip_addresses(ip1)
        ip2 = IPAddress.objects.create(
            address="10.0.0.4/24",
            tenant=tenants[2],
            status=statuses[1],
            role=roles[1],
            dns_name="ipaddress-d",
            namespace=cls.namespace,
        )
        interfaces[2].add_ip_addresses(ip2)
        IPAddress.objects.create(
            address="10.0.0.5/24",
            tenant=None,
            status=statuses[0],
            namespace=cls.namespace,
        )
        cls.ipv6_address = IPAddress.objects.create(
            address="2001:db8::1/64",
            tenant=None,
            status=statuses[0],
            dns_name="ipaddress-a",
            namespace=cls.namespace,
        )
        ip3 = IPAddress.objects.create(
            address="2001:db8::2/64",
            tenant=tenants[0],
            status=statuses[0],
            dns_name="ipaddress-b",
            namespace=cls.namespace,
        )
        vminterfaces[0].add_ip_addresses(ip3)
        ip4 = IPAddress.objects.create(
            address="2001:db8::3/64",
            tenant=tenants[1],
            status=statuses[2],
            role=roles[2],
            dns_name="ipaddress-c",
            namespace=cls.namespace,
        )
        vminterfaces[1].add_ip_addresses(ip4)
        ip5 = IPAddress.objects.create(
            address="2001:db8::4/64",
            tenant=tenants[2],
            status=statuses[1],
            role=roles[1],
            dns_name="ipaddress-d",
            namespace=cls.namespace,
        )
        vminterfaces[2].add_ip_addresses(ip5)
        IPAddress.objects.create(
            address="2001:db8::5/65",
            tenant=None,
            status=statuses[0],
            namespace=cls.namespace,
        )

    def test_search(self):
        ipv4_octets = self.ipv4_address.host.split(".")
        ipv6_hextets = self.ipv6_address.host.split(":")

        search_terms = [
            str(self.ipv4_address.address),  # ipv4 address with mask: 10.0.0.1/24
            self.ipv4_address.host,  # ipv4 address without mask: 10.0.0.1
            str(self.ipv6_address.address),  # ipv6 address with mask: 2001:db8::1/64
            self.ipv6_address.host,  # ipv6 address without mask: 2001:db8::1
            self.ipv4_address.dns_name,
            ipv4_octets[0],  # 10
            f"{ipv4_octets[0]}.",  # 10.
            f"{ipv4_octets[0]}.{ipv4_octets[1]}",  # 10.0
            f"{ipv4_octets[0]}.{ipv4_octets[1]}.",  # 10.0.
            ipv6_hextets[0],  # 2001
            f"{ipv6_hextets[0]}:",  # 2001:
            f"{ipv6_hextets[0]}::",  # 2001::
        ]

        for term in search_terms:
            with self.subTest(term):
                params = {"q": term}
                self.assertQuerysetEqualAndNotEmpty(
                    self.filterset(params, self.queryset).qs, self.queryset.string_search(term)
                )

        with self.subTest("search that matches no objects"):
            params = {"q": "no objects match this search"}
            self.assertQuerysetEqual(self.filterset(params, self.queryset).qs, self.queryset.none())

        with self.subTest("blank query should return all objects"):
            params = {"q": ""}
            self.assertQuerysetEqualAndNotEmpty(self.filterset(params, self.queryset).qs, self.queryset.all())

    def test_ip_version(self):
        params = {"ip_version": "6"}
        self.assertQuerysetEqualAndNotEmpty(
            self.filterset(params, self.queryset).qs, self.queryset.filter(ip_version=6)
        )
        params = {"ip_version": "4"}
        self.assertQuerysetEqualAndNotEmpty(
            self.filterset(params, self.queryset).qs, self.queryset.filter(ip_version=4)
        )
        params = {"ip_version": ""}
        self.assertQuerysetEqualAndNotEmpty(self.filterset(params, self.queryset).qs, self.queryset.all())

    def test_dns_name(self):
        names = list(self.queryset.exclude(dns_name="").distinct_values_list("dns_name", flat=True)[:2])
        params = {"dns_name": names}
        self.assertQuerysetEqualAndNotEmpty(
            self.filterset(params, self.queryset).qs, self.queryset.filter(dns_name__in=names)
        )

    def test_parent(self):
        params = {"parent": [str(self.prefix4.pk)]}
        self.assertQuerysetEqualAndNotEmpty(
            self.filterset(params, self.queryset).qs, self.queryset.filter(parent=self.prefix4)
        )
        params = {"parent": [str(self.prefix6.pk)]}
        self.assertQuerysetEqualAndNotEmpty(
            self.filterset(params, self.queryset).qs, self.queryset.filter(parent=self.prefix6)
        )

    def test_prefix(self):
        ipv4_parent = self.queryset.filter(ip_version=4).first().address.supernet()[-1]
        params = {"prefix": str(ipv4_parent)}
        self.assertQuerysetEqualAndNotEmpty(
            self.filterset(params, self.queryset).qs, self.queryset.net_host_contained(ipv4_parent)
        )
        ipv6_parent = self.queryset.filter(ip_version=6).first().address.supernet()[-1]
        params = {"prefix": str(ipv6_parent)}
        self.assertQuerysetEqualAndNotEmpty(
            self.filterset(params, self.queryset).qs, self.queryset.net_host_contained(ipv6_parent)
        )

    def test_filter_address(self):
        """Check IPv4 and IPv6, with and without a mask"""
        ipv4_addresses = self.queryset.filter(ip_version=4)[:2]
        ipv6_addresses = self.queryset.filter(ip_version=6)[:2]
        # single ipv4 address with mask: 10.0.0.1/24
        params = {"address": [str(ipv4_addresses[0].address)]}
        self.assertQuerysetEqualAndNotEmpty(
            self.filterset(params, self.queryset).qs, self.queryset.net_in(params["address"])
        )
        # single ipv4 address without mask: 10.0.0.1
        params = {"address": [ipv4_addresses[0].host]}
        self.assertQuerysetEqualAndNotEmpty(
            self.filterset(params, self.queryset).qs, self.queryset.net_in(params["address"])
        )
        # single ipv6 address with mask: 2001:db8::1/64
        params = {"address": [str(ipv6_addresses[0].address)]}
        self.assertQuerysetEqualAndNotEmpty(
            self.filterset(params, self.queryset).qs, self.queryset.net_in(params["address"])
        )
        # single ipv6 address without mask: 2001:db8::1
        params = {"address": [ipv6_addresses[0].host]}
        self.assertQuerysetEqualAndNotEmpty(
            self.filterset(params, self.queryset).qs, self.queryset.net_in(params["address"])
        )

        # two addresses with mask: 10.0.0.1/24, 2001:db8::1/64
        params = {"address": [str(ipv4_addresses[0].address), str(ipv6_addresses[1].address)]}
        self.assertQuerysetEqualAndNotEmpty(
            self.filterset(params, self.queryset).qs, self.queryset.net_in(params["address"])
        )
        # two addresses without mask: 10.0.0.1, 2001:db8::1
        params = {"address": [ipv4_addresses[0].host, ipv6_addresses[1].host]}
        self.assertQuerysetEqualAndNotEmpty(
            self.filterset(params, self.queryset).qs, self.queryset.net_in(params["address"])
        )

    def test_mask_length(self):
        # Test filtering by a single integer value
        params = {"mask_length": self.queryset.first().mask_length}
        self.assertQuerysetEqualAndNotEmpty(
            self.filterset(params, self.queryset).qs, self.queryset.filter(mask_length=params["mask_length"])
        )
        # Test filtering by multiple integer values
        params = {"mask_length": [self.queryset.first().mask_length, self.queryset.last().mask_length]}
        self.assertQuerysetEqualAndNotEmpty(
            self.filterset(params, self.queryset).qs, self.queryset.filter(mask_length__in=params["mask_length"])
        )

    def test_vrfs(self):
        vrfs = list(VRF.objects.filter(prefixes__ip_addresses__isnull=False, rd__isnull=False).distinct())[:2]
        params = {"vrfs": [vrfs[0].pk, vrfs[1].pk]}
        self.assertQuerysetEqualAndNotEmpty(
            self.filterset(params, self.queryset).qs, self.queryset.filter(parent__vrfs__in=vrfs).distinct()
        )
        params = {"vrfs": [vrfs[0].pk, vrfs[1].rd]}
        self.assertQuerysetEqualAndNotEmpty(
            self.filterset(params, self.queryset).qs, self.queryset.filter(parent__vrfs__in=vrfs).distinct()
        )

    def test_device(self):
        interfaces = Interface.objects.filter(ip_addresses__isnull=False)
        devices = list(Device.objects.filter(interfaces__in=interfaces).distinct()[:2])
        params = {"device_id": [devices[0].pk, devices[1].pk]}
        self.assertQuerysetEqualAndNotEmpty(
            self.filterset(params, self.queryset).qs,
            self.queryset.filter(interfaces__in=devices[0].interfaces.all() | devices[1].interfaces.all()),
        )

        params = {"device": [devices[0].name, devices[1].name]}
        self.assertQuerysetEqualAndNotEmpty(
            self.filterset(params, self.queryset).qs,
            self.queryset.filter(interfaces__in=devices[0].interfaces.all() | devices[1].interfaces.all()),
        )

    def test_virtual_machine(self):
        vm_interfaces = VMInterface.objects.filter(ip_addresses__isnull=False)
        virtual_machines = list(VirtualMachine.objects.filter(interfaces__in=vm_interfaces).distinct()[:2])
        params = {"virtual_machine_id": [virtual_machines[0].pk, virtual_machines[1].pk]}
        self.assertQuerysetEqualAndNotEmpty(
            self.filterset(params, self.queryset).qs,
            self.queryset.filter(
                vm_interfaces__in=virtual_machines[0].interfaces.all() | virtual_machines[1].interfaces.all()
            ),
        )

        params = {"virtual_machine": [virtual_machines[0].name, virtual_machines[1].name]}
        self.assertQuerysetEqualAndNotEmpty(
            self.filterset(params, self.queryset).qs,
            self.queryset.filter(
                vm_interfaces__in=virtual_machines[0].interfaces.all() | virtual_machines[1].interfaces.all()
            ),
        )

    def test_interfaces(self):
        interfaces = list(Interface.objects.filter(ip_addresses__isnull=False)[:2])
        params = {"interfaces": [interfaces[0].pk, interfaces[1].name]}
        self.assertQuerysetEqualAndNotEmpty(
            self.filterset(params, self.queryset).qs,
            self.queryset.filter(interfaces__in=[interfaces[0], interfaces[1]]),
        )

    def test_vm_interfaces(self):
        vm_interfaces = list(VMInterface.objects.filter(ip_addresses__isnull=False)[:2])
        params = {"vm_interfaces": [vm_interfaces[0].pk, vm_interfaces[1].name]}
        self.assertQuerysetEqualAndNotEmpty(
            self.filterset(params, self.queryset).qs,
            self.queryset.filter(vm_interfaces__in=[vm_interfaces[0], vm_interfaces[1]]),
        )

    def test_has_interface_assignments(self):
        params = {"has_interface_assignments": True}
        self.assertQuerysetEqualAndNotEmpty(
            self.filterset(params, self.queryset).qs,
            self.queryset.filter(Q(interfaces__isnull=False) | Q(vm_interfaces__isnull=False)),
        )
        params = {"has_interface_assignments": False}
        self.assertQuerysetEqualAndNotEmpty(
            self.filterset(params, self.queryset).qs,
            self.queryset.filter(Q(interfaces__isnull=True) & Q(vm_interfaces__isnull=True)),
        )

    def test_present_in_vrf(self):
        # clear out all the randomly generated route targets and vrfs before running this custom test
        test_ip_addresses_pk_list = list(self.queryset.values_list("pk", flat=True)[:10])
        test_ip_addresses = self.queryset[:10]
        # With advent of `IPAddress.parent`, IPAddresses can't just be bulk deleted without clearing their
        # `parent` first in an `update()` query which doesn't call `save()` or `fire `(pre|post)_save` signals.
        unwanted_ips = self.queryset.exclude(pk__in=test_ip_addresses_pk_list)
        unwanted_ips.update(parent=None)
        unwanted_ips.delete()
        VRF.objects.all().delete()
        RouteTarget.objects.all().delete()
        route_targets = (
            RouteTarget.objects.create(name="65000:100"),
            RouteTarget.objects.create(name="65000:200"),
            RouteTarget.objects.create(name="65000:300"),
        )
        vrfs = (
            VRF.objects.create(name="VRF 1", rd="65000:100", namespace=self.namespace),
            VRF.objects.create(name="VRF 2", rd="65000:200", namespace=self.namespace),
            VRF.objects.create(name="VRF 3", rd="65000:300", namespace=self.namespace),
        )
        test_ip_addresses[0].parent.namespace = self.namespace
        test_ip_addresses[0].validated_save()
        test_ip_addresses[1].parent.namespace = self.namespace
        test_ip_addresses[1].validated_save()
        test_ip_addresses[2].parent.namespace = self.namespace
        test_ip_addresses[2].validated_save()
        vrfs[0].import_targets.add(route_targets[0], route_targets[1], route_targets[2])
        vrfs[1].export_targets.add(route_targets[1])
        vrfs[2].export_targets.add(route_targets[2])

        test_ip_addresses[0].parent.vrfs.add(vrfs[0], vrfs[1], vrfs[2])
        test_ip_addresses[1].parent.vrfs.add(vrfs[0], vrfs[1], vrfs[2])
        test_ip_addresses[2].parent.vrfs.add(vrfs[0], vrfs[1], vrfs[2])
        self.assertQuerysetEqualAndNotEmpty(
            self.filterset({"present_in_vrf_id": vrfs[0].pk}, self.queryset).qs,
            self.queryset.filter(
                Q(parent__vrfs=vrfs[0]) | Q(parent__vrfs__export_targets__in=vrfs[0].import_targets.all())
            ).distinct(),
        )
        self.assertQuerysetEqualAndNotEmpty(
            self.filterset({"present_in_vrf_id": vrfs[1].pk}, self.queryset).qs,
            self.queryset.filter(
                Q(parent__vrfs=vrfs[1]) | Q(parent__vrfs__export_targets__in=vrfs[1].import_targets.all())
            ).distinct(),
        )
        self.assertQuerysetEqualAndNotEmpty(
            self.filterset({"present_in_vrf": vrfs[0].rd}, self.queryset).qs,
            self.queryset.filter(
                Q(parent__vrfs=vrfs[0]) | Q(parent__vrfs__export_targets__in=vrfs[0].import_targets.all())
            ).distinct(),
        )
        self.assertQuerysetEqualAndNotEmpty(
            self.filterset({"present_in_vrf": vrfs[1].rd}, self.queryset).qs,
            self.queryset.filter(
                Q(parent__vrfs=vrfs[1]) | Q(parent__vrfs__export_targets__in=vrfs[1].import_targets.all())
            ).distinct(),
        )

    def test_status(self):
        statuses = list(Status.objects.get_for_model(IPAddress).filter(ip_addresses__isnull=False)[:2])
        params = {"status": [statuses[0].name, statuses[1].name]}
        self.assertQuerysetEqualAndNotEmpty(
            self.filterset(params, self.queryset).qs, self.queryset.filter(status__in=statuses)
        )

    def test_role(self):
        roles = list(IPAddress.objects.exclude(role__isnull=True).distinct_values_list("role", flat=True)[:2])
        params = {"role": roles}
        self.assertQuerysetEqualAndNotEmpty(
            self.filterset(params, self.queryset).qs,
            self.queryset.filter(role__in=roles),
        )


class IPAddressToInterfaceTestCase(FilterTestCases.FilterTestCase):
    queryset = IPAddressToInterface.objects.all()
    filterset = IPAddressToInterfaceFilterSet
    generic_filter_tests = (
        ["ip_address"],
        ["interface", "interface__id"],
        ["interface", "interface__name"],
        ["vm_interface", "vm_interface__id"],
        ["vm_interface", "vm_interface__name"],
    )

    @classmethod
    def setUpTestData(cls):
        ip_addresses = list(IPAddress.objects.all()[:5])
        location = Location.objects.get_for_model(Device).first()
        devicetype = DeviceType.objects.first()
        devicerole = Role.objects.get_for_model(Device).first()
        devicestatus = Status.objects.get_for_model(Device).first()
        device = Device.objects.create(
            name="Device 1",
            location=location,
            device_type=devicetype,
            role=devicerole,
            status=devicestatus,
        )
        int_status = Status.objects.get_for_model(Interface).first()
        int_type = InterfaceTypeChoices.TYPE_1GE_FIXED
        interfaces = [
            Interface.objects.create(device=device, name="eth0", status=int_status, type=int_type),
            Interface.objects.create(device=device, name="eth1", status=int_status, type=int_type),
            Interface.objects.create(device=device, name="eth2", status=int_status, type=int_type),
        ]

        clustertype = ClusterType.objects.create(name="Cluster Type 1")
        cluster = Cluster.objects.create(cluster_type=clustertype, name="Cluster 1")
        vm_status = Status.objects.get_for_model(VirtualMachine).first()
        virtual_machine = (VirtualMachine.objects.create(name="Virtual Machine 1", cluster=cluster, status=vm_status),)
        vm_int_status = Status.objects.get_for_model(VMInterface).first()
        vm_interfaces = [
            VMInterface.objects.create(virtual_machine=virtual_machine[0], name="veth0", status=vm_int_status),
            VMInterface.objects.create(virtual_machine=virtual_machine[0], name="veth1", status=vm_int_status),
        ]

        IPAddressToInterface.objects.create(ip_address=ip_addresses[0], interface=interfaces[0], vm_interface=None)
        IPAddressToInterface.objects.create(ip_address=ip_addresses[1], interface=interfaces[1], vm_interface=None)
        IPAddressToInterface.objects.create(ip_address=ip_addresses[2], interface=interfaces[2], vm_interface=None)
        IPAddressToInterface.objects.create(ip_address=ip_addresses[3], interface=None, vm_interface=vm_interfaces[0])
        IPAddressToInterface.objects.create(ip_address=ip_addresses[4], interface=None, vm_interface=vm_interfaces[1])

    def test_boolean_filters(self):
        filters = [
            "is_source",
            "is_destination",
            "is_default",
            "is_preferred",
            "is_primary",
            "is_secondary",
            "is_standby",
        ]

        ip_association1 = IPAddressToInterface.objects.first()
        ip_association2 = IPAddressToInterface.objects.last()
        for test_filter in filters:
            setattr(ip_association1, test_filter, True)
            setattr(ip_association2, test_filter, True)
        ip_association1.validated_save()
        ip_association2.validated_save()

        for test_filter in filters:
            with self.subTest(filter=test_filter):
                params = {test_filter: True}
                self.assertQuerysetEqualAndNotEmpty(
                    self.filterset(params, self.queryset).qs, self.queryset.filter(**{test_filter: True}), ordered=False
                )
                params = {test_filter: False}
                self.assertQuerysetEqualAndNotEmpty(
                    self.filterset(params, self.queryset).qs,
                    self.queryset.filter(**{test_filter: False}),
                    ordered=False,
                )


class VLANGroupTestCase(FilterTestCases.NameOnlyFilterTestCase):
    queryset = VLANGroup.objects.all()
    filterset = VLANGroupFilterSet

    @classmethod
    def setUpTestData(cls):
        cls.location_type_1 = LocationType.objects.get(name="Campus")
        cls.location_type_2 = LocationType.objects.get(name="Building")
        loc_status = Status.objects.get_for_model(Location).first()
        cls.locations = (
            Location.objects.create(name="Location 1", location_type=cls.location_type_1, status=loc_status),
            Location.objects.create(name="Location 2", location_type=cls.location_type_1, status=loc_status),
            Location.objects.create(name="Location 3", location_type=cls.location_type_2, status=loc_status),
        )
        cls.locations[1].parent = cls.locations[0]
        cls.locations[2].parent = cls.locations[1]

        VLANGroup.objects.create(name="VLAN Group 1", location=cls.locations[0], description="A")
        VLANGroup.objects.create(name="VLAN Group 2", location=cls.locations[1], description="B")
        VLANGroup.objects.create(name="VLAN Group 3", location=cls.locations[2], description="C")
        VLANGroup.objects.create(name="VLAN Group 4", location=None)

    def test_description(self):
        descriptions = list(VLANGroup.objects.exclude(description="").values_list("description", flat=True)[:2])
        params = {"description": descriptions}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)

    def test_location(self):
        params = {"location": [self.locations[0].pk, self.locations[1].pk]}
        self.assertQuerysetEqual(
            self.filterset(params, self.queryset).qs, self.queryset.filter(location__in=params["location"])
        )
        params = {"location": [self.locations[0].name, self.locations[1].name]}
        self.assertQuerysetEqual(
            self.filterset(params, self.queryset).qs, self.queryset.filter(location__name__in=params["location"])
        )


class VLANTestCase(FilterTestCases.FilterTestCase, FilterTestCases.TenancyFilterTestCaseMixin):
    queryset = VLAN.objects.all()
    filterset = VLANFilterSet
    tenancy_related_name = "vlans"

    @classmethod
    def setUpTestData(cls):
        cls.location_type_1 = LocationType.objects.get(name="Campus")
        cls.location_type_2 = LocationType.objects.get(name="Building")
        loc_status = Status.objects.get_for_model(Location).first()
        cls.locations = (
            Location.objects.create(name="Location 1", location_type=cls.location_type_1, status=loc_status),
            Location.objects.create(name="Location 2", location_type=cls.location_type_1, status=loc_status),
            Location.objects.create(name="Location 3", location_type=cls.location_type_2, status=loc_status),
        )
        cls.locations[1].parent = cls.locations[0]

        roles = Role.objects.all()[:3]

        groups = (
            VLANGroup.objects.create(name="VLAN Group 1", location=cls.locations[0]),
            VLANGroup.objects.create(name="VLAN Group 2", location=cls.locations[1]),
            VLANGroup.objects.create(name="VLAN Group 3", location=None),
        )

        tenants = Tenant.objects.filter(tenant_group__isnull=False)[:3]

        statuses = Status.objects.get_for_model(VLAN)

        vlans = (
            VLAN.objects.create(
                vid=101,
                name="VLAN 101",
                location=cls.locations[0],
                vlan_group=groups[0],
                role=roles[0],
                tenant=tenants[0],
                status=statuses[0],
            ),
            VLAN.objects.create(
                vid=102,
                name="VLAN 102",
                location=cls.locations[0],
                vlan_group=groups[0],
                role=roles[0],
                tenant=tenants[0],
                status=statuses[0],
            ),
            VLAN.objects.create(
                vid=201,
                name="VLAN 201",
                location=cls.locations[1],
                vlan_group=groups[1],
                role=roles[1],
                tenant=tenants[1],
                status=statuses[1],
            ),
            VLAN.objects.create(
                vid=202,
                name="VLAN 202",
                location=cls.locations[1],
                vlan_group=groups[1],
                role=roles[1],
                tenant=tenants[1],
                status=statuses[1],
            ),
            VLAN.objects.create(
                vid=301,
                name="VLAN 301",
                location=cls.locations[2],
                vlan_group=groups[2],
                role=roles[2],
                tenant=tenants[2],
                status=statuses[2],
            ),
            VLAN.objects.create(
                vid=302,
                name="VLAN 302",
                location=cls.locations[2],
                vlan_group=groups[2],
                role=roles[2],
                tenant=tenants[2],
                status=statuses[2],
            ),
        )
        vlans[0].tags.set(Tag.objects.all()[:2])
        vlans[1].tags.set(Tag.objects.all()[:2])

    def test_name(self):
        names = list(VLAN.objects.all().values_list("name", flat=True)[:2])
        params = {"name": names}
        self.assertQuerysetEqual(self.filterset(params, self.queryset).qs, self.queryset.filter(name__in=names))

    def test_vid(self):
        vids = list(VLAN.objects.all().values_list("vid", flat=True)[:3])
        params = {"vid": vids}
        self.assertQuerysetEqual(self.filterset(params, self.queryset).qs, self.queryset.filter(vid__in=vids))

    def test_location(self):
        params = {"location": [self.locations[0].pk, self.locations[1].pk]}
        self.assertQuerysetEqual(
            self.filterset(params, self.queryset).qs, self.queryset.filter(location__in=params["location"])
        )
        params = {"location": [self.locations[0].name, self.locations[1].name]}
        self.assertQuerysetEqual(
            self.filterset(params, self.queryset).qs, self.queryset.filter(location__name__in=params["location"])
        )

    def test_vlan_group(self):
        groups = list(VLANGroup.objects.filter(vlans__isnull=False).distinct())[:2]
        filter_params = [{"vlan_group": [groups[0].pk, groups[1].pk]}, {"vlan_group": [groups[0].pk, groups[1].name]}]
        for params in filter_params:
            self.assertQuerysetEqualAndNotEmpty(
                self.filterset(params, self.queryset).qs, self.queryset.filter(vlan_group__in=groups)
            )

    def test_role(self):
        roles = Role.objects.get_for_model(VLAN)[:2]
        params = {"role": [roles[0].pk, roles[1].name]}
        self.assertQuerysetEqualAndNotEmpty(
            self.filterset(params, self.queryset).qs, self.queryset.filter(role__in=[roles[0], roles[1]])
        )

    def test_status(self):
        statuses = list(Status.objects.get_for_model(VLAN).filter(vlans__isnull=False).distinct())[:2]
        params = {"status": [statuses[0].name, statuses[1].name]}
        self.assertQuerysetEqual(self.filterset(params, self.queryset).qs, self.queryset.filter(status__in=statuses))

    def test_search(self):
        value = self.queryset.values_list("pk", flat=True)[0]
        params = {"q": value}
        self.assertEqual(self.filterset(params, self.queryset).qs.values_list("pk", flat=True)[0], value)

    def test_available_on_device(self):
        manufacturer = Manufacturer.objects.first()
        devicetype = DeviceType.objects.create(manufacturer=manufacturer, model="Device Type 1")
        location = self.locations[0]
        devicerole = Role.objects.get_for_model(Device).first()
        devicestatus = Status.objects.get_for_model(Device).first()
        device = Device.objects.create(
            device_type=devicetype, role=devicerole, name="Device 1", location=location, status=devicestatus
        )
        params = {"available_on_device": [device.pk]}
        self.assertQuerysetEqual(
            self.filterset(params, self.queryset).qs,
            self.queryset.filter(Q(location=device.location) | Q(location__isnull=True)),
        )


class ServiceTestCase(FilterTestCases.FilterTestCase):
    queryset = Service.objects.all()
    filterset = ServiceFilterSet
    generic_filter_tests = (
        ["name"],
        ["device", "device__id"],
        ["device", "device__name"],
        ["virtual_machine", "virtual_machine__id"],
        ["virtual_machine", "virtual_machine__name"],
    )

    @classmethod
    def setUpTestData(cls):
        location = Location.objects.filter(location_type=LocationType.objects.get(name="Campus")).first()
        manufacturer = Manufacturer.objects.first()
        device_type = DeviceType.objects.create(manufacturer=manufacturer, model="Device Type 1")
        device_role = Role.objects.get_for_model(Device).first()
        device_status = Status.objects.get_for_model(Device).first()

        devices = (
            Device.objects.create(
                device_type=device_type,
                name="Device 1",
                location=location,
                role=device_role,
                status=device_status,
            ),
            Device.objects.create(
                device_type=device_type,
                name="Device 2",
                location=location,
                role=device_role,
                status=device_status,
            ),
            Device.objects.create(
                device_type=device_type,
                name="Device 3",
                location=location,
                role=device_role,
                status=device_status,
            ),
        )

        clustertype = ClusterType.objects.create(name="Cluster Type 1")
        cluster = Cluster.objects.create(cluster_type=clustertype, name="Cluster 1")

        vmstatus = Status.objects.get_for_model(VirtualMachine).first()
        virtual_machines = (
            VirtualMachine.objects.create(name="Virtual Machine 1", cluster=cluster, status=vmstatus),
            VirtualMachine.objects.create(name="Virtual Machine 2", cluster=cluster, status=vmstatus),
            VirtualMachine.objects.create(name="Virtual Machine 3", cluster=cluster, status=vmstatus),
        )

        services = (
            Service.objects.create(
                device=devices[0],
                name="Service 1",
                protocol=ServiceProtocolChoices.PROTOCOL_TCP,
                ports=[1001],
            ),
            Service.objects.create(
                device=devices[1],
                name="Service 2",
                protocol=ServiceProtocolChoices.PROTOCOL_TCP,
                ports=[1002],
            ),
            Service.objects.create(
                device=devices[2],
                name="Service 3",
                protocol=ServiceProtocolChoices.PROTOCOL_UDP,
                ports=[1003],
            ),
            Service.objects.create(
                virtual_machine=virtual_machines[0],
                name="Service 4",
                protocol=ServiceProtocolChoices.PROTOCOL_TCP,
                ports=[2001],
            ),
            Service.objects.create(
                virtual_machine=virtual_machines[1],
                name="Service 5",
                protocol=ServiceProtocolChoices.PROTOCOL_TCP,
                ports=[2002],
            ),
            Service.objects.create(
                virtual_machine=virtual_machines[2],
                name="Service 6",
                protocol=ServiceProtocolChoices.PROTOCOL_UDP,
                ports=[2003],
            ),
        )
        services[0].tags.set(Tag.objects.get_for_model(Service))
        services[1].tags.set(Tag.objects.get_for_model(Service)[:3])

    def test_protocol(self):
        params = {"protocol": [ServiceProtocolChoices.PROTOCOL_TCP]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 4)

    def test_ports(self):
        params = {"ports": "1001"}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 1)

    def test_search(self):
        value = self.queryset.values_list("pk", flat=True)[0]
        params = {"q": value}
        self.assertEqual(self.filterset(params, self.queryset).qs.values_list("pk", flat=True)[0], value)
