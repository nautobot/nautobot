from unittest import skipIf

import netaddr
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.db import connection
from django.test import TestCase, override_settings

from nautobot.dcim.models import Device, DeviceRole, DeviceType, Interface, Location, LocationType, Manufacturer, Site
from nautobot.extras.models import Status
from nautobot.ipam.choices import IPAddressRoleChoices, IPAddressStatusChoices
from nautobot.ipam.models import Aggregate, IPAddress, Prefix, RIR, VLAN, VLANGroup, VRF


class TestVarbinaryIPField(TestCase):
    """Tests for `nautobot.ipam.fields.VarbinaryIPField`."""

    def setUp(self):
        super().setUp()

        # Field is a VarbinaryIPField we'll use to test.
        self.prefix = Prefix.objects.create(prefix="10.0.0.0/24")
        self.field = self.prefix._meta.get_field("network")
        self.network = self.prefix.network
        self.network_packed = bytes(self.prefix.prefix.network)

    def test_db_type(self):
        """Test `VarbinaryIPField.db_type`."""
        # Mapping of vendor -> db_type
        db_types = {
            "postgresql": "bytea",
            "mysql": "varbinary(16)",
        }

        expected = db_types[connection.vendor]
        self.assertEqual(self.field.db_type(connection), expected)

    def test_value_to_string(self):
        """Test `VarbinaryIPField.value_to_string`."""
        # value_to_string calls _parse_address so no need for negative tests here.
        self.assertEqual(self.field.value_to_string(self.prefix), self.network)

    def test_parse_address_success(self):
        """Test `VarbinaryIPField._parse_address` PASS."""

        # str => netaddr.IPAddress
        obj = self.field._parse_address(self.prefix.network)
        self.assertEqual(obj, netaddr.IPAddress(self.network))

        # bytes => netaddr.IPAddress
        self.assertEqual(self.field._parse_address(bytes(obj)), obj)

        # int => netaddr.IPAddress
        self.assertEqual(self.field._parse_address(int(obj)), obj)

        # IPAddress => netaddr.IPAddress
        self.assertEqual(self.field._parse_address(obj), obj)

        # Special cases involving values that could be IPv4 or IPv6 if naively interpreted
        self.assertEqual(self.field._parse_address(bytes(netaddr.IPAddress("0.0.0.1"))), netaddr.IPAddress("0.0.0.1"))
        self.assertEqual(self.field._parse_address(bytes(netaddr.IPAddress("::1"))), netaddr.IPAddress("::1"))
        self.assertEqual(
            self.field._parse_address(bytes(netaddr.IPAddress("::192.0.2.15"))), netaddr.IPAddress("::192.0.2.15")
        )

    def test_parse_address_failure(self):
        """Test `VarbinaryIPField._parse_address` FAIL."""

        bad_inputs = (
            None,
            -42,
            "10.10.10.10/32",  # Prefixes not allowed here
            "310.10.10.10",  # Bad IP
        )
        for bad in bad_inputs:
            self.assertRaises(ValidationError, self.field._parse_address, bad)

    def test_to_python(self):
        """Test `VarbinaryIPField.to_python`."""

        # to_python calls _parse_address so no need for negative tests here.

        # str => str
        self.assertEqual(self.field.to_python(self.prefix.network), self.network)

        # netaddr.IPAddress => str
        self.assertEqual(self.field.to_python(self.prefix.prefix.ip), self.network)

    @skipIf(
        connection.vendor != "postgresql",
        "postgres is not the database driver",
    )
    def test_get_db_prep_value_postgres(self):
        """Test `VarbinaryIPField.get_db_prep_value`."""

        # PostgreSQL escapes `bytes` in `::bytea` and you must call
        # `getquoted()` to extract the value.
        prepped = self.field.get_db_prep_value(self.network, connection)
        manual = connection.Database.Binary(self.network_packed)
        self.assertEqual(prepped.getquoted(), manual.getquoted())

    @skipIf(
        connection.vendor != "mysql",
        "mysql is not the database driver",
    )
    def test_get_db_prep_value_mysql(self):
        """Test `VarbinaryIPField.get_db_prep_value` for MySQL."""

        # MySQL uses raw `bytes`
        prepped = self.field.get_db_prep_value(self.network, connection)
        manual = bytes(self.network_packed)
        self.assertEqual(prepped, manual)


class TestAggregate(TestCase):
    def test_get_utilization(self):
        aggregate = Aggregate(prefix=netaddr.IPNetwork("22.0.0.0/8"), rir=RIR.objects.first())
        aggregate.save()

        # 25% utilization
        Prefix.objects.bulk_create(
            (
                Prefix(prefix=netaddr.IPNetwork("22.0.0.0/12")),
                Prefix(prefix=netaddr.IPNetwork("22.16.0.0/12")),
                Prefix(prefix=netaddr.IPNetwork("22.32.0.0/12")),
                Prefix(prefix=netaddr.IPNetwork("22.48.0.0/12")),
            )
        )
        self.assertEqual(aggregate.get_utilization(), (4194304, 16777216))

        # 50% utilization
        Prefix.objects.bulk_create((Prefix(prefix=netaddr.IPNetwork("22.64.0.0/10")),))
        self.assertEqual(aggregate.get_utilization(), (8388608, 16777216))

        # 100% utilization
        Prefix.objects.bulk_create((Prefix(prefix=netaddr.IPNetwork("22.128.0.0/9")),))
        self.assertEqual(aggregate.get_utilization(), (16777216, 16777216))

        # TODO: equivalent IPv6 tests for thoroughness?


class TestPrefix(TestCase):
    def setUp(self):
        super().setUp()
        self.statuses = Status.objects.get_for_model(Prefix)

    def test_prefix_validation(self):
        location_type = LocationType.objects.get(name="Room")
        location = Location.objects.filter(location_type=location_type).first()
        prefix = Prefix(prefix=netaddr.IPNetwork("192.0.2.0/24"), location=location)
        prefix.status = self.statuses.get(slug="active")
        with self.assertRaises(ValidationError) as cm:
            prefix.validated_save()
        self.assertIn(f'Prefixes may not associate to locations of type "{location_type.name}"', str(cm.exception))

        location_type.content_types.add(ContentType.objects.get_for_model(Prefix))
        site_2 = Site.objects.exclude(pk=location.base_site.pk).last()
        prefix.site = site_2
        with self.assertRaises(ValidationError) as cm:
            prefix.validated_save()
        self.assertIn(f'Location "{location.name}" does not belong to site "{site_2.name}"', str(cm.exception))

    def test_get_duplicates(self):
        prefixes = (
            Prefix.objects.create(prefix=netaddr.IPNetwork("192.0.2.0/24")),
            Prefix.objects.create(prefix=netaddr.IPNetwork("192.0.2.0/24")),
            Prefix.objects.create(prefix=netaddr.IPNetwork("192.0.2.0/24")),
        )
        duplicate_prefix_pks = [p.pk for p in prefixes[0].get_duplicates()]

        self.assertSetEqual(set(duplicate_prefix_pks), {prefixes[1].pk, prefixes[2].pk})

    def test_get_child_prefixes(self):
        vrfs = VRF.objects.all()[:3]
        prefixes = (
            Prefix.objects.create(prefix=netaddr.IPNetwork("10.0.0.0/16"), status=Prefix.STATUS_CONTAINER),
            Prefix.objects.create(prefix=netaddr.IPNetwork("10.0.0.0/24"), vrf=None),
            Prefix.objects.create(prefix=netaddr.IPNetwork("10.0.1.0/24"), vrf=vrfs[0]),
            Prefix.objects.create(prefix=netaddr.IPNetwork("10.0.2.0/24"), vrf=vrfs[1]),
            Prefix.objects.create(prefix=netaddr.IPNetwork("10.0.3.0/24"), vrf=vrfs[2]),
        )
        child_prefix_pks = {p.pk for p in prefixes[0].get_child_prefixes()}

        # Global container should return all children
        self.assertSetEqual(
            child_prefix_pks,
            {prefixes[1].pk, prefixes[2].pk, prefixes[3].pk, prefixes[4].pk},
        )

        prefixes[0].vrf = vrfs[0]
        prefixes[0].save()
        child_prefix_pks = {p.pk for p in prefixes[0].get_child_prefixes()}

        # VRF container is limited to its own VRF
        self.assertSetEqual(child_prefix_pks, {prefixes[2].pk})

    def test_get_child_ips(self):
        vrfs = VRF.objects.all()[:3]
        parent_prefix = Prefix.objects.create(prefix=netaddr.IPNetwork("10.0.0.0/16"), status=Prefix.STATUS_CONTAINER)
        ips = (
            IPAddress.objects.create(address=netaddr.IPNetwork("10.0.0.1/24"), vrf=None),
            IPAddress.objects.create(address=netaddr.IPNetwork("10.0.1.1/24"), vrf=vrfs[0]),
            IPAddress.objects.create(address=netaddr.IPNetwork("10.0.2.1/24"), vrf=vrfs[1]),
            IPAddress.objects.create(address=netaddr.IPNetwork("10.0.3.1/24"), vrf=vrfs[2]),
        )
        child_ip_pks = {p.pk for p in parent_prefix.get_child_ips()}

        # Global container should return all children
        self.assertSetEqual(child_ip_pks, {ips[0].pk, ips[1].pk, ips[2].pk, ips[3].pk})

        parent_prefix.vrf = vrfs[0]
        parent_prefix.save()
        child_ip_pks = {p.pk for p in parent_prefix.get_child_ips()}

        # VRF container is limited to its own VRF
        self.assertSetEqual(child_ip_pks, {ips[1].pk})

        # Make sure /31 is handled correctly
        parent_prefix_31 = Prefix.objects.create(
            prefix=netaddr.IPNetwork("10.0.4.0/31"), status=Prefix.STATUS_CONTAINER
        )
        ips_31 = (
            IPAddress.objects.create(address=netaddr.IPNetwork("10.0.4.0/31"), vrf=None),
            IPAddress.objects.create(address=netaddr.IPNetwork("10.0.4.1/31"), vrf=None),
        )

        child_ip_pks = {p.pk for p in parent_prefix_31.get_child_ips()}
        self.assertSetEqual(child_ip_pks, {ips_31[0].pk, ips_31[1].pk})

    def test_get_available_prefixes(self):

        prefixes = Prefix.objects.bulk_create(
            (
                Prefix(prefix=netaddr.IPNetwork("10.0.0.0/16")),  # Parent prefix
                Prefix(prefix=netaddr.IPNetwork("10.0.0.0/20")),
                Prefix(prefix=netaddr.IPNetwork("10.0.32.0/20")),
                Prefix(prefix=netaddr.IPNetwork("10.0.128.0/18")),
            )
        )
        missing_prefixes = netaddr.IPSet(
            [
                netaddr.IPNetwork("10.0.16.0/20"),
                netaddr.IPNetwork("10.0.48.0/20"),
                netaddr.IPNetwork("10.0.64.0/18"),
                netaddr.IPNetwork("10.0.192.0/18"),
            ]
        )
        available_prefixes = prefixes[0].get_available_prefixes()

        self.assertEqual(available_prefixes, missing_prefixes)

    def test_get_available_ips(self):

        parent_prefix = Prefix.objects.create(prefix=netaddr.IPNetwork("10.0.0.0/28"))
        IPAddress.objects.bulk_create(
            (
                IPAddress(address=netaddr.IPNetwork("10.0.0.1/26")),
                IPAddress(address=netaddr.IPNetwork("10.0.0.3/26")),
                IPAddress(address=netaddr.IPNetwork("10.0.0.5/26")),
                IPAddress(address=netaddr.IPNetwork("10.0.0.7/26")),
                IPAddress(address=netaddr.IPNetwork("10.0.0.9/26")),
                IPAddress(address=netaddr.IPNetwork("10.0.0.11/26")),
                IPAddress(address=netaddr.IPNetwork("10.0.0.13/26")),
            )
        )
        missing_ips = netaddr.IPSet(
            [
                "10.0.0.2/32",
                "10.0.0.4/32",
                "10.0.0.6/32",
                "10.0.0.8/32",
                "10.0.0.10/32",
                "10.0.0.12/32",
                "10.0.0.14/32",
            ]
        )
        available_ips = parent_prefix.get_available_ips()

        self.assertEqual(available_ips, missing_ips)

    def test_get_first_available_prefix(self):

        prefixes = Prefix.objects.bulk_create(
            (
                Prefix(prefix=netaddr.IPNetwork("10.0.0.0/16")),  # Parent prefix
                Prefix(prefix=netaddr.IPNetwork("10.0.0.0/24")),
                Prefix(prefix=netaddr.IPNetwork("10.0.1.0/24")),
                Prefix(prefix=netaddr.IPNetwork("10.0.2.0/24")),
            )
        )
        self.assertEqual(prefixes[0].get_first_available_prefix(), netaddr.IPNetwork("10.0.3.0/24"))

        Prefix.objects.create(prefix=netaddr.IPNetwork("10.0.3.0/24"))
        self.assertEqual(prefixes[0].get_first_available_prefix(), netaddr.IPNetwork("10.0.4.0/22"))

    def test_get_first_available_ip(self):

        parent_prefix = Prefix.objects.create(prefix=netaddr.IPNetwork("10.0.0.0/24"))
        IPAddress.objects.bulk_create(
            (
                IPAddress(address=netaddr.IPNetwork("10.0.0.1/24")),
                IPAddress(address=netaddr.IPNetwork("10.0.0.2/24")),
                IPAddress(address=netaddr.IPNetwork("10.0.0.3/24")),
            )
        )
        self.assertEqual(parent_prefix.get_first_available_ip(), "10.0.0.4/24")

        IPAddress.objects.create(address=netaddr.IPNetwork("10.0.0.4/24"))
        self.assertEqual(parent_prefix.get_first_available_ip(), "10.0.0.5/24")

    def test_get_utilization(self):

        # Container Prefix
        prefix = Prefix.objects.create(prefix=netaddr.IPNetwork("10.0.0.0/24"), status=Prefix.STATUS_CONTAINER)
        Prefix.objects.bulk_create(
            (
                Prefix(prefix=netaddr.IPNetwork("10.0.0.0/26")),
                Prefix(prefix=netaddr.IPNetwork("10.0.0.128/26")),
            )
        )
        self.assertEqual(prefix.get_utilization(), (128, 256))

        # IPv4 Non-container Prefix /24
        prefix.status = self.statuses.get(slug="active")
        prefix.save()
        IPAddress.objects.bulk_create(
            # Create 32 IPAddresses within the Prefix
            [IPAddress(address=netaddr.IPNetwork(f"10.0.0.{i}/24")) for i in range(1, 33)]
        )
        # Create IPAddress objects for network and broadcast addresses
        IPAddress.objects.bulk_create(
            (IPAddress(address=netaddr.IPNetwork("10.0.0.0/32")), IPAddress(address=netaddr.IPNetwork("10.0.0.255/32")))
        )
        self.assertEqual(prefix.get_utilization(), (32, 254))

        # Change prefix to a pool, network and broadcast address will count toward numerator and denominator in utilization
        prefix.is_pool = True
        prefix.save()
        self.assertEqual(prefix.get_utilization(), (34, 256))

        # IPv4 Non-container Prefix /31, network and broadcast addresses count toward utilization
        prefix = Prefix.objects.create(prefix="10.0.1.0/31")
        IPAddress.objects.bulk_create(
            (IPAddress(address=netaddr.IPNetwork("10.0.1.0/32")), IPAddress(address=netaddr.IPNetwork("10.0.1.1/32")))
        )
        self.assertEqual(prefix.get_utilization(), (2, 2))

        # IPv6 Non-container Prefix, network and broadcast addresses count toward utilization
        prefix = Prefix.objects.create(prefix="aaaa::/124")
        IPAddress.objects.bulk_create(
            (IPAddress(address=netaddr.IPNetwork("aaaa::0/128")), IPAddress(address=netaddr.IPNetwork("aaaa::f/128")))
        )
        self.assertEqual(prefix.get_utilization(), (2, 16))

    #
    # Uniqueness enforcement tests
    #

    @override_settings(ENFORCE_GLOBAL_UNIQUE=False)
    def test_duplicate_global(self):
        Prefix.objects.create(prefix=netaddr.IPNetwork("192.0.2.0/24"))
        duplicate_prefix = Prefix(prefix=netaddr.IPNetwork("192.0.2.0/24"))
        self.assertIsNone(duplicate_prefix.clean())

    @override_settings(ENFORCE_GLOBAL_UNIQUE=True)
    def test_duplicate_global_unique(self):
        Prefix.objects.create(prefix=netaddr.IPNetwork("192.0.2.0/24"))
        duplicate_prefix = Prefix(prefix=netaddr.IPNetwork("192.0.2.0/24"))
        self.assertRaises(ValidationError, duplicate_prefix.clean)

    def test_duplicate_vrf(self):
        vrf = VRF.objects.filter(enforce_unique=False).first()
        Prefix.objects.create(vrf=vrf, prefix=netaddr.IPNetwork("192.0.2.0/24"))
        duplicate_prefix = Prefix(vrf=vrf, prefix=netaddr.IPNetwork("192.0.2.0/24"))
        self.assertIsNone(duplicate_prefix.clean())

    def test_duplicate_vrf_unique(self):
        vrf = VRF.objects.filter(enforce_unique=True).first()
        Prefix.objects.create(vrf=vrf, prefix=netaddr.IPNetwork("192.0.2.0/24"))
        duplicate_prefix = Prefix(vrf=vrf, prefix=netaddr.IPNetwork("192.0.2.0/24"))
        self.assertRaises(ValidationError, duplicate_prefix.clean)


class TestIPAddress(TestCase):
    def test_get_duplicates(self):
        ips = (
            IPAddress.objects.create(address=netaddr.IPNetwork("192.0.2.1/24")),
            IPAddress.objects.create(address=netaddr.IPNetwork("192.0.2.1/24")),
            IPAddress.objects.create(address=netaddr.IPNetwork("192.0.2.1/24")),
        )
        duplicate_ip_pks = [p.pk for p in ips[0].get_duplicates()]

        self.assertSetEqual(set(duplicate_ip_pks), {ips[1].pk, ips[2].pk})

    #
    # Uniqueness enforcement tests
    #

    @override_settings(ENFORCE_GLOBAL_UNIQUE=False)
    def test_duplicate_global(self):
        IPAddress.objects.create(address=netaddr.IPNetwork("192.0.2.1/24"))
        duplicate_ip = IPAddress(address=netaddr.IPNetwork("192.0.2.1/24"))
        self.assertIsNone(duplicate_ip.clean())

    @override_settings(ENFORCE_GLOBAL_UNIQUE=True)
    def test_duplicate_global_unique(self):
        IPAddress.objects.create(address=netaddr.IPNetwork("192.0.2.1/24"))
        duplicate_ip = IPAddress(address=netaddr.IPNetwork("192.0.2.1/24"))
        self.assertRaises(ValidationError, duplicate_ip.clean)

    def test_duplicate_vrf(self):
        vrf = VRF.objects.filter(enforce_unique=False).first()
        IPAddress.objects.create(vrf=vrf, address=netaddr.IPNetwork("192.0.2.1/24"))
        duplicate_ip = IPAddress(vrf=vrf, address=netaddr.IPNetwork("192.0.2.1/24"))
        self.assertIsNone(duplicate_ip.clean())

    def test_duplicate_vrf_unique(self):
        vrf = VRF.objects.filter(enforce_unique=True).first()
        IPAddress.objects.create(vrf=vrf, address=netaddr.IPNetwork("192.0.2.1/24"))
        duplicate_ip = IPAddress(vrf=vrf, address=netaddr.IPNetwork("192.0.2.1/24"))
        self.assertRaises(ValidationError, duplicate_ip.clean)

    @override_settings(ENFORCE_GLOBAL_UNIQUE=True)
    def test_duplicate_nonunique_role(self):
        IPAddress.objects.create(
            address=netaddr.IPNetwork("192.0.2.1/24"),
            role=IPAddressRoleChoices.ROLE_VIP,
        )
        IPAddress.objects.create(
            address=netaddr.IPNetwork("192.0.2.1/24"),
            role=IPAddressRoleChoices.ROLE_VIP,
        )

    def test_multiple_nat_outside(self):
        """
        Test suite to test supporing multiple nat_inside related fields.

        Includes tests for legacy getter/setter for nat_outside.
        """

        # Setup mimicked legacy data model relationships: 1-to-1
        nat_inside = IPAddress.objects.create(address=netaddr.IPNetwork("192.168.0.1/24"))
        nat_outside1 = IPAddress.objects.create(address=netaddr.IPNetwork("192.0.2.1/24"), nat_inside=nat_inside)
        nat_inside.refresh_from_db()

        # Assert legacy getter behaves as expected for backwards compatibility, and that FK relationship works
        self.assertEqual(nat_inside.nat_outside, nat_outside1)
        self.assertEqual(nat_inside.nat_outside_list.count(), 1)
        self.assertEqual(nat_inside.nat_outside_list.first(), nat_outside1)

        # Create unassigned IPAddress
        nat_outside2 = IPAddress.objects.create(address=netaddr.IPNetwork("192.0.2.2/24"))
        nat_inside.nat_outside = nat_outside2
        nat_inside.refresh_from_db()

        # Test legacy setter behaves as expected for backwards compatibility and that previous FK relationship removed
        self.assertEqual(nat_inside.nat_outside, nat_outside2)
        self.assertEqual(nat_inside.nat_outside_list.count(), 1)
        self.assertEqual(nat_inside.nat_outside_list.first(), nat_outside2)

        # Create IPAddress with nat_inside assigned, setting up current 1-to-many relationship
        nat_outside3 = IPAddress.objects.create(address=netaddr.IPNetwork("192.0.2.3/24"), nat_inside=nat_inside)
        nat_inside.refresh_from_db()

        # Now ensure safeguards are in place when using legacy methods with 1-to-many relationships
        with self.assertRaises(IPAddress.NATOutsideMultipleObjectsReturned):
            nat_inside.nat_outside
        with self.assertRaises(IPAddress.NATOutsideMultipleObjectsReturned):
            nat_inside.nat_outside = nat_outside1

        # Assert FK relationship behaves as expected
        self.assertEqual(nat_inside.nat_outside_list.count(), 2)
        self.assertEqual(nat_inside.nat_outside_list.first(), nat_outside2)
        self.assertEqual(nat_inside.nat_outside_list.last(), nat_outside3)

    @override_settings(ENFORCE_GLOBAL_UNIQUE=True)
    def test_not_null_assigned_object_type_and_null_assigned_object_id(self):
        site = Site.objects.first()
        manufacturer = Manufacturer.objects.create(name="Test Manufacturer 1", slug="test-manufacturer-1")
        devicetype = DeviceType.objects.create(
            manufacturer=manufacturer,
            model="Test Device Type 1",
            slug="test-device-type-1",
        )
        devicerole = DeviceRole.objects.create(name="Test Device Role 1", slug="test-device-role-1", color="ff0000")
        device_status = Status.objects.get_for_model(Device).get(slug="active")
        device = Device.objects.create(
            device_type=devicetype,
            device_role=devicerole,
            name="TestDevice1",
            site=site,
            status=device_status,
        )
        interface = Interface.objects.create(device=device, name="eth0")
        ipaddress_1 = IPAddress(
            address=netaddr.IPNetwork("192.0.2.1/24"),
            role=IPAddressRoleChoices.ROLE_VIP,
            assigned_object_id=interface.id,
        )

        self.assertRaises(ValidationError, ipaddress_1.clean)

        # Test IPAddress.clean() raises no exception if assigned_object_id and assigned_object_type
        # are both provided
        ipaddress_2 = IPAddress(
            address=netaddr.IPNetwork("192.0.2.1/24"),
            role=IPAddressRoleChoices.ROLE_VIP,
            assigned_object_id=interface.id,
            assigned_object_type=ContentType.objects.get_for_model(Interface),
        )
        self.assertIsNone(ipaddress_2.clean())

    def test_create_ip_address_without_slaac_status(self):
        IPAddress.objects.filter(status__slug=IPAddressStatusChoices.STATUS_SLAAC).delete()
        Status.objects.get(slug=IPAddressStatusChoices.STATUS_SLAAC).delete()
        IPAddress.objects.create(address="1.1.1.1/32")
        self.assertTrue(IPAddress.objects.filter(address="1.1.1.1/32").exists())


class TestVLANGroup(TestCase):
    def test_vlan_group_validation(self):
        location_type = LocationType.objects.get(name="Elevator")
        location = Location.objects.filter(location_type=location_type).first()
        group = VLANGroup(name="Group 1", location=location)
        with self.assertRaises(ValidationError) as cm:
            group.validated_save()
        self.assertIn(f'VLAN groups may not associate to locations of type "{location_type.name}"', str(cm.exception))

        location_type.content_types.add(ContentType.objects.get_for_model(VLANGroup))
        site_2 = Site.objects.exclude(pk=location.base_site.pk).last()
        group.site = site_2
        with self.assertRaises(ValidationError) as cm:
            group.validated_save()
        self.assertIn(f'Location "{location.name}" does not belong to site "{site_2.name}"', str(cm.exception))

    def test_get_next_available_vid(self):

        vlangroup = VLANGroup.objects.create(name="VLAN Group 1", slug="vlan-group-1")
        VLAN.objects.bulk_create(
            (
                VLAN(name="VLAN 1", vid=1, group=vlangroup),
                VLAN(name="VLAN 2", vid=2, group=vlangroup),
                VLAN(name="VLAN 3", vid=3, group=vlangroup),
                VLAN(name="VLAN 5", vid=5, group=vlangroup),
            )
        )
        self.assertEqual(vlangroup.get_next_available_vid(), 4)

        VLAN.objects.bulk_create((VLAN(name="VLAN 4", vid=4, group=vlangroup),))
        self.assertEqual(vlangroup.get_next_available_vid(), 6)


class VLANTestCase(TestCase):
    def test_vlan_validation(self):
        location_type = LocationType.objects.get(name="Root")
        location_type.content_types.set([])
        location_type.validated_save()
        location = Location.objects.filter(location_type=location_type).first()
        vlan = VLAN(name="Group 1", vid=1, location=location)
        vlan.status = Status.objects.get_for_model(VLAN).get(slug="active")
        with self.assertRaises(ValidationError) as cm:
            vlan.validated_save()
        self.assertIn(f'VLANs may not associate to locations of type "{location_type.name}"', str(cm.exception))

        location_type.content_types.add(ContentType.objects.get_for_model(VLAN))
        site_2 = Site.objects.exclude(pk=location.site.pk).first()
        vlan.site = site_2
        with self.assertRaises(ValidationError) as cm:
            vlan.validated_save()
        self.assertIn(f'Location "{location.name}" does not belong to site "{site_2.name}"', str(cm.exception))

        vlan.site = location.site
        group = VLANGroup.objects.create(name="Group 1", site=site_2)
        vlan.group = group
        with self.assertRaises(ValidationError) as cm:
            vlan.validated_save()
        self.assertIn(f"VLAN group must belong to the assigned site ({location.site.name})", str(cm.exception))

        group.site = location.site
        location_2 = Location.objects.create(name="Location 2", location_type=location_type, site=location.site)
        group.location = location_2
        group.save()
        with self.assertRaises(ValidationError) as cm:
            vlan.validated_save()
        self.assertIn(
            f'The assigned group belongs to a location that does not include location "{location.name}"',
            str(cm.exception),
        )
