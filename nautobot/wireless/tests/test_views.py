from nautobot.core.testing import ViewTestCases
from nautobot.dcim.models import Controller
from nautobot.extras.models import SecretsGroup, Tag
from nautobot.tenancy.models import Tenant
from nautobot.wireless import choices
from nautobot.wireless.models import AccessPointGroup, RadioProfile, SupportedDataRate, WirelessNetwork


class AccessPointGroupTestCase(ViewTestCases.PrimaryObjectViewTestCase):
    model = AccessPointGroup

    @classmethod
    def setUpTestData(cls):
        AccessPointGroup.objects.create(name="Deletable Access Point Group 1")
        AccessPointGroup.objects.create(name="Deletable Access Point Group 2")
        AccessPointGroup.objects.create(name="Deletable Access Point Group 3")
        cls.form_data = {
            "name": "New Access Point Group",
            "description": "A new access point group",
            "controller": Controller.objects.first().pk,
            "tenant": Tenant.objects.first().pk,
            "tags": [t.pk for t in Tag.objects.get_for_model(AccessPointGroup)],
            # Management form fields required for the dynamic Wireless Network formset
            "wireless_network_assignments-TOTAL_FORMS": "0",
            "wireless_network_assignments-INITIAL_FORMS": "1",
            "wireless_network_assignments-MIN_NUM_FORMS": "0",
            "wireless_network_assignments-MAX_NUM_FORMS": "1000",
        }

        cls.bulk_edit_data = {
            "controller": Controller.objects.first().pk,
            "tenant": Tenant.objects.first().pk,
            "description": "New description",
        }


class WirelessNetworkTestCase(ViewTestCases.PrimaryObjectViewTestCase):
    model = WirelessNetwork

    @classmethod
    def setUpTestData(cls):
        WirelessNetwork.objects.create(
            name="Deletable Wireless Network 1",
            mode=choices.WirelessNetworkModeChoices.STANDALONE,
            authentication=choices.WirelessNetworkAuthenticationChoices.WPA2_PERSONAL,
            ssid="SSID 1",
            description="Description 1",
            enabled=True,
            hidden=False,
            secrets_group=SecretsGroup.objects.first(),
        )
        WirelessNetwork.objects.create(
            name="Deletable Wireless Network 2",
            mode=choices.WirelessNetworkModeChoices.CENTRAL,
            authentication=choices.WirelessNetworkAuthenticationChoices.WPA2_ENTERPRISE,
            ssid="SSID 2",
            description="Description 2",
            enabled=True,
            hidden=False,
            secrets_group=SecretsGroup.objects.first(),
        )
        WirelessNetwork.objects.create(
            name="Deletable Wireless Network 3",
            mode=choices.WirelessNetworkModeChoices.LOCAL,
            authentication=choices.WirelessNetworkAuthenticationChoices.WPA2_ENTERPRISE,
            ssid="SSID 3",
            description="Description 3",
            enabled=False,
            hidden=True,
            secrets_group=SecretsGroup.objects.first(),
        )
        cls.form_data = {
            "name": "New Wireless Network",
            "description": "A new wireless network",
            "mode": choices.WirelessNetworkModeChoices.MESH,
            "authentication": choices.WirelessNetworkAuthenticationChoices.WPA3_ENTERPRISE_192_BIT,
            "ssid": "SOME SSID",
            "tags": [t.pk for t in Tag.objects.get_for_model(WirelessNetwork)],
            # Management form fields required for the dynamic Access Point Group formset
            "access_point_group_assignments-TOTAL_FORMS": "0",
            "access_point_group_assignments-INITIAL_FORMS": "1",
            "access_point_group_assignments-MIN_NUM_FORMS": "0",
            "access_point_group_assignments-MAX_NUM_FORMS": "1000",
        }

        cls.bulk_edit_data = {
            "mode": choices.WirelessNetworkModeChoices.LOCAL,
            "authentication": choices.WirelessNetworkAuthenticationChoices.WPA2_ENTERPRISE,
            "enabled": False,
            "ssid": "New SSID",
            "description": "New description",
        }


class SupportedDataRateTestCase(ViewTestCases.PrimaryObjectViewTestCase):
    model = SupportedDataRate

    @classmethod
    def setUpTestData(cls):
        SupportedDataRate.objects.create(rate=10000, standard=choices.SupportedDataRateStandardChoices.B, mcs_index=1)
        SupportedDataRate.objects.create(rate=60000, standard=choices.SupportedDataRateStandardChoices.G, mcs_index=2)
        SupportedDataRate.objects.create(rate=128000, standard=choices.SupportedDataRateStandardChoices.N, mcs_index=3)
        cls.form_data = {
            "rate": 30000,
            "standard": "802.11ac",
            "tags": [t.pk for t in Tag.objects.get_for_model(SupportedDataRate)],
        }
        cls.bulk_edit_data = {
            "mcs_index": 11,
        }


class RadioProfileTestCase(ViewTestCases.PrimaryObjectViewTestCase):
    model = RadioProfile


    @classmethod
    def setUpTestData(cls):
        supported_data_rates = (
            SupportedDataRate.objects.create(rate=10000, standard=choices.SupportedDataRateStandardChoices.AC, mcs_index=1),
            SupportedDataRate.objects.create(rate=60000, standard=choices.SupportedDataRateStandardChoices.AX, mcs_index=2),
            SupportedDataRate.objects.create(rate=128000, standard=choices.SupportedDataRateStandardChoices.BE, mcs_index=3),
        )
        rp1 = RadioProfile.objects.create(
            name="Deletable Radio Profile 1",
            frequency=choices.RadioProfileFrequencyChoices.FREQUENCY_5G,
            tx_power_min=1,
            tx_power_max=10,
            channel_width=[20, 40, 80],
            allowed_channel_list=[36, 40, 44, 48],
            regulatory_domain=choices.RadioProfileRegulatoryDomainChoices.US,
            rx_power_min=-90,
        )
        rp2 = RadioProfile.objects.create(
            name="Deletable Radio Profile 2",
            frequency=choices.RadioProfileFrequencyChoices.FREQUENCY_2_4G,
            tx_power_min=2,
            tx_power_max=11,
            channel_width=[20, 40, 80, 160],
            allowed_channel_list=[1, 6, 11],
            regulatory_domain=choices.RadioProfileRegulatoryDomainChoices.JP,
            rx_power_min=-89,
        )
        rp3 = RadioProfile.objects.create(
            name="Deletable Radio Profile 3",
            frequency=choices.RadioProfileFrequencyChoices.FREQUENCY_6G,
            tx_power_min=15,
            tx_power_max=25,
            rx_power_min=-80,
            regulatory_domain=choices.RadioProfileRegulatoryDomainChoices.JP,
            allowed_channel_list=[],
            channel_width=[],
        )
        rp1.supported_data_rates.set([supported_data_rates[0]])
        rp2.supported_data_rates.set([supported_data_rates[1]])
        rp3.supported_data_rates.set(supported_data_rates[:2])
        cls.form_data = {
            "name": "New Radio Profile",
            "frequency": choices.RadioProfileFrequencyChoices.FREQUENCY_5G,
            "tx_power_min": 1,
            "tx_power_max": 10,
            # "allowed_channel_list": "36,37",
            "regulatory_domain": choices.RadioProfileRegulatoryDomainChoices.US,
            "rx_power_min": -90,
            "tags": [t.pk for t in Tag.objects.get_for_model(RadioProfile)],
        }
        cls.bulk_edit_data = {
            "frequency": choices.RadioProfileFrequencyChoices.FREQUENCY_2_4G,
            "tx_power_min": 2,
            "tx_power_max": 11,
            # "allowed_channel_list": "1,2",
            "regulatory_domain": choices.RadioProfileRegulatoryDomainChoices.JP,
            "rx_power_min": -89,
        }
