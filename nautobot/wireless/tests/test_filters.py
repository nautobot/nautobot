from nautobot.core.testing import FilterTestCases
from nautobot.wireless import filters, models


class SupportedDataRateTestCase(FilterTestCases.FilterTestCase):
    queryset = models.SupportedDataRate.objects.all()
    filterset = filters.SupportedDataRateFilterSet
    generic_filter_tests = [
        ("mcs_index",),
        ("rate",),
        ("standard",),
    ]


class RadioProfileTestCase(FilterTestCases.FilterTestCase):
    queryset = models.RadioProfile.objects.all()
    filterset = filters.RadioProfileFilterSet
    generic_filter_tests = [
        ("name",),
        ("regulatory_domain",),
        ("frequency",),
    ]


class WirelessNetworkTestCase(FilterTestCases.FilterTestCase):
    queryset = models.WirelessNetwork.objects.all()
    filterset = filters.WirelessNetworkFilterSet
    generic_filter_tests = [
        ("description",),
        ("name",),
        ("ssid",),
    ]


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
