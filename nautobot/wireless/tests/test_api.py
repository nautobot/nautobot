from nautobot.core.testing import APIViewTestCases
from nautobot.dcim.models import ControllerManagedDeviceGroup
from nautobot.extras.models import SecretsGroup
from nautobot.ipam.models import VLAN
from nautobot.tenancy.models import Tenant
from nautobot.wireless import choices, models


class SupportedDataRateTest(APIViewTestCases.APIViewTestCase):
    model = models.SupportedDataRate
    choices_fields = ["standard"]

    @classmethod
    def setUpTestData(cls):
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
            regulatory_domain=choices.RadioProfileRegulatoryDomainChoices.US,
            allowed_channel_list=[1, 6, 11],
            channel_width=[],
        )
        models.RadioProfile.objects.create(
            name="Radio Profile 2",
            frequency="5GHz",
            tx_power_min=10,
            tx_power_max=20,
            rx_power_min=-75,
            regulatory_domain=choices.RadioProfileRegulatoryDomainChoices.GB,
            allowed_channel_list=[36, 40, 44],
            channel_width=[20, 40, 160],
        )
        models.RadioProfile.objects.create(
            name="Radio Profile 3",
            frequency="6GHz",
            tx_power_min=15,
            tx_power_max=25,
            rx_power_min=-80,
            regulatory_domain=choices.RadioProfileRegulatoryDomainChoices.JP,
            allowed_channel_list=[],
            channel_width=[20],
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
                "channel_width": [],
                "frequency": "6GHz",
                "regulatory_domain": "CA",
                "tx_power_min": 20,
                "allowed_channel_list": [],
            },
            {
                "name": "Radio Profile 7",
                "frequency": "6GHz",
                "regulatory_domain": "US",
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
            authentication=choices.WirelessNetworkAuthenticationChoices.WPA2_PERSONAL,
            ssid="ssid1",
            mode=choices.WirelessNetworkModeChoices.LOCAL,
        )
        models.WirelessNetwork.objects.create(
            name="Wireless Network 2",
            tenant=tenants[1],
            authentication=choices.WirelessNetworkAuthenticationChoices.WPA2_ENTERPRISE,
            ssid="ssid2",
            mode=choices.WirelessNetworkModeChoices.MESH,
        )
        models.WirelessNetwork.objects.create(
            name="Wireless Network 3",
            tenant=tenants[2],
            authentication=choices.WirelessNetworkAuthenticationChoices.OPEN,
            ssid="ssid3",
            mode=choices.WirelessNetworkModeChoices.BRIDGE,
        )
        cls.create_data = [
            {
                "name": "Wireless Network 4",
                "description": "This is wireless network 4",
                "ssid": "ssid4",
                "mode": "Central",
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


class ControllerManagedDeviceGroupRadioProfileAssignmentTest(APIViewTestCases.APIViewTestCase):
    model = models.ControllerManagedDeviceGroupRadioProfileAssignment

    @classmethod
    def setUpTestData(cls):
        controller_managed_device_groups = ControllerManagedDeviceGroup.objects.all()[:3]
        cls.create_data = [
            {
                "controller_managed_device_group": controller_managed_device_groups[0].pk,
                "radio_profile": models.RadioProfile.objects.exclude(
                    controller_managed_device_groups=controller_managed_device_groups[0]
                )
                .first()
                .pk,
            },
            {
                "controller_managed_device_group": controller_managed_device_groups[1].pk,
                "radio_profile": models.RadioProfile.objects.exclude(
                    controller_managed_device_groups=controller_managed_device_groups[1]
                )
                .first()
                .pk,
            },
            {
                "controller_managed_device_group": controller_managed_device_groups[2].pk,
                "radio_profile": models.RadioProfile.objects.exclude(
                    controller_managed_device_groups=controller_managed_device_groups[2]
                )
                .first()
                .pk,
            },
        ]


class ControllerManagedDeviceGroupWirelessNetworkAssignmentTest(APIViewTestCases.APIViewTestCase):
    model = models.ControllerManagedDeviceGroupWirelessNetworkAssignment

    @classmethod
    def setUpTestData(cls):
        vlans = VLAN.objects.all()
        controller_managed_device_groups = ControllerManagedDeviceGroup.objects.all()[:3]
        cls.create_data = [
            {
                "controller_managed_device_group": controller_managed_device_groups[0].pk,
                "wireless_network": models.WirelessNetwork.objects.exclude(
                    controller_managed_device_groups=controller_managed_device_groups[0]
                )
                .first()
                .pk,
                "vlan": vlans[0].pk,
            },
            {
                "controller_managed_device_group": controller_managed_device_groups[1].pk,
                "wireless_network": models.WirelessNetwork.objects.exclude(
                    controller_managed_device_groups=controller_managed_device_groups[1]
                )
                .first()
                .pk,
                "vlan": vlans[1].pk,
            },
            {
                "controller_managed_device_group": controller_managed_device_groups[2].pk,
                "wireless_network": models.WirelessNetwork.objects.exclude(
                    controller_managed_device_groups=controller_managed_device_groups[2]
                )
                .first()
                .pk,
            },
        ]
