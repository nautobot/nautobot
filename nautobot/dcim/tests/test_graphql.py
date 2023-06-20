from django.contrib.contenttypes.models import ContentType
from django.test import override_settings

from nautobot.core.graphql import execute_query
from nautobot.core.testing import create_test_user, TestCase
from nautobot.dcim.choices import InterfaceTypeChoices
from nautobot.dcim.models import Device, DeviceType, Interface, Location, LocationType, Manufacturer
from nautobot.extras.models import DynamicGroup, Role, Status


class GraphQLTestCase(TestCase):
    def setUp(self):
        self.user = create_test_user("graphql_testuser")
        self.location = Location.objects.filter(location_type=LocationType.objects.get(name="Campus")).first()
        self.device_role = Role.objects.get_for_model(Device).first()
        self.manufacturer = Manufacturer.objects.first()
        self.device_type = DeviceType.objects.create(model="Model", manufacturer=self.manufacturer)
        device_status = Status.objects.get_for_model(Device).first()
        self.device = Device.objects.create(
            location=self.location,
            role=self.device_role,
            device_type=self.device_type,
            name="Device",
            status=device_status,
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
        query = "query {devices {name interfaces {name mac_address} dynamic_groups {name}}}"
        resp = execute_query(query, user=self.user).to_dict()
        self.assertFalse(resp["data"].get("error"))
        self.assertEqual(
            resp["data"]["devices"][0]["interfaces"][0]["mac_address"], str(self.interfaces[0].mac_address)
        )
        self.assertIsNone(resp["data"]["devices"][0]["interfaces"][1]["mac_address"])
        self.assertEqual(resp["data"]["devices"][0]["dynamic_groups"][0]["name"], self.dynamic_group.name)
