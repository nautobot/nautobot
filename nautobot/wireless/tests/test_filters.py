from nautobot.core.testing import FilterTestCases
from nautobot.wireless import filters, models


class AccessPointGroupTestCase(FilterTestCases.FilterTestCase):
    queryset = models.AccessPointGroup.objects.all()
    filterset = filters.AccessPointGroupFilterSet
    generic_filter_tests = [
        ("controller",),
        ("description",),
        ("name",),
        ("tenant", "tenant__id"),
        ("tenant", "tenant__name"),
    ]


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


class AccessPointGroupWirelessNetworkAssignmentTestCase(FilterTestCases.FilterTestCase):
    queryset = models.AccessPointGroupWirelessNetworkAssignment.objects.all()
    filterset = filters.AccessPointGroupWirelessNetworkAssignmentFilterSet
    generic_filter_tests = [
        ("access_point_group", "access_point_group__id"),
        ("access_point_group", "access_point_group__name"),
        ("wireless_network", "wireless_network__id"),
        ("wireless_network", "wireless_network__name"),
    ]


class AccessPointGroupRadioProfileAssignmentTestCase(FilterTestCases.FilterTestCase):
    queryset = models.AccessPointGroupRadioProfileAssignment.objects.all()
    filterset = filters.AccessPointGroupRadioProfileAssignmentFilterSet
    generic_filter_tests = [
        ("access_point_group", "access_point_group__id"),
        ("access_point_group", "access_point_group__name"),
        ("radio_profile", "radio_profile__id"),
        ("radio_profile", "radio_profile__name"),
    ]


class AccessPointGroupDeviceAssignmentTestCase(FilterTestCases.FilterTestCase):
    queryset = models.AccessPointGroupDeviceAssignment.objects.all()
    filterset = filters.AccessPointGroupDeviceAssignmentFilterSet
    generic_filter_tests = [
        ("access_point_group", "access_point_group__id"),
        ("access_point_group", "access_point_group__name"),
        ("device", "device__id"),
        ("device", "device__name"),
    ]
