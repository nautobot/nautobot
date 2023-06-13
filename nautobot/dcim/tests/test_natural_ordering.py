from django.test import TestCase

from nautobot.dcim.models import (
    Device,
    DeviceType,
    Interface,
    Location,
    LocationType,
    Manufacturer,
)
from nautobot.extras.models import Role, Status


class NaturalOrderingTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        location = Location.objects.filter(location_type=LocationType.objects.get(name="Campus")).first()
        manufacturer = Manufacturer.objects.first()
        devicetype = DeviceType.objects.create(
            manufacturer=manufacturer,
            model="Test Device Type 1",
        )
        devicerole = Role.objects.get_for_model(Device).first()
        devicestatus = Status.objects.get_for_model(Device).first()
        cls.device = Device.objects.create(
            device_type=devicetype, role=devicerole, name="Test Device 1", location=location, status=devicestatus
        )
        cls.interface_status = Status.objects.get_for_model(Interface).first()

    def test_interface_ordering_numeric(self):
        INTERFACES = [
            "0",
            "0.0",
            "0.1",
            "0.2",
            "0.10",
            "0.100",
            "0:1",
            "0:1.0",
            "0:1.1",
            "0:1.2",
            "0:1.10",
            "0:2",
            "0:2.0",
            "0:2.1",
            "0:2.2",
            "0:2.10",
            "1",
            "1.0",
            "1.1",
            "1.2",
            "1.10",
            "1.100",
            "1:1",
            "1:1.0",
            "1:1.1",
            "1:1.2",
            "1:1.10",
            "1:2",
            "1:2.0",
            "1:2.1",
            "1:2.2",
            "1:2.10",
        ]

        for name in INTERFACES:
            iface = Interface(device=self.device, name=name, status=self.interface_status)
            iface.save()

        self.assertListEqual(
            list(Interface.objects.filter(device=self.device).values_list("name", flat=True)),
            INTERFACES,
        )

    def test_interface_ordering_linux(self):
        INTERFACES = [
            "eth0",
            "eth0.1",
            "eth0.2",
            "eth0.10",
            "eth0.100",
            "eth1",
            "eth1.1",
            "eth1.2",
            "eth1.100",
            "lo0",
        ]

        for name in INTERFACES:
            iface = Interface(device=self.device, name=name, status=self.interface_status)
            iface.save()

        self.assertListEqual(
            list(Interface.objects.filter(device=self.device).values_list("name", flat=True)),
            INTERFACES,
        )

    def test_interface_ordering_junos(self):
        INTERFACES = [
            "xe-0/0/0",
            "xe-0/0/1",
            "xe-0/0/2",
            "xe-0/0/3",
            "xe-0/1/0",
            "xe-0/1/1",
            "xe-0/1/2",
            "xe-0/1/3",
            "xe-1/0/0",
            "xe-1/0/1",
            "xe-1/0/2",
            "xe-1/0/3",
            "xe-1/1/0",
            "xe-1/1/1",
            "xe-1/1/2",
            "xe-1/1/3",
            "xe-2/0/0.1",
            "xe-2/0/0.2",
            "xe-2/0/0.10",
            "xe-2/0/0.11",
            "xe-2/0/0.100",
            "xe-3/0/0:1",
            "xe-3/0/0:2",
            "xe-3/0/0:10",
            "xe-3/0/0:11",
            "xe-3/0/0:100",
            "xe-10/1/0",
            "xe-10/1/1",
            "xe-10/1/2",
            "xe-10/1/3",
            "ae1",
            "ae2",
            "ae10.1",
            "ae10.10",
            "irb.1",
            "irb.2",
            "irb.10",
            "irb.100",
            "lo0",
        ]

        for name in INTERFACES:
            iface = Interface(device=self.device, name=name, status=self.interface_status)
            iface.save()

        self.assertListEqual(
            list(Interface.objects.filter(device=self.device).values_list("name", flat=True)),
            INTERFACES,
        )

    def test_interface_ordering_ios(self):
        INTERFACES = [
            "GigabitEthernet0/1",
            "GigabitEthernet0/2",
            "GigabitEthernet0/10",
            "TenGigabitEthernet0/20",
            "TenGigabitEthernet0/21",
            "GigabitEthernet1/1",
            "GigabitEthernet1/2",
            "GigabitEthernet1/10",
            "TenGigabitEthernet1/20",
            "TenGigabitEthernet1/21",
            "FastEthernet1",
            "FastEthernet2",
            "FastEthernet10",
        ]

        for name in INTERFACES:
            iface = Interface(device=self.device, name=name, status=self.interface_status)
            iface.save()

        self.assertListEqual(
            list(Interface.objects.filter(device=self.device).values_list("name", flat=True)),
            INTERFACES,
        )
