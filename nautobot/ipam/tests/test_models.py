from unittest import skipIf
from unittest.mock import patch

from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.db import connection, IntegrityError
from django.db.models import ProtectedError
from django.test import TestCase
import netaddr

from nautobot.core.testing.models import ModelTestCases
from nautobot.dcim import choices as dcim_choices
from nautobot.dcim.models import Device, DeviceType, Interface, Location, LocationType, Module, ModuleBay, ModuleType
from nautobot.extras.models import Role, Status
from nautobot.ipam.choices import IPAddressTypeChoices, PrefixTypeChoices, ServiceProtocolChoices
from nautobot.ipam.models import (
    get_default_namespace,
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
        int_role = Role.objects.get_for_model(Interface).first()
        cls.test_int1 = Interface.objects.create(
            device=cls.test_device,
            name="int1",
            status=int_status,
            role=int_role,
            type=dcim_choices.InterfaceTypeChoices.TYPE_1GE_FIXED,
        )
        cls.test_int2 = Interface.objects.create(
            device=cls.test_device,
            name="int2",
            status=int_status,
            role=int_role,
            type=dcim_choices.InterfaceTypeChoices.TYPE_1GE_FIXED,
        )
        cluster_type = ClusterType.objects.create(name="Cluster Type 1")
        cluster = Cluster.objects.create(name="cluster1", cluster_type=cluster_type)
        vmint_status = Status.objects.get_for_model(VMInterface).first()
        vmint_role = Role.objects.get_for_model(VMInterface).first()
        cls.test_vm = VirtualMachine.objects.create(
            name="vm1",
            cluster=cluster,
            status=Status.objects.get_for_model(VirtualMachine).first(),
            role=vmint_role,
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
            role=vmint_role,
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

    def test_primary_ip_retained_when_deleted_from_device_or_module_interface(self):
        """Test primary_ip4 remains set when the same IP is assigned to multiple interfaces and deleted from one."""

        # Create a module bay on the existing device
        device_module_bay = ModuleBay.objects.create(parent_device=self.test_device, name="Test Bay")

        # Create a module with an interface and add it to the module bay on the device
        module = Module.objects.create(
            module_type=ModuleType.objects.first(),
            status=Status.objects.get_for_model(Module).first(),
            parent_module_bay=device_module_bay,
        )

        # Set status for the module interface
        int_status = Status.objects.get_for_model(Interface).first()

        # Create an interface on the module
        interface_module = Interface.objects.create(
            name="eth0_module",
            module=module,
            type=dcim_choices.InterfaceTypeChoices.TYPE_1GE_FIXED,
            status=int_status,
        )

        # Link the module to the device
        self.test_device.installed_device = interface_module
        self.test_device.save()

        # Create IP and assign it to multiple interfaces
        ip_address = IPAddress.objects.create(address="192.0.2.1/24", namespace=self.namespace, status=self.status)
        assignment_device_int1 = IPAddressToInterface.objects.create(interface=self.test_int1, ip_address=ip_address)
        assignment_module_int1 = IPAddressToInterface.objects.create(interface=interface_module, ip_address=ip_address)

        # Set the primary IP on the device
        self.test_device.primary_ip4 = assignment_device_int1.ip_address
        self.test_device.save()

        # Verify that the primary IP is set
        self.assertEqual(self.test_device.primary_ip4, ip_address)

        # Delete the IP assignment from one interface
        assignment_device_int1.delete()

        # Refresh and check that the primary IP is still assigned
        self.test_device.refresh_from_db()
        self.assertEqual(self.test_device.primary_ip4, ip_address)

        # Verify remaining IP assignments on the IP object
        remaining_assignments = ip_address.interface_assignments.all()
        self.assertEqual(remaining_assignments.count(), 1)
        self.assertIn(assignment_module_int1, remaining_assignments)

    def test_primary_ip_retained_when_deleted_from_device_interface_with_nested_module(self):
        """Test primary_ip4 remains set when the same IP is assigned to a device and nested module interfaces, and deleted from the device interface."""

        # Create a module bay on the existing device
        device_module_bay = ModuleBay.objects.create(parent_device=self.test_device, name="Primary Module Bay")

        # Create a primary module with an interface and add it to the module bay on the device
        primary_module = Module.objects.create(
            module_type=ModuleType.objects.first(),
            status=Status.objects.get_for_model(Module).first(),
            parent_module_bay=device_module_bay,
        )

        # Create a secondary module bay within the primary module for nested module creation
        nested_module_bay = ModuleBay.objects.create(parent_module=primary_module, name="Nested Module Bay")

        # Create a nested module within the primary module's module bay
        nested_module = Module.objects.create(
            module_type=ModuleType.objects.first(),
            status=Status.objects.get_for_model(Module).first(),
            parent_module_bay=nested_module_bay,
        )

        # Set status for the nested module interface
        int_status = Status.objects.get_for_model(Interface).first()

        # Create an interface on the nested module and assign an IP
        nested_interface = Interface.objects.create(
            name="eth0_nested",
            module=nested_module,
            type=dcim_choices.InterfaceTypeChoices.TYPE_1GE_FIXED,
            status=int_status,
        )

        # Create IP and assign it to both the device and the nested module interface
        ip_address = IPAddress.objects.create(address="192.0.2.1/24", namespace=self.namespace, status=self.status)
        assignment_device_int1 = IPAddressToInterface.objects.create(interface=self.test_int1, ip_address=ip_address)
        assignment_nested_module = IPAddressToInterface.objects.create(
            interface=nested_interface, ip_address=ip_address
        )

        # Set the primary IP on the device to the IP on the device interface
        self.test_device.primary_ip4 = assignment_nested_module.ip_address
        self.test_device.save()

        # Verify that the primary IP is correctly set
        self.assertEqual(self.test_device.primary_ip4, ip_address)

        # Delete the IP assignment from the device interface
        assignment_device_int1.delete()

        # Refresh and check that the primary IP is still assigned to the device
        self.test_device.refresh_from_db()
        self.assertEqual(self.test_device.primary_ip4, ip_address)

        # Confirm that the IP is still associated with the nested module interface
        remaining_assignments = ip_address.interface_assignments.all()
        self.assertEqual(remaining_assignments.count(), 1)
        self.assertIn(assignment_nested_module, remaining_assignments)


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
            prefix="101.102.0.0/16", status=self.status, namespace=self.namespace, type=PrefixTypeChoices.TYPE_CONTAINER
        )
        self.parent = Prefix.objects.create(
            prefix="101.102.103.0/24",
            status=self.status,
            namespace=self.namespace,
            type=PrefixTypeChoices.TYPE_CONTAINER,
        )
        self.child1 = Prefix.objects.create(prefix="101.102.103.0/26", status=self.status, namespace=self.namespace)
        self.child2 = Prefix.objects.create(prefix="101.102.103.104/32", status=self.status, namespace=self.namespace)

    def test_parent_exists_after_model_clean(self):
        prefix = Prefix(
            prefix="101.102.1.0/24",
            status=self.status,
            namespace=self.namespace,
            type=PrefixTypeChoices.TYPE_CONTAINER,
        )
        prefix.clean()
        self.assertEqual(prefix.parent, self.root)

    def test_reparent_subnets_and_reparent_ips_call(self):
        """Assert reparent_subnets and reparent_ips are only called if there is an update to either of network, namespace or prefix_length"""
        prefix_ip = "101.102.0.0/28"
        with self.subTest("Assert reparent_subnets"):
            with patch.object(Prefix, "reparent_subnets", return_value=None) as mock_reparent_subnets:
                Prefix.objects.create(prefix=prefix_ip, status=self.status, namespace=self.namespace)
                mock_reparent_subnets.assert_called_once()

            with patch.object(Prefix, "reparent_subnets", return_value=None) as mock_reparent_subnets:
                prefix = Prefix.objects.get(prefix=prefix_ip)
                prefix.description = "Sample Description"
                prefix.save()
                mock_reparent_subnets.assert_not_called()
                prefix.delete()

        with self.subTest("Assert reparent_ips"):
            with patch.object(Prefix, "reparent_ips", return_value=None) as reparent_ips:
                Prefix.objects.create(prefix=prefix_ip, status=self.status, namespace=self.namespace)
                reparent_ips.assert_called_once()

            with patch.object(Prefix, "reparent_ips", return_value=None) as reparent_ips:
                prefix = Prefix.objects.get(prefix=prefix_ip)
                prefix.description = "Sample Description"
                prefix.save()
                reparent_ips.assert_not_called()

    def test_location_queries(self):
        locations = Location.objects.all()[:4]
        for location in locations:
            location.location_type.content_types.add(ContentType.objects.get_for_model(Prefix))
        for i in range(10):
            pfx = Prefix.objects.create(prefix=f"1.1.1.{4 * i}/30", status=self.status, namespace=self.namespace)
            if i > 4:
                pfx.locations.set(locations)

        with self.subTest("Assert filtering and excluding `location`"):
            self.assertQuerysetEqualAndNotEmpty(
                Prefix.objects.filter(location=locations[0]),
                Prefix.objects.filter(locations__in=[locations[0]]),
            )
            self.assertQuerysetEqualAndNotEmpty(
                Prefix.objects.exclude(location=locations[0]),
                Prefix.objects.exclude(locations__in=[locations[0]]),
            )
            self.assertQuerysetEqualAndNotEmpty(
                Prefix.objects.filter(location__in=[locations[0]]),
                Prefix.objects.filter(locations__in=[locations[0]]),
            )
            self.assertQuerysetEqualAndNotEmpty(
                Prefix.objects.exclude(location__in=[locations[0]]),
                Prefix.objects.exclude(locations__in=[locations[0]]),
            )

        # We use `assertQuerysetEqualAndNotEmpty` for test validation. Including a nullable field could lead
        # to flaky tests where querysets might return None, causing tests to fail. Therefore, we select
        # fields that consistently contain values to ensure reliable filtering.
        query_params = ["name", "location_type", "status"]

        for field_name in query_params:
            with self.subTest(f"Assert location__{field_name} query."):
                value = getattr(locations[0], field_name)
                self.assertQuerysetEqualAndNotEmpty(
                    Prefix.objects.filter(**{f"location__{field_name}": value}),
                    Prefix.objects.filter(**{f"locations__{field_name}": value}),
                )
                self.assertQuerysetEqualAndNotEmpty(
                    Prefix.objects.exclude(**{f"location__{field_name}": value}),
                    Prefix.objects.exclude(**{f"locations__{field_name}": value}),
                )

    def test_prefix_validation(self):
        location_type = LocationType.objects.get(name="Room")
        location = Location.objects.filter(location_type=location_type).first()
        prefix = Prefix(prefix="192.0.2.0/24", location=location, status=self.statuses[0])
        with self.assertRaises(ValidationError) as cm:
            prefix.validated_save()
        self.assertIn(f"Prefixes may not associate to Locations of types {[location_type.name]}", str(cm.exception))

    def test_location_validation(self):
        location_type = LocationType.objects.get(name="Room")
        location = Location.objects.filter(location_type=location_type).first()
        with self.assertRaises(ValidationError) as cm:
            location.prefixes.add(self.root)
        self.assertIn(f"{location} is a Room and may not have Prefixes associated to it.", str(cm.exception))

    def test_create_field_population(self):
        """Test the various ways of creating a Prefix all result in correctly populated fields."""
        with self.subTest("Creation with a prefix and status"):
            prefix = Prefix(prefix="192.0.3.0/24", status=self.status)
            for method in [prefix.clean, prefix.save, prefix.refresh_from_db]:
                method()
                self.assertEqual(prefix.network, "192.0.3.0")
                self.assertEqual(prefix.broadcast, "192.0.3.255")
                self.assertEqual(prefix.prefix_length, 24)
                self.assertEqual(prefix.type, PrefixTypeChoices.TYPE_NETWORK)  # default value
                # parent field is tested exhaustively below
                self.assertEqual(prefix.ip_version, 4)
                self.assertEqual(prefix.namespace, get_default_namespace())  # default value

        with self.subTest("Creation with a network and prefix_length"):
            prefix = Prefix(network="192.0.4.0", prefix_length=24, status=self.status)
            for method in [prefix.clean, prefix.save, prefix.refresh_from_db]:
                method()
                self.assertEqual(prefix.network, "192.0.4.0")
                self.assertEqual(prefix.broadcast, "192.0.4.255")
                self.assertEqual(prefix.prefix_length, 24)
                self.assertEqual(prefix.type, PrefixTypeChoices.TYPE_NETWORK)  # default value
                # parent field is tested exhaustively below
                self.assertEqual(prefix.ip_version, 4)
                self.assertEqual(prefix.namespace, get_default_namespace())  # default value
                self.assertEqual(prefix.prefix, netaddr.IPNetwork("192.0.4.0/24"))

        with self.subTest("Creation with a network, broadcast, and prefix_length"):
            prefix = Prefix(network="192.0.5.0", broadcast="192.0.5.255", prefix_length=24, status=self.status)
            for method in [prefix.clean, prefix.save, prefix.refresh_from_db]:
                method()
                self.assertEqual(prefix.network, "192.0.5.0")
                self.assertEqual(prefix.broadcast, "192.0.5.255")
                self.assertEqual(prefix.prefix_length, 24)
                self.assertEqual(prefix.type, PrefixTypeChoices.TYPE_NETWORK)  # default value
                # parent field is tested exhaustively below
                self.assertEqual(prefix.ip_version, 4)
                self.assertEqual(prefix.namespace, get_default_namespace())  # default value
                self.assertEqual(prefix.prefix, netaddr.IPNetwork("192.0.5.0/24"))

        with self.subTest("With conflicting values - prefix overrules network/broadcast/prefix_length/ip_version"):
            prefix = Prefix(
                prefix="192.0.6.0/24",
                status=self.status,
                network="1.1.1.1",
                broadcast="2.2.2.2",
                prefix_length=27,
                ip_version=6,
            )
            for method in [prefix.clean, prefix.save, prefix.refresh_from_db]:
                method()
                self.assertEqual(prefix.network, "192.0.6.0")
                self.assertEqual(prefix.broadcast, "192.0.6.255")
                self.assertEqual(prefix.prefix_length, 24)
                self.assertEqual(prefix.ip_version, 4)

        with self.subTest("With conflicting values - network/prefix_length overrule broadcast/ip_version"):
            prefix = Prefix(
                status=self.status, network="192.0.7.0", prefix_length=24, broadcast="192.0.7.127", ip_version=6
            )
            for method in [prefix.clean, prefix.save, prefix.refresh_from_db]:
                method()
                self.assertEqual(prefix.network, "192.0.7.0")
                self.assertEqual(prefix.broadcast, "192.0.7.255")
                self.assertEqual(prefix.prefix_length, 24)
                self.assertEqual(prefix.ip_version, 4)

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
        parent2 = Prefix.objects.create(prefix="101.102.128.0/24", status=self.status, namespace=self.namespace)
        self.assertEqual(list(self.parent.siblings()), [parent2])
        self.assertEqual(list(self.parent.siblings(include_self=True)), [self.parent, parent2])

    def test_reparenting_on_create_and_delete(self):
        """Test that reparenting algorithm works in its most basic form."""
        # tree hierarchy
        self.assertIsNone(self.root.parent)
        self.assertEqual(self.parent.parent, self.root)
        self.assertEqual(self.child1.parent, self.parent)

        # Delete the parent (/24); child1/child2 now have root (/16) as their parent.
        num_deleted, _ = self.parent.delete()
        self.assertEqual(num_deleted, 1)

        self.assertEqual(list(self.root.children.all()), [self.child1, self.child2])
        self.child1.refresh_from_db()
        self.child2.refresh_from_db()
        self.assertEqual(self.child1.parent, self.root)
        self.assertEqual(self.child2.parent, self.root)
        self.assertEqual(list(self.child1.ancestors()), [self.root])

        # Add /24 back in as a parent and assert that child1/child2 now have it as their parent, and
        # /16 is its parent.
        self.parent = Prefix.objects.create(
            prefix="101.102.103.0/24",
            status=self.status,
            namespace=self.namespace,
            type=PrefixTypeChoices.TYPE_CONTAINER,
        )
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
        parent = Prefix.objects.create(
            prefix="101.102.0.0/25", status=self.status, namespace=namespace, type=PrefixTypeChoices.TYPE_CONTAINER
        )
        child1.refresh_from_db()
        child2.refresh_from_db()
        self.assertEqual(child1.parent, parent)
        self.assertEqual(child2.parent, parent)
        self.assertEqual(list(child1.ancestors()), [root, parent])

    def test_reparenting_on_field_updates(self):
        """Test that reparenting occurs when network, prefix_length, etc. are updated."""
        self.assertIsNone(self.root.parent)
        self.assertEqual(self.parent.parent, self.root)
        self.assertEqual(self.child1.parent, self.parent)
        self.assertEqual(self.child2.parent, self.parent)

        ip1 = IPAddress.objects.create(address="101.102.103.127/32", status=self.status, namespace=self.namespace)
        ip2 = IPAddress.objects.create(address="101.102.103.128/32", status=self.status, namespace=self.namespace)
        self.assertEqual(ip1.parent, self.parent)
        self.assertEqual(ip2.parent, self.parent)

        with self.subTest("Decrease prefix_length, gaining children"):
            self.child1.prefix_length = 25
            self.child1.save()
            self.child1.refresh_from_db()
            self.child2.refresh_from_db()
            self.assertEqual(self.child2.parent, self.child1)
            ip1.refresh_from_db()
            self.assertEqual(ip1.parent, self.child1)

        with self.subTest("Increase prefix_length, losing children"):
            self.child1.prefix_length = 26
            self.child1.save()
            self.child1.refresh_from_db()
            self.child2.refresh_from_db()
            self.assertEqual(self.child2.parent, self.parent)
            ip1.refresh_from_db()
            self.assertEqual(ip1.parent, self.parent)

        with self.subTest("Broaden prefix, becoming parent of former parent"):
            self.parent.prefix = "101.0.0.0/8"
            self.parent.save()
            self.assertIsNone(self.parent.parent)
            # Former root is now a child of parent
            self.root.refresh_from_db()
            self.assertEqual(self.root.parent, self.parent)
            # Former children are now children of former root
            self.child1.refresh_from_db()
            self.assertEqual(self.child1.parent, self.root)
            self.child2.refresh_from_db()
            self.assertEqual(self.child2.parent, self.root)
            ip1.refresh_from_db()
            self.assertEqual(ip1.parent, self.root)
            ip2.refresh_from_db()
            self.assertEqual(ip2.parent, self.root)

        with self.subTest("Narrow prefix, becoming child of former child"):
            self.parent.prefix = "101.102.103.0/24"
            self.parent.save()
            self.assertEqual(self.parent.parent, self.root)
            # Former root is now again root
            self.root.refresh_from_db()
            self.assertIsNone(self.root.parent)
            # Former children are again children of parent
            self.child1.refresh_from_db()
            self.assertEqual(self.child1.parent, self.parent)
            self.child2.refresh_from_db()
            self.assertEqual(self.child2.parent, self.parent)
            ip1.refresh_from_db()
            self.assertEqual(ip1.parent, self.parent)
            ip2.refresh_from_db()
            self.assertEqual(ip2.parent, self.parent)

        with self.subTest("Change former root on multiple dimensions"):
            self.root.network = "101.102.103.0"
            self.root.prefix_length = 25
            self.root.save()
            self.assertEqual(self.root.parent, self.parent)
            self.parent.refresh_from_db()
            self.assertEqual(self.parent.parent, None)
            self.child1.refresh_from_db()
            self.assertEqual(self.child1.parent, self.root)
            self.child2.refresh_from_db()
            self.assertEqual(self.child2.parent, self.root)
            ip1.refresh_from_db()
            self.assertEqual(ip1.parent, self.root)
            ip2.refresh_from_db()
            self.assertEqual(ip2.parent, self.parent)

        with self.subTest("Reclaim root position"):
            self.root.network = "101.0.0.0"
            self.root.prefix_length = 8
            self.root.save()
            self.assertIsNone(self.root.parent)
            self.parent.refresh_from_db()
            self.assertEqual(self.parent.parent, self.root)
            self.child1.refresh_from_db()
            self.assertEqual(self.child1.parent, self.parent)
            self.child2.refresh_from_db()
            self.assertEqual(self.child2.parent, self.parent)
            ip1.refresh_from_db()
            self.assertEqual(ip1.parent, self.parent)
            ip2.refresh_from_db()
            self.assertEqual(ip2.parent, self.parent)

    def test_clean_fails_if_would_orphan_ips(self):
        """Test that clean() fails if reparenting would orphan IPs."""
        self.ip = IPAddress.objects.create(address="101.102.1.1/32", status=self.status, namespace=self.namespace)
        self.assertEqual(self.ip.parent, self.root)
        with self.assertRaises(ValidationError) as cm:
            self.root.prefix = "102.103.0.0/16"
            self.root.clean()
        self.assertIn(
            f"1 existing IP addresses (including {self.ip.host}) would no longer have a valid parent", str(cm.exception)
        )
        self.root.refresh_from_db()
        self.ip2 = IPAddress.objects.create(address="101.102.1.2/32", status=self.status, namespace=self.namespace)
        self.assertEqual(self.ip2.parent, self.root)
        with self.assertRaises(ValidationError) as cm:
            self.root.prefix = "102.103.0.0/16"
            self.root.clean()
        self.assertIn(
            f"2 existing IP addresses (including {self.ip.host}) would no longer have a valid parent",
            str(cm.exception),
        )

    def test_clean_fails_if_namespace_changed_and_vrfs_involved(self):
        vrf = VRF.objects.create(name="VRF Red", namespace=self.namespace)
        vrf.add_prefix(self.root)

        new_namespace = Namespace.objects.exclude(id=self.namespace.id).first()

        self.root.namespace = new_namespace
        with self.assertRaises(ValidationError) as cm:
            self.root.clean()
        self.assertIn("Cannot move to a different Namespace while associated to VRFs", str(cm.exception))

        vrf.remove_prefix(self.root)
        self.root.clean()

        vrf.add_prefix(self.parent)
        with self.assertRaises(ValidationError) as cm:
            self.root.clean()
        self.assertIn(
            "Cannot move to a different Namespace with descendant Prefixes associated to VRFs", str(cm.exception)
        )

    def test_namespace_change_success_updates_descendants_and_claims_new_children(self):
        new_namespace = Namespace.objects.exclude(id=self.namespace.id).first()
        new_catchall = Prefix.objects.create(prefix="0.0.0.0/0", status=self.status, namespace=new_namespace)
        new_parent = Prefix.objects.create(prefix="101.102.200.0/24", status=self.status, namespace=new_namespace)
        new_child = Prefix.objects.create(prefix="101.102.103.64/26", status=self.status, namespace=new_namespace)
        new_grandchild = Prefix.objects.create(prefix="101.102.103.0/27", status=self.status, namespace=new_namespace)
        new_ip = IPAddress.objects.create(address="101.102.150.200/32", status=self.status, namespace=new_namespace)

        # Before:
        # self.namespace
        #   self.root        101.102.0.0/16
        #     self.parent    101.102.103.0/24
        #       self.child1  101.102.103.0/26
        #       self.child2  101.102.103.104/32
        # new_namespace
        #   new_catchall      0.0.0.0/0
        #     new_grandchild  101.102.103.0/27
        #     new_child       101.102.103.64/26
        #     new_ip          101.102.150.200/32
        #     new_parent      101.102.200.0/24
        #
        # After:
        # new_namespace
        #   new_catchall            0.0.0.0/0
        #     self.root             101.102.0.0/16
        #       self.parent         101.102.103.0/24
        #         self.child1       101.102.103.0/26
        #           new_grandchild  101.102.103.0/27
        #         new_child         101.102.103.64/26
        #           self.child2     101.102.103.104/32
        #       new_ip              101.102.150.200/32
        #       new_parent          101.102.200.0/24

        self.root.namespace = new_namespace
        self.root.save()
        self.assertEqual(self.root.namespace, new_namespace)
        self.assertEqual(self.root.parent, new_catchall)  # automatically updated
        self.parent.refresh_from_db()
        self.assertEqual(self.parent.namespace, new_namespace)  # automatically updated
        self.assertEqual(self.parent.parent, self.root)  # unchanged
        self.child1.refresh_from_db()
        self.assertEqual(self.child1.namespace, new_namespace)  # automatically updated
        self.assertEqual(self.child1.parent, self.parent)  # unchanged
        self.child2.refresh_from_db()
        self.assertEqual(self.child2.namespace, new_namespace)  # automatically updated
        self.assertEqual(self.child2.parent, new_child)  # automatically updated
        new_parent.refresh_from_db()
        self.assertEqual(new_parent.namespace, new_namespace)  # unchanged
        self.assertEqual(new_parent.parent, self.root)  # automatically updated
        new_child.refresh_from_db()
        self.assertEqual(new_child.namespace, new_namespace)  # unchanged
        self.assertEqual(new_child.parent, self.parent)  # automatically updated
        new_grandchild.refresh_from_db()
        self.assertEqual(new_grandchild.namespace, new_namespace)  # unchanged
        self.assertEqual(new_grandchild.parent, self.child1)  # automatically updated
        new_ip.refresh_from_db()
        self.assertEqual(new_ip.parent, self.root)

    def test_namespace_change_results_in_merge_collisions(self):
        new_namespace = Namespace.objects.exclude(id=self.namespace.id).first()
        new_root = Prefix.objects.create(prefix="101.102.0.0/16", status=self.status, namespace=new_namespace)

        self.root.namespace = new_namespace
        with self.assertRaises(IntegrityError):
            self.root.save()
        self.root.refresh_from_db()
        self.assertEqual(self.root.namespace, self.namespace)
        self.parent.refresh_from_db()
        self.assertEqual(self.parent.namespace, self.namespace)
        self.child1.refresh_from_db()
        self.assertEqual(self.child1.namespace, self.namespace)
        self.child2.refresh_from_db()
        self.assertEqual(self.child2.namespace, self.namespace)

        new_root.delete()
        new_parent = Prefix.objects.create(prefix="101.102.103.0/24", status=self.status, namespace=new_namespace)

        self.root.namespace = new_namespace
        with self.assertRaises(IntegrityError):
            self.root.save()
        self.root.refresh_from_db()
        self.assertEqual(self.root.namespace, self.namespace)
        self.parent.refresh_from_db()
        self.assertEqual(self.parent.namespace, self.namespace)
        self.child1.refresh_from_db()
        self.assertEqual(self.child1.namespace, self.namespace)
        self.child2.refresh_from_db()
        self.assertEqual(self.child2.namespace, self.namespace)

        new_parent.delete()

        existing_ip = IPAddress.objects.create(address="101.102.103.1/32", status=self.status, namespace=self.namespace)
        new_prefix = Prefix.objects.create(prefix="0.0.0.0/0", status=self.status, namespace=new_namespace)
        new_ip = IPAddress.objects.create(address="101.102.103.1/32", status=self.status, namespace=new_namespace)
        self.assertEqual(new_ip.parent, new_prefix)

        self.root.namespace = new_namespace
        with self.assertRaises(IntegrityError):
            self.root.save()
        self.root.refresh_from_db()
        self.assertIsNone(self.root.parent)
        self.assertEqual(self.root.namespace, self.namespace)
        self.parent.refresh_from_db()
        self.assertEqual(self.parent.namespace, self.namespace)
        self.child1.refresh_from_db()
        self.assertEqual(self.child1.namespace, self.namespace)
        self.child2.refresh_from_db()
        self.assertEqual(self.child2.namespace, self.namespace)
        existing_ip.refresh_from_db()
        self.assertEqual(existing_ip.parent, self.child1)
        new_ip.refresh_from_db()
        self.assertEqual(new_ip.parent, new_prefix)

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
        self.assertQuerysetEqualAndNotEmpty(parent_prefix.ip_addresses.all(), parent_prefix.get_child_ips())
        self.assertQuerysetEqualAndNotEmpty(parent_prefix.ip_addresses.all(), parent_prefix.get_all_ips())
        child_ip_pks = {p.pk for p in parent_prefix.ip_addresses.all()}
        # Global container should return all children
        self.assertSetEqual(child_ip_pks, {ips[0].pk, ips[1].pk, ips[2].pk, ips[3].pk})

        # Make sure /31 is handled correctly
        parent_prefix_31 = Prefix.objects.create(prefix="20.0.4.0/31", status=self.status, namespace=self.namespace)
        ips_31 = (
            IPAddress.objects.create(address="20.0.4.0/31", status=self.status, namespace=self.namespace),
            IPAddress.objects.create(address="20.0.4.1/31", status=self.status, namespace=self.namespace),
        )
        self.assertQuerysetEqualAndNotEmpty(parent_prefix_31.ip_addresses.all(), parent_prefix_31.get_child_ips())
        self.assertQuerysetEqualAndNotEmpty(parent_prefix_31.ip_addresses.all(), parent_prefix_31.get_all_ips())
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

    def test_get_first_available_ip_calculate_child_ips(self):
        parent_prefix = Prefix.objects.create(prefix="10.0.3.0/29", status=self.status, namespace=self.namespace)
        Prefix.objects.create(prefix="10.0.3.0/30", status=self.status, namespace=self.namespace)
        IPAddress(address="10.0.3.1/30", status=self.status, namespace=self.namespace).save()

        self.assertEqual(parent_prefix.get_first_available_ip(), "10.0.3.2/29")

    def test_get_all_ips_issue_3319(self):
        # https://github.com/nautobot/nautobot/issues/3319
        # Confirm that IPv4 addresses aren't caught up in the IPv6 ::/96 subnet by accident, and vice versa.
        prefix_v6 = Prefix.objects.create(
            prefix="::/0", type=PrefixTypeChoices.TYPE_CONTAINER, status=self.status, namespace=self.namespace
        )
        prefix_v4 = Prefix.objects.create(
            prefix="0.0.0.0/0", type=PrefixTypeChoices.TYPE_CONTAINER, status=self.status, namespace=self.namespace
        )
        IPAddress.objects.create(address="::0102:0304/128", status=self.status, namespace=self.namespace)
        IPAddress.objects.create(address="1.2.3.4/32", status=self.status, namespace=self.namespace)
        self.assertQuerysetEqualAndNotEmpty(
            prefix_v6.get_all_ips(), IPAddress.objects.filter(ip_version=6, parent__namespace=self.namespace)
        )
        self.assertQuerysetEqualAndNotEmpty(
            prefix_v4.get_all_ips(), IPAddress.objects.filter(ip_version=4, parent__namespace=self.namespace)
        )

    def test_get_utilization(self):
        # Container Prefix
        prefix = Prefix.objects.create(
            prefix="10.0.0.0/24", type=PrefixTypeChoices.TYPE_CONTAINER, status=self.status, namespace=self.namespace
        )
        slash26 = Prefix.objects.create(prefix="10.0.0.0/26", status=self.status, namespace=self.namespace)
        slash25 = Prefix.objects.create(prefix="10.0.0.128/25", status=self.status, namespace=self.namespace)
        self.assertEqual(prefix.get_utilization(), (192, 256))

        # Create 32 IPAddresses within the /26 Prefix
        for i in range(1, 33):
            IPAddress.objects.create(address=f"10.0.0.{i}/32", status=self.status, namespace=self.namespace)

        # Assert differing behavior of get_all_ips() versus get_child_ips() for the /24 and /26 prefixes
        self.assertQuerysetEqual(prefix.get_child_ips(), IPAddress.objects.none())
        self.assertQuerysetEqualAndNotEmpty(
            prefix.get_all_ips(), IPAddress.objects.filter(host__net_host_contained="10.0.0.0/24")
        )
        self.assertQuerysetEqualAndNotEmpty(
            slash26.get_child_ips(), IPAddress.objects.filter(host__net_host_contained="10.0.0.0/24")
        )
        self.assertQuerysetEqualAndNotEmpty(
            slash26.get_all_ips(), IPAddress.objects.filter(host__net_host_contained="10.0.0.0/24")
        )

        # The parent prefix utilization does not change because the ip addresses are parented to the child /26 prefix.
        self.assertEqual(prefix.get_utilization(), (192, 256))

        # The /26 will have 32 IPs
        self.assertEqual(slash26.get_utilization(), (32, 62))

        # Create IPAddress objects for network and broadcast addresses
        IPAddress.objects.create(address="10.0.0.0/32", status=self.status, namespace=self.namespace)
        IPAddress.objects.create(address="10.0.0.63/32", status=self.status, namespace=self.namespace)

        self.assertQuerysetEqual(prefix.get_child_ips(), IPAddress.objects.none())
        self.assertQuerysetEqualAndNotEmpty(
            prefix.get_all_ips(), IPAddress.objects.filter(host__net_host_contained="10.0.0.0/24")
        )
        self.assertQuerysetEqualAndNotEmpty(
            slash26.get_child_ips(), IPAddress.objects.filter(host__net_host_contained="10.0.0.0/24")
        )
        self.assertQuerysetEqualAndNotEmpty(
            slash26.get_all_ips(), IPAddress.objects.filter(host__net_host_contained="10.0.0.0/24")
        )

        # The /26 denominator will change to 64
        self.assertEqual(slash26.get_utilization(), (34, 64))

        # Add a pool, entire pool will count toward numerator in utilization
        pool = Prefix.objects.create(
            prefix="10.0.0.128/30", type=PrefixTypeChoices.TYPE_POOL, status=self.status, namespace=self.namespace
        )
        self.assertEqual(slash25.get_utilization(), (4, 128))

        # When the pool does not overlap with broadcast or network address, the denominator decrements by 2
        pool.delete()
        pool = Prefix.objects.create(
            prefix="10.0.0.132/30", type=PrefixTypeChoices.TYPE_POOL, status=self.status, namespace=self.namespace
        )
        self.assertEqual(slash25.get_utilization(), (4, 126))

        # Further distinguishing between get_child_ips() and get_all_ips():
        IPAddress.objects.create(address="10.0.0.64/32", status=self.status, namespace=self.namespace)
        self.assertQuerysetEqualAndNotEmpty(
            prefix.get_child_ips(), IPAddress.objects.filter(host__net_host_contained="10.0.0.64/26")
        )
        self.assertQuerysetEqualAndNotEmpty(
            prefix.get_all_ips(), IPAddress.objects.filter(host__net_host_contained="10.0.0.0/24")
        )

        slash27 = Prefix.objects.create(prefix="10.0.0.0/27", status=self.status, namespace=self.namespace)
        self.assertEqual(slash27.get_utilization(), (32, 32))
        self.assertQuerysetEqualAndNotEmpty(
            prefix.get_child_ips(), IPAddress.objects.filter(host__net_host_contained="10.0.0.64/26")
        )
        self.assertQuerysetEqualAndNotEmpty(
            prefix.get_all_ips(), IPAddress.objects.filter(host__net_host_contained="10.0.0.0/24")
        )
        self.assertQuerysetEqualAndNotEmpty(
            slash26.get_child_ips(), IPAddress.objects.filter(host__net_host_contained="10.0.0.32/27")
        )
        self.assertQuerysetEqualAndNotEmpty(
            slash26.get_all_ips(), IPAddress.objects.filter(host__net_host_contained="10.0.0.0/26")
        )
        self.assertQuerysetEqualAndNotEmpty(
            slash27.get_child_ips(), IPAddress.objects.filter(host__net_host_contained="10.0.0.0/27")
        )
        self.assertQuerysetEqualAndNotEmpty(
            slash27.get_all_ips(), IPAddress.objects.filter(host__net_host_contained="10.0.0.0/27")
        )

        # IPv4 Non-container Prefix /31, network and broadcast addresses count toward utilization
        slash31 = Prefix.objects.create(prefix="10.0.1.0/31", status=self.status, namespace=self.namespace)
        IPAddress.objects.create(address="10.0.1.0/32", status=self.status, namespace=self.namespace)
        IPAddress.objects.create(address="10.0.1.1/32", status=self.status, namespace=self.namespace)
        self.assertEqual(slash31.get_utilization(), (2, 2))

        # IPv6 Non-container Prefix, first and last addresses count toward utilization
        slash124_1 = Prefix.objects.create(prefix="aaab::/124", status=self.status, namespace=self.namespace)
        IPAddress.objects.create(address="aaab::1/128", status=self.status, namespace=self.namespace)
        IPAddress.objects.create(address="aaab::2/128", status=self.status, namespace=self.namespace)
        self.assertEqual(slash124_1.get_utilization(), (2, 16))

        slash124_2 = Prefix.objects.create(prefix="aaaa::/124", status=self.status, namespace=self.namespace)
        IPAddress.objects.create(address="aaaa::0/128", status=self.status, namespace=self.namespace)
        IPAddress.objects.create(address="aaaa::f/128", status=self.status, namespace=self.namespace)
        self.assertEqual(slash124_2.get_utilization(), (2, 16))

        # single address prefixes
        slash128 = Prefix.objects.create(prefix="cccc::1/128", status=self.status, namespace=self.namespace)
        IPAddress.objects.create(address="cccc::1/128", status=self.status, namespace=self.namespace)
        self.assertEqual(slash128.get_utilization(), (1, 1))
        slash32 = Prefix.objects.create(prefix="1.1.1.1/32", status=self.status, namespace=self.namespace)
        IPAddress.objects.create(address="1.1.1.1/32", status=self.status, namespace=self.namespace)
        self.assertEqual(slash32.get_utilization(), (1, 1))

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

        # https://github.com/nautobot/nautobot/issues/3319
        v4_10dot_address_space_in_v6 = Prefix.objects.create(
            prefix="0a00::/8", type=PrefixTypeChoices.TYPE_NETWORK, status=self.status, namespace=self.namespace
        )
        self.assertSequenceEqual(v4_10dot_address_space_in_v6.get_utilization(), (0, 2**120))

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
        Prefix.objects.create(
            prefix="12.0.0.0/24", status=self.status, namespace=namespace, type=PrefixTypeChoices.TYPE_POOL
        )

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
            self.assertEqual(ip.parent, pool)
            pool.delete()
            ip.refresh_from_db()
            self.assertEqual(ip.parent, network)

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

    def test_get_or_create(self):
        """Assert `get_or_create` method to permit specifying a namespace as an alternative to a parent prefix."""
        default_namespace = get_default_namespace()
        namespace = Namespace.objects.create(name="Test Namespace")

        ipaddr_status = Status.objects.get_for_model(IPAddress).first()
        prefix_status = Status.objects.get_for_model(Prefix).first()

        parent = Prefix.objects.create(prefix="10.1.1.0/24", namespace=namespace, status=prefix_status)
        default_namespace_parent = Prefix.objects.create(
            prefix="10.0.0.0/24", namespace=default_namespace, status=prefix_status
        )

        ipaddress = IPAddress.objects.create(address="10.1.1.1/24", namespace=namespace, status=ipaddr_status)
        default_namespace_ipaddress = IPAddress.objects.create(
            address="10.0.0.1/24", namespace=default_namespace, status=ipaddr_status
        )
        mask_length = 24

        with self.subTest("Assert retrieve"):
            ip_obj, created = IPAddress.objects.get_or_create(
                host=ipaddress.host,
                mask_length=mask_length,
                namespace=namespace,
                status=ipaddr_status,
            )
            self.assertEqual(ip_obj, ipaddress)
            self.assertFalse(created)

            ip_obj, created = IPAddress.objects.get_or_create(host=ipaddress.host, status=ipaddr_status)
            self.assertEqual(ip_obj.status, ipaddr_status)
            self.assertFalse(created)

        with self.subTest(
            "Assert get_or_create utilizes default namespace when retrieving parent if no namespace is provided"
        ):
            ip_obj, created = IPAddress.objects.get_or_create(
                host=default_namespace_ipaddress.host,
                mask_length=default_namespace_ipaddress.mask_length,
                status=ipaddr_status,
            )
            self.assertEqual(ip_obj, default_namespace_ipaddress)
            self.assertFalse(created)

        with self.subTest("Assert create"):
            new_host = "10.0.0.2"
            ip_obj, created = IPAddress.objects.get_or_create(
                host=new_host,
                mask_length=mask_length,
                status=ipaddr_status,
            )
            self.assertEqual(ip_obj.host, new_host)
            self.assertEqual(ip_obj.mask_length, mask_length)
            self.assertEqual(ip_obj.parent, default_namespace_parent)
            self.assertEqual(ip_obj.parent.namespace, default_namespace)
            self.assertTrue(created)

        with self.subTest("Assert create explicitly defining a non default namespace"):
            new_host = "10.1.1.2"
            ip_obj, created = IPAddress.objects.get_or_create(
                host=new_host, mask_length=mask_length, status=ipaddr_status, namespace=namespace
            )
            self.assertEqual(ip_obj.host, new_host)
            self.assertEqual(ip_obj.mask_length, mask_length)
            self.assertEqual(ip_obj.parent, parent)
            self.assertEqual(ip_obj.parent.namespace, namespace)
            self.assertTrue(created)

        with self.subTest("Assert passing invalid host/mask_length"):
            with self.assertRaises(ValidationError) as err:
                IPAddress.objects.get_or_create(
                    host="0.000.0", mask_length=mask_length, status=ipaddr_status, namespace=namespace
                )
            self.assertIn(
                "Enter a valid IPv4 or IPv6 address.",
                str(err.exception),
            )
            with self.assertRaises(ValidationError) as err:
                IPAddress.objects.get_or_create(
                    host=ipaddress.host, mask_length=5712, status=ipaddr_status, namespace=namespace
                )
            self.assertIn(
                f"{ipaddress.host}/5712 does not appear to be an IPv4 or IPv6 network.",
                str(err.exception),
            )

    def test_get_or_create_address_kwarg(self):
        status = Status.objects.get(name="Active")
        namespace = Namespace.objects.create(name="Test IPAddress get_or_create with address kwarg")
        Prefix.objects.create(prefix="10.0.0.0/24", namespace=namespace, status=status)
        ip_address, created = IPAddress.objects.get_or_create(
            address="10.0.0.40/32", namespace=namespace, defaults={"status": status}
        )
        self.assertEqual(ip_address.host, "10.0.0.40")
        self.assertEqual(ip_address.mask_length, 32)
        self.assertTrue(created)
        _, created = IPAddress.objects.get_or_create(
            address="10.0.0.40/32", namespace=namespace, defaults={"status": status}
        )
        self.assertFalse(created)
        self.assertTrue(IPAddress.objects.filter(address="10.0.0.40/32", parent__namespace=namespace).exists())

    def test_create_field_population(self):
        """Test that the various ways of creating an IPAddress result in correctly populated fields."""
        if self.namespace != get_default_namespace():
            prefix = Prefix.objects.create(prefix="192.0.2.0/24", status=self.status, namespace=get_default_namespace())
        else:
            prefix = self.prefix

        with self.subTest("Creation with an address"):
            ip = IPAddress(address="192.0.2.1/24", status=self.status)
            ip.save()
            self.assertEqual(ip.host, "192.0.2.1")
            self.assertEqual(ip.mask_length, 24)
            self.assertEqual(ip.type, IPAddressTypeChoices.TYPE_HOST)  # default value
            self.assertEqual(ip.parent, prefix)
            self.assertEqual(ip.ip_version, 4)

        with self.subTest("Creation with a host and mask_length"):
            ip = IPAddress(host="192.0.2.2", mask_length=24, status=self.status)
            ip.save()
            self.assertEqual(ip.host, "192.0.2.2")
            self.assertEqual(ip.mask_length, 24)
            self.assertEqual(ip.type, IPAddressTypeChoices.TYPE_HOST)  # default value
            self.assertEqual(ip.parent, prefix)
            self.assertEqual(ip.ip_version, 4)

        with self.subTest("Creation with conflicting values - address takes precedence"):
            ip = IPAddress(address="192.0.2.3/24", host="1.1.1.1", mask_length=32, ip_version=6, status=self.status)
            ip.save()
            self.assertEqual(ip.host, "192.0.2.3")
            self.assertEqual(ip.mask_length, 24)
            self.assertEqual(ip.type, IPAddressTypeChoices.TYPE_HOST)  # default value
            self.assertEqual(ip.parent, prefix)
            self.assertEqual(ip.ip_version, 4)

    #
    # Uniqueness enforcement tests
    #

    def test_duplicate_global_unique(self):
        """Test that duplicate IPs in the same Namespace raises an error."""
        IPAddress.objects.create(address="192.0.2.1/24", status=self.status, namespace=self.namespace)
        duplicate_ip = IPAddress(address="192.0.2.1/24", status=self.status, namespace=self.namespace)
        with self.assertRaises(ValidationError):
            duplicate_ip.full_clean()

    def test_multiple_nat_outside_list(self):
        """
        Test suite to test supporting nat_outside_list.
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

        with self.assertRaises(ValidationError) as err:
            IPAddress.objects.create(address="13.0.0.1/32", status=self.status, namespace=namespace)
        self.assertEqual(
            err.exception.message_dict["namespace"][0],
            "No suitable parent Prefix for 13.0.0.1 exists in Namespace test_parenting_constraints",
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
        # No namespace, and no appropriate parent in the default namespace --> error
        with self.assertRaises(ValidationError) as err:
            ip = IPAddress(address="1976:2023::1/128", status=self.status)
            ip.validated_save()
        self.assertIn("namespace", err.exception.message_dict)
        self.assertEqual(
            err.exception.message_dict["namespace"][0],
            "No suitable parent Prefix for 1976:2023::1 exists in Namespace Global",
        )

        # Appropriate parent exists in the default namespace --> no error
        Prefix.objects.create(
            prefix="1976:2023::/32",
            status=self.status,
            namespace=get_default_namespace(),
            type=PrefixTypeChoices.TYPE_NETWORK,
        )
        ip.validated_save()

    def test_change_parent_and_namespace(self):
        namespaces = (
            Namespace.objects.create(name="test_change_parent 1"),
            Namespace.objects.create(name="test_change_parent 2"),
        )
        prefixes = (
            Prefix.objects.create(
                prefix="10.0.0.0/8", status=self.status, namespace=namespaces[0], type=PrefixTypeChoices.TYPE_NETWORK
            ),
            Prefix.objects.create(
                prefix="10.0.0.0/16", status=self.status, namespace=namespaces[1], type=PrefixTypeChoices.TYPE_NETWORK
            ),
        )

        ip = IPAddress(address="10.0.0.1", status=self.status, namespace=namespaces[0])
        ip.validated_save()
        ip.refresh_from_db()
        self.assertEqual(ip.parent, prefixes[0])

        ip.parent = prefixes[1]
        ip.validated_save()
        ip.refresh_from_db()
        self.assertEqual(ip.parent, prefixes[1])

        ip._namespace = namespaces[0]
        ip.validated_save()
        self.assertEqual(ip.parent, prefixes[0])

    def test_change_host(self):
        ip = IPAddress.objects.create(address="192.0.2.1/32", status=self.status, namespace=self.namespace)
        self.assertEqual(ip.parent, self.prefix)

        ip.host = "192.168.1.1"
        with self.assertRaises(ValidationError) as cm:
            ip.validated_save()
        self.assertIn("Host address cannot be changed once created", str(cm.exception))

    def test_varbinary_ip_fields_with_empty_values_do_not_violate_not_null_constrains(self):
        # Assert that an error is triggered when the host is not provided.
        # Initially, VarbinaryIPField fields with None values are stored as the binary representation of b'',
        # thereby bypassing the Not Null Constraint check.
        with self.assertRaises(IntegrityError):
            IPAddress.objects.create(mask_length=32, status=self.status)


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
        vlangroup = VLANGroup.objects.create(name="VLAN Group 1", range="1-6")
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
        # Next out of range.
        VLAN.objects.bulk_create((VLAN(name="VLAN 6", vid=6, vlan_group=vlangroup, status=status),))
        self.assertEqual(vlangroup.get_next_available_vid(), None)

    def test_range_resize(self):
        vlangroup = VLANGroup.objects.create(name="VLAN Group 1", range="1-3")
        status = Status.objects.get_for_model(VLAN).first()
        VLAN.objects.bulk_create(
            (
                VLAN(name="VLAN 1", vid=1, vlan_group=vlangroup, status=status),
                VLAN(name="VLAN 2", vid=2, vlan_group=vlangroup, status=status),
                VLAN(name="VLAN 3", vid=3, vlan_group=vlangroup, status=status),
            )
        )
        with self.assertRaises(ValidationError) as exc:
            vlangroup.range = "1-2"
            vlangroup.validated_save()
        self.assertEqual(
            str(exc.exception), "{'range': ['VLAN group range may not be re-sized due to existing VLANs (IDs: 3).']}"
        )

    def test_assign_vlan_out_of_range(self):
        vlangroup = VLANGroup.objects.create(name="VLAN Group 1", range="1-2")
        status = Status.objects.get_for_model(VLAN).first()
        VLAN.objects.bulk_create(
            (
                VLAN(name="VLAN 1", vid=1, vlan_group=vlangroup, status=status),
                VLAN(name="VLAN 2", vid=2, vlan_group=vlangroup, status=status),
            )
        )
        with self.assertRaises(ValidationError) as exc:
            vlan = VLAN(name="VLAN 3", vid=3, vlan_group=vlangroup, status=status)
            vlan.validated_save()
        self.assertEqual(str(exc.exception), "{'vid': ['VLAN ID is not contained in VLAN Group range (1-2)']}")


class TestVLAN(ModelTestCases.BaseModelTestCase):
    model = VLAN

    def test_vlan_validation(self):
        location_type = LocationType.objects.get(name="Floor")  # Floors may not have VLANs according to our factory
        location = Location.objects.filter(location_type=location_type).first()
        vlan = VLAN(name="Group 1", vid=1, location=location)
        vlan.status = Status.objects.get_for_model(VLAN).first()
        with self.assertRaises(ValidationError) as cm:
            vlan.validated_save()
        self.assertIn(f"VLANs may not associate to Locations of types {[location_type.name]}", str(cm.exception))

    def test_location_validation(self):
        location_type = LocationType.objects.get(name="Floor")  # Floors may not have VLANs according to our factory
        location = Location.objects.filter(location_type=location_type).first()
        vlan = VLAN.objects.first()
        with self.assertRaises(ValidationError) as cm:
            location.vlans.add(vlan)
        self.assertIn(f"{location} is a Floor and may not have VLANs associated to it.", str(cm.exception))

    def test_location_queries(self):
        location = VLAN.objects.filter(locations__isnull=False).first().locations.first()

        with self.subTest("Assert filtering and excluding `location`"):
            self.assertQuerysetEqualAndNotEmpty(
                VLAN.objects.filter(location=location),
                VLAN.objects.filter(locations__in=[location]),
            )
            self.assertQuerysetEqualAndNotEmpty(
                VLAN.objects.exclude(location=location),
                VLAN.objects.exclude(locations__in=[location]),
            )
            self.assertQuerysetEqualAndNotEmpty(
                VLAN.objects.filter(location__in=[location]),
                VLAN.objects.filter(locations__in=[location]),
            )
            self.assertQuerysetEqualAndNotEmpty(
                VLAN.objects.exclude(location__in=[location]),
                VLAN.objects.exclude(locations__in=[location]),
            )

        # We use `assertQuerysetEqualAndNotEmpty` for test validation. Including a nullable field could lead
        # to flaky tests where querysets might return None, causing tests to fail. Therefore, we select
        # fields that consistently contain values to ensure reliable filtering.
        query_params = ["name", "location_type", "status"]

        for field_name in query_params:
            with self.subTest(f"Assert location__{field_name} query."):
                value = getattr(location, field_name)
                self.assertQuerysetEqualAndNotEmpty(
                    VLAN.objects.filter(**{f"location__{field_name}": value}),
                    VLAN.objects.filter(**{f"locations__{field_name}": value}),
                )
                self.assertQuerysetEqualAndNotEmpty(
                    VLAN.objects.exclude(**{f"location__{field_name}": value}),
                    VLAN.objects.exclude(**{f"locations__{field_name}": value}),
                )


class TestVRF(ModelTestCases.BaseModelTestCase):
    model = VRF
    # TODO(jathan): Add VRF model tests.
