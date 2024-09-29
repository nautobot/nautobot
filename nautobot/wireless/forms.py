import json

from django import forms

from nautobot.core.constants import CHARFIELD_MAX_LENGTH
from nautobot.core.forms import (
    DynamicModelChoiceField,
    DynamicModelMultipleChoiceField,
    NumericArrayField,
    JSONArrayFormField,
    TagFilterField,
)
from nautobot.core.forms.fields import MultipleContentTypeField
from nautobot.dcim.models import Controller
from nautobot.extras.forms import NautobotBulkEditForm, NautobotFilterForm, NautobotModelForm, TagsBulkEditFormMixin
from nautobot.extras.models import SecretsGroup
from nautobot.ipam.models import Namespace, Prefix
from nautobot.tenancy.forms import TenancyFilterForm
from nautobot.tenancy.models import Tenant
from nautobot.wireless.choices import RadioProfileChannelWidthChoices
from nautobot.wireless.models import AccessPointGroup, RadioProfile, SupportedDataRate, WirelessNetwork


class AccessPointGroupForm(NautobotModelForm):
    controller = DynamicModelChoiceField(
        queryset=Controller.objects.all(),
        help_text="The controller managing this access point group.",
        required=False,
    )
    class Meta:
        model = AccessPointGroup
        fields = [
            "name",
            "description",
            "controller",
            "tenant",
            # "devices",
            # "radio_profiles",
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
    class Meta:
        model = RadioProfile
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        print(f"{",".join(str(v) for v in self.instance.channel_width)}")
        self.fields["channel_width"].initial = ",".join(str(v) for v in self.instance.channel_width)


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


class WirelessNetworkFilterForm(NautobotFilterForm):
    model = WirelessNetwork
    q = forms.CharField(required=False, label="Search")
    tags = TagFilterField(model)


class WirelessNetworkBulkEditForm(TagsBulkEditFormMixin, NautobotBulkEditForm):
    pk = forms.ModelMultipleChoiceField(queryset=WirelessNetwork.objects.all(), widget=forms.MultipleHiddenInput)
