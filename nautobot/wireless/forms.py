from django import forms

from nautobot.core.constants import CHARFIELD_MAX_LENGTH
from nautobot.core.forms import (
    add_blank_choice,
    BootstrapMixin,
    BulkEditNullBooleanSelect,
    DynamicModelChoiceField,
    DynamicModelMultipleChoiceField,
    NumericArrayField,
    StaticSelect2,
    TagFilterField,
)
from nautobot.core.forms.fields import JSONArrayFormField
from nautobot.dcim.models import ControllerManagedDeviceGroup, Location
from nautobot.extras.forms import NautobotBulkEditForm, NautobotFilterForm, NautobotModelForm, TagsBulkEditFormMixin
from nautobot.extras.models import SecretsGroup
from nautobot.ipam.models import VLAN, VLANGroup
from nautobot.wireless.models import (
    ControllerManagedDeviceGroupWirelessNetworkAssignment,
    RadioProfile,
    SupportedDataRate,
    WirelessNetwork,
)

from .choices import (
    RadioProfileChannelWidthChoices,
    RadioProfileFrequencyChoices,
    RadioProfileRegulatoryDomainChoices,
    SupportedDataRateStandardChoices,
    WirelessNetworkAuthenticationChoices,
    WirelessNetworkModeChoices,
)


class ControllerManagedDeviceGroupWirelessNetworkAssignmentForm(BootstrapMixin, forms.ModelForm):
    locations = DynamicModelMultipleChoiceField(
        queryset=Location.objects.all(),
        required=False,
        label="VLAN Locations (filter)",
        null_option="None",
    )
    vlan_group = DynamicModelChoiceField(
        queryset=VLANGroup.objects.all(),
        required=False,
        label="VLAN group (filter)",
        null_option="None",
        initial_params={"vlans": "$vlan"},
    )
    vlan = DynamicModelChoiceField(
        queryset=VLAN.objects.all(),
        required=False,
        label="VLAN",
        query_params={
            "locations": "$locations",
            "vlan_group": "$vlan_group",
        },
    )
    controller_managed_device_group = DynamicModelChoiceField(
        queryset=ControllerManagedDeviceGroup.objects.all(),
        required=False,
    )
    wireless_network = DynamicModelChoiceField(
        queryset=WirelessNetwork.objects.all(),
        required=False,
    )

    class Meta:
        model = ControllerManagedDeviceGroupWirelessNetworkAssignment
        fields = [
            "wireless_network",
            "controller_managed_device_group",
            "locations",
            "vlan_group",
            "vlan",
        ]
        field_order = [
            "wireless_network",
            "controller_managed_device_group",
            "locations",
            "vlan_group",
            "vlan",
        ]

    def clean_wireless_network(self):
        wireless_network = self.cleaned_data.get("wireless_network")
        if not wireless_network:
            raise forms.ValidationError("Wireless Network is required.")
        return wireless_network

    def clean_controller_managed_device_group(self):
        controller_managed_device_group = self.cleaned_data.get("controller_managed_device_group")
        if not controller_managed_device_group:
            raise forms.ValidationError("Controller Managed Device Group is required.")
        return controller_managed_device_group


ControllerManagedDeviceGroupWirelessNetworkFormSet = forms.inlineformset_factory(
    parent_model=ControllerManagedDeviceGroup,
    model=ControllerManagedDeviceGroupWirelessNetworkAssignment,
    form=ControllerManagedDeviceGroupWirelessNetworkAssignmentForm,
    exclude=["controller_managed_device_group"],
    extra=5,
)


WirelessNetworkControllerManagedDeviceGroupFormSet = forms.inlineformset_factory(
    parent_model=WirelessNetwork,
    model=ControllerManagedDeviceGroupWirelessNetworkAssignment,
    form=ControllerManagedDeviceGroupWirelessNetworkAssignmentForm,
    exclude=["wireless_network"],
    extra=5,
)


class RadioProfileForm(NautobotModelForm):
    allowed_channel_list = NumericArrayField(
        base_field=forms.IntegerField(),
        help_text="List of allowed channels for this radio profile.",
        required=False,
    )
    controller_managed_device_group = DynamicModelMultipleChoiceField(
        queryset=ControllerManagedDeviceGroup.objects.all(),
        required=False,
        label="Controller Managed Device Groups",
    )
    supported_data_rates = DynamicModelMultipleChoiceField(
        queryset=SupportedDataRate.objects.all(),
        required=False,
        label="Supported Data Rates",
    )

    class Meta:
        model = RadioProfile
        fields = "__all__"


class RadioProfileFilterForm(NautobotFilterForm):
    model = RadioProfile
    q = forms.CharField(required=False, label="Search")
    tags = TagFilterField(model)


class RadioProfileBulkEditForm(TagsBulkEditFormMixin, NautobotBulkEditForm):
    pk = forms.ModelMultipleChoiceField(queryset=RadioProfile.objects.all(), widget=forms.MultipleHiddenInput)
    name = forms.CharField(max_length=CHARFIELD_MAX_LENGTH, required=False)
    frequency = forms.ChoiceField(
        choices=add_blank_choice(RadioProfileFrequencyChoices),
        required=False,
        widget=StaticSelect2(),
    )
    add_supported_data_rates = DynamicModelMultipleChoiceField(
        queryset=SupportedDataRate.objects.all(),
        required=False,
        label="Add Supported Data Rates",
    )
    remove_supported_data_rates = DynamicModelMultipleChoiceField(
        queryset=SupportedDataRate.objects.all(),
        required=False,
        label="Remove Supported Data Rates",
    )
    add_controller_managed_device_groups = DynamicModelMultipleChoiceField(
        queryset=ControllerManagedDeviceGroup.objects.all(),
        required=False,
        label="Add Controller Managed Device Groups",
    )
    remove_controller_managed_device_groups = DynamicModelMultipleChoiceField(
        queryset=ControllerManagedDeviceGroup.objects.all(),
        required=False,
        label="Remove Controller Managed Device Groups",
    )
    allowed_channel_list = NumericArrayField(
        base_field=forms.IntegerField(),
        required=False,
        label="Allowed Channel List",
    )
    tx_power_min = forms.IntegerField(required=False, label="TX Power Min")
    tx_power_max = forms.IntegerField(required=False, label="TX Power Max")
    rx_power_min = forms.IntegerField(required=False, label="RX Power Min")
    regulatory_domain = forms.ChoiceField(
        choices=add_blank_choice(RadioProfileRegulatoryDomainChoices),
        required=False,
        widget=StaticSelect2(),
    )
    channel_width = JSONArrayFormField(
        choices=RadioProfileChannelWidthChoices,
        base_field=forms.IntegerField(),
        required=False,
    )

    class Meta:
        nullable_fields = [
            "frequency",
            "allowed_channel_list",
            "tx_power_min",
            "tx_power_max",
            "rx_power_min",
            "channel_width",
        ]


class SupportedDataRateForm(NautobotModelForm):
    class Meta:
        model = SupportedDataRate
        fields = "__all__"


class SupportedDataRateFilterForm(NautobotFilterForm):
    model = SupportedDataRate
    q = forms.CharField(required=False, label="Search")
    tags = TagFilterField(model)


class SupportedDataRateBulkEditForm(TagsBulkEditFormMixin, NautobotBulkEditForm):
    pk = forms.ModelMultipleChoiceField(queryset=SupportedDataRate.objects.all(), widget=forms.MultipleHiddenInput)
    standard = forms.ChoiceField(
        choices=add_blank_choice(SupportedDataRateStandardChoices),
        required=False,
        widget=StaticSelect2(),
    )
    rate = forms.IntegerField(min_value=1, required=False, label="Rate (Kbps)")
    mcs_index = forms.IntegerField(required=False, label="MCS Index")

    class Meta:
        nullable_fields = [
            "mcs_index",
        ]


class WirelessNetworkForm(NautobotModelForm):
    class Meta:
        model = WirelessNetwork
        fields = "__all__"
        field_order = [
            "ssid",
            "name",
            "description",
        ]


class WirelessNetworkFilterForm(NautobotFilterForm):
    model = WirelessNetwork
    q = forms.CharField(required=False, label="Search")
    tags = TagFilterField(model)


class WirelessNetworkBulkEditForm(TagsBulkEditFormMixin, NautobotBulkEditForm):
    pk = forms.ModelMultipleChoiceField(queryset=WirelessNetwork.objects.all(), widget=forms.MultipleHiddenInput)
    description = forms.CharField(max_length=CHARFIELD_MAX_LENGTH, required=False)
    add_controller_managed_device_groups = DynamicModelMultipleChoiceField(
        queryset=ControllerManagedDeviceGroup.objects.all(),
        required=False,
        label="Add Controller Managed Device Groups",
    )
    remove_controller_managed_device_groups = DynamicModelMultipleChoiceField(
        queryset=ControllerManagedDeviceGroup.objects.all(),
        required=False,
        label="Remove Controller Managed Device Groups",
    )
    ssid = forms.CharField(max_length=CHARFIELD_MAX_LENGTH, required=False)
    mode = forms.ChoiceField(
        choices=add_blank_choice(WirelessNetworkModeChoices),
        required=False,
        widget=StaticSelect2(),
    )
    enabled = forms.NullBooleanField(required=False, widget=BulkEditNullBooleanSelect)
    hidden = forms.NullBooleanField(required=False, widget=BulkEditNullBooleanSelect)
    authentication = forms.ChoiceField(
        choices=add_blank_choice(WirelessNetworkAuthenticationChoices),
        required=False,
        widget=StaticSelect2(),
    )
    secrets_group = DynamicModelChoiceField(
        queryset=SecretsGroup.objects.all(),
        required=False,
    )

    class Meta:
        nullable_fields = [
            "description",
            "secrets_group",
        ]
