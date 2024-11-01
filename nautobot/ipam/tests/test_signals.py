from django.test import TestCase

from nautobot.dcim.choices import InterfaceTypeChoices
from nautobot.dcim.models import Device, DeviceType, Interface, Location, Module, ModuleBay, ModuleType
from nautobot.extras.models import Role, Status
from nautobot.ipam.models import IPAddress, IPAddressToInterface, Namespace, Prefix


class IPAddressToInterfaceSignalTests(TestCase):

    def setUp(self):
        # Create required supporting objects
        self.namespace = Namespace.objects.first()
        self.status = Status.objects.get(name="Active")
        self.prefix = Prefix.objects.create(prefix="1.1.1.0/24", status=self.status, namespace=self.namespace)

        # Set up device and associated structures
        self.test_device = Device.objects.create(
            name="device1",
            role=Role.objects.get_for_model(Device).first(),
            device_type=DeviceType.objects.first(),
            location=Location.objects.get_for_model(Device).first(),
            status=Status.objects.get_for_model(Device).first(),
        )

        # Create a module bay on the device
        self.device_module_bay = ModuleBay.objects.create(parent_device=self.test_device, name="Test Bay")

        # Create a module with an interface and add it to the device bay
        self.module = Module.objects.create(module_type=ModuleType.objects.first(), status=Status.objects.get_for_model(Module).first(), parent_module_bay=self.device_module_bay)

        int_status = Status.objects.get_for_model(Interface).first()

        self.interface_module = Interface.objects.create(
            name="eth0_module",
            module=self.module,
            type=InterfaceTypeChoices.TYPE_1GE_FIXED,
            status=int_status,
        )

        # Create an interface directly on the device
        self.interface_device = Interface.objects.create(
            name="eth0_device",
            device=self.test_device,
            type=InterfaceTypeChoices.TYPE_1GE_FIXED,
            status=int_status,
        )

        self.test_device.installed_device = self.module  # Link the module to the bay
        self.test_device.save()

    def test_setup(self):
        """Test to verify that the setup has all components created as expected."""

        # Check if namespace, status, and prefix are correctly set up
        self.assertIsNotNone(self.namespace)
        self.assertIsNotNone(self.status)
        self.assertIsNotNone(self.prefix)
        self.assertEqual(self.prefix.status, self.status)
        self.assertEqual(self.prefix.namespace, self.namespace)

        # Verify the device is set up correctly
        self.assertIsNotNone(self.test_device)
        self.assertEqual(self.test_device.name, "device1")
        self.assertEqual(self.test_device.role, Role.objects.get_for_model(Device).first())
        self.assertEqual(self.test_device.device_type, DeviceType.objects.first())
        self.assertEqual(self.test_device.location, Location.objects.get_for_model(Device).first())
        self.assertEqual(self.test_device.status, Status.objects.get_for_model(Device).first())

        # Verify the module bay is created and associated with the device
        self.assertIsNotNone(self.device_module_bay)
        self.assertEqual(self.device_module_bay.parent_device, self.test_device)
        self.assertEqual(self.device_module_bay.name, "Test Bay")

        # Verify the module is created and installed in the module bay
        self.assertIsNotNone(self.module)
        self.assertEqual(self.module.module_type, ModuleType.objects.first())
        self.assertEqual(self.module.status, Status.objects.get_for_model(Module).first())
        self.assertEqual(self.module.parent_module_bay, self.device_module_bay)

        # Verify the module interface
        self.assertIsNotNone(self.interface_module)
        self.assertEqual(self.interface_module.name, "eth0_module")
        self.assertEqual(self.interface_module.module, self.module)
        self.assertEqual(self.interface_module.type, InterfaceTypeChoices.TYPE_1GE_FIXED)
        self.assertEqual(self.interface_module.status, Status.objects.get_for_model(Interface).first())

        # Verify the device interface
        self.assertIsNotNone(self.interface_device)
        self.assertEqual(self.interface_device.name, "eth0_device")
        self.assertEqual(self.interface_device.device, self.test_device)
        self.assertEqual(self.interface_device.type, InterfaceTypeChoices.TYPE_1GE_FIXED)
        self.assertEqual(self.interface_device.status, Status.objects.get_for_model(Interface).first())

        # Verify the device has the module installed
        self.assertEqual(self.test_device.installed_device, self.module)



    def test_primary_ip_retained_when_deleted_from_one_interface(self):
        """Test that primary_ip4 remains set when the same IP is assigned to both device and module interfaces, and deleted from one."""

        # Step 1: Create and assign the IP to both interfaces
        ip_address = IPAddress.objects.create(address="1.1.1.10/24", namespace=self.namespace, status=self.status)

        # Assign the IP to both the device and module interfaces
        assignment_device = IPAddressToInterface.objects.create(
            interface=self.interface_device,
            ip_address=ip_address,
        )
        assignment_module = IPAddressToInterface.objects.create(
            interface=self.interface_module,
            ip_address=ip_address,
        )

        # Assert that the IP has been assigned to both interfaces
        self.assertEqual(ip_address.interface_assignments.count(), 2)

        # Step 2: Verify that both assignments belong to interfaces on the same device
        for assignment in ip_address.interface_assignments.all():
            self.assertEqual(assignment.interface.parent, self.test_device)

        # Step 3: Set the primary IP on the device
        self.test_device.primary_ip4 = assignment_device.ip_address
        self.test_device.save()

        # Verify the primary IP is correctly set on the device
        self.test_device.refresh_from_db()
        self.assertEqual(self.test_device.primary_ip4, ip_address)

        # Step 4: Delete the device interface assignment to trigger pre_delete signal
        assignment_device.delete()

        # Step 5: Refresh the device instance and confirm primary_ip4 remains as long as another interface holds the IP
        self.test_device.refresh_from_db()
        self.assertEqual(self.test_device.primary_ip4, ip_address)

        # Step 6: Confirm the remaining IP assignments on the IP object
        remaining_assignments = ip_address.interface_assignments.all()
        self.assertEqual(remaining_assignments.count(), 1)
        self.assertIn(assignment_module, remaining_assignments)




    def test_primary_ip_nullified_when_removed_from_all_interfaces(self):
        """Test that primary_ip4 is nullified when the primary IP is removed from all interfaces."""
        # Create two IP addresses and set one as the primary IP
        ip_address1 = IPAddress.objects.create(address="1.1.1.10/24", namespace=self.namespace, status=self.status)
        ip_address2 = IPAddress.objects.create(address="1.1.1.11/24", namespace=self.namespace, status=self.status)
        self.test_device.primary_ip4 = ip_address1
        self.test_device.save()

        # Assign IP addresses to both interfaces
        assignment_device = IPAddressToInterface.objects.create(
            interface=self.interface_device,
            ip_address=ip_address1,
        )
        assignment_module = IPAddressToInterface.objects.create(
            interface=self.interface_module,
            ip_address=ip_address2,
        )

        # Remove the primary IP from all interfaces
        assignment_device.delete()

        # Refresh device instance and check if primary_ip4 is nullified
        self.test_device.refresh_from_db()
        self.assertIsNone(self.test_device.primary_ip4)
