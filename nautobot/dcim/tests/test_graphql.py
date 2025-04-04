from django.contrib.contenttypes.models import ContentType
from django.test import override_settings

from nautobot.core.graphql import execute_query
from nautobot.core.testing import create_test_user, TestCase
from nautobot.dcim.choices import InterfaceTypeChoices
from nautobot.dcim.models import (
    Controller,
    Device,
    DeviceType,
    Interface,
    Location,
    LocationType,
    Manufacturer,
    Platform,
)
from nautobot.extras.models import DynamicGroup, Role, Status


class GraphQLTestCase(TestCase):
    def setUp(self):
        Controller.objects.filter(controller_device__isnull=False).delete()
        Device.objects.all().delete()
        self.user = create_test_user("graphql_testuser")
        self.location = Location.objects.filter(location_type=LocationType.objects.get(name="Campus")).first()
        self.device_role = Role.objects.get_for_model(Device).first()
        self.manufacturer = Manufacturer.objects.first()
        self.platform = Platform.objects.create(name="Platform", network_driver="cisco_ios")
        self.device_type = DeviceType.objects.create(model="Model", manufacturer=self.manufacturer)
        device_status = Status.objects.get_for_model(Device).first()
        self.device = Device.objects.create(
            location=self.location,
            role=self.device_role,
            device_type=self.device_type,
            name="Device",
            status=device_status,
            platform=self.platform,
        )
        interface_status = Status.objects.get_for_model(Interface).first()
        self.interfaces = (
            Interface(
                device=self.device,
                name="eth0",
                status=interface_status,
                type=InterfaceTypeChoices.TYPE_VIRTUAL,
                mac_address="11:22:33:44:55:66",
            ),
            Interface(
                device=self.device,
                name="eth1",
                status=interface_status,
                type=InterfaceTypeChoices.TYPE_VIRTUAL,
                mac_address=None,
            ),
        )
        for interface in self.interfaces:
            interface.validated_save()
        self.dynamic_group = DynamicGroup.objects.create(
            name="Dynamic_Group", content_type=ContentType.objects.get_for_model(Device)
        )

    @override_settings(EXEMPT_VIEW_PERMISSIONS=["*"])
    def test_execute_query(self):
        with self.subTest("device dynamic groups and interfaces query"):
            query = "query {devices {name interfaces {name mac_address} dynamic_groups {name}}}"
            resp = execute_query(query, user=self.user).to_dict()
            self.assertFalse(resp["data"].get("error"))
            self.assertEqual(
                resp["data"]["devices"][0]["interfaces"][0]["mac_address"], str(self.interfaces[0].mac_address)
            )
            self.assertIsNone(resp["data"]["devices"][0]["interfaces"][1]["mac_address"])
            self.assertEqual(resp["data"]["devices"][0]["dynamic_groups"][0]["name"], self.dynamic_group.name)

        with self.subTest("device platform drivers query"):
            query = "query {devices {platform {network_driver network_driver_mappings}}}"
            resp = execute_query(query, user=self.user).to_dict()
            self.assertFalse(resp["data"].get("error"))
            self.assertEqual(resp["data"]["devices"][0]["platform"]["network_driver"], "cisco_ios")
            self.assertEqual(
                resp["data"]["devices"][0]["platform"]["network_driver_mappings"]["ansible"], "cisco.ios.ios"
            )
            self.assertEqual(resp["data"]["devices"][0]["platform"]["network_driver_mappings"]["netmiko"], "cisco_ios")
            self.assertEqual(
                resp["data"]["devices"][0]["platform"]["network_driver_mappings"]["scrapli"], "cisco_iosxe"
            )

        with self.subTest("device serial number query"):
            non_empty_serial_device = Device.objects.first()
            non_empty_serial_device.serial = "1234567890abceFGHIJKL"
            non_empty_serial_device.save()

            # Test device serial query default behavior: serial__ie
            query = 'query { devices (serial: " ") { name serial } }'
            resp = execute_query(query, user=self.user).to_dict()
            self.assertFalse(resp["data"].get("error"))
            for device in resp["data"]["devices"]:
                self.assertEqual(device["serial"], "")

            # Test device serial default filter with non-empty serial number
            query = 'query { devices (serial:"' + non_empty_serial_device.serial.lower() + '") { name serial } }'
            resp = execute_query(query, user=self.user).to_dict()
            self.assertFalse(resp["data"].get("error"))
            self.assertEqual(resp["data"]["devices"][0]["serial"], non_empty_serial_device.serial)

            # Test device serial iexact filter with non-empty serial number
            query = 'query { devices (serial__ie:"' + non_empty_serial_device.serial.upper() + '") { name serial } }'
            resp = execute_query(query, user=self.user).to_dict()
            self.assertFalse(resp["data"].get("error"))
            self.assertEqual(resp["data"]["devices"][0]["serial"], non_empty_serial_device.serial)

            # Test device serial__nie filter with non-empty serial number
            query = 'query { devices (serial__nie:"' + non_empty_serial_device.serial.lower() + '") { name serial } }'
            resp = execute_query(query, user=self.user).to_dict()
            self.assertFalse(resp["data"].get("error"))
            for device in resp["data"]["devices"]:
                self.assertNotEqual(device["serial"], non_empty_serial_device.serial)

            # Test device serial__ie filter with empty serial number
            query = 'query { devices (serial__ie:" ") { name serial } }'
            resp = execute_query(query, user=self.user).to_dict()
            self.assertFalse(resp["data"].get("error"))
            for device in resp["data"]["devices"]:
                self.assertEqual(device["serial"], "")

            # Test device serial__nie filter with empty serial number
            query = 'query { devices (serial__nie:" ") { name serial } }'
            resp = execute_query(query, user=self.user).to_dict()
            self.assertFalse(resp["data"].get("error"))
            for device in resp["data"]["devices"]:
                self.assertNotEqual(device["serial"], "")

            # Test device serial__n filter with empty serial number
            query = 'query { devices (serial__n:" ") { name serial } }'
            resp = execute_query(query, user=self.user).to_dict()
            self.assertFalse(resp["data"].get("error"))
            for device in resp["data"]["devices"]:
                self.assertNotEqual(device["serial"], "")
