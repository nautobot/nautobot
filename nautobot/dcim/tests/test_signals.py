"""Tests for DCIM Signals.py"""

from django.test import TestCase

from nautobot.dcim.models import (
    Controller,
    Device,
    DeviceRedundancyGroup,
    DeviceType,
    Location,
    LocationType,
    Manufacturer,
    VirtualChassis,
)
from nautobot.extras.models import Role, Status


class VirtualChassisTest(TestCase):
    """Class to test signals for VirtualChassis."""

    @classmethod
    def setUpTestData(cls):
        """Setup Test Data for VirtualChassis Signal tests."""
        location = Location.objects.filter(location_type=LocationType.objects.get(name="Campus")).first()
        manufacturer = Manufacturer.objects.first()
        devicetype = DeviceType.objects.create(manufacturer=manufacturer, model="Device Type")
        devicerole = Role.objects.get_for_model(Device).first()
        devicestatus = Status.objects.get_for_model(Device).first()

        cls.device = Device.objects.create(
            name="Device 1",
            device_type=devicetype,
            role=devicerole,
            status=devicestatus,
            location=location,
        )

    def test_master_device_vc_assignment(self):
        """Test device assigned vc_position keeps assignment after being set to master.

        This test is for https://github.com/nautobot/nautobot/issues/393
        """
        self.device.vc_position = 3
        self.device.save()
        self.assertEqual(self.device.vc_position, 3)
        virtualchassis = VirtualChassis.objects.create(name="Virtual Chassis 1", master=self.device, domain="domain-1")
        self.device.refresh_from_db()
        self.assertEqual(self.device.vc_position, 3)
        self.assertEqual(self.device.virtual_chassis, virtualchassis)

    def test_master_device_vc_position_is_0(self):
        """Test device assigned vc_position 0 keeps assignment after being set to master.

        This test is for https://github.com/nautobot/nautobot/issues/393
        """
        self.device.vc_position = 0
        self.device.save()
        self.assertEqual(self.device.vc_position, 0)
        virtualchassis = VirtualChassis.objects.create(name="Virtual Chassis 1", master=self.device, domain="domain-1")
        self.device.refresh_from_db()
        self.assertEqual(self.device.vc_position, 0)
        self.assertEqual(self.device.virtual_chassis, virtualchassis)

    def test_master_device_null_vc_assignment(self):
        """Test device with null vc_position gets assigned 1 after being set to master.

        This test is for https://github.com/nautobot/nautobot/issues/393
        """
        self.assertIsNone(self.device.vc_position)
        virtualchassis = VirtualChassis.objects.create(name="Virtual Chassis 1", master=self.device, domain="domain-1")
        self.device.refresh_from_db()
        self.assertEqual(self.device.vc_position, 1)
        self.assertEqual(self.device.virtual_chassis, virtualchassis)


class DeviceRedundancyGroupTest(TestCase):
    """Class to test signals for DeviceRedundancyGroup."""

    @classmethod
    def setUpTestData(cls):
        """Setup Test Data for DeviceRedundancyGroup Signal tests."""
        location = Location.objects.filter(location_type=LocationType.objects.get(name="Campus")).first()
        manufacturer = Manufacturer.objects.first()
        devicetype = DeviceType.objects.create(manufacturer=manufacturer, model="Device Type")
        devicerole = Role.objects.get_for_model(Device).first()
        devicestatus = Status.objects.get_for_model(Device).first()

        cls.device = Device.objects.create(
            name="Device 1",
            device_type=devicetype,
            role=devicerole,
            status=devicestatus,
            location=location,
        )

    def test_device_redundancy_group_priority_is_null(self):
        """Test device with not null device_redundancy_group_priority is null after its device redundancy group is deleted.

        This test is for https://github.com/nautobot/nautobot/issues/4718
        """
        deviceredundancygroup = DeviceRedundancyGroup.objects.first()

        self.device.device_redundancy_group = deviceredundancygroup
        self.device.device_redundancy_group_priority = 1
        self.device.validated_save()

        # Protected FK constraint prevents deletion of DeviceRedundancyGroup
        Controller.objects.all().delete()
        deviceredundancygroup.delete()

        self.device.refresh_from_db()

        self.assertIsNone(self.device.device_redundancy_group)
        self.assertIsNone(self.device.device_redundancy_group_priority)
