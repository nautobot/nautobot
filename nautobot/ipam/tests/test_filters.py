from django.contrib.contenttypes.models import ContentType
from django.db.models import Q

from nautobot.dcim.models import (
    Device,
    DeviceRole,
    DeviceType,
    Interface,
    Manufacturer,
    Region,
    Site,
)
from nautobot.extras.models import Status
from nautobot.ipam.choices import IPAddressRoleChoices, ServiceProtocolChoices
from nautobot.ipam.factory import PrefixFactory
from nautobot.ipam.filters import (
    AggregateFilterSet,
    IPAddressFilterSet,
    PrefixFilterSet,
    RIRFilterSet,
    RoleFilterSet,
    RouteTargetFilterSet,
    ServiceFilterSet,
    VLANFilterSet,
    VLANGroupFilterSet,
    VRFFilterSet,
)
from nautobot.ipam.models import (
    Aggregate,
    IPAddress,
    Prefix,
    RIR,
    Role,
    RouteTarget,
    Service,
    VLAN,
    VLANGroup,
    VRF,
)
from nautobot.tenancy.models import Tenant
from nautobot.utilities.testing import FilterTestCases
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

    def test_name(self):
        names = list(self.queryset.values_list("name", flat=True))[:2]
        params = {"name": names}
        self.assertQuerysetEqual(self.filterset(params, self.queryset).qs, self.queryset.filter(name__in=names))

    def test_rd(self):
        vrfs = self.queryset.filter(rd__isnull=False)[:2]
        params = {"rd": [vrfs[0].rd, vrfs[1].rd]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)

    def test_enforce_unique(self):
        params = {"enforce_unique": "true"}
        self.assertQuerysetEqual(
            self.filterset(params, self.queryset).qs, self.queryset.filter(enforce_unique=True), ordered=False
        )
        params = {"enforce_unique": "false"}
        self.assertQuerysetEqual(
            self.filterset(params, self.queryset).qs, self.queryset.filter(enforce_unique=False), ordered=False
        )

    def test_import_target(self):
        route_targets = list(RouteTarget.objects.filter(importing_vrfs__isnull=False).distinct())[:2]
        params = {"import_target_id": [route_targets[0].pk, route_targets[1].pk]}
        self.assertQuerysetEqual(
            self.filterset(params, self.queryset).qs,
            self.queryset.filter(import_targets__in=route_targets).distinct(),
            ordered=False,
        )
        params = {"import_target": [route_targets[0].name, route_targets[1].name]}
        self.assertQuerysetEqual(
            self.filterset(params, self.queryset).qs,
            self.queryset.filter(import_targets__in=route_targets).distinct(),
            ordered=False,
        )

    def test_export_target(self):
        route_targets = list(RouteTarget.objects.filter(exporting_vrfs__isnull=False).distinct())[:2]
        params = {"export_target_id": [route_targets[0].pk, route_targets[1].pk]}
        self.assertQuerysetEqual(
            self.filterset(params, self.queryset).qs,
            self.queryset.filter(export_targets__in=route_targets).distinct(),
            ordered=False,
        )
        params = {"export_target": [route_targets[0].name, route_targets[1].name]}
        self.assertQuerysetEqual(
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

    def test_name(self):
        params = {"name": [self.queryset[0].name, self.queryset[1].name, self.queryset[2].name]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 3)

    def test_importing_vrf(self):
        vrfs = list(VRF.objects.filter(import_targets__isnull=False, rd__isnull=False).distinct())[:2]
        params = {"importing_vrf_id": [vrfs[0].pk, vrfs[1].pk]}
        self.assertQuerysetEqual(
            self.filterset(params, self.queryset).qs, self.queryset.filter(importing_vrfs__in=vrfs).distinct()
        )
        params = {"importing_vrf": [vrfs[0].rd, vrfs[1].rd]}
        self.assertQuerysetEqual(
            self.filterset(params, self.queryset).qs, self.queryset.filter(importing_vrfs__in=vrfs).distinct()
        )

    def test_exporting_vrf(self):
        vrfs = list(VRF.objects.filter(export_targets__isnull=False, rd__isnull=False).distinct())[:2]
        params = {"exporting_vrf_id": [vrfs[0].pk, vrfs[1].pk]}
        self.assertQuerysetEqual(
            self.filterset(params, self.queryset).qs, self.queryset.filter(exporting_vrfs__in=vrfs).distinct()
        )
        params = {"exporting_vrf": [vrfs[0].rd, vrfs[1].rd]}
        self.assertQuerysetEqual(
            self.filterset(params, self.queryset).qs, self.queryset.filter(exporting_vrfs__in=vrfs).distinct()
        )

    def test_search(self):
        value = self.queryset.values_list("pk", flat=True)[0]
        params = {"q": value}
        self.assertEqual(self.filterset(params, self.queryset).qs.values_list("pk", flat=True)[0], value)


class RIRTestCase(FilterTestCases.NameSlugFilterTestCase):
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


class AggregateTestCase(FilterTestCases.FilterTestCase, FilterTestCases.TenancyFilterTestCaseMixin):
    queryset = Aggregate.objects.all()
    filterset = AggregateFilterSet
    tenancy_related_name = "aggregates"

    def test_search(self):
        test_values = [
            str(self.queryset.ip_family(4).last().prefix),  # e.g "10.0.0.0/8"
            str(self.queryset.ip_family(4).first().network),  # e.g. "10.0.0.0"
            str(self.queryset.ip_family(4).first().network).rsplit(".", 1)[0],  # e.g. "10.0.0"
            str(self.queryset.ip_family(6).last().prefix),  # e.g "2001:db8:1::/48"
            str(self.queryset.ip_family(6).first().network),  # e.g. "2001:db8:1::"
            str(self.queryset.ip_family(6).first().network).rsplit("::", 1)[0],  # e.g. "2001:db8:1"
        ]
        for value in test_values:
            with self.subTest(value=value):
                params = {"q": value}
                self.assertEqual(self.filterset(params, self.queryset).qs.count(), 1)

    def test_family(self):
        params = {"family": "4"}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), self.queryset.ip_family(4).count())
        params = {"family": "6"}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), self.queryset.ip_family(6).count())

    def test_date_added(self):
        dates = self.queryset.exclude(date_added__isnull=True).values_list("date_added", flat=True)[:2]
        params = {"date_added": [str(date) for date in dates]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)

    # TODO: Test for multiple values
    def test_prefix(self):
        params = {"prefix": self.queryset.ip_family(4).first().prefix}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 1)
        params = {"prefix": self.queryset.ip_family(6).first().prefix}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 1)

    def test_rir(self):
        rirs = list(RIR.objects.filter(aggregates__isnull=False).distinct())[:2]
        params = {"rir_id": [rirs[0].pk, rirs[1].pk]}
        self.assertQuerysetEqual(self.filterset(params, self.queryset).qs, self.queryset.filter(rir__in=rirs))
        params = {"rir": [rirs[0].slug, rirs[1].slug]}
        self.assertQuerysetEqual(self.filterset(params, self.queryset).qs, self.queryset.filter(rir__in=rirs))


class RoleTestCase(FilterTestCases.NameSlugFilterTestCase):
    queryset = Role.objects.all()
    filterset = RoleFilterSet


class PrefixTestCase(FilterTestCases.FilterTestCase, FilterTestCases.TenancyFilterTestCaseMixin):
    queryset = Prefix.objects.all()
    filterset = PrefixFilterSet
    tenancy_related_name = "prefixes"

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

    def test_family(self):
        params = {"family": "6"}
        ipv6_prefixes = self.queryset.ip_family(6)
        self.assertQuerysetEqualAndNotEmpty(self.filterset(params, self.queryset).qs, ipv6_prefixes)

    def test_is_pool(self):
        params = {"is_pool": "true"}
        self.assertQuerysetEqualAndNotEmpty(
            self.filterset(params, self.queryset).qs, self.queryset.filter(is_pool=True)
        )
        params = {"is_pool": "false"}
        self.assertQuerysetEqualAndNotEmpty(
            self.filterset(params, self.queryset).qs, self.queryset.exclude(is_pool=True)
        )

    def test_within(self):
        unique_description = f"test_{__name__}"
        qs = self.queryset.filter(description=unique_description)
        matches = (
            PrefixFactory(description=unique_description, prefix="10.0.1.2/31", children__max_count=0).pk,
            PrefixFactory(description=unique_description, prefix="10.0.1.4/31", children__max_count=0).pk,
        )
        PrefixFactory(description=unique_description, prefix="10.0.0.0/16")
        PrefixFactory(description=unique_description, prefix="2.2.2.2/31")
        PrefixFactory(description=unique_description, prefix="4.4.4.4/31")
        params = {"within": "10.0.0.0/16"}
        self.assertQuerysetEqualAndNotEmpty(self.filterset(params, qs).qs, qs.filter(pk__in=matches))

    def test_within_include(self):
        unique_description = f"test_{__name__}"
        qs = self.queryset.filter(description=unique_description)
        matches = (
            PrefixFactory(description=unique_description, prefix="10.0.0.0/16", children__max_count=0).pk,
            PrefixFactory(description=unique_description, prefix="10.0.1.2/31", children__max_count=0).pk,
            PrefixFactory(description=unique_description, prefix="10.0.1.4/31", children__max_count=0).pk,
        )
        PrefixFactory(description=unique_description, prefix="2.2.2.2/31")
        PrefixFactory(description=unique_description, prefix="4.4.4.4/31")
        params = {"within_include": "10.0.0.0/16"}
        self.assertQuerysetEqualAndNotEmpty(self.filterset(params, qs).qs, qs.filter(pk__in=matches))

    def test_contains(self):
        unique_description = f"test_{__name__}"
        qs = self.queryset.filter(description=unique_description)
        matches_ipv4 = (
            PrefixFactory(description=unique_description, prefix="10.0.0.0/16", children__max_count=0).pk,
            PrefixFactory(description=unique_description, prefix="10.0.1.0/24", children__max_count=0).pk,
        )
        matches_ipv6 = (
            PrefixFactory(description=unique_description, prefix="2001:db8::/32", children__max_count=0).pk,
            PrefixFactory(description=unique_description, prefix="2001:db8:0:1::/64", children__max_count=0).pk,
        )
        PrefixFactory(prefix="10.2.2.0/31")
        PrefixFactory(prefix="192.168.0.0/16")
        PrefixFactory(prefix="2001:db8:0:2::/64")
        PrefixFactory(prefix="abcd::/32")
        params = {"contains": "10.0.1.0/24"}
        self.assertQuerysetEqualAndNotEmpty(self.filterset(params, qs).qs, qs.filter(pk__in=matches_ipv4))
        params = {"contains": "2001:db8:0:1::/64"}
        self.assertQuerysetEqualAndNotEmpty(self.filterset(params, qs).qs, qs.filter(pk__in=matches_ipv6))

    def test_mask_length(self):
        for prefix_length in self.queryset.values_list("prefix_length", flat=True):
            with self.subTest(prefix_length):
                params = {"mask_length": prefix_length}
                self.assertQuerysetEqualAndNotEmpty(
                    self.filterset(params, self.queryset).qs,
                    self.queryset.filter(prefix_length=prefix_length),
                )

    def test_vrf(self):
        prefixes = self.queryset.filter(vrf__rd__isnull=False)[:2]
        vrfs = [prefixes[0].vrf, prefixes[1].vrf]
        params = {"vrf_id": [vrfs[0].pk, vrfs[1].pk]}
        self.assertQuerysetEqualAndNotEmpty(
            self.filterset(params, self.queryset).qs, self.queryset.filter(vrf__in=vrfs)
        )
        params = {"vrf": [vrfs[0].rd, vrfs[1].rd]}
        self.assertQuerysetEqualAndNotEmpty(
            self.filterset(params, self.queryset).qs,
            self.queryset.filter(vrf__rd__in=[vrfs[0].rd, vrfs[1].rd]),
        )

    def test_present_in_vrf(self):
        # clear out all the randomly generated route targets and vrfs before running this custom test
        test_prefixes = list(self.queryset.values_list("pk", flat=True)[:10])
        self.queryset.exclude(pk__in=test_prefixes).delete()
        self.queryset.all().update(vrf=None)
        IPAddress.objects.all().update(vrf=None)
        VRF.objects.all().delete()
        RouteTarget.objects.all().delete()
        route_targets = (
            RouteTarget.objects.create(name="65000:100"),
            RouteTarget.objects.create(name="65000:200"),
            RouteTarget.objects.create(name="65000:300"),
        )
        vrfs = (
            VRF.objects.create(name="VRF 1", rd="65000:100"),
            VRF.objects.create(name="VRF 2", rd="65000:200"),
            VRF.objects.create(name="VRF 3", rd="65000:300"),
        )
        vrfs[0].import_targets.add(route_targets[0], route_targets[1], route_targets[2])
        vrfs[1].export_targets.add(route_targets[1])
        vrfs[2].export_targets.add(route_targets[2])
        self.queryset.filter(pk__in=[test_prefixes[0], test_prefixes[1]]).update(vrf=vrfs[0])
        self.queryset.filter(pk__in=[test_prefixes[2], test_prefixes[3]]).update(vrf=vrfs[1])
        self.queryset.filter(pk__in=[test_prefixes[4], test_prefixes[5]]).update(vrf=vrfs[2])
        self.assertEqual(self.filterset({"present_in_vrf_id": vrfs[0].pk}, self.queryset).qs.count(), 6)
        self.assertEqual(self.filterset({"present_in_vrf_id": vrfs[1].pk}, self.queryset).qs.count(), 2)
        self.assertEqual(self.filterset({"present_in_vrf": vrfs[0].rd}, self.queryset).qs.count(), 6)
        self.assertEqual(self.filterset({"present_in_vrf": vrfs[1].rd}, self.queryset).qs.count(), 2)

    def test_region(self):
        regions = Region.objects.filter(sites__isnull=False)[:3]
        test_sites = (
            Site.objects.filter(region=regions[0]).first(),
            Site.objects.filter(region=regions[1]).first(),
            Site.objects.filter(region=regions[2]).first(),
        )
        PrefixFactory(location=None, site=test_sites[0])
        PrefixFactory(location=None, site=test_sites[1])
        params = {"region_id": [regions[0].pk, regions[1].pk]}
        self.assertQuerysetEqualAndNotEmpty(
            self.filterset(params, self.queryset).qs, self.queryset.filter(site__region__in=params["region_id"])
        )
        params = {"region": [regions[0].slug, regions[1].slug]}
        self.assertQuerysetEqualAndNotEmpty(
            self.filterset(params, self.queryset).qs, self.queryset.filter(site__region__slug__in=params["region"])
        )

    def test_site(self):
        test_sites = (
            Site.objects.create(name="site1", status=Status.objects.get_for_model(Site).first()),
            Site.objects.create(name="site2", status=Status.objects.get_for_model(Site).first()),
            Site.objects.create(name="site3", status=Status.objects.get_for_model(Site).first()),
        )
        PrefixFactory(location=None, site=test_sites[0])
        PrefixFactory(location=None, site=test_sites[1])
        params = {"site_id": [test_sites[0].pk, test_sites[1].pk]}
        self.assertQuerysetEqualAndNotEmpty(
            self.filterset(params, self.queryset).qs,
            self.queryset.filter(site__in=[test_sites[0], test_sites[1]]),
        )
        params = {"site": [test_sites[0].slug, test_sites[1].slug]}
        self.assertQuerysetEqualAndNotEmpty(
            self.filterset(params, self.queryset).qs,
            self.queryset.filter(site__in=[test_sites[0], test_sites[1]]),
        )

    def test_vlan(self):
        vlans = list(VLAN.objects.filter(prefixes__isnull=False)[:2])
        params = {"vlan_id": [vlans[0], vlans[1]]}
        self.assertQuerysetEqualAndNotEmpty(
            self.filterset(params, self.queryset).qs, self.queryset.filter(vlan__in=vlans)
        )
        # TODO: Test for multiple values
        params = {"vlan_vid": vlans[0].vid}
        self.assertQuerysetEqualAndNotEmpty(
            self.filterset(params, self.queryset).qs, self.queryset.filter(vlan__vid=vlans[0].vid)
        )

    def test_role(self):
        roles = list(Role.objects.filter(prefixes__isnull=False)[:2])
        params = {"role_id": [roles[0].pk, roles[1].pk]}
        self.assertQuerysetEqualAndNotEmpty(
            self.filterset(params, self.queryset).qs, self.queryset.filter(role__in=roles)
        )
        params = {"role": [roles[0].slug, roles[1].slug]}
        self.assertQuerysetEqualAndNotEmpty(
            self.filterset(params, self.queryset).qs, self.queryset.filter(role__in=roles)
        )

    def test_status(self):
        statuses = list(Status.objects.get_for_model(Prefix).filter(ipam_prefix_related__isnull=False)[:2])
        params = {"status": [statuses[0].slug, statuses[1].slug]}
        self.assertQuerysetEqualAndNotEmpty(
            self.filterset(params, self.queryset).qs, self.queryset.filter(status__in=statuses)
        )


class IPAddressTestCase(FilterTestCases.FilterTestCase, FilterTestCases.TenancyFilterTestCaseMixin):
    queryset = IPAddress.objects.all()
    filterset = IPAddressFilterSet
    tenancy_related_name = "ip_addresses"

    @classmethod
    def setUpTestData(cls):

        vrfs = VRF.objects.filter(rd__isnull=False)[:3]

        cls.interface_ct = ContentType.objects.get_for_model(Interface)
        cls.vm_interface_ct = ContentType.objects.get_for_model(VMInterface)

        site = Site.objects.first()
        manufacturer = Manufacturer.objects.create(name="Manufacturer 1", slug="manufacturer-1")
        device_type = DeviceType.objects.create(manufacturer=manufacturer, model="Device Type 1")
        device_role = DeviceRole.objects.create(name="Device Role 1", slug="device-role-1")

        devices = (
            Device.objects.create(
                device_type=device_type,
                name="Device 1",
                site=site,
                device_role=device_role,
            ),
            Device.objects.create(
                device_type=device_type,
                name="Device 2",
                site=site,
                device_role=device_role,
            ),
            Device.objects.create(
                device_type=device_type,
                name="Device 3",
                site=site,
                device_role=device_role,
            ),
        )

        interfaces = (
            Interface.objects.create(device=devices[0], name="Interface 1"),
            Interface.objects.create(device=devices[1], name="Interface 2"),
            Interface.objects.create(device=devices[2], name="Interface 3"),
        )

        clustertype = ClusterType.objects.create(name="Cluster Type 1", slug="cluster-type-1")
        cluster = Cluster.objects.create(type=clustertype, name="Cluster 1")

        virtual_machines = (
            VirtualMachine.objects.create(name="Virtual Machine 1", cluster=cluster),
            VirtualMachine.objects.create(name="Virtual Machine 2", cluster=cluster),
            VirtualMachine.objects.create(name="Virtual Machine 3", cluster=cluster),
        )

        vminterfaces = (
            VMInterface.objects.create(virtual_machine=virtual_machines[0], name="Interface 1"),
            VMInterface.objects.create(virtual_machine=virtual_machines[1], name="Interface 2"),
            VMInterface.objects.create(virtual_machine=virtual_machines[2], name="Interface 3"),
        )

        tenants = Tenant.objects.filter(group__isnull=False)[:3]

        statuses = Status.objects.get_for_model(IPAddress)
        status_map = {s.slug: s for s in statuses.all()}

        cls.ipv4_address = IPAddress.objects.create(
            address="10.0.0.1/24",
            tenant=None,
            vrf=None,
            assigned_object=None,
            status=status_map["active"],
            dns_name="ipaddress-a",
        )
        IPAddress.objects.create(
            address="10.0.0.2/24",
            tenant=tenants[0],
            vrf=vrfs[0],
            assigned_object=interfaces[0],
            status=status_map["active"],
            dns_name="ipaddress-b",
        )
        IPAddress.objects.create(
            address="10.0.0.3/24",
            tenant=tenants[1],
            vrf=vrfs[1],
            assigned_object=interfaces[1],
            status=status_map["reserved"],
            role=IPAddressRoleChoices.ROLE_VIP,
            dns_name="ipaddress-c",
        )
        IPAddress.objects.create(
            address="10.0.0.4/24",
            tenant=tenants[2],
            vrf=vrfs[2],
            assigned_object=interfaces[2],
            status=status_map["deprecated"],
            role=IPAddressRoleChoices.ROLE_SECONDARY,
            dns_name="ipaddress-d",
        )
        IPAddress.objects.create(
            address="10.0.0.1/25",
            tenant=None,
            vrf=None,
            assigned_object=None,
            status=status_map["active"],
        )
        cls.ipv6_address = IPAddress.objects.create(
            address="2001:db8::1/64",
            tenant=None,
            vrf=None,
            assigned_object=None,
            status=status_map["active"],
            dns_name="ipaddress-a",
        )
        IPAddress.objects.create(
            address="2001:db8::2/64",
            tenant=tenants[0],
            vrf=vrfs[0],
            assigned_object=vminterfaces[0],
            status=status_map["active"],
            dns_name="ipaddress-b",
        )
        IPAddress.objects.create(
            address="2001:db8::3/64",
            tenant=tenants[1],
            vrf=vrfs[1],
            assigned_object=vminterfaces[1],
            status=status_map["reserved"],
            role=IPAddressRoleChoices.ROLE_VIP,
            dns_name="ipaddress-c",
        )
        IPAddress.objects.create(
            address="2001:db8::4/64",
            tenant=tenants[2],
            vrf=vrfs[2],
            assigned_object=vminterfaces[2],
            status=status_map["deprecated"],
            role=IPAddressRoleChoices.ROLE_SECONDARY,
            dns_name="ipaddress-d",
        )
        IPAddress.objects.create(
            address="2001:db8::1/65",
            tenant=None,
            vrf=None,
            assigned_object=None,
            status=status_map["active"],
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

    def test_family(self):
        params = {"family": "6"}
        self.assertQuerysetEqualAndNotEmpty(self.filterset(params, self.queryset).qs, self.queryset.ip_family(6))
        params = {"family": "4"}
        self.assertQuerysetEqualAndNotEmpty(self.filterset(params, self.queryset).qs, self.queryset.ip_family(4))

    def test_dns_name(self):
        names = list(self.queryset.exclude(dns_name="").distinct_values_list("dns_name", flat=True)[:2])
        params = {"dns_name": names}
        self.assertQuerysetEqualAndNotEmpty(
            self.filterset(params, self.queryset).qs, self.queryset.filter(dns_name__in=names)
        )

    def test_parent(self):
        ipv4_parent = self.queryset.ip_family(4).first().address.supernet()[-1]
        params = {"parent": str(ipv4_parent)}
        self.assertQuerysetEqualAndNotEmpty(
            self.filterset(params, self.queryset).qs, self.queryset.net_host_contained(ipv4_parent)
        )
        ipv6_parent = self.queryset.ip_family(6).first().address.supernet()[-1]
        params = {"parent": str(ipv6_parent)}
        self.assertQuerysetEqualAndNotEmpty(
            self.filterset(params, self.queryset).qs, self.queryset.net_host_contained(ipv6_parent)
        )

    def test_filter_address(self):
        """Check IPv4 and IPv6, with and without a mask"""
        ipv4_addresses = self.queryset.ip_family(4)[:2]
        ipv6_addresses = self.queryset.ip_family(6)[:2]
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
        params = {"mask_length": self.queryset.first().prefix_length}
        self.assertQuerysetEqualAndNotEmpty(
            self.filterset(params, self.queryset).qs, self.queryset.filter(prefix_length=params["mask_length"])
        )

    def test_vrf(self):
        vrfs = list(VRF.objects.filter(ip_addresses__isnull=False, rd__isnull=False).distinct())[:2]
        params = {"vrf_id": [vrfs[0].pk, vrfs[1].pk]}
        self.assertQuerysetEqualAndNotEmpty(
            self.filterset(params, self.queryset).qs, self.queryset.filter(vrf__in=vrfs).distinct()
        )
        params = {"vrf": [vrfs[0].rd, vrfs[1].rd]}
        self.assertQuerysetEqualAndNotEmpty(
            self.filterset(params, self.queryset).qs, self.queryset.filter(vrf__in=vrfs).distinct()
        )

    def test_device(self):
        interfaces = Interface.objects.filter(ip_addresses__isnull=False)
        devices = list(Device.objects.filter(interfaces__in=interfaces).distinct()[:2])
        params = {"device_id": [devices[0].pk, devices[1].pk]}
        self.assertQuerysetEqualAndNotEmpty(
            self.filterset(params, self.queryset).qs,
            self.queryset.filter(assigned_object_id__in=devices[0].interfaces.all() | devices[1].interfaces.all()),
        )

        params = {"device": [devices[0].name, devices[1].name]}
        self.assertQuerysetEqualAndNotEmpty(
            self.filterset(params, self.queryset).qs,
            self.queryset.filter(assigned_object_id__in=devices[0].interfaces.all() | devices[1].interfaces.all()),
        )

    def test_virtual_machine(self):
        vm_interfaces = VMInterface.objects.filter(ip_addresses__isnull=False)
        virtual_machines = list(VirtualMachine.objects.filter(interfaces__in=vm_interfaces).distinct()[:2])
        params = {"virtual_machine_id": [virtual_machines[0].pk, virtual_machines[1].pk]}
        self.assertQuerysetEqualAndNotEmpty(
            self.filterset(params, self.queryset).qs,
            self.queryset.filter(
                assigned_object_id__in=virtual_machines[0].interfaces.all() | virtual_machines[1].interfaces.all()
            ),
        )

        params = {"virtual_machine": [virtual_machines[0].name, virtual_machines[1].name]}
        self.assertQuerysetEqualAndNotEmpty(
            self.filterset(params, self.queryset).qs,
            self.queryset.filter(
                assigned_object_id__in=virtual_machines[0].interfaces.all() | virtual_machines[1].interfaces.all()
            ),
        )

    def test_interface(self):
        interfaces = list(Interface.objects.filter(ip_addresses__isnull=False)[:2])
        params = {"interface_id": [interfaces[0].pk, interfaces[1].pk]}
        self.assertQuerysetEqualAndNotEmpty(
            self.filterset(params, self.queryset).qs,
            self.queryset.filter(assigned_object_id__in=[interfaces[0].pk, interfaces[1].pk]),
        )

        params = {"interface": [interfaces[0].name, interfaces[1].name]}
        self.assertQuerysetEqualAndNotEmpty(
            self.filterset(params, self.queryset).qs,
            self.queryset.filter(assigned_object_id__in=[interfaces[0].pk, interfaces[1].pk]),
        )

    def test_vminterface(self):
        vm_interfaces = list(VMInterface.objects.filter(ip_addresses__isnull=False)[:2])
        params = {"vminterface_id": [vm_interfaces[0].pk, vm_interfaces[1].pk]}
        self.assertQuerysetEqualAndNotEmpty(
            self.filterset(params, self.queryset).qs,
            self.queryset.filter(assigned_object_id__in=[vm_interfaces[0].pk, vm_interfaces[1].pk]),
        )

        params = {"vminterface": [vm_interfaces[0].name, vm_interfaces[1].name]}
        self.assertQuerysetEqualAndNotEmpty(
            self.filterset(params, self.queryset).qs,
            self.queryset.filter(assigned_object_id__in=[vm_interfaces[0].pk, vm_interfaces[1].pk]),
        )

    def test_assigned_to_interface(self):
        params = {"assigned_to_interface": "true"}
        self.assertQuerysetEqualAndNotEmpty(
            self.filterset(params, self.queryset).qs,
            self.queryset.filter(assigned_object_id__isnull=False),
        )
        params = {"assigned_to_interface": "false"}
        self.assertQuerysetEqualAndNotEmpty(
            self.filterset(params, self.queryset).qs,
            self.queryset.filter(assigned_object_id__isnull=True),
        )

    def test_status(self):
        statuses = list(Status.objects.get_for_model(IPAddress).filter(ipam_ipaddress_related__isnull=False)[:2])
        params = {"status": [statuses[0].slug, statuses[1].slug]}
        self.assertQuerysetEqualAndNotEmpty(
            self.filterset(params, self.queryset).qs, self.queryset.filter(status__in=statuses)
        )

    def test_role(self):
        roles = list(IPAddress.objects.exclude(role="").distinct_values_list("role", flat=True)[:2])
        params = {"role": roles}
        self.assertQuerysetEqualAndNotEmpty(
            self.filterset(params, self.queryset).qs,
            self.queryset.filter(role__in=roles),
        )


class VLANGroupTestCase(FilterTestCases.NameSlugFilterTestCase):
    queryset = VLANGroup.objects.all()
    filterset = VLANGroupFilterSet

    @classmethod
    def setUpTestData(cls):

        cls.regions = Region.objects.filter(sites__isnull=False)[:3]
        cls.sites = (
            Site.objects.filter(region=cls.regions[0]).first(),
            Site.objects.filter(region=cls.regions[1]).first(),
            Site.objects.filter(region=cls.regions[2]).first(),
        )

        VLANGroup.objects.create(name="VLAN Group 1", slug="vlan-group-1", site=cls.sites[0], description="A")
        VLANGroup.objects.create(name="VLAN Group 2", slug="vlan-group-2", site=cls.sites[1], description="B")
        VLANGroup.objects.create(name="VLAN Group 3", slug="vlan-group-3", site=cls.sites[2], description="C")
        VLANGroup.objects.create(name="VLAN Group 4", slug="vlan-group-4", site=None)

    def test_description(self):
        descriptions = list(VLANGroup.objects.exclude(description="").values_list("description", flat=True)[:2])
        params = {"description": descriptions}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)

    def test_region(self):
        regions = list(self.regions[:2])
        params = {"region_id": [regions[0].pk, regions[1].pk]}
        self.assertQuerysetEqual(
            self.filterset(params, self.queryset).qs, self.queryset.filter(site__region__in=regions)
        )
        params = {"region": [regions[0].slug, regions[1].slug]}
        self.assertQuerysetEqual(
            self.filterset(params, self.queryset).qs, self.queryset.filter(site__region__in=regions)
        )

    def test_site(self):
        sites = list(self.sites[:2])
        params = {"site_id": [sites[0].pk, sites[1].pk]}
        self.assertQuerysetEqual(self.filterset(params, self.queryset).qs, self.queryset.filter(site__in=sites))
        params = {"site": [sites[0].slug, sites[1].slug]}
        self.assertQuerysetEqual(self.filterset(params, self.queryset).qs, self.queryset.filter(site__in=sites))


class VLANTestCase(FilterTestCases.FilterTestCase, FilterTestCases.TenancyFilterTestCaseMixin):
    queryset = VLAN.objects.all()
    filterset = VLANFilterSet
    tenancy_related_name = "vlans"

    @classmethod
    def setUpTestData(cls):

        cls.regions = Region.objects.filter(sites__isnull=False)
        cls.sites = (
            Site.objects.filter(region=cls.regions[0]).first(),
            Site.objects.filter(region=cls.regions[1]).first(),
            Site.objects.filter(region=cls.regions[2]).first(),
        )

        roles = Role.objects.all()[:3]

        groups = (
            VLANGroup.objects.create(name="VLAN Group 1", slug="vlan-group-1", site=cls.sites[0]),
            VLANGroup.objects.create(name="VLAN Group 2", slug="vlan-group-2", site=cls.sites[1]),
            VLANGroup.objects.create(name="VLAN Group 3", slug="vlan-group-3", site=None),
        )

        tenants = Tenant.objects.filter(group__isnull=False)[:3]

        statuses = Status.objects.get_for_model(VLAN)
        status_map = {s.slug: s for s in statuses.all()}

        VLAN.objects.create(
            vid=101,
            name="VLAN 101",
            site=cls.sites[0],
            group=groups[0],
            role=roles[0],
            tenant=tenants[0],
            status=status_map["active"],
        )
        VLAN.objects.create(
            vid=102,
            name="VLAN 102",
            site=cls.sites[0],
            group=groups[0],
            role=roles[0],
            tenant=tenants[0],
            status=status_map["active"],
        )
        VLAN.objects.create(
            vid=201,
            name="VLAN 201",
            site=cls.sites[1],
            group=groups[1],
            role=roles[1],
            tenant=tenants[1],
            status=status_map["deprecated"],
        )
        VLAN.objects.create(
            vid=202,
            name="VLAN 202",
            site=cls.sites[1],
            group=groups[1],
            role=roles[1],
            tenant=tenants[1],
            status=status_map["deprecated"],
        )
        VLAN.objects.create(
            vid=301,
            name="VLAN 301",
            site=cls.sites[2],
            group=groups[2],
            role=roles[2],
            tenant=tenants[2],
            status=status_map["reserved"],
        )
        VLAN.objects.create(
            vid=302,
            name="VLAN 302",
            site=cls.sites[2],
            group=groups[2],
            role=roles[2],
            tenant=tenants[2],
            status=status_map["reserved"],
        )

    def test_name(self):
        names = list(VLAN.objects.all().values_list("name", flat=True)[:2])
        params = {"name": names}
        self.assertQuerysetEqual(self.filterset(params, self.queryset).qs, self.queryset.filter(name__in=names))

    def test_vid(self):
        vids = list(VLAN.objects.all().values_list("vid", flat=True)[:3])
        params = {"vid": vids}
        self.assertQuerysetEqual(self.filterset(params, self.queryset).qs, self.queryset.filter(vid__in=vids))

    def test_region(self):
        regions = list(self.regions[:2])
        params = {"region_id": [regions[0].pk, regions[1].pk]}
        self.assertQuerysetEqual(
            self.filterset(params, self.queryset).qs, self.queryset.filter(site__region__in=regions)
        )
        params = {"region": [regions[0].slug, regions[1].slug]}
        self.assertQuerysetEqual(
            self.filterset(params, self.queryset).qs, self.queryset.filter(site__region__in=regions)
        )

    def test_site(self):
        sites = list(self.sites[:2])
        params = {"site_id": [sites[0].pk, sites[1].pk]}
        self.assertQuerysetEqual(self.filterset(params, self.queryset).qs, self.queryset.filter(site__in=sites))
        params = {"site": [sites[0].slug, sites[1].slug]}
        self.assertQuerysetEqual(self.filterset(params, self.queryset).qs, self.queryset.filter(site__in=sites))

    def test_group(self):
        groups = list(VLANGroup.objects.filter(vlans__isnull=False).distinct())[:2]
        params = {"group_id": [groups[0].pk, groups[1].pk]}
        self.assertQuerysetEqual(self.filterset(params, self.queryset).qs, self.queryset.filter(group__in=groups))
        params = {"group": [groups[0].slug, groups[1].slug]}
        self.assertQuerysetEqual(self.filterset(params, self.queryset).qs, self.queryset.filter(group__in=groups))

    def test_role(self):
        roles = list(Role.objects.filter(vlans__isnull=False).distinct())[:2]
        params = {"role_id": [roles[0].pk, roles[1].pk]}
        self.assertQuerysetEqual(self.filterset(params, self.queryset).qs, self.queryset.filter(role__in=roles))
        params = {"role": [roles[0].slug, roles[1].slug]}
        self.assertQuerysetEqual(self.filterset(params, self.queryset).qs, self.queryset.filter(role__in=roles))

    def test_status(self):
        statuses = list(Status.objects.get_for_model(VLAN).filter(ipam_vlan_related__isnull=False).distinct())[:2]
        params = {"status": [statuses[0].slug, statuses[1].slug]}
        self.assertQuerysetEqual(self.filterset(params, self.queryset).qs, self.queryset.filter(status__in=statuses))

    def test_search(self):
        value = self.queryset.values_list("pk", flat=True)[0]
        params = {"q": value}
        self.assertEqual(self.filterset(params, self.queryset).qs.values_list("pk", flat=True)[0], value)

    def test_available_on_device(self):
        manufacturer = Manufacturer.objects.create(name="Test Manufacturer 1", slug="test-manufacturer-1")
        devicetype = DeviceType.objects.create(manufacturer=manufacturer, model="Device Type 1", slug="device-type-1")
        site = self.sites[0]
        devicerole = DeviceRole.objects.create(name="Test Device Role 1", slug="test-device-role-1", color="ff0000")
        device = Device.objects.create(device_type=devicetype, device_role=devicerole, name="Device 1", site=site)
        params = {"available_on_device": device.pk}
        self.assertQuerysetEqual(
            self.filterset(params, self.queryset).qs, self.queryset.filter(Q(site=device.site) | Q(site__isnull=True))
        )


class ServiceTestCase(FilterTestCases.FilterTestCase):
    queryset = Service.objects.all()
    filterset = ServiceFilterSet

    @classmethod
    def setUpTestData(cls):

        site = Site.objects.first()
        manufacturer = Manufacturer.objects.create(name="Manufacturer 1", slug="manufacturer-1")
        device_type = DeviceType.objects.create(manufacturer=manufacturer, model="Device Type 1")
        device_role = DeviceRole.objects.create(name="Device Role 1", slug="device-role-1")

        devices = (
            Device.objects.create(
                device_type=device_type,
                name="Device 1",
                site=site,
                device_role=device_role,
            ),
            Device.objects.create(
                device_type=device_type,
                name="Device 2",
                site=site,
                device_role=device_role,
            ),
            Device.objects.create(
                device_type=device_type,
                name="Device 3",
                site=site,
                device_role=device_role,
            ),
        )

        clustertype = ClusterType.objects.create(name="Cluster Type 1", slug="cluster-type-1")
        cluster = Cluster.objects.create(type=clustertype, name="Cluster 1")

        virtual_machines = (
            VirtualMachine.objects.create(name="Virtual Machine 1", cluster=cluster),
            VirtualMachine.objects.create(name="Virtual Machine 2", cluster=cluster),
            VirtualMachine.objects.create(name="Virtual Machine 3", cluster=cluster),
        )

        Service.objects.create(
            device=devices[0],
            name="Service 1",
            protocol=ServiceProtocolChoices.PROTOCOL_TCP,
            ports=[1001],
        )
        Service.objects.create(
            device=devices[1],
            name="Service 2",
            protocol=ServiceProtocolChoices.PROTOCOL_TCP,
            ports=[1002],
        )
        Service.objects.create(
            device=devices[2],
            name="Service 3",
            protocol=ServiceProtocolChoices.PROTOCOL_UDP,
            ports=[1003],
        )
        Service.objects.create(
            virtual_machine=virtual_machines[0],
            name="Service 4",
            protocol=ServiceProtocolChoices.PROTOCOL_TCP,
            ports=[2001],
        )
        Service.objects.create(
            virtual_machine=virtual_machines[1],
            name="Service 5",
            protocol=ServiceProtocolChoices.PROTOCOL_TCP,
            ports=[2002],
        )
        Service.objects.create(
            virtual_machine=virtual_machines[2],
            name="Service 6",
            protocol=ServiceProtocolChoices.PROTOCOL_UDP,
            ports=[2003],
        )

    def test_name(self):
        params = {"name": ["Service 1", "Service 2"]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)

    def test_protocol(self):
        params = {"protocol": ServiceProtocolChoices.PROTOCOL_TCP}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 4)

    def test_port(self):
        params = {"port": "1001"}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 1)

    def test_device(self):
        devices = Device.objects.all()[:2]
        params = {"device_id": [devices[0].pk, devices[1].pk]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)
        params = {"device": [devices[0].name, devices[1].name]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)

    def test_virtual_machine(self):
        vms = VirtualMachine.objects.all()[:2]
        params = {"virtual_machine_id": [vms[0].pk, vms[1].pk]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)
        params = {"virtual_machine": [vms[0].name, vms[1].name]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)

    def test_search(self):
        value = self.queryset.values_list("pk", flat=True)[0]
        params = {"q": value}
        self.assertEqual(self.filterset(params, self.queryset).qs.values_list("pk", flat=True)[0], value)
