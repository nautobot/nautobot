from nautobot.core.testing import FilterTestCases
from nautobot.extras.models import SecretsGroup
from nautobot.wireless import filters, models


class SupportedDataRateTestCase(FilterTestCases.FilterTestCase):
    queryset = models.SupportedDataRate.objects.all()
    filterset = filters.SupportedDataRateFilterSet
    generic_filter_tests = [
        ("mcs_index",),
        ("radio_profiles", "radio_profiles__id"),
        ("radio_profiles", "radio_profiles__name"),
        ("rate",),
        ("standard",),
    ]


class RadioProfileTestCase(FilterTestCases.FilterTestCase):
    queryset = models.RadioProfile.objects.all()
    filterset = filters.RadioProfileFilterSet
    generic_filter_tests = [
        ("name",),
        ("controller_managed_device_groups", "controller_managed_device_groups__id"),
        ("controller_managed_device_groups", "controller_managed_device_groups__name"),
        ("frequency",),
        ("regulatory_domain",),
    ]

    def test_channel_width(self):
        self.assertQuerysetEqualAndNotEmpty(
            self.filterset({"channel_width": "80"}, self.queryset).qs,
            self.queryset.filter(channel_width__contains=[80]),
        )


class WirelessNetworkTestCase(FilterTestCases.FilterTestCase):
    queryset = models.WirelessNetwork.objects.all()
    filterset = filters.WirelessNetworkFilterSet
    generic_filter_tests = [
        ("authentication",),
        ("controller_managed_device_groups", "controller_managed_device_groups__id"),
        ("controller_managed_device_groups", "controller_managed_device_groups__name"),
        ("description",),
        ("mode",),
        ("name",),
        ("secrets_group", "secrets_group__id"),
        ("secrets_group", "secrets_group__name"),
        ("ssid",),
    ]

    @classmethod
    def setUpTestData(cls):
        secrets_groups = (
            SecretsGroup.objects.create(name="Secrets Group 1"),
            SecretsGroup.objects.create(name="Secrets Group 2"),
            SecretsGroup.objects.create(name="Secrets Group 3"),
        )
        for i, wireless_network in enumerate(models.WirelessNetwork.objects.all()[:3]):
            wireless_network.secrets_group = secrets_groups[i]
            wireless_network.validated_save()


class ControllerManagedDeviceGroupWirelessNetworkAssignmentTestCase(FilterTestCases.FilterTestCase):
    queryset = models.ControllerManagedDeviceGroupWirelessNetworkAssignment.objects.all()
    filterset = filters.ControllerManagedDeviceGroupWirelessNetworkAssignmentFilterSet
    generic_filter_tests = [
        ("controller_managed_device_group", "controller_managed_device_group__id"),
        ("controller_managed_device_group", "controller_managed_device_group__name"),
        ("wireless_network", "wireless_network__id"),
        ("wireless_network", "wireless_network__name"),
    ]


class ControllerManagedDeviceGroupRadioProfileAssignmentTestCase(FilterTestCases.FilterTestCase):
    queryset = models.ControllerManagedDeviceGroupRadioProfileAssignment.objects.all()
    filterset = filters.ControllerManagedDeviceGroupRadioProfileAssignmentFilterSet
    generic_filter_tests = [
        ("controller_managed_device_group", "controller_managed_device_group__id"),
        ("controller_managed_device_group", "controller_managed_device_group__name"),
        ("radio_profile", "radio_profile__id"),
        ("radio_profile", "radio_profile__name"),
    ]
