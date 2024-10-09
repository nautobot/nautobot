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
from nautobot.dcim.models import Controller, Device, Location
from nautobot.extras.forms import NautobotBulkEditForm, NautobotFilterForm, NautobotModelForm, TagsBulkEditFormMixin
from nautobot.extras.models import SecretsGroup
from nautobot.ipam.models import VLAN, VLANGroup
from nautobot.tenancy.forms import TenancyFilterForm
from nautobot.tenancy.models import Tenant
from nautobot.wireless.models import (
    AccessPointGroup,
    AccessPointGroupWirelessNetworkAssignment,
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


class AccessPointGroupWirelessNetworkAssignmentForm(BootstrapMixin, forms.ModelForm):
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
    access_point_group = DynamicModelChoiceField(
        queryset=AccessPointGroup.objects.all(),
        required=False,
    )
    wireless_network = DynamicModelChoiceField(
        queryset=WirelessNetwork.objects.all(),
        required=False,
    )

    class Meta:
        model = AccessPointGroupWirelessNetworkAssignment
        fields = [
            "wireless_network",
            "access_point_group",
            "locations",
            "vlan_group",
            "vlan",
        ]
        field_order = [
            "wireless_network",
            "access_point_group",
            "locations",
            "vlan_group",
            "vlan",
        ]

    def clean_wireless_network(self):
        wireless_network = self.cleaned_data.get("wireless_network")
        if not wireless_network:
            raise forms.ValidationError("Wireless Network is required.")
        return wireless_network

    def clean_access_point_group(self):
        access_point_group = self.cleaned_data.get("access_point_group")
        if not access_point_group:
            raise forms.ValidationError("Access Point Group is required.")
        return access_point_group


AccessPointGroupWirelessNetworkFormSet = forms.inlineformset_factory(
    parent_model=AccessPointGroup,
    model=AccessPointGroupWirelessNetworkAssignment,
    form=AccessPointGroupWirelessNetworkAssignmentForm,
    exclude=["access_point_group"],
    extra=5,
)


WirelessNetworkAccessPointGroupFormSet = forms.inlineformset_factory(
    parent_model=WirelessNetwork,
    model=AccessPointGroupWirelessNetworkAssignment,
    form=AccessPointGroupWirelessNetworkAssignmentForm,
    exclude=["wireless_network"],
    extra=5,
)


class AccessPointGroupForm(NautobotModelForm):
    controller = DynamicModelChoiceField(
        queryset=Controller.objects.all(),
        help_text="The controller managing this access point group.",
        required=False,
    )
    devices = DynamicModelMultipleChoiceField(
        queryset=Device.objects.all(),
        required=False,
        label="Devices",
    )
    radio_profiles = DynamicModelMultipleChoiceField(
        queryset=RadioProfile.objects.all(),
        required=False,
        label="Radio Profiles",
    )
    tenant = DynamicModelChoiceField(
        queryset=Tenant.objects.all(),
        required=False,
        label="Tenant",
    )

    class Meta:
        model = AccessPointGroup
        fields = [
            "name",
            "description",
            "controller",
            "tenant",
            "devices",
            "radio_profiles",
            "tags",
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["devices"].initial = self.instance.devices.all()


class AccessPointGroupFilterForm(NautobotFilterForm, TenancyFilterForm):
    model = AccessPointGroup
    q = forms.CharField(required=False, label="Search")
    controller_id = DynamicModelMultipleChoiceField(
        queryset=Controller.objects.all(),
        to_field_name="id",
        required=False,
        label="Controller",
    )
    tags = TagFilterField(model)


class AccessPointGroupBulkEditForm(TagsBulkEditFormMixin, NautobotBulkEditForm):
    pk = forms.ModelMultipleChoiceField(queryset=AccessPointGroup.objects.all(), widget=forms.MultipleHiddenInput)
    controller = DynamicModelChoiceField(
        queryset=Controller.objects.all(),
        required=False,
        label="Controller",
    )
    tenant = DynamicModelChoiceField(
        queryset=Tenant.objects.all(),
        required=False,
    )
    name = forms.CharField(max_length=CHARFIELD_MAX_LENGTH, required=False)
    add_radio_profiles = DynamicModelMultipleChoiceField(
        queryset=RadioProfile.objects.all(),
        required=False,
        label="Add Radio Profiles",
    )
    remove_radio_profiles = DynamicModelMultipleChoiceField(
        queryset=RadioProfile.objects.all(),
        required=False,
        label="Remove Radio Profiles",
    )
    description = forms.CharField(max_length=CHARFIELD_MAX_LENGTH, required=False)

    class Meta:
        nullable_fields = [
            "controller",
            "tenant",
            "description",
        ]


class RadioProfileForm(NautobotModelForm):
    allowed_channel_list = NumericArrayField(
        base_field=forms.IntegerField(),
        help_text="List of allowed channels for this radio profile.",
        required=False,
    )
    access_point_groups = DynamicModelMultipleChoiceField(
        queryset=AccessPointGroup.objects.all(),
        required=False,
        label="Access Point Groups",
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
    add_access_point_groups = DynamicModelMultipleChoiceField(
        queryset=AccessPointGroup.objects.all(),
        required=False,
        label="Add Access Point Groups",
    )
    remove_access_point_groups = DynamicModelMultipleChoiceField(
        queryset=AccessPointGroup.objects.all(),
        required=False,
        label="Remove Access Point Groups",
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
        choices=add_blank_choice(RadioProfileChannelWidthChoices),
        base_field=forms.IntegerField(),
        required=False,
    )

    class Meta:
        nullable_fields = [
            "frequency",
            "allowed_channel_list",
            "regulatory_domain",
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
    add_access_point_groups = DynamicModelMultipleChoiceField(
        queryset=AccessPointGroup.objects.all(),
        required=False,
        label="Add Access Point Groups",
    )
    remove_access_point_groups = DynamicModelMultipleChoiceField(
        queryset=AccessPointGroup.objects.all(),
        required=False,
        label="Remove Access Point Groups",
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
