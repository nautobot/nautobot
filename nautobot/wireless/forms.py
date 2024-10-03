from django import forms

from nautobot.core.forms import (
    BootstrapMixin,
    DynamicModelChoiceField,
    DynamicModelMultipleChoiceField,
    NumericArrayField,
    TagFilterField,
)
from nautobot.dcim.models import Controller, Device, Location
from nautobot.extras.forms import NautobotBulkEditForm, NautobotFilterForm, NautobotModelForm, TagsBulkEditFormMixin
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


class AccessPointGroupWirelessNetworkVLANForm(BootstrapMixin, forms.ModelForm):
    locations = DynamicModelMultipleChoiceField(
        queryset=Location.objects.all(),
        required=False,
        label="Locations",
        null_option="None",
    )
    vlan_group = DynamicModelChoiceField(
        queryset=VLANGroup.objects.all(),
        required=False,
        label="VLAN group",
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

AccessPointGroupWirelessNetworkFormSet = forms.inlineformset_factory(
    parent_model=AccessPointGroup,
    model=AccessPointGroupWirelessNetworkAssignment,
    form=AccessPointGroupWirelessNetworkVLANForm,
    exclude=["access_point_group"],
    extra=5,
)


WirelessNetworkAccessPointGroupFormSet = forms.inlineformset_factory(
    parent_model=WirelessNetwork,
    model=AccessPointGroupWirelessNetworkAssignment,
    form=AccessPointGroupWirelessNetworkVLANForm,
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
    class Meta:
        model = AccessPointGroup
        fields = [
            "name",
            "description",
            "controller",
            "tenant",
            "devices",
            "radio_profiles",
            # "wireless_networks",
            "tags",
        ]


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
