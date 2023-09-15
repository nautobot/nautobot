from unittest import skipIf

import netaddr
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.db import connection, IntegrityError
from django.db.models import ProtectedError
from django.test import TestCase

from nautobot.core.testing.models import ModelTestCases
from nautobot.dcim import choices as dcim_choices
from nautobot.dcim.models import Device, DeviceType, Interface, Location, LocationType
from nautobot.extras.models import Role, Status
from nautobot.ipam.choices import IPAddressTypeChoices, PrefixTypeChoices, ServiceProtocolChoices
from nautobot.ipam.models import (
    IPAddress,
    IPAddressToInterface,
    Namespace,
    Prefix,
    RIR,
    RouteTarget,
    Service,
    VLAN,
    VLANGroup,
    VRF,
)
from nautobot.virtualization.models import Cluster, ClusterType, VirtualMachine, VMInterface


class IPAddressToInterfaceTest(TestCase):
    """Tests for `nautobot.ipam.models.IPAddressToInterface`."""

    @classmethod
    def setUpTestData(cls):
        cls.namespace = Namespace.objects.first()
        cls.status = Status.objects.get(name="Active")
        cls.prefix = Prefix.objects.create(prefix="192.0.2.0/24", status=cls.status, namespace=cls.namespace)
        cls.test_device = Device.objects.create(
            name="device1",
            role=Role.objects.get_for_model(Device).first(),
            device_type=DeviceType.objects.first(),
            location=Location.objects.get_for_model(Device).first(),
            status=Status.objects.get_for_model(Device).first(),
        )
        int_status = Status.objects.get_for_model(Interface).first()
        cls.test_int1 = Interface.objects.create(
            device=cls.test_device,
            name="int1",
            status=int_status,
            type=dcim_choices.InterfaceTypeChoices.TYPE_1GE_FIXED,
        )
        cls.test_int2 = Interface.objects.create(
            device=cls.test_device,
            name="int2",
            status=int_status,
            type=dcim_choices.InterfaceTypeChoices.TYPE_1GE_FIXED,
        )
        cluster_type = ClusterType.objects.create(name="Cluster Type 1")
        cluster = Cluster.objects.create(name="cluster1", cluster_type=cluster_type)
        vmint_status = Status.objects.get_for_model(VMInterface).first()
        cls.test_vm = VirtualMachine.objects.create(
            name="vm1",
            cluster=cluster,
            status=Status.objects.get_for_model(VirtualMachine).first(),
        )
        cls.test_vmint1 = VMInterface.objects.create(
            name="vmint1",
            virtual_machine=cls.test_vm,
            status=vmint_status,
        )
        cls.test_vmint2 = VMInterface.objects.create(
            name="vmint2",
            virtual_machine=cls.test_vm,
            status=vmint_status,
        )

    def test_removing_ip_addresses_containing_host_device_primary_ip_nullifies_host_device_primary_ip(self):
        """
        Test that removing IPAddress from an Interface that is the host Device's primary ip nullifies the primary_ip field.
        """
        dev_ip_addr = IPAddress.objects.last()
        self.test_int1.add_ip_addresses(dev_ip_addr)
        self.test_int2.add_ip_addresses(dev_ip_addr)
        ip_to_interface_1 = IPAddressToInterface.objects.get(interface=self.test_int1, ip_address=dev_ip_addr)
        ip_to_interface_2 = IPAddressToInterface.objects.get(interface=self.test_int2, ip_address=dev_ip_addr)
        self.assertIsNotNone(ip_to_interface_1)
        self.assertIsNotNone(ip_to_interface_2)
        if dev_ip_addr.ip_version == 4:
            self.test_device.primary_ip4 = dev_ip_addr
        else:
            self.test_device.primary_ip6 = dev_ip_addr
        self.test_device.save()
        # You can delete IPAddress from the first Interface without nullifying primary_ip field
        # Since the second Interface still contains that IPAddress
        self.test_int1.remove_ip_addresses(dev_ip_addr)
        self.test_device.refresh_from_db()
        if dev_ip_addr.ip_version == 4:
            self.assertEqual(self.test_device.primary_ip4, dev_ip_addr)
        else:
            self.assertEqual(self.test_device.primary_ip6, dev_ip_addr)
        # This operation should nullify the device's primary_ip field since test_int2 is the only Interface
        # that contains the primary ip
        self.test_int2.remove_ip_addresses(dev_ip_addr)
        self.test_device.refresh_from_db()
        if dev_ip_addr.ip_version == 4:
            self.assertEqual(self.test_device.primary_ip4, None)
        else:
            self.assertEqual(self.test_device.primary_ip6, None)

    def test_removing_ip_addresses_containing_host_vm_primary_ip_nullifies_host_vm_primary_ip(self):
        """
        Test that removing IPAddress from an Interface that is the host Virtual Machine's primary ip nullifies the primary_ip field.
        """
        vm_ip_addr = IPAddress.objects.last()
        self.test_vmint1.add_ip_addresses(vm_ip_addr)
        self.test_vmint2.add_ip_addresses(vm_ip_addr)
        ip_to_vminterface_1 = IPAddressToInterface.objects.get(vm_interface=self.test_vmint1, ip_address=vm_ip_addr)
        ip_to_vminterface_2 = IPAddressToInterface.objects.get(vm_interface=self.test_vmint2, ip_address=vm_ip_addr)
        self.assertIsNotNone(ip_to_vminterface_1)
        self.assertIsNotNone(ip_to_vminterface_2)
        if vm_ip_addr.ip_version == 4:
            self.test_vm.primary_ip4 = vm_ip_addr
        else:
            self.test_vm.primary_ip6 = vm_ip_addr
        self.test_vm.save()
        # You can delete IPAddress from the first Interface without nullifying primary_ip field
        # Since the second Interface still contains that IPAddress
        self.test_vmint1.remove_ip_addresses(vm_ip_addr)
        self.test_vm.refresh_from_db()
        if vm_ip_addr.ip_version == 4:
            self.assertEqual(self.test_vm.primary_ip4, vm_ip_addr)
        else:
            self.assertEqual(self.test_vm.primary_ip6, vm_ip_addr)
        # This operation should nullify the device's primary_ip field since test_int2 is the only Interface
        # that contains the primary ip
        self.test_vmint2.remove_ip_addresses(vm_ip_addr)
        self.test_vm.refresh_from_db()
        if vm_ip_addr.ip_version == 4:
            self.assertEqual(self.test_vm.primary_ip4, None)
        else:
            self.assertEqual(self.test_vm.primary_ip6, None)

    def test_ip_address_to_interface_uniqueness_constraint(self):
        ip_addr = IPAddress.objects.create(address="192.0.2.1/24", status=self.status, namespace=self.namespace)
        IPAddressToInterface.objects.create(interface=self.test_int1, ip_address=ip_addr)
        with self.assertRaises(ValidationError):
            IPAddressToInterface.objects.create(
                vm_interface=self.test_vmint1, interface=self.test_int1, ip_address=ip_addr
            )
        IPAddressToInterface.objects.create(vm_interface=self.test_vmint1, ip_address=ip_addr)
        with self.assertRaises(ValidationError):
            IPAddressToInterface.objects.create(vm_interface=self.test_vmint1, ip_address=ip_addr)

    def test_pre_save_signal_invoked_on_ip_address_to_interface_manual_creation(self):
        ip_addr = IPAddress.objects.create(address="192.0.2.1/24", status=self.status, namespace=self.namespace)
        with self.assertRaises(ValidationError) as cm:
            IPAddressToInterface.objects.create(
                vm_interface=self.test_vmint1, interface=self.test_int1, ip_address=ip_addr
            )
        self.assertIn(
            "Cannot use a single instance to associate to both an Interface and a VMInterface.", str(cm.exception)
        )
        with self.assertRaises(ValidationError) as cm:
            IPAddressToInterface.objects.create(vm_interface=None, interface=None, ip_address=ip_addr)
        self.assertIn("Must associate to either an Interface or a VMInterface.", str(cm.exception))


class TestVarbinaryIPField(TestCase):
    """Tests for `nautobot.ipam.fields.VarbinaryIPField`."""

    @classmethod
    def setUpTestData(cls):
        # Field is a VarbinaryIPField we'll use to test.
        cls.namespace = Namespace.objects.first()
        cls.status = Status.objects.get(name="Active")
        cls.prefix = Prefix.objects.create(prefix="10.0.0.0/24", status=cls.status, namespace=cls.namespace)
        cls.field = cls.prefix._meta.get_field("network")
        cls.network = cls.prefix.network
        cls.network_packed = bytes(cls.prefix.prefix.network)

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


class TestNamespace(ModelTestCases.BaseModelTestCase):
    model = Namespace


class TestPrefix(ModelTestCases.BaseModelTestCase):
    model = Prefix

    def setUp(self):
        super().setUp()
        # With advent of `Prefix.parent`, Prefixes can't just be bulk deleted without clearing their
        # `parent` first in an `update()` query which doesn't call `save()` or `fire `(pre|post)_save` signals.
        IPAddress.objects.update(parent=None)
        IPAddress.objects.all().delete()
        Prefix.objects.update(parent=None)
        Prefix.objects.all().delete()
        self.namespace = Namespace.objects.first()
        self.statuses = Status.objects.get_for_model(Prefix)
        self.status = self.statuses.first()
        self.status.content_types.add(ContentType.objects.get_for_model(IPAddress))
        self.root = Prefix.objects.create(
            prefix="101.102.0.0/24", status=self.status, namespace=self.namespace, type=PrefixTypeChoices.TYPE_CONTAINER
        )
        self.parent = Prefix.objects.create(
            prefix="101.102.0.0/25", status=self.status, namespace=self.namespace, type=PrefixTypeChoices.TYPE_CONTAINER
        )
        self.child1 = Prefix.objects.create(prefix="101.102.0.0/26", status=self.status, namespace=self.namespace)
        self.child2 = Prefix.objects.create(prefix="101.102.0.64/26", status=self.status, namespace=self.namespace)

    def test_prefix_validation(self):
        location_type = LocationType.objects.get(name="Room")
        location = Location.objects.filter(location_type=location_type).first()
        prefix = Prefix(prefix="192.0.2.0/24", location=location, status=self.statuses[0])
        with self.assertRaises(ValidationError) as cm:
            prefix.validated_save()
        self.assertIn(f'Prefixes may not associate to locations of type "{location_type.name}"', str(cm.exception))

    def test_tree_methods(self):
        """Test the various tree methods work as expected."""

        # supernets()
        self.assertEqual(list(self.root.supernets()), [])
        self.assertEqual(list(self.child1.supernets()), [self.root, self.parent])
        self.assertEqual(list(self.child1.supernets(include_self=True)), [self.root, self.parent, self.child1])
        self.assertEqual(list(self.child1.supernets(direct=True)), [self.parent])

        # subnets()
        self.assertEqual(list(self.root.subnets()), [self.parent, self.child1, self.child2])
        self.assertEqual(list(self.root.subnets(direct=True)), [self.parent])
        self.assertEqual(list(self.root.subnets(include_self=True)), [self.root, self.parent, self.child1, self.child2])

        # is_child_node()
        self.assertFalse(self.root.is_child_node())
        self.assertTrue(self.parent.is_child_node())
        self.assertTrue(self.child1.is_child_node())

        # is_leaf_node()
        self.assertFalse(self.root.is_leaf_node())
        self.assertFalse(self.parent.is_leaf_node())
        self.assertTrue(self.child1.is_leaf_node())

        # is_root_node()
        self.assertTrue(self.root.is_root_node())
        self.assertFalse(self.parent.is_leaf_node())
        self.assertFalse(self.child1.is_root_node())

        # ancestors()
        self.assertEqual(list(self.child1.ancestors()), [self.root, self.parent])
        self.assertEqual(list(self.child1.ancestors(ascending=True)), [self.parent, self.root])
        self.assertEqual(list(self.child1.ancestors(include_self=True)), [self.root, self.parent, self.child1])

        # children.all()
        self.assertEqual(list(self.parent.children.all()), [self.child1, self.child2])

        # descendants()
        self.assertEqual(list(self.root.descendants()), [self.parent, self.child1, self.child2])
        self.assertEqual(
            list(self.root.descendants(include_self=True)), [self.root, self.parent, self.child1, self.child2]
        )

        # root()
        self.assertEqual(self.child1.root(), self.root)
        self.assertIsNone(self.root.root())

        # siblings()
        self.assertEqual(list(self.child1.siblings()), [self.child2])
        self.assertEqual(list(self.child1.siblings(include_self=True)), [self.child1, self.child2])
        parent2 = Prefix.objects.create(prefix="101.102.0.128/25", status=self.status, namespace=self.namespace)
        self.assertEqual(list(self.parent.siblings()), [parent2])
        self.assertEqual(list(self.parent.siblings(include_self=True)), [self.parent, parent2])

    def test_reparenting(self):
        """Test that reparenting algorithm works in its most basic form."""
        # tree hierarchy
        self.assertIsNone(self.root.parent)
        self.assertEqual(self.parent.parent, self.root)
        self.assertEqual(self.child1.parent, self.parent)

        # Delete the parent (/25); child1/child2 now have root (/24) as their parent.
        num_deleted, _ = self.parent.delete()
        self.assertEqual(num_deleted, 1)

        self.assertEqual(list(self.root.children.all()), [self.child1, self.child2])
        self.child1.refresh_from_db()
        self.child2.refresh_from_db()
        self.assertEqual(self.child1.parent, self.root)
        self.assertEqual(self.child2.parent, self.root)
        self.assertEqual(list(self.child1.ancestors()), [self.root])

        # Add /25 back in as a parent and assert that child1/child2 now have it as their parent, and
        # /24 is its parent.
        self.parent.save()  # This creates another Prefix using the same instance.
        self.child1.refresh_from_db()
        self.child2.refresh_from_db()
        self.assertEqual(self.child1.parent, self.parent)
        self.assertEqual(self.child2.parent, self.parent)
        self.assertEqual(list(self.child1.ancestors()), [self.root, self.parent])

        # Now let's create some duplicates in another Namespace and perform the same tests.

        namespace = Namespace.objects.exclude(id=self.namespace.id).first()
        root = Prefix.objects.create(
            prefix="101.102.0.0/24", status=self.status, namespace=namespace, type=PrefixTypeChoices.TYPE_CONTAINER
        )
        parent = Prefix.objects.create(
            prefix="101.102.0.0/25", status=self.status, namespace=namespace, type=PrefixTypeChoices.TYPE_CONTAINER
        )
        child1 = Prefix.objects.create(prefix="101.102.0.0/26", status=self.status, namespace=namespace)
        child2 = Prefix.objects.create(prefix="101.102.0.64/26", status=self.status, namespace=namespace)

        # tree hierarchy
        self.assertIsNone(root.parent)
        self.assertEqual(parent.parent, root)
        self.assertEqual(child1.parent, parent)

        # Delete the parent (/25); child1/child2 now have root (/24) as their parent.
        num_deleted, _ = parent.delete()
        self.assertEqual(num_deleted, 1)

        self.assertEqual(list(root.children.all()), [child1, child2])
        child1.refresh_from_db()
        child2.refresh_from_db()
        self.assertEqual(child1.parent, root)
        self.assertEqual(child2.parent, root)
        self.assertEqual(list(child1.ancestors()), [root])

        # Add /25 back in as a parent and assert that child1/child2 now have it as their parent, and
        # /24 is its parent.
        parent.save()  # This creates another Prefix using the same instance.
        child1.refresh_from_db()
        child2.refresh_from_db()
        self.assertEqual(child1.parent, parent)
        self.assertEqual(child2.parent, parent)
        self.assertEqual(list(child1.ancestors()), [root, parent])

    def test_descendants(self):
        prefixes = (
            Prefix.objects.create(
                prefix="10.0.0.0/16",
                type=PrefixTypeChoices.TYPE_CONTAINER,
                status=self.status,
                namespace=self.namespace,
            ),
            Prefix.objects.create(prefix="10.0.0.0/24", status=self.status, namespace=self.namespace),
            Prefix.objects.create(prefix="10.0.1.0/24", status=self.status, namespace=self.namespace),
            Prefix.objects.create(prefix="10.0.2.0/24", status=self.status, namespace=self.namespace),
            Prefix.objects.create(prefix="10.0.3.0/24", status=self.status, namespace=self.namespace),
        )
        prefix_pks = {p.pk for p in prefixes[1:]}
        child_prefix_pks = {p.pk for p in prefixes[0].descendants()}

        # Global container should return all children
        self.assertSetEqual(child_prefix_pks, prefix_pks)

    def test_child_ip_addresses(self):
        parent_prefix = Prefix.objects.create(prefix="10.0.0.0/16", status=self.status, namespace=self.namespace)
        ips = (
            IPAddress.objects.create(address="10.0.0.1/24", status=self.status, namespace=self.namespace),
            IPAddress.objects.create(address="10.0.1.1/24", status=self.status, namespace=self.namespace),
            IPAddress.objects.create(address="10.0.2.1/24", status=self.status, namespace=self.namespace),
            IPAddress.objects.create(address="10.0.3.1/24", status=self.status, namespace=self.namespace),
        )
        child_ip_pks = {p.pk for p in parent_prefix.ip_addresses.all()}

        # Global container should return all children
        self.assertSetEqual(child_ip_pks, {ips[0].pk, ips[1].pk, ips[2].pk, ips[3].pk})

        # Make sure /31 is handled correctly
        parent_prefix_31 = Prefix.objects.create(prefix="20.0.4.0/31", status=self.status, namespace=self.namespace)
        ips_31 = (
            IPAddress.objects.create(address="20.0.4.0/31", status=self.status, namespace=self.namespace),
            IPAddress.objects.create(address="20.0.4.1/31", status=self.status, namespace=self.namespace),
        )
        child_ip_pks = {p.pk for p in parent_prefix_31.ip_addresses.all()}
        self.assertSetEqual(child_ip_pks, {ips_31[0].pk, ips_31[1].pk})

    def test_get_available_prefixes(self):
        prefixes = [
            Prefix(
                prefix="10.0.0.0/16",
                status=self.status,
                namespace=self.namespace,
                type=PrefixTypeChoices.TYPE_CONTAINER,
            ),  # Parent prefix
            Prefix(prefix="10.0.0.0/20", status=self.status, namespace=self.namespace),
            Prefix(prefix="10.0.32.0/20", status=self.status, namespace=self.namespace),
            Prefix(prefix="10.0.128.0/18", status=self.status, namespace=self.namespace),
        ]
        [p.save() for p in prefixes]  # pylint: disable=expression-not-assigned
        missing_prefixes = netaddr.IPSet(
            [
                "10.0.16.0/20",
                "10.0.48.0/20",
                "10.0.64.0/18",
                "10.0.192.0/18",
            ]
        )
        available_prefixes = prefixes[0].get_available_prefixes()

        self.assertEqual(available_prefixes, missing_prefixes)

    def test_get_available_ips(self):
        parent_prefix = Prefix.objects.create(prefix="10.0.0.0/28", status=self.status, namespace=self.namespace)
        ip_list = [
            IPAddress(address="10.0.0.1/26", status=self.status, namespace=self.namespace),
            IPAddress(address="10.0.0.3/26", status=self.status, namespace=self.namespace),
            IPAddress(address="10.0.0.5/26", status=self.status, namespace=self.namespace),
            IPAddress(address="10.0.0.7/26", status=self.status, namespace=self.namespace),
            IPAddress(address="10.0.0.9/26", status=self.status, namespace=self.namespace),
            IPAddress(address="10.0.0.11/26", status=self.status, namespace=self.namespace),
            IPAddress(address="10.0.0.13/26", status=self.status, namespace=self.namespace),
        ]
        [i.save() for i in ip_list]  # pylint: disable=expression-not-assigned
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
        prefixes = [
            Prefix(
                prefix="10.0.0.0/16",
                status=self.status,
                namespace=self.namespace,
                type=PrefixTypeChoices.TYPE_CONTAINER,
            ),  # Parent prefix
            Prefix(prefix="10.0.0.0/24", status=self.status, namespace=self.namespace),
            Prefix(prefix="10.0.1.0/24", status=self.status, namespace=self.namespace),
            Prefix(prefix="10.0.2.0/24", status=self.status, namespace=self.namespace),
        ]
        [p.save() for p in prefixes]  # pylint: disable=expression-not-assigned
        self.assertEqual(prefixes[0].get_first_available_prefix(), netaddr.IPNetwork("10.0.3.0/24"))

        Prefix.objects.create(prefix="10.0.3.0/24", status=self.status, namespace=self.namespace)
        self.assertEqual(prefixes[0].get_first_available_prefix(), netaddr.IPNetwork("10.0.4.0/22"))

    def test_get_first_available_ip(self):
        parent_prefix = Prefix.objects.create(prefix="10.0.0.0/24", status=self.status, namespace=self.namespace)
        ip_list = [
            IPAddress(address="10.0.0.1/24", status=self.status, namespace=self.namespace),
            IPAddress(address="10.0.0.2/24", status=self.status, namespace=self.namespace),
            IPAddress(address="10.0.0.3/24", status=self.status, namespace=self.namespace),
        ]
        [i.save() for i in ip_list]  # pylint: disable=expression-not-assigned
        self.assertEqual(parent_prefix.get_first_available_ip(), "10.0.0.4/24")

        IPAddress.objects.create(address="10.0.0.4/24", status=self.status, namespace=self.namespace)
        self.assertEqual(parent_prefix.get_first_available_ip(), "10.0.0.5/24")

    def test_get_utilization(self):
        # Container Prefix
        prefix = Prefix.objects.create(
            prefix="10.0.0.0/24", type=PrefixTypeChoices.TYPE_CONTAINER, status=self.status, namespace=self.namespace
        )
        slash26 = Prefix.objects.create(prefix="10.0.0.0/26", status=self.status, namespace=self.namespace)
        slash25 = Prefix.objects.create(prefix="10.0.0.128/25", status=self.status, namespace=self.namespace)
        self.assertEqual(prefix.get_utilization(), (192, 256))

        # Create 32 IPAddresses within the Prefix
        for i in range(1, 33):
            IPAddress.objects.create(address=f"10.0.0.{i}/32", status=self.status, namespace=self.namespace)

        # The parent prefix utilization does not change because the ip addresses are parented to the child /26 prefix.
        self.assertEqual(prefix.get_utilization(), (192, 256))

        # The /26 will have 32 IPs
        self.assertEqual(slash26.get_utilization(), (32, 62))

        # Create IPAddress objects for network and broadcast addresses
        IPAddress.objects.create(address="10.0.0.0/32", status=self.status, namespace=self.namespace)
        IPAddress.objects.create(address="10.0.0.63/32", status=self.status, namespace=self.namespace)

        # The /26 denominator will change to 64
        self.assertEqual(slash26.get_utilization(), (34, 64))

        # Add a pool, entire pool will count toward numerator in utilization
        pool = Prefix.objects.create(
            prefix="10.0.0.128/30", type=PrefixTypeChoices.TYPE_POOL, status=self.status, namespace=self.namespace
        )
        self.assertEqual(slash25.get_utilization(), (4, 128))

        # When the pool does not overlap with broadcast or network address, the denominator decrements by 2
        pool.network = "10.0.0.132"
        pool.save()
        self.assertEqual(slash25.get_utilization(), (4, 126))

        # IPv4 Non-container Prefix /31, network and broadcast addresses count toward utilization
        prefix = Prefix.objects.create(prefix="10.0.1.0/31", status=self.status, namespace=self.namespace)
        IPAddress.objects.create(address="10.0.1.0/32", status=self.status, namespace=self.namespace)
        IPAddress.objects.create(address="10.0.1.1/32", status=self.status, namespace=self.namespace)
        self.assertEqual(prefix.get_utilization(), (2, 2))

        # IPv6 Non-container Prefix, first and last addresses count toward utilization
        prefix = Prefix.objects.create(prefix="aaab::/124", status=self.status, namespace=self.namespace)
        IPAddress.objects.create(address="aaab::1/128", status=self.status, namespace=self.namespace)
        IPAddress.objects.create(address="aaab::2/128", status=self.status, namespace=self.namespace)
        self.assertEqual(prefix.get_utilization(), (2, 16))

        prefix = Prefix.objects.create(prefix="aaaa::/124", status=self.status, namespace=self.namespace)
        IPAddress.objects.create(address="aaaa::0/128", status=self.status, namespace=self.namespace)
        IPAddress.objects.create(address="aaaa::f/128", status=self.status, namespace=self.namespace)
        self.assertEqual(prefix.get_utilization(), (2, 16))

        # single address prefixes
        prefix = Prefix.objects.create(prefix="cccc::1/128", status=self.status, namespace=self.namespace)
        IPAddress.objects.create(address="cccc::1/128", status=self.status, namespace=self.namespace)
        self.assertEqual(prefix.get_utilization(), (1, 1))
        prefix = Prefix.objects.create(prefix="1.1.1.1/32", status=self.status, namespace=self.namespace)
        IPAddress.objects.create(address="1.1.1.1/32", status=self.status, namespace=self.namespace)
        self.assertEqual(prefix.get_utilization(), (1, 1))

        # Large Prefix
        large_prefix = Prefix.objects.create(
            prefix="22.0.0.0/8", type=PrefixTypeChoices.TYPE_CONTAINER, status=self.status, namespace=self.namespace
        )

        # 25% utilization
        Prefix.objects.create(prefix="22.0.0.0/12", status=self.status, namespace=self.namespace)
        Prefix.objects.create(prefix="22.16.0.0/12", status=self.status, namespace=self.namespace)
        Prefix.objects.create(prefix="22.32.0.0/12", status=self.status, namespace=self.namespace)
        Prefix.objects.create(prefix="22.48.0.0/12", status=self.status, namespace=self.namespace)
        self.assertEqual(large_prefix.get_utilization(), (4194304, 16777216))

        # 50% utilization
        Prefix.objects.create(prefix="22.64.0.0/10", status=self.status, namespace=self.namespace)
        self.assertEqual(large_prefix.get_utilization(), (8388608, 16777216))

        # 100% utilization
        Prefix.objects.create(prefix="22.128.0.0/9", status=self.status, namespace=self.namespace)
        self.assertEqual(large_prefix.get_utilization(), (16777216, 16777216))

        # IPv6 Large Prefix
        large_prefix_v6 = Prefix.objects.create(
            prefix="ab00::/8", type=PrefixTypeChoices.TYPE_CONTAINER, status=self.status, namespace=self.namespace
        )

        # 25% utilization
        Prefix.objects.create(prefix="ab00::/12", status=self.status, namespace=self.namespace)
        Prefix.objects.create(prefix="ab10::/12", status=self.status, namespace=self.namespace)
        Prefix.objects.create(prefix="ab20::/12", status=self.status, namespace=self.namespace)
        Prefix.objects.create(prefix="ab30::/12", status=self.status, namespace=self.namespace)
        self.assertEqual(large_prefix_v6.get_utilization(), (2**118, 2**120))

        # 50% utilization
        Prefix.objects.create(prefix="ab40::/10", status=self.status, namespace=self.namespace)
        self.assertEqual(large_prefix_v6.get_utilization(), (2**119, 2**120))

        # 100% utilization
        Prefix.objects.create(prefix="ab80::/9", status=self.status, namespace=self.namespace)
        self.assertEqual(large_prefix_v6.get_utilization(), (2**120, 2**120))

    #
    # Uniqueness enforcement tests
    #

    def test_duplicate_global_unique(self):
        """Test that duplicate Prefixes in the same Namespace raises an error."""
        Prefix.objects.create(prefix="192.0.2.0/24", status=self.status, namespace=self.namespace)
        duplicate_prefix = Prefix(prefix="192.0.2.0/24", status=self.status, namespace=self.namespace)
        self.assertRaises(ValidationError, duplicate_prefix.full_clean)

    def test_parenting_constraints_on_save(self):
        """Test that Prefix parenting correctly raises validation errors when saving a prefix would create an invalid parent/child relationship."""

        namespace = Namespace.objects.create(name="test_parenting_constraints")
        Prefix.objects.create(
            prefix="10.0.0.0/24", status=self.status, namespace=namespace, type=PrefixTypeChoices.TYPE_CONTAINER
        )
        Prefix.objects.create(
            prefix="11.0.0.0/24", status=self.status, namespace=namespace, type=PrefixTypeChoices.TYPE_NETWORK
        )
        # 3.0 TODO: replace with the commented below once type enforcement is enabled
        # pool_prefix = Prefix.objects.create(
        Prefix.objects.create(
            prefix="12.0.0.0/24", status=self.status, namespace=namespace, type=PrefixTypeChoices.TYPE_POOL
        )

        # 3.0 TODO: uncomment the below tests once type enforcement is enabled

        # with self.assertRaises(ValidationError, msg="Network prefix parent cannot be a network"):
        #     Prefix.objects.create(
        #         prefix="11.0.0.0/30", status=self.status, namespace=namespace, type=PrefixTypeChoices.TYPE_NETWORK
        #     )

        # with self.assertRaises(ValidationError, msg="Network prefix parent cannot be a pool"):
        #     Prefix.objects.create(
        #         prefix="12.0.0.0/30", status=self.status, namespace=namespace, type=PrefixTypeChoices.TYPE_NETWORK
        #     )

        # with self.assertRaises(ValidationError, msg="Container prefix parent cannot be a network"):
        #     Prefix.objects.create(
        #         prefix="11.0.0.0/30", status=self.status, namespace=namespace, type=PrefixTypeChoices.TYPE_CONTAINER
        #     )

        # with self.assertRaises(ValidationError, msg="Container prefix parent cannot be a pool"):
        #     Prefix.objects.create(
        #         prefix="12.0.0.0/30", status=self.status, namespace=namespace, type=PrefixTypeChoices.TYPE_CONTAINER
        #     )

        # with self.assertRaises(ValidationError, msg="Pool prefix parent cannot be a container"):
        #     Prefix.objects.create(
        #         prefix="10.0.0.0/30", status=self.status, namespace=namespace, type=PrefixTypeChoices.TYPE_POOL
        #     )

        # with self.assertRaises(ValidationError, msg="Pool prefix parent cannot be a pool"):
        #     Prefix.objects.create(
        #         prefix="12.0.0.0/30", status=self.status, namespace=namespace, type=PrefixTypeChoices.TYPE_POOL
        #     )

        # with self.assertRaises(
        #     ValidationError, msg="Test that an invalid parent cannot be created (network parenting container)"
        # ):
        #     Prefix.objects.create(
        #         prefix="10.0.0.0/16", status=self.status, namespace=namespace, type=PrefixTypeChoices.TYPE_NETWORK
        #     )

        # with self.assertRaises(
        #     ValidationError, msg="Test that an invalid parent cannot be created (pool parenting container)"
        # ):
        #     Prefix.objects.create(
        #         prefix="10.0.0.0/16", status=self.status, namespace=namespace, type=PrefixTypeChoices.TYPE_POOL
        #     )

        # with self.assertRaises(
        #     ValidationError, msg="Test that an invalid parent cannot be created (network parenting network)"
        # ):
        #     Prefix.objects.create(
        #         prefix="11.0.0.0/16", status=self.status, namespace=namespace, type=PrefixTypeChoices.TYPE_NETWORK
        #     )

        # with self.assertRaises(
        #     ValidationError, msg="Test that an invalid parent cannot be created (pool parenting network)"
        # ):
        #     Prefix.objects.create(
        #         prefix="11.0.0.0/16", status=self.status, namespace=namespace, type=PrefixTypeChoices.TYPE_POOL
        #     )

        # with self.assertRaises(
        #     ValidationError, msg="Test that an invalid parent cannot be created (container parenting pool)"
        # ):
        #     Prefix.objects.create(
        #         prefix="12.0.0.0/16", status=self.status, namespace=namespace, type=PrefixTypeChoices.TYPE_CONTAINER
        #     )

        # with self.assertRaises(
        #     ValidationError, msg="Test that an invalid parent cannot be created (pool parenting pool)"
        # ):
        #     Prefix.objects.create(
        #         prefix="12.0.0.0/16", status=self.status, namespace=namespace, type=PrefixTypeChoices.TYPE_POOL
        #     )

        with self.subTest("Test that valid parents can be created"):
            Prefix.objects.create(
                prefix="12.0.0.0/16", status=self.status, namespace=namespace, type=PrefixTypeChoices.TYPE_NETWORK
            )
            Prefix.objects.create(
                prefix="12.0.0.0/8", status=self.status, namespace=namespace, type=PrefixTypeChoices.TYPE_CONTAINER
            )
            Prefix.objects.create(
                prefix="12.0.0.0/7", status=self.status, namespace=namespace, type=PrefixTypeChoices.TYPE_CONTAINER
            )

        with self.subTest("Test that valid children can be created"):
            Prefix.objects.create(
                prefix="10.0.0.0/25", status=self.status, namespace=namespace, type=PrefixTypeChoices.TYPE_CONTAINER
            )
            Prefix.objects.create(
                prefix="10.0.0.0/26", status=self.status, namespace=namespace, type=PrefixTypeChoices.TYPE_CONTAINER
            )

        # 3.0 TODO: uncomment once type enforcement is enabled
        # with self.assertRaises(
        #     ValidationError,
        #     msg="Test that modifying a prefix's type fails if it would result in an invalid parent/child relationship",
        # ):
        #     pool_prefix.type = PrefixTypeChoices.TYPE_NETWORK
        #     pool_prefix.validated_save()

        with self.subTest(
            "Test that modifying a prefix's type is allowed if it does not create an invalid relationship"
        ):
            child = Prefix.objects.create(
                prefix="10.0.0.0/28", status=self.status, namespace=namespace, type=PrefixTypeChoices.TYPE_NETWORK
            )
            child.type = PrefixTypeChoices.TYPE_CONTAINER
            child.validated_save()

    def test_parenting_constraints_on_delete(self):
        """Test that Prefix parenting correctly raises validation errors when deleting a prefix would create an invalid parent/child relationship."""

        namespace = Namespace.objects.create(name="test_parenting_constraints")
        root = Prefix.objects.create(
            prefix="10.0.0.0/8", status=self.status, namespace=namespace, type=PrefixTypeChoices.TYPE_CONTAINER
        )
        container = Prefix.objects.create(
            prefix="10.0.0.0/16", status=self.status, namespace=namespace, type=PrefixTypeChoices.TYPE_CONTAINER
        )
        network = Prefix.objects.create(
            prefix="10.0.0.0/24", status=self.status, namespace=namespace, type=PrefixTypeChoices.TYPE_NETWORK
        )
        pool = Prefix.objects.create(
            prefix="10.0.0.0/26", status=self.status, namespace=namespace, type=PrefixTypeChoices.TYPE_POOL
        )

        # 3.0 TODO: uncomment once type enforcement is enabled
        # with self.assertRaises(
        #     ProtectedError,
        #     msg="Test that deleting a network prefix that would make a pool prefix's parent a container raises a ProtectedError",
        # ):
        #     network.delete()

        with self.subTest("Test that deleting a parent prefix properly reparents the child prefixes"):
            container.delete()
            root.refresh_from_db()
            network.refresh_from_db()
            pool.refresh_from_db()
            self.assertIsNone(root.parent)
            self.assertEqual(network.parent, root)
            self.assertEqual(pool.parent, network)

        ip = IPAddress.objects.create(address="10.0.0.1/32", status=self.status, namespace=namespace)

        with self.subTest("Test that deleting a pool prefix containing IPs succeeds"):
            self.assertEqual(ip.parent, pool)  # 3.0 TODO: change this to ", network)" once IP-to-pool is disallowed
            pool.delete()
            ip.refresh_from_db()
            self.assertEqual(ip.parent, network)

        # 3.0 TODO: uncomment once type enforcement is enabled
        # with self.assertRaises(
        #     ProtectedError,
        #     msg="Test that deleting a network prefix that would make an IP's parent a container raises a ProtectedError",
        # ):
        #     network.delete()

        with self.subTest("Test that deleting the root prefix succeeds"):
            root.delete()
            network.refresh_from_db()
            self.assertIsNone(network.parent)

        with self.assertRaises(
            ProtectedError,
            msg="Test that deleting a network prefix that would orphan an IP raises a ProtectedError",
        ):
            network.delete()

        with self.subTest("Test that deleting all child IPs of a network prefix allows the prefix to be deleted"):
            ip.delete()
            network.delete()


class TestIPAddress(ModelTestCases.BaseModelTestCase):
    model = IPAddress

    def setUp(self):
        super().setUp()
        self.namespace = Namespace.objects.first()
        self.status = Status.objects.get(name="Active")
        self.prefix = Prefix.objects.create(prefix="192.0.2.0/24", status=self.status, namespace=self.namespace)

    #
    # Uniqueness enforcement tests
    #

    def test_duplicate_global_unique(self):
        """Test that duplicate IPs in the same Namespace raises an error."""
        IPAddress.objects.create(address="192.0.2.1/24", status=self.status, namespace=self.namespace)
        with self.assertRaises(IntegrityError):
            IPAddress.objects.create(address="192.0.2.1/24", status=self.status, namespace=self.namespace)

    def test_multiple_nat_outside_list(self):
        """
        Test suite to test supporing nat_outside_list.
        """
        Prefix.objects.create(prefix="192.168.0.0/24", status=self.status, namespace=self.namespace)
        nat_inside = IPAddress.objects.create(address="192.168.0.1/24", status=self.status, namespace=self.namespace)
        nat_outside1 = IPAddress.objects.create(
            address="192.0.2.1/24", nat_inside=nat_inside, status=self.status, namespace=self.namespace
        )
        nat_outside2 = IPAddress.objects.create(
            address="192.0.2.2/24", nat_inside=nat_inside, status=self.status, namespace=self.namespace
        )
        nat_outside3 = IPAddress.objects.create(
            address="192.0.2.3/24", nat_inside=nat_inside, status=self.status, namespace=self.namespace
        )
        nat_inside.refresh_from_db()
        self.assertEqual(nat_inside.nat_outside_list.count(), 3)
        self.assertEqual(nat_inside.nat_outside_list.all()[0], nat_outside1)
        self.assertEqual(nat_inside.nat_outside_list.all()[1], nat_outside2)
        self.assertEqual(nat_inside.nat_outside_list.all()[2], nat_outside3)

    def test_create_ip_address_with_slaac_type(self):
        """Assert that SLAAC can only be set on IPv6 addresses."""
        # IPv6 be cool.
        Prefix.objects.create(prefix="1976:2023::/40", status=self.status, namespace=self.namespace)
        IPAddress.objects.create(
            address="1976:2023::1/128",
            status=self.status,
            type=IPAddressTypeChoices.TYPE_SLAAC,
            namespace=self.namespace,
        )
        self.assertTrue(IPAddress.objects.filter(address="1976:2023::1/128").exists())

        # IPv4 be uncool.
        with self.assertRaises(ValidationError):
            ip = IPAddress(
                address="192.0.2.17/32",
                status=self.status,
                namespace=self.namespace,
                type=IPAddressTypeChoices.TYPE_SLAAC,
            )
            ip.validated_save()

    def test_get_closest_parent(self):
        for ip in IPAddress.objects.all():
            with self.subTest(ip=ip):
                ip.save()
                ip.refresh_from_db()
                self.assertIsNotNone(ip.parent)
                self.assertEqual(
                    ip.parent,
                    Prefix.objects.filter(network__lte=ip.host, broadcast__gte=ip.host)
                    .order_by("-prefix_length")
                    .first(),
                )

    def test_parenting_constraints(self):
        """Test that IPAddress parenting correctly raises validation errors when unable to assign a valid parent prefix."""

        namespace = Namespace.objects.create(name="test_parenting_constraints")

        Prefix.objects.create(
            prefix="10.0.0.0/24", status=self.status, namespace=namespace, type=PrefixTypeChoices.TYPE_CONTAINER
        )
        Prefix.objects.create(
            prefix="11.0.0.0/24", status=self.status, namespace=namespace, type=PrefixTypeChoices.TYPE_NETWORK
        )
        Prefix.objects.create(
            prefix="12.0.0.0/24", status=self.status, namespace=namespace, type=PrefixTypeChoices.TYPE_POOL
        )

        # 3.0 TODO: uncomment once type enforcement is enabled
        # with self.assertRaises(ValidationError, msg="IP Address parent cannot be a container"):
        #     IPAddress.objects.create(address="10.0.0.1/32", status=self.status, namespace=namespace)

        # with self.assertRaises(Prefix.DoesNotExist, msg="IP Address parent cannot be a pool"):
        #     IPAddress.objects.create(address="12.0.0.1/32", status=self.status, namespace=namespace)

        with self.assertRaises(ValidationError) as err:
            IPAddress.objects.create(address="13.0.0.1/32", status=self.status, namespace=namespace)
        self.assertEqual(
            err.exception.message_dict["namespace"][0], "No suitable parent Prefix exists in this Namespace"
        )

        with self.subTest("Test that IP address can be assigned to a valid parent"):
            IPAddress.objects.create(address="11.0.0.1/32", status=self.status, namespace=namespace)

        with self.subTest("Test that IP address can be assigned to a pool that is a child of a network"):
            Prefix.objects.create(
                prefix="11.0.0.8/29", status=self.status, namespace=namespace, type=PrefixTypeChoices.TYPE_POOL
            )
            IPAddress.objects.create(address="11.0.0.9/32", status=self.status, namespace=namespace)

    def test_creating_ipaddress_with_an_invalid_parent(self):
        namespace = Namespace.objects.create(name="test_parenting_constraints")
        prefixes = (
            Prefix.objects.create(
                prefix="10.0.0.0/8", status=self.status, namespace=namespace, type=PrefixTypeChoices.TYPE_NETWORK
            ),
            Prefix.objects.create(
                prefix="192.168.0.0/16", status=self.status, namespace=namespace, type=PrefixTypeChoices.TYPE_NETWORK
            ),
        )

        with self.assertRaises(ValidationError) as err:
            ipaddress = IPAddress(address="192.168.0.1/16", parent=prefixes[0], status=self.status)
            ipaddress.validated_save()
        expected_err_msg = (
            f"{prefixes[0]} cannot be assigned as the parent of {ipaddress}. "
            f" In namespace {namespace}, the expected parent would be {prefixes[1]}."
        )
        self.assertEqual(expected_err_msg, err.exception.message_dict["parent"][0])

    def test_creating_an_ipaddress_without_namespace_or_parent(self):
        with self.assertRaises(ValidationError) as err:
            ip = IPAddress(address="1976:2023::1/128", status=self.status)
            ip.validated_save()
        self.assertEqual(err.exception.message_dict["parent"][0], "Either a parent or a namespace must be provided.")


class TestRIR(ModelTestCases.BaseModelTestCase):
    model = RIR


class TestRouteTarget(ModelTestCases.BaseModelTestCase):
    model = RouteTarget


class TestService(ModelTestCases.BaseModelTestCase):
    model = Service

    @classmethod
    def setUpTestData(cls):
        location = Location.objects.filter(location_type=LocationType.objects.get(name="Campus")).first()
        devicetype = DeviceType.objects.first()
        devicerole = Role.objects.get_for_model(Device).first()
        devicestatus = Status.objects.get_for_model(Device).first()
        device = Device.objects.create(
            name="Device 1", location=location, device_type=devicetype, role=devicerole, status=devicestatus
        )
        Service.objects.create(
            device=device,
            name="Service 1",
            protocol=ServiceProtocolChoices.PROTOCOL_TCP,
            ports=[101],
        )


class TestVLANGroup(ModelTestCases.BaseModelTestCase):
    model = VLANGroup

    def test_vlan_group_validation(self):
        location_type = LocationType.objects.get(name="Elevator")
        location = Location.objects.filter(location_type=location_type).first()
        group = VLANGroup(name="Group 1", location=location)
        with self.assertRaises(ValidationError) as cm:
            group.validated_save()
        self.assertIn(f'VLAN groups may not associate to locations of type "{location_type.name}"', str(cm.exception))

    def test_get_next_available_vid(self):
        vlangroup = VLANGroup.objects.create(name="VLAN Group 1")
        status = Status.objects.get_for_model(VLAN).first()
        VLAN.objects.bulk_create(
            (
                VLAN(name="VLAN 1", vid=1, vlan_group=vlangroup, status=status),
                VLAN(name="VLAN 2", vid=2, vlan_group=vlangroup, status=status),
                VLAN(name="VLAN 3", vid=3, vlan_group=vlangroup, status=status),
                VLAN(name="VLAN 5", vid=5, vlan_group=vlangroup, status=status),
            )
        )
        self.assertEqual(vlangroup.get_next_available_vid(), 4)

        VLAN.objects.bulk_create((VLAN(name="VLAN 4", vid=4, vlan_group=vlangroup, status=status),))
        self.assertEqual(vlangroup.get_next_available_vid(), 6)


class TestVLAN(ModelTestCases.BaseModelTestCase):
    model = VLAN

    def test_vlan_validation(self):
        location_type = LocationType.objects.get(name="Root")
        location_type.content_types.set([])
        location_type.validated_save()
        location = Location.objects.filter(location_type=location_type).first()
        vlan = VLAN(name="Group 1", vid=1, location=location)
        vlan.status = Status.objects.get_for_model(VLAN).first()
        with self.assertRaises(ValidationError) as cm:
            vlan.validated_save()
        self.assertIn(f'VLANs may not associate to locations of type "{location_type.name}"', str(cm.exception))

        location_type.content_types.add(ContentType.objects.get_for_model(VLAN))
        group = VLANGroup.objects.create(name="Group 1")
        vlan.vlan_group = group
        location_status = Status.objects.get_for_model(Location).first()
        location_2 = Location.objects.create(name="Location 2", location_type=location_type, status=location_status)
        group.location = location_2
        group.save()
        with self.assertRaises(ValidationError) as cm:
            vlan.validated_save()
        self.assertIn(
            f'The assigned group belongs to a location that does not include location "{location.name}"',
            str(cm.exception),
        )


class TestVRF(ModelTestCases.BaseModelTestCase):
    model = VRF
    # TODO(jathan): Add VRF model tests.
