from unittest import skipIf

import netaddr
from django.db import connection
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
from nautobot.utilities.testing import TestCase, FilterTestCases
from nautobot.virtualization.models import (
    Cluster,
    ClusterType,
    VirtualMachine,
    VMInterface,
)


class VRFTestCase(FilterTestCases.FilterTestCase, FilterTestCases.TenancyFilterTestCaseMixin):
    queryset = VRF.objects.all()
    filterset = VRFFilterSet
    tenancy_related_name = "vrfs"

    # Note: all assertQuerySetEqual() calls here must use ordered=False,
    # because order_by=["name", "rd"] but name is not globally unique and rd can be null,
    # so relative ordering of VRFs with identical name and null rd is not guaranteed.

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
    fixtures = ("status",)
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
        ipv6_prefixes = Prefix.objects.ip_family(6)
        self.assertQuerysetEqual(self.filterset(params, self.queryset).qs, ipv6_prefixes)

    def test_is_pool(self):
        params = {"is_pool": "true"}
        self.assertQuerysetEqual(self.filterset(params, self.queryset).qs, Prefix.objects.filter(is_pool=True))
        params = {"is_pool": "false"}
        self.assertQuerysetEqual(self.filterset(params, self.queryset).qs, Prefix.objects.exclude(is_pool=True))

    def test_within(self):
        unique_description = f"test_{__name__}"
        qs = self.queryset.filter(description=unique_description)
        matches = (
            PrefixFactory(description=unique_description, prefix="10.0.1.2/31").pk,
            PrefixFactory(description=unique_description, prefix="10.0.1.4/31").pk,
        )
        PrefixFactory(description=unique_description, prefix="10.0.0.0/16")
        PrefixFactory(description=unique_description, prefix="2.2.2.2/31")
        PrefixFactory(description=unique_description, prefix="4.4.4.4/31")
        params = {"within": "10.0.0.0/16"}
        self.assertQuerysetEqual(self.filterset(params, qs).qs, qs.filter(pk__in=matches))

    def test_within_include(self):
        unique_description = f"test_{__name__}"
        qs = self.queryset.filter(description=unique_description)
        matches = (
            PrefixFactory(description=unique_description, prefix="10.0.0.0/16").pk,
            PrefixFactory(description=unique_description, prefix="10.0.1.2/31").pk,
            PrefixFactory(description=unique_description, prefix="10.0.1.4/31").pk,
        )
        PrefixFactory(description=unique_description, prefix="2.2.2.2/31")
        PrefixFactory(description=unique_description, prefix="4.4.4.4/31")
        params = {"within_include": "10.0.0.0/16"}
        self.assertQuerysetEqual(self.filterset(params, qs).qs, qs.filter(pk__in=matches))

    def test_contains(self):
        unique_description = f"test_{__name__}"
        qs = self.queryset.filter(description=unique_description)
        matches_ipv4 = (
            PrefixFactory(description=unique_description, prefix="10.0.0.0/16").pk,
            PrefixFactory(description=unique_description, prefix="10.0.1.0/24").pk,
        )
        matches_ipv6 = (
            PrefixFactory(description=unique_description, prefix="2001:db8::/32").pk,
            PrefixFactory(description=unique_description, prefix="2001:db8:0:1::/64").pk,
        )
        PrefixFactory(prefix="10.2.2.0/31")
        PrefixFactory(prefix="192.168.0.0/16")
        PrefixFactory(prefix="2001:db8:0:2::/64")
        PrefixFactory(prefix="abcd::/32")
        params = {"contains": "10.0.1.0/24"}
        self.assertQuerysetEqual(self.filterset(params, qs).qs, qs.filter(pk__in=matches_ipv4))
        params = {"contains": "2001:db8:0:1::/64"}
        self.assertQuerysetEqual(self.filterset(params, qs).qs, qs.filter(pk__in=matches_ipv6))

    def test_mask_length(self):
        for prefix_length in self.queryset.values_list("prefix_length", flat=True):
            with self.subTest(prefix_length):
                params = {"mask_length": prefix_length}
                self.assertQuerysetEqual(
                    self.filterset(params, self.queryset).qs,
                    self.queryset.filter(prefix_length=prefix_length),
                )

    def test_vrf(self):
        prefixes = Prefix.objects.filter(vrf__rd__isnull=False)[:2]
        vrfs = [prefixes[0].vrf, prefixes[1].vrf]
        params = {"vrf_id": [vrfs[0].pk, vrfs[1].pk]}
        self.assertQuerysetEqual(self.filterset(params, self.queryset).qs, self.queryset.filter(vrf__in=vrfs))
        params = {"vrf": [vrfs[0].rd, vrfs[1].rd]}
        self.assertQuerysetEqual(
            self.filterset(params, self.queryset).qs,
            self.queryset.filter(vrf__rd__in=[vrfs[0].rd, vrfs[1].rd]),
        )

    def test_present_in_vrf(self):
        # clear out all the randomly generated route targets and vrfs before running this custom test
        test_prefixes = Prefix.objects.all()[:10]
        Prefix.objects.exclude(pk__in=test_prefixes.values_list("pk", flat=True)).delete()
        Prefix.objects.all().update(vrf=None)
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
        Prefix.objects.filter(pk__in=[test_prefixes[0].pk, test_prefixes[1].pk]).update(vrf=vrfs[0])
        Prefix.objects.filter(pk__in=[test_prefixes[2].pk, test_prefixes[3].pk]).update(vrf=vrfs[1])
        Prefix.objects.filter(pk__in=[test_prefixes[4].pk, test_prefixes[5].pk]).update(vrf=vrfs[2])
        self.assertEqual(self.filterset({"present_in_vrf_id": vrfs[0].pk}, self.queryset).qs.count(), 6)
        self.assertEqual(self.filterset({"present_in_vrf_id": vrfs[1].pk}, self.queryset).qs.count(), 2)
        self.assertEqual(self.filterset({"present_in_vrf": vrfs[0].rd}, self.queryset).qs.count(), 6)
        self.assertEqual(self.filterset({"present_in_vrf": vrfs[1].rd}, self.queryset).qs.count(), 2)

    def test_region(self):
        regions = (
            Region.objects.create(name="region1"),
            Region.objects.create(name="region2"),
            Region.objects.create(name="region3"),
        )
        test_sites = (
            Site.objects.create(name="site1", region=regions[0], status=Status.objects.get_for_model(Site).first()),
            Site.objects.create(name="site2", region=regions[1], status=Status.objects.get_for_model(Site).first()),
            Site.objects.create(name="site3", region=regions[2], status=Status.objects.get_for_model(Site).first()),
        )
        PrefixFactory(site=test_sites[0])
        PrefixFactory(site=test_sites[1])
        params = {"region_id": [regions[0].pk, regions[1].pk]}
        self.assertQuerysetEqual(
            self.filterset(params, self.queryset).qs, self.queryset.filter(site__region__in=params["region_id"])
        )
        params = {"region": [regions[0].slug, regions[1].slug]}
        self.assertQuerysetEqual(
            self.filterset(params, self.queryset).qs, self.queryset.filter(site__region__slug__in=params["region"])
        )

    def test_site(self):
        sites = Site.objects.all()[:2]
        params = {"site_id": [sites[0].pk, sites[1].pk]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 4)
        params = {"site": [sites[0].slug, sites[1].slug]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 4)

    def test_vlan(self):
        vlans = VLAN.objects.all()[:2]
        params = {"vlan_id": [vlans[0].pk, vlans[1].pk]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 4)
        # TODO: Test for multiple values
        params = {"vlan_vid": vlans[0].vid}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)

    def test_role(self):
        roles = Role.objects.all()[:2]
        params = {"role_id": [roles[0].pk, roles[1].pk]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 4)
        params = {"role": [roles[0].slug, roles[1].slug]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 4)

    def test_status(self):
        params = {"status": ["deprecated", "reserved"]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 4)


class IPAddressTestCase(FilterTestCases.FilterTestCase, FilterTestCases.TenancyFilterTestCaseMixin):
    queryset = IPAddress.objects.all()
    filterset = IPAddressFilterSet
    fixtures = ("status",)
    tenancy_related_name = "ip_addresses"

    @classmethod
    def setUpTestData(cls):

        vrfs = VRF.objects.filter(rd__isnull=False)[:3]

        site = Site.objects.create(name="Site 1", slug="site-1")
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

        IPAddress.objects.create(
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
        IPAddress.objects.create(
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
        search_terms = {
            # string searches
            "ipaddress-a": 2,
            "foo": 0,
            # network searches
            "": 10,
            "10": 5,
            "10.": 5,
            "10.0": 5,
            "10.0.0.4": 1,
            "10.0.0.4/24": 1,
            "11": 0,
            "11.": 0,
            "11.0": 0,
            "10.10.10.0/24": 0,
            "2001": 5,
            "2001:": 5,
            "2001::": 5,
            "2001:db8:": 5,
            "2001:db8::": 5,
            "2001:db8::/64": 5,
            "2001:db8::2": 1,
            "2001:db8:0:2": 0,
            "fe80": 0,
            "fe80::": 0,
            "foo.bar": 0,
        }

        for term, cnt in search_terms.items():
            params = {"q": term}
            self.assertEqual(self.filterset(params, self.queryset).qs.count(), cnt)

    def test_family(self):
        params = {"family": "6"}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 5)

    def test_dns_name(self):
        params = {"dns_name": ["ipaddress-a", "ipaddress-b"]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 4)

    def test_parent(self):
        params = {"parent": "10.0.0.0/24"}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 5)
        params = {"parent": "2001:db8::/64"}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 5)

    def test_filter_address(self):
        # Check IPv4 and IPv6, with and without a mask
        params = {"address": ["10.0.0.1/24"]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 1)
        params = {"address": ["10.0.0.1"]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)
        params = {"address": ["10.0.0.1/24", "10.0.0.1/25"]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)
        params = {"address": ["2001:db8::1/64"]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 1)
        params = {"address": ["2001:db8::1"]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)
        params = {"address": ["2001:db8::1/64", "2001:db8::1/65"]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)

    def test_mask_length(self):
        params = {"mask_length": "24"}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 4)

    def test_vrf(self):
        vrfs = list(VRF.objects.filter(ip_addresses__isnull=False, rd__isnull=False).distinct())[:2]
        params = {"vrf_id": [vrfs[0].pk, vrfs[1].pk]}
        self.assertQuerysetEqual(
            self.filterset(params, self.queryset).qs, self.queryset.filter(vrf__in=vrfs).distinct()
        )
        params = {"vrf": [vrfs[0].rd, vrfs[1].rd]}
        self.assertQuerysetEqual(
            self.filterset(params, self.queryset).qs, self.queryset.filter(vrf__in=vrfs).distinct()
        )

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

    def test_interface(self):
        interfaces = Interface.objects.all()[:2]
        params = {"interface_id": [interfaces[0].pk, interfaces[1].pk]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)
        params = {"interface": ["Interface 1", "Interface 2"]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)

    def test_vminterface(self):
        vminterfaces = VMInterface.objects.all()[:2]
        params = {"vminterface_id": [vminterfaces[0].pk, vminterfaces[1].pk]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)
        params = {"vminterface": ["Interface 1", "Interface 2"]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)

    def test_assigned_to_interface(self):
        params = {"assigned_to_interface": "true"}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 6)
        params = {"assigned_to_interface": "false"}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 4)

    def test_status(self):
        params = {"status": ["deprecated", "reserved"]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 4)

    def test_role(self):
        params = {"role": [IPAddressRoleChoices.ROLE_SECONDARY, IPAddressRoleChoices.ROLE_VIP]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 4)


class VLANGroupTestCase(FilterTestCases.NameSlugFilterTestCase):
    queryset = VLANGroup.objects.all()
    filterset = VLANGroupFilterSet

    @classmethod
    def setUpTestData(cls):

        regions = (
            Region.objects.create(name="Test Region 1", slug="test-region-1"),
            Region.objects.create(name="Test Region 2", slug="test-region-2"),
            Region.objects.create(name="Test Region 3", slug="test-region-3"),
        )

        sites = (
            Site.objects.create(name="Test Site 1", slug="test-site-1", region=regions[0]),
            Site.objects.create(name="Test Site 2", slug="test-site-2", region=regions[1]),
            Site.objects.create(name="Test Site 3", slug="test-site-3", region=regions[2]),
        )

        VLANGroup.objects.create(name="VLAN Group 1", slug="vlan-group-1", site=sites[0], description="A")
        VLANGroup.objects.create(name="VLAN Group 2", slug="vlan-group-2", site=sites[1], description="B")
        VLANGroup.objects.create(name="VLAN Group 3", slug="vlan-group-3", site=sites[2], description="C")
        VLANGroup.objects.create(name="VLAN Group 4", slug="vlan-group-4", site=None)

    def test_description(self):
        params = {"description": VLANGroup.objects.exclude(description="")[:2].values_list("description", flat=True)}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)

    def test_region(self):
        regions = list(Region.objects.filter(sites__isnull=False, sites__vlan_groups__isnull=False).distinct())[:2]
        params = {"region_id": [regions[0].pk, regions[1].pk]}
        self.assertQuerysetEqual(
            self.filterset(params, self.queryset).qs, self.queryset.filter(site__region__in=regions)
        )
        params = {"region": [regions[0].slug, regions[1].slug]}
        self.assertQuerysetEqual(
            self.filterset(params, self.queryset).qs, self.queryset.filter(site__region__in=regions)
        )

    def test_site(self):
        sites = list(Site.objects.filter(vlan_groups__isnull=False).distinct())[:2]
        params = {"site_id": [sites[0].pk, sites[1].pk]}
        self.assertQuerysetEqual(self.filterset(params, self.queryset).qs, self.queryset.filter(site__in=sites))
        params = {"site": [sites[0].slug, sites[1].slug]}
        self.assertQuerysetEqual(self.filterset(params, self.queryset).qs, self.queryset.filter(site__in=sites))


class VLANTestCase(FilterTestCases.FilterTestCase, FilterTestCases.TenancyFilterTestCaseMixin):
    queryset = VLAN.objects.all()
    filterset = VLANFilterSet
    fixtures = ("status",)
    tenancy_related_name = "vlans"

    @classmethod
    def setUpTestData(cls):

        regions = (
            Region.objects.create(name="Test Region 1", slug="test-region-1"),
            Region.objects.create(name="Test Region 2", slug="test-region-2"),
            Region.objects.create(name="Test Region 3", slug="test-region-3"),
        )

        sites = (
            Site.objects.create(name="Test Site 1", slug="test-site-1", region=regions[0]),
            Site.objects.create(name="Test Site 2", slug="test-site-2", region=regions[1]),
            Site.objects.create(name="Test Site 3", slug="test-site-3", region=regions[2]),
        )

        roles = Role.objects.all()[:3]

        groups = (
            VLANGroup.objects.create(name="VLAN Group 1", slug="vlan-group-1", site=sites[0]),
            VLANGroup.objects.create(name="VLAN Group 2", slug="vlan-group-2", site=sites[1]),
            VLANGroup.objects.create(name="VLAN Group 3", slug="vlan-group-3", site=None),
        )

        tenants = Tenant.objects.filter(group__isnull=False)[:3]

        statuses = Status.objects.get_for_model(VLAN)
        status_map = {s.slug: s for s in statuses.all()}

        VLAN.objects.create(
            vid=101,
            name="VLAN 101",
            site=sites[0],
            group=groups[0],
            role=roles[0],
            tenant=tenants[0],
            status=status_map["active"],
        )
        VLAN.objects.create(
            vid=102,
            name="VLAN 102",
            site=sites[0],
            group=groups[0],
            role=roles[0],
            tenant=tenants[0],
            status=status_map["active"],
        )
        VLAN.objects.create(
            vid=201,
            name="VLAN 201",
            site=sites[1],
            group=groups[1],
            role=roles[1],
            tenant=tenants[1],
            status=status_map["deprecated"],
        )
        VLAN.objects.create(
            vid=202,
            name="VLAN 202",
            site=sites[1],
            group=groups[1],
            role=roles[1],
            tenant=tenants[1],
            status=status_map["deprecated"],
        )
        VLAN.objects.create(
            vid=301,
            name="VLAN 301",
            site=sites[2],
            group=groups[2],
            role=roles[2],
            tenant=tenants[2],
            status=status_map["reserved"],
        )
        VLAN.objects.create(
            vid=302,
            name="VLAN 302",
            site=sites[2],
            group=groups[2],
            role=roles[2],
            tenant=tenants[2],
            status=status_map["reserved"],
        )

    def test_name(self):
        params = {"name": VLAN.objects.all().values_list("name", flat=True)[:2]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)

    def test_vid(self):
        params = {"vid": VLAN.objects.all().values_list("vid", flat=True)[:3]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 3)

    def test_region(self):
        regions = list(Region.objects.filter(sites__isnull=False, sites__vlans__isnull=False).distinct())[:2]
        params = {"region_id": [regions[0].pk, regions[1].pk]}
        self.assertQuerysetEqual(
            self.filterset(params, self.queryset).qs, self.queryset.filter(site__region__in=regions)
        )
        params = {"region": [regions[0].slug, regions[1].slug]}
        self.assertQuerysetEqual(
            self.filterset(params, self.queryset).qs, self.queryset.filter(site__region__in=regions)
        )

    def test_site(self):
        sites = list(Site.objects.filter(vlans__isnull=False).distinct())[:2]
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
        site = Site.objects.get(slug="test-site-1")
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

        site = Site.objects.create(name="Site 1", slug="site-1")
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


class IPAddressFilterTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):

        IPAddress.objects.create(address="10.0.0.1/24", vrf=None, tenant=None)
        IPAddress.objects.create(address="10.0.0.2/24", vrf=None, tenant=None)
        IPAddress.objects.create(address="10.0.0.3/24", vrf=None, tenant=None)
        IPAddress.objects.create(address="10.0.0.4/24", vrf=None, tenant=None)
        IPAddress.objects.create(address="10.0.0.1/25", vrf=None, tenant=None)
        IPAddress.objects.create(address="2001:db8::1/64", vrf=None, tenant=None)
        IPAddress.objects.create(address="2001:db8::2/64", vrf=None, tenant=None)
        IPAddress.objects.create(address="2001:db8::3/64", vrf=None, tenant=None)

    def test_family(self):
        self.assertEqual(IPAddress.objects.filter(host__family=4).count(), 5)
        self.assertEqual(IPAddress.objects.filter(host__family=6).count(), 3)

    def test_net_host(self):
        self.assertEqual(IPAddress.objects.filter(host__net_host="10.0.0.1").count(), 2)
        self.assertEqual(IPAddress.objects.filter(host__net_host="10.0.0.2").count(), 1)
        self.assertEqual(IPAddress.objects.filter(host__net_host="10.0.0.50").count(), 0)
        self.assertEqual(IPAddress.objects.filter(host__net_host="2001:db8::1").count(), 1)
        self.assertEqual(IPAddress.objects.filter(host__net_host="2001:db8::5").count(), 0)

    def test_net_host_contained(self):
        self.assertEqual(IPAddress.objects.filter(host__net_host_contained="10.0.0.0/24").count(), 5)
        self.assertEqual(IPAddress.objects.filter(host__net_host_contained="10.0.0.0/30").count(), 4)
        self.assertEqual(IPAddress.objects.filter(host__net_host_contained="10.0.0.0/31").count(), 2)
        self.assertEqual(IPAddress.objects.filter(host__net_host_contained="10.0.0.2/31").count(), 2)
        self.assertEqual(IPAddress.objects.filter(host__net_host_contained="10.0.10.0/24").count(), 0)
        self.assertEqual(IPAddress.objects.filter(host__net_host_contained="2001:db8::/64").count(), 3)
        self.assertEqual(IPAddress.objects.filter(host__net_host_contained="2222:db8::/64").count(), 0)

    def test_net_in(self):
        self.assertEqual(IPAddress.objects.filter(host__net_in=["10.0.0.0/31", "10.0.0.2/31"]).count(), 4)
        self.assertEqual(IPAddress.objects.filter(host__net_in=["10.0.0.0/24"]).count(), 5)
        self.assertEqual(IPAddress.objects.filter(host__net_in=["172.16.0.0/24"]).count(), 0)
        self.assertEqual(IPAddress.objects.filter(host__net_in=["2001:db8::/64"]).count(), 3)
        self.assertEqual(IPAddress.objects.filter(host__net_in=["10.0.0.0/24", "2001:db8::/64"]).count(), 8)

        IPAddress.objects.create(address="192.168.0.1/24", vrf=None, tenant=None)
        self.assertEqual(IPAddress.objects.filter(host__net_in=["192.168.0.0/31"]).count(), 1)

    @skipIf(
        connection.vendor == "postgresql",
        "Not currently supported on postgresql",
    )
    def test_exact(self):
        self.assertEqual(IPAddress.objects.filter(host__exact="10.0.0.1").count(), 2)
        self.assertEqual(IPAddress.objects.filter(host__exact="10.0.0.2").count(), 1)
        self.assertEqual(IPAddress.objects.filter(host__exact="10.0.0.10").count(), 0)
        self.assertEqual(IPAddress.objects.filter(host__iexact="10.0.0.1").count(), 2)
        self.assertEqual(IPAddress.objects.filter(host__iexact="10.0.0.2").count(), 1)
        self.assertEqual(IPAddress.objects.filter(host__iexact="10.0.0.10").count(), 0)

        self.assertEqual(IPAddress.objects.filter(host__exact="2001:db8::1").count(), 1)
        self.assertEqual(IPAddress.objects.filter(host__exact="2001:db8::5").count(), 0)
        self.assertEqual(IPAddress.objects.filter(host__iexact="2001:db8::1").count(), 1)
        self.assertEqual(IPAddress.objects.filter(host__iexact="2001:db8::5").count(), 0)

    @skipIf(
        connection.vendor == "postgresql",
        "Not currently supported on postgresql",
    )
    def test_endswith(self):
        self.assertEqual(IPAddress.objects.filter(host__endswith="0.2").count(), 1)
        self.assertEqual(IPAddress.objects.filter(host__endswith="0.1").count(), 2)
        self.assertEqual(IPAddress.objects.filter(host__endswith="0.50").count(), 0)
        self.assertEqual(IPAddress.objects.filter(host__iendswith="0.2").count(), 1)
        self.assertEqual(IPAddress.objects.filter(host__iendswith="0.1").count(), 2)
        self.assertEqual(IPAddress.objects.filter(host__iendswith="0.50").count(), 0)

        self.assertEqual(IPAddress.objects.filter(host__endswith="8::1").count(), 1)
        self.assertEqual(IPAddress.objects.filter(host__endswith="8::5").count(), 0)
        self.assertEqual(IPAddress.objects.filter(host__iendswith="8::1").count(), 1)
        self.assertEqual(IPAddress.objects.filter(host__iendswith="8::5").count(), 0)

    @skipIf(
        connection.vendor == "postgresql",
        "Not currently supported on postgresql",
    )
    def test_startswith(self):
        self.assertEqual(IPAddress.objects.filter(host__startswith="10.0.0.").count(), 5)
        self.assertEqual(IPAddress.objects.filter(host__startswith="10.0.0.1").count(), 2)
        self.assertEqual(IPAddress.objects.filter(host__startswith="10.50.0.").count(), 0)
        self.assertEqual(IPAddress.objects.filter(host__istartswith="10.0.0.").count(), 5)
        self.assertEqual(IPAddress.objects.filter(host__istartswith="10.0.0.1").count(), 2)
        self.assertEqual(IPAddress.objects.filter(host__istartswith="10.50.0.").count(), 0)

        self.assertEqual(IPAddress.objects.filter(host__startswith="2001:db8::").count(), 3)
        self.assertEqual(IPAddress.objects.filter(host__startswith="2001:db8::1").count(), 1)
        self.assertEqual(IPAddress.objects.filter(host__startswith="2001:db8::5").count(), 0)
        self.assertEqual(IPAddress.objects.filter(host__istartswith="2001:db8::").count(), 3)
        self.assertEqual(IPAddress.objects.filter(host__istartswith="2001:db8::1").count(), 1)
        self.assertEqual(IPAddress.objects.filter(host__istartswith="2001:db8::5").count(), 0)

    @skipIf(
        connection.vendor == "postgresql",
        "Not currently supported on postgresql",
    )
    def test_regex(self):
        self.assertEqual(IPAddress.objects.filter(host__regex=r"10\.(.*)\.1").count(), 2)
        self.assertEqual(IPAddress.objects.filter(host__regex=r"10\.(.*)\.4").count(), 1)
        self.assertEqual(IPAddress.objects.filter(host__regex=r"10\.(.*)\.50").count(), 0)
        self.assertEqual(IPAddress.objects.filter(host__iregex=r"10\.(.*)\.1").count(), 2)
        self.assertEqual(IPAddress.objects.filter(host__iregex=r"10\.(.*)\.4").count(), 1)
        self.assertEqual(IPAddress.objects.filter(host__iregex=r"10\.(.*)\.50").count(), 0)

        self.assertEqual(IPAddress.objects.filter(host__regex=r"2001(.*)1").count(), 1)
        self.assertEqual(IPAddress.objects.filter(host__regex=r"2001(.*)5").count(), 0)
        self.assertEqual(IPAddress.objects.filter(host__iregex=r"2001(.*)1").count(), 1)
        self.assertEqual(IPAddress.objects.filter(host__iregex=r"2001(.*)5").count(), 0)


class PrefixFilterTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):

        Prefix.objects.create(prefix=netaddr.IPNetwork("192.168.0.0/16"))
        Prefix.objects.create(prefix=netaddr.IPNetwork("192.168.1.0/24"))
        Prefix.objects.create(prefix=netaddr.IPNetwork("192.168.2.0/24"))
        Prefix.objects.create(prefix=netaddr.IPNetwork("192.168.3.0/24"))

        Prefix.objects.create(prefix=netaddr.IPNetwork("192.168.3.192/28"))
        Prefix.objects.create(prefix=netaddr.IPNetwork("192.168.3.208/28"))
        Prefix.objects.create(prefix=netaddr.IPNetwork("192.168.3.224/28"))

        Prefix.objects.create(prefix=netaddr.IPNetwork("fd78:da4f:e596:c217::/64"))
        Prefix.objects.create(prefix=netaddr.IPNetwork("fd78:da4f:e596:c217::/120"))
        Prefix.objects.create(prefix=netaddr.IPNetwork("fd78:da4f:e596:c217::/122"))

    def test_family(self):
        self.assertEqual(Prefix.objects.filter(network__family=4).count(), 7)
        self.assertEqual(Prefix.objects.filter(network__family=6).count(), 3)

    def test_net_equals(self):
        self.assertEqual(Prefix.objects.filter(network__net_equals="192.168.0.0/16").count(), 1)
        self.assertEqual(Prefix.objects.filter(network__net_equals="192.1.0.0/16").count(), 0)
        self.assertEqual(Prefix.objects.filter(network__net_equals="192.1.0.0/28").count(), 0)
        self.assertEqual(Prefix.objects.filter(network__net_equals="192.1.0.0/32").count(), 0)
        self.assertEqual(Prefix.objects.filter(network__net_equals="fd78:da4f:e596:c217::/64").count(), 1)
        self.assertEqual(Prefix.objects.filter(network__net_equals="fd78:da4f:e596:c218::/122").count(), 0)
        self.assertEqual(Prefix.objects.filter(network__net_equals="fd78:da4f:e596:c218::/64").count(), 0)

    def test_net_contained(self):
        self.assertEqual(Prefix.objects.filter(network__net_contained="192.0.0.0/8").count(), 7)
        self.assertEqual(Prefix.objects.filter(network__net_contained="192.168.0.0/16").count(), 6)
        self.assertEqual(Prefix.objects.filter(network__net_contained="192.168.3.0/24").count(), 3)
        self.assertEqual(Prefix.objects.filter(network__net_contained="192.168.1.0/24").count(), 0)
        self.assertEqual(Prefix.objects.filter(network__net_contained="192.168.3.192/28").count(), 0)
        self.assertEqual(Prefix.objects.filter(network__net_contained="192.168.3.192/32").count(), 0)

        self.assertEqual(Prefix.objects.filter(network__net_contained="fd78:da4f:e596:c217::/64").count(), 2)
        self.assertEqual(Prefix.objects.filter(network__net_contained="fd78:da4f:e596:c217::/120").count(), 1)
        self.assertEqual(Prefix.objects.filter(network__net_contained="fd78:da4f:e596:c218::/64").count(), 0)

    def test_net_contained_or_equal(self):
        self.assertEqual(Prefix.objects.filter(network__net_contained_or_equal="192.0.0.0/8").count(), 7)
        self.assertEqual(Prefix.objects.filter(network__net_contained_or_equal="192.168.0.0/16").count(), 7)
        self.assertEqual(Prefix.objects.filter(network__net_contained_or_equal="192.168.3.0/24").count(), 4)
        self.assertEqual(Prefix.objects.filter(network__net_contained_or_equal="192.168.1.0/24").count(), 1)
        self.assertEqual(Prefix.objects.filter(network__net_contained_or_equal="192.168.3.192/28").count(), 1)
        self.assertEqual(Prefix.objects.filter(network__net_contained_or_equal="192.168.3.192/32").count(), 0)

        self.assertEqual(Prefix.objects.filter(network__net_contained_or_equal="fd78:da4f:e596:c217::/64").count(), 3)
        self.assertEqual(Prefix.objects.filter(network__net_contained_or_equal="fd78:da4f:e596:c217::/120").count(), 2)
        self.assertEqual(Prefix.objects.filter(network__net_contained_or_equal="fd78:da4f:e596:c218::/64").count(), 0)

    def test_net_contains(self):
        self.assertEqual(Prefix.objects.filter(network__net_contains="192.0.0.0/8").count(), 0)
        self.assertEqual(Prefix.objects.filter(network__net_contains="192.168.0.0/16").count(), 0)
        self.assertEqual(Prefix.objects.filter(network__net_contains="192.168.3.0/24").count(), 1)
        self.assertEqual(Prefix.objects.filter(network__net_contains="192.168.3.192/28").count(), 2)
        self.assertEqual(Prefix.objects.filter(network__net_contains="192.168.3.192/30").count(), 3)
        self.assertEqual(Prefix.objects.filter(network__net_contains="192.168.3.192/32").count(), 3)

        self.assertEqual(Prefix.objects.filter(network__net_contains="fd78:da4f:e596:c217::/64").count(), 0)
        self.assertEqual(Prefix.objects.filter(network__net_contains="fd78:da4f:e596:c217::/120").count(), 1)
        self.assertEqual(Prefix.objects.filter(network__net_contains="fd78:da4f:e596:c217::/122").count(), 2)
        self.assertEqual(Prefix.objects.filter(network__net_contains="fd78:da4f:e596:c218::/64").count(), 0)

    def test_net_contains_or_equals(self):
        self.assertEqual(Prefix.objects.filter(network__net_contains_or_equals="192.0.0.0/8").count(), 0)
        self.assertEqual(Prefix.objects.filter(network__net_contains_or_equals="192.168.0.0/16").count(), 1)
        self.assertEqual(Prefix.objects.filter(network__net_contains_or_equals="192.168.3.0/24").count(), 2)
        self.assertEqual(Prefix.objects.filter(network__net_contains_or_equals="192.168.3.192/28").count(), 3)
        self.assertEqual(Prefix.objects.filter(network__net_contains_or_equals="192.168.3.192/30").count(), 3)
        self.assertEqual(Prefix.objects.filter(network__net_contains_or_equals="192.168.3.192/32").count(), 3)

        self.assertEqual(Prefix.objects.filter(network__net_contains_or_equals="fd78:da4f:e596:c217::/64").count(), 1)
        self.assertEqual(Prefix.objects.filter(network__net_contains_or_equals="fd78:da4f:e596:c217::/120").count(), 2)
        self.assertEqual(Prefix.objects.filter(network__net_contains_or_equals="fd78:da4f:e596:c217::/122").count(), 3)
        self.assertEqual(Prefix.objects.filter(network__net_contains_or_equals="fd78:da4f:e596:c218::/64").count(), 0)

    def test_get_by_prefix(self):
        prefix = Prefix.objects.filter(network__net_equals="192.168.0.0/16")[0]
        self.assertEqual(Prefix.objects.get(prefix="192.168.0.0/16"), prefix)

    def test_get_by_prefix_fails(self):
        _ = Prefix.objects.filter(network__net_equals="192.168.0.0/16")[0]
        with self.assertRaises(Prefix.DoesNotExist):
            Prefix.objects.get(prefix="192.168.3.0/16")

    def test_filter_by_prefix(self):
        prefix = Prefix.objects.filter(network__net_equals="192.168.0.0/16")[0]
        self.assertEqual(Prefix.objects.filter(prefix="192.168.0.0/16")[0], prefix)

    @skipIf(
        connection.vendor == "postgresql",
        "Not currently supported on postgresql",
    )
    def test_exact(self):
        self.assertEqual(Prefix.objects.filter(network__exact="192.168.0.0").count(), 1)
        self.assertEqual(Prefix.objects.filter(network__exact="192.168.1.0").count(), 1)
        self.assertEqual(Prefix.objects.filter(network__exact="192.168.50.0").count(), 0)
        self.assertEqual(Prefix.objects.filter(network__iexact="192.168.0.0").count(), 1)
        self.assertEqual(Prefix.objects.filter(network__iexact="192.168.1.0").count(), 1)
        self.assertEqual(Prefix.objects.filter(network__iexact="192.168.50.0").count(), 0)

        self.assertEqual(Prefix.objects.filter(network__exact="fd78:da4f:e596:c217::").count(), 3)
        self.assertEqual(Prefix.objects.filter(network__exact="fd78:da4f:e596:c218::").count(), 0)
        self.assertEqual(Prefix.objects.filter(network__iexact="fd78:da4f:e596:c217::").count(), 3)
        self.assertEqual(Prefix.objects.filter(network__iexact="fd78:da4f:e596:c218::").count(), 0)

    @skipIf(
        connection.vendor == "postgresql",
        "Not currently supported on postgresql",
    )
    def test_endswith(self):
        self.assertEqual(Prefix.objects.filter(network__endswith=".224").count(), 1)
        self.assertEqual(Prefix.objects.filter(network__endswith=".0").count(), 4)
        self.assertEqual(Prefix.objects.filter(network__endswith="0.0").count(), 1)
        self.assertEqual(Prefix.objects.filter(network__iendswith=".224").count(), 1)
        self.assertEqual(Prefix.objects.filter(network__iendswith=".0").count(), 4)
        self.assertEqual(Prefix.objects.filter(network__iendswith="0.0").count(), 1)

        self.assertEqual(Prefix.objects.filter(network__endswith="c217::").count(), 3)
        self.assertEqual(Prefix.objects.filter(network__endswith="c218::").count(), 0)
        self.assertEqual(Prefix.objects.filter(network__iendswith="c217::").count(), 3)
        self.assertEqual(Prefix.objects.filter(network__iendswith="c218::").count(), 0)

    @skipIf(
        connection.vendor == "postgresql",
        "Not currently supported on postgresql",
    )
    def test_startswith(self):
        self.assertEqual(Prefix.objects.filter(network__startswith="192.").count(), 7)
        self.assertEqual(Prefix.objects.filter(network__startswith="192.168.3.").count(), 4)
        self.assertEqual(Prefix.objects.filter(network__startswith="192.168.3.2").count(), 2)
        self.assertEqual(Prefix.objects.filter(network__startswith="192.168.50").count(), 0)
        self.assertEqual(Prefix.objects.filter(network__istartswith="192.").count(), 7)
        self.assertEqual(Prefix.objects.filter(network__istartswith="192.168.3.").count(), 4)
        self.assertEqual(Prefix.objects.filter(network__istartswith="192.168.3.2").count(), 2)
        self.assertEqual(Prefix.objects.filter(network__istartswith="192.168.50").count(), 0)

        self.assertEqual(Prefix.objects.filter(network__startswith="fd78:").count(), 3)
        self.assertEqual(Prefix.objects.filter(network__startswith="fd79:").count(), 0)
        self.assertEqual(Prefix.objects.filter(network__istartswith="fd78:").count(), 3)
        self.assertEqual(Prefix.objects.filter(network__istartswith="fd79:").count(), 0)

    @skipIf(
        connection.vendor == "postgresql",
        "Not currently supported on postgresql",
    )
    def test_regex(self):
        self.assertEqual(Prefix.objects.filter(network__regex=r"192\.(.*)\.0").count(), 4)
        self.assertEqual(Prefix.objects.filter(network__regex=r"192\.\d+(.*)\.0").count(), 4)
        self.assertEqual(Prefix.objects.filter(network__regex=r"10\.\d+(.*)\.0").count(), 0)
        self.assertEqual(Prefix.objects.filter(network__iregex=r"192\.(.*)\.0").count(), 4)
        self.assertEqual(Prefix.objects.filter(network__iregex=r"192\.\d+(.*)\.0").count(), 4)
        self.assertEqual(Prefix.objects.filter(network__iregex=r"10\.\d+(.*)\.0").count(), 0)

        self.assertEqual(Prefix.objects.filter(network__regex=r"fd78(.*)c217(.*)").count(), 3)
        self.assertEqual(Prefix.objects.filter(network__regex=r"fd78(.*)c218(.*)").count(), 0)
        self.assertEqual(Prefix.objects.filter(network__iregex=r"fd78(.*)c217(.*)").count(), 3)
        self.assertEqual(Prefix.objects.filter(network__iregex=r"fd78(.*)c218(.*)").count(), 0)
