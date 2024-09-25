import django_filters

from nautobot.core.filters import BaseFilterSet, NaturalKeyOrPKMultipleChoiceFilter, NumericArrayFilter, SearchFilter
from nautobot.dcim.models import Controller, Device
from nautobot.extras.filters import NautobotFilterSet
from nautobot.extras.models import SecretsGroup
from nautobot.tenancy.filters import TenancyModelFilterSetMixin
from nautobot.wireless import choices, models


class AccessPointGroupFilterSet(NautobotFilterSet, TenancyModelFilterSetMixin):
    q = SearchFilter(
        filter_predicates={
            "name": "icontains",
            "description": "icontains",
            "controller__name": "icontains",
        }
    )
    controller = NaturalKeyOrPKMultipleChoiceFilter(
        field_name="controller",
        queryset=Controller.objects.all(),
        to_field_name="name",
        label="Controller (name or ID)",
    )

    class Meta:
        model = models.AccessPointGroup
        fields = "__all__"


class SupportedDataRateFilterSet(BaseFilterSet):
    q = SearchFilter(
        filter_predicates={
            "rate": {
                "lookup_expr": "exact",
                "preprocessor": int,
            },
            "standard": "icontains",
            "mcs_index": {
                "lookup_expr": "exact",
                "preprocessor": int,
            },
        }
    )

    class Meta:
        model = models.SupportedDataRate
        fields = "__all__"


class RadioProfileFilterSet(NautobotFilterSet):
    q = SearchFilter(
        filter_predicates={
            "name": "icontains",
            "regulatory_domain": "icontains",
            "frequency": "exact",
        }
    )
    regulatory_domain = django_filters.MultipleChoiceFilter(
        choices=choices.RadioProfileRegulatoryDomainChoices,
        null_value=None,
    )
    channel_width = NumericArrayFilter(
        field_name="channel_width",
        lookup_expr="contains",
    )

    frequency = django_filters.MultipleChoiceFilter(
        choices=choices.RadioProfileFrequencyChoices,
        null_value=None,
    )

    class Meta:
        model = models.RadioProfile
        fields = "__all__"


class WirelessNetworkFilterSet(NautobotFilterSet, TenancyModelFilterSetMixin):
    q = SearchFilter(
        filter_predicates={
            "name": "icontains",
            "description": "icontains",
            "ssid": "icontains",
        }
    )
    mode = django_filters.MultipleChoiceFilter(
        choices=choices.WirelessNetworkModeChoices,
        null_value=None,
    )
    enabled = django_filters.BooleanFilter()
    authentication = django_filters.MultipleChoiceFilter(
        choices=choices.WirelessNetworkAuthenticationChoices,
        null_value=None,
    )
    secrets_group = NaturalKeyOrPKMultipleChoiceFilter(
        field_name="secrets_group",
        queryset=SecretsGroup.objects.all(),
        to_field_name="name",
        label="Secrets group (name or ID)",
    )
    hidden = django_filters.BooleanFilter()

    class Meta:
        model = models.WirelessNetwork
        fields = "__all__"


class AccessPointGroupWirelessNetworkAssignmentFilterSet(BaseFilterSet):
    q = SearchFilter(
        filter_predicates={
            "access_point_group__name": "icontains",
            "wireless_network__name": "icontains",
        }
    )
    access_point_group = NaturalKeyOrPKMultipleChoiceFilter(
        field_name="access_point_group",
        queryset=models.AccessPointGroup.objects.all(),
        to_field_name="name",
        label="Access Point Group (name or ID)",
    )
    wireless_network = NaturalKeyOrPKMultipleChoiceFilter(
        field_name="wireless_network",
        queryset=models.WirelessNetwork.objects.all(),
        to_field_name="name",
        label="Wireless Network (name or ID)",
    )

    class Meta:
        model = models.AccessPointGroupWirelessNetworkAssignment
        fields = "__all__"


class AccessPointGroupRadioProfileAssignmentFilterSet(BaseFilterSet):
    q = SearchFilter(
        filter_predicates={
            "access_point_group__name": "icontains",
            "radio_profile__name": "icontains",
        }
    )
    access_point_group = NaturalKeyOrPKMultipleChoiceFilter(
        field_name="access_point_group",
        queryset=models.AccessPointGroup.objects.all(),
        to_field_name="name",
        label="Access Point Group (name or ID)",
    )
    radio_profile = NaturalKeyOrPKMultipleChoiceFilter(
        field_name="radio_profile",
        queryset=models.RadioProfile.objects.all(),
        to_field_name="name",
        label="Radio Profile (name or ID)",
    )

    class Meta:
        model = models.AccessPointGroupRadioProfileAssignment
        fields = "__all__"


class AccessPointGroupDeviceAssignmentFilterSet(BaseFilterSet):
    q = SearchFilter(
        filter_predicates={
            "access_point_group__name": "icontains",
            "device__name": "icontains",
        }
    )
    access_point_group = NaturalKeyOrPKMultipleChoiceFilter(
        field_name="access_point_group",
        queryset=models.AccessPointGroup.objects.all(),
        to_field_name="name",
        label="Access Point Group (name or ID)",
    )
    device = NaturalKeyOrPKMultipleChoiceFilter(
        field_name="device",
        queryset=Device.objects.all(),
        to_field_name="name",
        label="Device (name or ID)",
    )

    class Meta:
        model = models.AccessPointGroupDeviceAssignment
        fields = "__all__"
