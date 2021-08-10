import copy
from unittest import skipIf

import netaddr
from django.core.exceptions import ValidationError
from django.db import connection
from django.test import TestCase, override_settings

from nautobot.extras.models import Status
from nautobot.ipam.choices import IPAddressRoleChoices
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
        """"Test `VarbinaryIPField.value_to_string`."""
        # value_to_string calls _parse_address so no need for negative tests here.
        self.assertEqual(self.field.value_to_string(self.prefix), self.network)

    def test_parse_address_success(self):
        """"Test `VarbinaryIPField._parse_address` PASS."""

        # str => netaddr.IPAddress
        obj = self.field._parse_address(self.prefix.network)
        self.assertEqual(obj, netaddr.IPAddress(self.network))

        # bytes => netaddr.IPAddress
        self.assertEqual(self.field._parse_address(bytes(obj)), obj)

        # int => netaddr.IPAddress
        self.assertEqual(self.field._parse_address(int(obj)), obj)

        # IPAddress => netaddr.IPAddress
        self.assertEqual(self.field._parse_address(obj), obj)

    def test_parse_address_failure(self):
        """"Test `VarbinaryIPField._parse_address` FAIL."""

        bad_inputs = (
            None,
            -42,
            "10.10.10.10/32",  # Prefixes not allowed here
            "310.10.10.10",  # Bad IP
        )
        for bad in bad_inputs:
            self.assertRaises(ValidationError, self.field._parse_address, bad)

    def test_to_python(self):
        """"Test `VarbinaryIPField.to_python`."""

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
        """"Test `VarbinaryIPField.get_db_prep_value`."""

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
        """"Test `VarbinaryIPField.get_db_prep_value` for MySQL."""

        # MySQL uses raw `bytes`
        prepped = self.field.get_db_prep_value(self.network, connection)
        manual = bytes(self.network_packed)
        self.assertEqual(prepped, manual)


class TestAggregate(TestCase):
    def test_get_utilization(self):
        rir = RIR.objects.create(name="RIR 1", slug="rir-1")
        aggregate = Aggregate(prefix=netaddr.IPNetwork("10.0.0.0/8"), rir=rir)
        aggregate.save()

        # 25% utilization
        Prefix.objects.bulk_create(
            (
                Prefix(prefix=netaddr.IPNetwork("10.0.0.0/12")),
                Prefix(prefix=netaddr.IPNetwork("10.16.0.0/12")),
                Prefix(prefix=netaddr.IPNetwork("10.32.0.0/12")),
                Prefix(prefix=netaddr.IPNetwork("10.48.0.0/12")),
            )
        )
        self.assertEqual(aggregate.get_utilization(), (4194304, 16777216))

        # 50% utilization
        Prefix.objects.bulk_create((Prefix(prefix=netaddr.IPNetwork("10.64.0.0/10")),))
        self.assertEqual(aggregate.get_utilization(), (8388608, 16777216))

        # 100% utilization
        Prefix.objects.bulk_create((Prefix(prefix=netaddr.IPNetwork("10.128.0.0/9")),))
        self.assertEqual(aggregate.get_utilization(), (16777216, 16777216))


class TestPrefix(TestCase):
    def setUp(self):
        super().setUp()
        self.statuses = Status.objects.get_for_model(Prefix)

    def test_get_duplicates(self):
        prefixes = (
            Prefix.objects.create(prefix=netaddr.IPNetwork("192.0.2.0/24")),
            Prefix.objects.create(prefix=netaddr.IPNetwork("192.0.2.0/24")),
            Prefix.objects.create(prefix=netaddr.IPNetwork("192.0.2.0/24")),
        )
        duplicate_prefix_pks = [p.pk for p in prefixes[0].get_duplicates()]

        self.assertSetEqual(set(duplicate_prefix_pks), {prefixes[1].pk, prefixes[2].pk})

    def test_get_child_prefixes(self):
        vrfs = (
            VRF.objects.create(name="VRF 1"),
            VRF.objects.create(name="VRF 2"),
            VRF.objects.create(name="VRF 3"),
        )
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
        vrfs = (
            VRF.objects.create(name="VRF 1"),
            VRF.objects.create(name="VRF 2"),
            VRF.objects.create(name="VRF 3"),
        )
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

        # Non-container Prefix
        prefix.status = self.statuses.get(slug="active")
        prefix.save()
        IPAddress.objects.bulk_create(
            # Create 32 IPAddresses within the Prefix
            [IPAddress(address=netaddr.IPNetwork("10.0.0.{}/24".format(i))) for i in range(1, 33)]
        )
        self.assertEqual(prefix.get_utilization(), (32, 254))

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
        vrf = VRF.objects.create(name="Test", rd="1:1", enforce_unique=False)
        Prefix.objects.create(vrf=vrf, prefix=netaddr.IPNetwork("192.0.2.0/24"))
        duplicate_prefix = Prefix(vrf=vrf, prefix=netaddr.IPNetwork("192.0.2.0/24"))
        self.assertIsNone(duplicate_prefix.clean())

    def test_duplicate_vrf_unique(self):
        vrf = VRF.objects.create(name="Test", rd="1:1", enforce_unique=True)
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
        vrf = VRF.objects.create(name="Test", rd="1:1", enforce_unique=False)
        IPAddress.objects.create(vrf=vrf, address=netaddr.IPNetwork("192.0.2.1/24"))
        duplicate_ip = IPAddress(vrf=vrf, address=netaddr.IPNetwork("192.0.2.1/24"))
        self.assertIsNone(duplicate_ip.clean())

    def test_duplicate_vrf_unique(self):
        vrf = VRF.objects.create(name="Test", rd="1:1", enforce_unique=True)
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


class TestVLANGroup(TestCase):
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
