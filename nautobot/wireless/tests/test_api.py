from nautobot.core.testing import APIViewTestCases
from nautobot.dcim.models import Controller, Device
from nautobot.extras.models import SecretsGroup
from nautobot.ipam.models import VLAN
from nautobot.tenancy.models import Tenant
from nautobot.wireless import models


class AccessPointGroupTest(APIViewTestCases.APIViewTestCase):
    model = models.AccessPointGroup

    @classmethod
    def setUpTestData(cls):
        tenants = Tenant.objects.all()
        controllers = Controller.objects.all()
        models.AccessPointGroup.objects.create(
            name="Access Point Group 1", controller=controllers[0], tenant=tenants[0]
        )
        models.AccessPointGroup.objects.create(
            name="Access Point Group 2", controller=controllers[1], tenant=tenants[1]
        )
        models.AccessPointGroup.objects.create(
            name="Access Point Group 3", controller=controllers[2], tenant=tenants[2]
        )
        cls.create_data = [
            {
                "name": "Access Point Group 4",
                "controller": controllers[3].pk,
                "tenant": tenants[3].pk,
                "description": "This is access point group 4",
            },
            {
                "name": "Access Point Group 5",
                "controller": controllers[4].pk,
            },
            {
                "name": "Access Point Group 6",
            },
        ]
        cls.bulk_update_data = {
            "controller": controllers[6].pk,
            "tenant": tenants[6].pk,
        }


class SupportedDataRateTest(APIViewTestCases.APIViewTestCase):
    model = models.SupportedDataRate
    choices_fields = ["standard"]

    @classmethod
    def setUpTestData(cls):
        models.SupportedDataRate.objects.create(rate=1000, standard="802.11b", mcs_index=1)
        models.SupportedDataRate.objects.create(rate=6000, standard="802.11g", mcs_index=2)
        models.SupportedDataRate.objects.create(rate=54000, standard="802.11n", mcs_index=3)
        cls.create_data = [
            {
                "rate": 200000,
                "standard": "802.11ac",
                "mcs_index": 4,
            },
            {
                "rate": 574000,
                "standard": "802.11ax",
                "mcs_index": 5,
            },
            {
                "rate": 20000000,
                "standard": "802.11be",
                "mcs_index": 6,
            },
        ]
        cls.bulk_update_data = {
            "standard": "802.11a",
            "mcs_index": 7,
        }


class RadioProfileTest(APIViewTestCases.APIViewTestCase):
    model = models.RadioProfile
    choices_fields = ["frequency", "regulatory_domain"]

    @classmethod
    def setUpTestData(cls):
        models.RadioProfile.objects.create(
            name="Radio Profile 1",
            frequency="2.4GHz",
            tx_power_min=5,
            tx_power_max=15,
            rx_power_min=-70,
            regulatory_domain="US",
            allowed_channel_list=[1, 6, 11],
        )
        models.RadioProfile.objects.create(
            name="Radio Profile 2",
            frequency="5GHz",
            tx_power_min=10,
            tx_power_max=20,
            rx_power_min=-75,
            regulatory_domain="GB",
            allowed_channel_list=[36, 40, 44],
        )
        models.RadioProfile.objects.create(
            name="Radio Profile 3",
            frequency="6GHz",
            tx_power_min=15,
            tx_power_max=25,
            rx_power_min=-80,
            regulatory_domain="JP",
            allowed_channel_list=[],
        )
        cls.create_data = [
            {
                "name": "Radio Profile 4",
                "frequency": "2.4GHz",
                "tx_power_min": 10,
                "tx_power_max": 20,
                "channel_width": [20, 40],
                "allowed_channel_list": [1, 6, 11],
                "regulatory_domain": "US",
                "rx_power_min": -80,
            },
            {
                "name": "Radio Profile 5",
                "channel_width": [80, 160],
                "frequency": "5GHz",
                "regulatory_domain": "AU",
                "rx_power_min": 5,
                "allowed_channel_list": [36, 40, 44],
            },
            {
                "name": "Radio Profile 6",
                "channel_width": [
                    20,
                ],
                "frequency": "6GHz",
                "regulatory_domain": "CA",
                "tx_power_min": 20,
                "allowed_channel_list": [],
            },
        ]
        cls.bulk_update_data = {
            "frequency": "5GHz",
            "tx_power_min": 5,
            "regulatory_domain": "GB",
        }


class WirelessNetworkTest(APIViewTestCases.APIViewTestCase):
    model = models.WirelessNetwork
    choices_fields = ["mode", "authentication"]

    @classmethod
    def setUpTestData(cls):
        SecretsGroup.objects.create(name="Secrets Group 1")
        tenants = Tenant.objects.all()
        models.WirelessNetwork.objects.create(
            name="Wireless Network 1",
            tenant=tenants[0],
            authentication="WPA3 Enterprise",
            ssid="ssid1",
            mode="Local (Flex)",
        )
        models.WirelessNetwork.objects.create(
            name="Wireless Network 2", tenant=tenants[1], authentication="WPA3 Personal", ssid="ssid2", mode="Mesh"
        )
        models.WirelessNetwork.objects.create(
            name="Wireless Network 3", tenant=tenants[2], authentication="Open", ssid="ssid3", mode="Bridge"
        )
        cls.create_data = [
            {
                "name": "Wireless Network 4",
                "description": "This is wireless network 4",
                "ssid": "ssid4",
                "mode": "Central (tunnelMode(controller managed))",
                "enabled": True,
                "authentication": "WPA2 Personal",
                "secrets_group": SecretsGroup.objects.first().pk,
                "hidden": False,
                "tenant": tenants[3].pk,
            },
            {
                "name": "Wireless Network 5",
                "tenant": tenants[4].pk,
                "authentication": "WPA2 Enterprise",
                "ssid": "ssid5",
                "mode": "Standalone (Autonomous)",
            },
            {
                "name": "Wireless Network 6",
                "tenant": tenants[5].pk,
                "authentication": "WPA3 Personal",
                "ssid": "ssid6",
                "mode": "Fabric",
            },
        ]
        cls.bulk_update_data = {
            "tenant": tenants[6].pk,
        }


class AccessPointGroupDeviceAssignmentTest(APIViewTestCases.APIViewTestCase):
    model = models.AccessPointGroupDeviceAssignment

    @classmethod
    def setUpTestData(cls):
        access_point_groups = models.AccessPointGroup.objects.all()[:3]
        cls.create_data = [
            {
                "access_point_group": access_point_groups[0].pk,
                "device": Device.objects.exclude(access_point_groups=access_point_groups[0]).first().pk,
            },
            {
                "access_point_group": access_point_groups[1].pk,
                "device": Device.objects.exclude(access_point_groups=access_point_groups[1]).first().pk,
            },
            {
                "access_point_group": access_point_groups[2].pk,
                "device": Device.objects.exclude(access_point_groups=access_point_groups[2]).first().pk,
            },
        ]


class AccessPointGroupRadioProfileAssignmentTest(APIViewTestCases.APIViewTestCase):
    model = models.AccessPointGroupRadioProfileAssignment

    @classmethod
    def setUpTestData(cls):
        access_point_groups = models.AccessPointGroup.objects.all()[:3]
        cls.create_data = [
            {
                "access_point_group": access_point_groups[0].pk,
                "radio_profile": models.RadioProfile.objects.exclude(access_point_groups=access_point_groups[0])
                .first()
                .pk,
            },
            {
                "access_point_group": access_point_groups[1].pk,
                "radio_profile": models.RadioProfile.objects.exclude(access_point_groups=access_point_groups[1])
                .first()
                .pk,
            },
            {
                "access_point_group": access_point_groups[2].pk,
                "radio_profile": models.RadioProfile.objects.exclude(access_point_groups=access_point_groups[2])
                .first()
                .pk,
            },
        ]


class AccessPointGroupWirelessNetworkAssignmentTest(APIViewTestCases.APIViewTestCase):
    model = models.AccessPointGroupWirelessNetworkAssignment

    @classmethod
    def setUpTestData(cls):
        vlans = VLAN.objects.all()
        access_point_groups = models.AccessPointGroup.objects.all()[:3]
        cls.create_data = [
            {
                "access_point_group": access_point_groups[0].pk,
                "wireless_network": models.WirelessNetwork.objects.exclude(access_point_groups=access_point_groups[0])
                .first()
                .pk,
                "vlan": vlans[0].pk,
            },
            {
                "access_point_group": access_point_groups[1].pk,
                "wireless_network": models.WirelessNetwork.objects.exclude(access_point_groups=access_point_groups[1])
                .first()
                .pk,
                "vlan": vlans[1].pk,
            },
            {
                "access_point_group": access_point_groups[2].pk,
                "wireless_network": models.WirelessNetwork.objects.exclude(access_point_groups=access_point_groups[2])
                .first()
                .pk,
            },
        ]
