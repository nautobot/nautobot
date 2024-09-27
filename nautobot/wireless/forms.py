from django import forms

from nautobot.core.constants import CHARFIELD_MAX_LENGTH
from nautobot.core.forms import (
    DynamicModelChoiceField,
    DynamicModelMultipleChoiceField,
    MultiValueCharField,
    TagFilterField,
)
from nautobot.core.forms.fields import MultipleContentTypeField
from nautobot.dcim.models import Controller
from nautobot.extras.forms import NautobotBulkEditForm, NautobotFilterForm, NautobotModelForm, TagsBulkEditFormMixin
from nautobot.extras.models import SecretsGroup
from nautobot.ipam.models import Namespace, Prefix
from nautobot.tenancy.forms import TenancyFilterForm
from nautobot.tenancy.models import Tenant
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
    class Meta:
        model = RadioProfile
        fields = [
            "name",
            "description",
            "tags",
        ]


class RadioProfileFilterForm(NautobotFilterForm):
    model = RadioProfile
    q = forms.CharField(required=False, label="Search")
    tags = TagFilterField(model)


class RadioProfileBulkEditForm(TagsBulkEditFormMixin, NautobotBulkEditForm):
    pk = forms.ModelMultipleChoiceField(queryset=RadioProfile.objects.all(), widget=forms.MultipleHiddenInput)


class SupportedDataRateForm(NautobotModelForm):
    class Meta:
        model = SupportedDataRate
        fields = [
            "rate",
            "tags",
        ]


class SupportedDataRateFilterForm(NautobotFilterForm):
    model = SupportedDataRate
    q = forms.CharField(required=False, label="Search")
    tags = TagFilterField(model)


class SupportedDataRateBulkEditForm(TagsBulkEditFormMixin, NautobotBulkEditForm):
    pk = forms.ModelMultipleChoiceField(queryset=SupportedDataRate.objects.all(), widget=forms.MultipleHiddenInput)


class WirelessNetworkForm(NautobotModelForm):
    class Meta:
        model = WirelessNetwork
        fields = [
            "name",
            "description",
            "tags",
        ]


class WirelessNetworkFilterForm(NautobotFilterForm):
    model = WirelessNetwork
    q = forms.CharField(required=False, label="Search")
    tags = TagFilterField(model)


class WirelessNetworkBulkEditForm(TagsBulkEditFormMixin, NautobotBulkEditForm):
    pk = forms.ModelMultipleChoiceField(queryset=WirelessNetwork.objects.all(), widget=forms.MultipleHiddenInput)
