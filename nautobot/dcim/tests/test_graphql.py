from django.contrib.contenttypes.models import ContentType
from django.test import override_settings

from nautobot.core.graphql import execute_query
from nautobot.core.testing import create_test_user, TestCase
from nautobot.dcim.choices import (
    InterfaceDuplexChoices,
    InterfaceSpeedChoices,
    InterfaceTypeChoices,
    PortTypeChoices,
    SubdeviceRoleChoices,
)
from nautobot.dcim.models import (
    ConsolePortTemplate,
    ConsoleServerPortTemplate,
    Controller,
    Device,
    DeviceBayTemplate,
    DeviceType,
    FrontPortTemplate,
    Interface,
    InterfaceTemplate,
    Location,
    LocationType,
    Manufacturer,
    ModuleBayTemplate,
    Platform,
    PowerOutletTemplate,
    PowerPortTemplate,
    RearPortTemplate,
)
from nautobot.extras.models import DynamicGroup, Role, Status
from nautobot.users.models import ObjectPermission


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
        self.parent_device_type = DeviceType.objects.create(
            model="Parent Model",
            manufacturer=self.manufacturer,
            subdevice_role=SubdeviceRoleChoices.ROLE_PARENT,
        )
        self.console_port_template = ConsolePortTemplate.objects.create(
            device_type=self.device_type,
            name="Console Port 1",
        )
        self.console_server_port_template = ConsoleServerPortTemplate.objects.create(
            device_type=self.device_type,
            name="Console Server Port 1",
        )
        self.power_port_template = PowerPortTemplate.objects.create(
            device_type=self.device_type,
            name="Power Port 1",
        )
        self.power_outlet_template = PowerOutletTemplate.objects.create(
            device_type=self.device_type,
            name="Power Outlet 1",
        )
        self.interface_template = InterfaceTemplate.objects.create(
            device_type=self.device_type,
            name="eth0-template",
            type=InterfaceTypeChoices.TYPE_1GE_FIXED,
        )
        self.rear_port_template = RearPortTemplate.objects.create(
            device_type=self.device_type,
            name="Rear Port 1",
            type=PortTypeChoices.TYPE_8P8C,
        )
        self.front_port_template = FrontPortTemplate.objects.create(
            device_type=self.device_type,
            name="Front Port 1",
            type=PortTypeChoices.TYPE_8P8C,
            rear_port_template=self.rear_port_template,
            rear_port_position=1,
        )
        self.device_bay_template = DeviceBayTemplate.objects.create(
            device_type=self.parent_device_type,
            name="Device Bay 1",
        )
        self.module_bay_template = ModuleBayTemplate.objects.create(
            device_type=self.device_type,
            name="Module Bay 1",
        )
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
            Interface.objects.create(
                device=self.device,
                name="eth2",
                status=interface_status,
                type=InterfaceTypeChoices.TYPE_1GE_FIXED,
                speed=InterfaceSpeedChoices.SPEED_1G,
                duplex=InterfaceDuplexChoices.DUPLEX_FULL,
            ),
            Interface.objects.create(
                device=self.device,
                name="eth3",
                status=interface_status,
                type=InterfaceTypeChoices.TYPE_10GE_SFP_PLUS,
                speed=InterfaceSpeedChoices.SPEED_10G,
                duplex="",
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
            resp = execute_query(query, user=self.user)
            self.assertIsNone(resp.errors)
            self.assertEqual(
                resp.data["devices"][0]["interfaces"][0]["mac_address"], str(self.interfaces[0].mac_address)
            )
            self.assertIsNone(resp.data["devices"][0]["interfaces"][1]["mac_address"])
            self.assertEqual(resp.data["devices"][0]["dynamic_groups"][0]["name"], self.dynamic_group.name)

        with self.subTest("device platform drivers query"):
            query = "query {devices {platform {network_driver network_driver_mappings}}}"
            resp = execute_query(query, user=self.user)
            self.assertIsNone(resp.errors)
            self.assertEqual(resp.data["devices"][0]["platform"]["network_driver"], "cisco_ios")
            self.assertEqual(resp.data["devices"][0]["platform"]["network_driver_mappings"]["ansible"], "cisco.ios.ios")
            self.assertEqual(resp.data["devices"][0]["platform"]["network_driver_mappings"]["netmiko"], "cisco_ios")
            self.assertEqual(resp.data["devices"][0]["platform"]["network_driver_mappings"]["scrapli"], "cisco_iosxe")

        with self.subTest("device serial number query"):
            non_empty_serial_device = Device.objects.first()
            non_empty_serial_device.serial = "1234567890abceFGHIJKL"
            non_empty_serial_device.save()

            # Test device serial query default behavior: serial__ie
            query = 'query { devices (serial: " ") { name serial } }'
            resp = execute_query(query, user=self.user)
            self.assertIsNone(resp.errors)
            for device in resp.data["devices"]:
                self.assertEqual(device["serial"], "")

            # Test device serial default filter with non-empty serial number
            query = 'query { devices (serial:"' + non_empty_serial_device.serial.lower() + '") { name serial } }'
            resp = execute_query(query, user=self.user)
            self.assertIsNone(resp.errors)
            self.assertEqual(resp.data["devices"][0]["serial"], non_empty_serial_device.serial)

            # Test device serial iexact filter with non-empty serial number
            query = 'query { devices (serial__ie:"' + non_empty_serial_device.serial.upper() + '") { name serial } }'
            resp = execute_query(query, user=self.user)
            self.assertIsNone(resp.errors)
            self.assertEqual(resp.data["devices"][0]["serial"], non_empty_serial_device.serial)

            # Test device serial__nie filter with non-empty serial number
            query = 'query { devices (serial__nie:"' + non_empty_serial_device.serial.lower() + '") { name serial } }'
            resp = execute_query(query, user=self.user)
            self.assertIsNone(resp.errors)
            for device in resp.data["devices"]:
                self.assertNotEqual(device["serial"], non_empty_serial_device.serial)

            # Test device serial__ie filter with empty serial number
            query = 'query { devices (serial__ie:" ") { name serial } }'
            resp = execute_query(query, user=self.user)
            self.assertIsNone(resp.errors)
            for device in resp.data["devices"]:
                self.assertEqual(device["serial"], "")

            # Test device serial__nie filter with empty serial number
            query = 'query { devices (serial__nie:" ") { name serial } }'
            resp = execute_query(query, user=self.user)
            self.assertIsNone(resp.errors)
            for device in resp.data["devices"]:
                self.assertNotEqual(device["serial"], "")

            # Test device serial__n filter with empty serial number
            query = 'query { devices (serial__n:" ") { name serial } }'
            resp = execute_query(query, user=self.user)
            self.assertIsNone(resp.errors)
            for device in resp.data["devices"]:
                self.assertNotEqual(device["serial"], "")

        with self.subTest("interface speed/duplex fields on device query"):
            query = "query { devices { name interfaces { name speed duplex } } }"
            resp = execute_query(query, user=self.user)
            self.assertFalse(resp.errors)
            interfaces = [i for d in resp.data["devices"] if d["name"] == self.device.name for i in d["interfaces"]]
            eth2 = next(i for i in interfaces if i["name"] == "eth2")
            eth3 = next(i for i in interfaces if i["name"] == "eth3")
            self.assertEqual(eth2["speed"], InterfaceSpeedChoices.SPEED_1G)
            self.assertEqual(eth2["duplex"].lower(), InterfaceDuplexChoices.DUPLEX_FULL)
            self.assertEqual(eth3["speed"], InterfaceSpeedChoices.SPEED_10G)
            self.assertEqual(eth3["duplex"], None)

        with self.subTest("interfaces root filter by speed and duplex"):
            query = f"query {{ interfaces(speed: {InterfaceSpeedChoices.SPEED_1G}) {{ name }} }}"
            resp = execute_query(query, user=self.user)
            self.assertFalse(resp.errors)
            names = {i["name"] for i in resp.data["interfaces"]}
            self.assertIn("eth2", names)
            self.assertNotIn("eth3", names)

            query = 'query { interfaces(duplex: ["full"]) { name } }'
            resp = execute_query(query, user=self.user)
            self.assertFalse(resp.errors)
            names = {i["name"] for i in resp.data["interfaces"]}
            self.assertIn("eth2", names)
            self.assertNotIn("eth3", names)

    @override_settings(EXEMPT_VIEW_PERMISSIONS=["*"])
    def test_query_optimizer_fk_resolution(self):
        """Test that nested forward FK fields don't cause N+1 queries.

        Regression test for graphene-django 3.x changes around FK resolution.
        """
        interface_status = Status.objects.get_for_model(Interface).first()

        # Amplify the N+1 issue by creating many interfaces with the same status object.
        for i in range(30):
            interface = Interface(
                device=self.device,
                name=f"eth_perf_{i}",
                status=interface_status,
                type=InterfaceTypeChoices.TYPE_VIRTUAL,
                mac_address=f"00:00:00:00:00:{i:02x}",
            )
            interface.validated_save()

        query = "query { interfaces { name status { name } } }"
        execute_query(query, user=self.user)  # prewarm

        with self.assertApproximateNumQueries(minimum=1, maximum=10):
            result = execute_query(query, user=self.user)

        self.assertIsNone(result.errors)

    @override_settings(EXEMPT_VIEW_PERMISSIONS=["*"])
    def test_query_component_templates(self):
        """Verify that all ComponentTemplateModel subclasses are queryable via GraphQL."""
        cases = [
            ("console_port_templates", self.console_port_template),
            ("console_server_port_templates", self.console_server_port_template),
            ("power_port_templates", self.power_port_template),
            ("power_outlet_templates", self.power_outlet_template),
            ("interface_templates", self.interface_template),
            ("rear_port_templates", self.rear_port_template),
            ("front_port_templates", self.front_port_template),
            ("device_bay_templates", self.device_bay_template),
            ("module_bay_templates", self.module_bay_template),
        ]
        for query_name, instance in cases:
            with self.subTest(query_name):
                query = f"{{ {query_name} {{ id name }} }}"
                resp = execute_query(query, user=self.user)
                self.assertIsNone(resp.errors)
                names = [t["name"] for t in resp.data[query_name]]
                self.assertIn(instance.name, names)


class GraphQLFKPermissionTest(GraphQLTestCase):
    def setUp(self):
        super().setUp()

        self.interface_content_type = ContentType.objects.get_for_model(Interface)
        self.status_content_type = ContentType.objects.get_for_model(Status)

        interface_statuses = list(Status.objects.get_for_model(Interface).order_by("name"))
        self.allowed_status = interface_statuses[0]
        if len(interface_statuses) > 1:
            self.denied_status = interface_statuses[1]
        else:
            # Ensure we have a distinct status object we can explicitly deny via ObjectPermission constraints.
            self.denied_status = Status.objects.create(name="DeniedStatusForGraphQLFKTest")
            self.denied_status.content_types.add(self.interface_content_type)

        allowed_status_perm = ObjectPermission.objects.create(
            name="View Status allowed",
            actions=["view"],
            constraints={"name": self.allowed_status.name},
        )
        allowed_status_perm.object_types.add(self.status_content_type)
        allowed_status_perm.users.add(self.user)

    @override_settings(EXEMPT_VIEW_PERMISSIONS=[])
    def test_status_id_lookup_enforces_object_permissions(self):
        query = "query ($id: ID!) { status(id: $id) { name } }"

        allowed_result = execute_query(query, user=self.user, variables={"id": str(self.allowed_status.pk)})
        self.assertIsNone(allowed_result.errors)
        self.assertIsNotNone(allowed_result.data["status"])
        self.assertEqual(allowed_result.data["status"]["name"], self.allowed_status.name)

        denied_result = execute_query(query, user=self.user, variables={"id": str(self.denied_status.pk)})
        self.assertIsNone(denied_result.errors)
        self.assertIsNone(denied_result.data["status"])
