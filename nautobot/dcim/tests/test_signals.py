"""Tests for DCIM Signals.py """

from django.test import TestCase

from nautobot.dcim.models import (
    Device,
    DeviceRole,
    DeviceType,
    Manufacturer,
    Site,
    VirtualChassis,
)


class VirtualChassisTest(TestCase):
    """Class to test signals for VirtualChassis."""

    def setUp(self):
        """Setup Test Data for VirtualChassis Signal tests."""
        site = Site.objects.first()
        manufacturer = Manufacturer.objects.create(name="Manufacturer 1", slug="manufacturer-1")
        devicetype = DeviceType.objects.create(manufacturer=manufacturer, model="Device Type", slug="device-type")
        devicerole = DeviceRole.objects.create(name="Device Role", slug="device-role", color="ff0000")

        self.device = Device.objects.create(
            name="Device 1",
            device_type=devicetype,
            device_role=devicerole,
            site=site,
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
