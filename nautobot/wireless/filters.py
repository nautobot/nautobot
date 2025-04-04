import django_filters

from nautobot.core.filters import (
    BaseFilterSet,
    NaturalKeyOrPKMultipleChoiceFilter,
    NumericArrayFilter,
    RelatedMembershipBooleanFilter,
    SearchFilter,
)
from nautobot.dcim.models import ControllerManagedDeviceGroup
from nautobot.extras.filters import NautobotFilterSet
from nautobot.extras.models import SecretsGroup
from nautobot.tenancy.filters import TenancyModelFilterSetMixin
from nautobot.wireless import choices, models


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
    radio_profiles = NaturalKeyOrPKMultipleChoiceFilter(
        queryset=models.RadioProfile.objects.all(),
        to_field_name="name",
        label="Radio Profile (name or ID)",
    )
    has_radio_profiles = RelatedMembershipBooleanFilter(
        field_name="radio_profiles",
        label="Has radio profiles",
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
    controller_managed_device_groups = NaturalKeyOrPKMultipleChoiceFilter(
        queryset=ControllerManagedDeviceGroup.objects.all(),
        to_field_name="name",
        label="Controller Managed Device Groups (name or ID)",
    )
    has_controller_managed_device_groups = RelatedMembershipBooleanFilter(
        field_name="controller_managed_device_groups",
        label="Has controller managed device groups",
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
    controller_managed_device_groups = NaturalKeyOrPKMultipleChoiceFilter(
        queryset=ControllerManagedDeviceGroup.objects.all(),
        to_field_name="name",
        label="Controller Managed Device Groups (name or ID)",
    )
    has_controller_managed_device_groups = RelatedMembershipBooleanFilter(
        field_name="controller_managed_device_groups",
        label="Has controller managed device groups",
    )
    hidden = django_filters.BooleanFilter()

    class Meta:
        model = models.WirelessNetwork
        fields = "__all__"


class ControllerManagedDeviceGroupWirelessNetworkAssignmentFilterSet(BaseFilterSet):
    q = SearchFilter(
        filter_predicates={
            "controller_managed_device_group__name": "icontains",
            "wireless_network__name": "icontains",
        }
    )
    controller_managed_device_group = NaturalKeyOrPKMultipleChoiceFilter(
        field_name="controller_managed_device_group",
        queryset=ControllerManagedDeviceGroup.objects.all(),
        to_field_name="name",
        label="Controller Managed Device Group (name or ID)",
    )
    wireless_network = NaturalKeyOrPKMultipleChoiceFilter(
        field_name="wireless_network",
        queryset=models.WirelessNetwork.objects.all(),
        to_field_name="name",
        label="Wireless Network (name or ID)",
    )

    class Meta:
        model = models.ControllerManagedDeviceGroupWirelessNetworkAssignment
        fields = "__all__"


class ControllerManagedDeviceGroupRadioProfileAssignmentFilterSet(BaseFilterSet):
    q = SearchFilter(
        filter_predicates={
            "controller_managed_device_group__name": "icontains",
            "radio_profile__name": "icontains",
        }
    )
    controller_managed_device_group = NaturalKeyOrPKMultipleChoiceFilter(
        field_name="controller_managed_device_group",
        queryset=ControllerManagedDeviceGroup.objects.all(),
        to_field_name="name",
        label="Controller Managed Device Group (name or ID)",
    )
    radio_profile = NaturalKeyOrPKMultipleChoiceFilter(
        field_name="radio_profile",
        queryset=models.RadioProfile.objects.all(),
        to_field_name="name",
        label="Radio Profile (name or ID)",
    )

    class Meta:
        model = models.ControllerManagedDeviceGroupRadioProfileAssignment
        fields = "__all__"
