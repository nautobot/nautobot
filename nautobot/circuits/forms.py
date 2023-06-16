from django import forms

from nautobot.core.forms import (
    CommentField,
    DatePicker,
    DynamicModelChoiceField,
    DynamicModelMultipleChoiceField,
    SmallTextarea,
    TagFilterField,
)
from nautobot.dcim.form_mixins import (
    LocatableModelFilterFormMixin,
    LocatableModelFormMixin,
)
from nautobot.extras.forms import (
    NautobotFilterForm,
    NautobotBulkEditForm,
    NautobotModelForm,
    StatusModelBulkEditFormMixin,
    StatusModelFilterFormMixin,
    TagsBulkEditFormMixin,
)
from nautobot.tenancy.forms import TenancyFilterForm, TenancyForm
from nautobot.tenancy.models import Tenant
from .models import Circuit, CircuitTermination, CircuitType, Provider, ProviderNetwork


#
# Providers
#


class ProviderForm(NautobotModelForm):
    comments = CommentField()

    class Meta:
        model = Provider
        fields = [
            "name",
            "asn",
            "account",
            "portal_url",
            "noc_contact",
            "admin_contact",
            "comments",
            "tags",
        ]
        widgets = {
            "noc_contact": SmallTextarea(attrs={"rows": 5}),
            "admin_contact": SmallTextarea(attrs={"rows": 5}),
        }
        help_texts = {
            "name": "Full name of the provider",
            "asn": "BGP autonomous system number (if applicable)",
            "portal_url": "URL of the provider's customer support portal",
            "noc_contact": "NOC email address and phone number",
            "admin_contact": "Administrative contact email address and phone number",
        }


class ProviderBulkEditForm(TagsBulkEditFormMixin, NautobotBulkEditForm):
    pk = forms.ModelMultipleChoiceField(queryset=Provider.objects.all(), widget=forms.MultipleHiddenInput)
    asn = forms.IntegerField(required=False, label="ASN")
    account = forms.CharField(max_length=100, required=False, label="Account number")
    portal_url = forms.URLField(required=False, label="Portal")
    noc_contact = forms.CharField(required=False, widget=SmallTextarea, label="NOC contact")
    admin_contact = forms.CharField(required=False, widget=SmallTextarea, label="Admin contact")
    comments = CommentField(widget=SmallTextarea, label="Comments")

    class Meta:
        nullable_fields = [
            "asn",
            "account",
            "portal_url",
            "noc_contact",
            "admin_contact",
            "comments",
        ]


class ProviderFilterForm(NautobotFilterForm, LocatableModelFilterFormMixin):
    model = Provider
    field_order = ["q"]
    q = forms.CharField(required=False, label="Search")
    asn = forms.IntegerField(required=False, label="ASN")
    tags = TagFilterField(model)


#
# Provider Networks
#


class ProviderNetworkForm(NautobotModelForm):
    provider = DynamicModelChoiceField(queryset=Provider.objects.all())
    comments = CommentField(label="Comments")

    class Meta:
        model = ProviderNetwork
        fields = [
            "provider",
            "name",
            "description",
            "comments",
            "tags",
        ]
        fieldsets = (("Provider Network", ("provider", "name", "description", "comments", "tags")),)


class ProviderNetworkBulkEditForm(TagsBulkEditFormMixin, NautobotBulkEditForm):
    pk = forms.ModelMultipleChoiceField(queryset=ProviderNetwork.objects.all(), widget=forms.MultipleHiddenInput)
    provider = DynamicModelChoiceField(queryset=Provider.objects.all(), required=False)
    description = forms.CharField(max_length=100, required=False)
    comments = CommentField(widget=SmallTextarea, label="Comments")

    class Meta:
        nullable_fields = [
            "description",
            "comments",
        ]


class ProviderNetworkFilterForm(NautobotFilterForm):
    model = ProviderNetwork
    field_order = ["q", "provider"]
    q = forms.CharField(required=False, label="Search")
    provider = DynamicModelMultipleChoiceField(
        queryset=Provider.objects.all(), required=False, label="Provider", to_field_name="name"
    )
    tags = TagFilterField(model)


#
# Circuit types
#


class CircuitTypeForm(NautobotModelForm):
    class Meta:
        model = CircuitType
        fields = [
            "name",
            "description",
        ]


#
# Circuits
#


class CircuitForm(NautobotModelForm, TenancyForm):
    provider = DynamicModelChoiceField(queryset=Provider.objects.all())
    circuit_type = DynamicModelChoiceField(queryset=CircuitType.objects.all())
    comments = CommentField()

    class Meta:
        model = Circuit
        fields = [
            "cid",
            "circuit_type",
            "provider",
            "status",
            "install_date",
            "commit_rate",
            "description",
            "tenant_group",
            "tenant",
            "comments",
            "tags",
        ]
        help_texts = {
            "cid": "Unique circuit ID",
            "commit_rate": "Committed rate",
        }
        widgets = {
            "install_date": DatePicker(),
        }


class CircuitBulkEditForm(TagsBulkEditFormMixin, StatusModelBulkEditFormMixin, NautobotBulkEditForm):
    pk = forms.ModelMultipleChoiceField(queryset=Circuit.objects.all(), widget=forms.MultipleHiddenInput)
    circuit_type = DynamicModelChoiceField(queryset=CircuitType.objects.all(), required=False)
    provider = DynamicModelChoiceField(queryset=Provider.objects.all(), required=False)
    tenant = DynamicModelChoiceField(queryset=Tenant.objects.all(), required=False)
    commit_rate = forms.IntegerField(required=False, label="Commit rate (Kbps)")
    description = forms.CharField(max_length=100, required=False)
    comments = CommentField(widget=SmallTextarea, label="Comments")

    class Meta:
        nullable_fields = [
            "tenant",
            "commit_rate",
            "description",
            "comments",
        ]


class CircuitFilterForm(
    NautobotFilterForm,
    LocatableModelFilterFormMixin,
    TenancyFilterForm,
    StatusModelFilterFormMixin,
):
    model = Circuit
    field_order = [
        "q",
        "circuit_type",
        "provider",
        "provider_network",
        "status",
        "location",
        "tenant_group",
        "tenant",
        "commit_rate",
    ]
    q = forms.CharField(required=False, label="Search")
    circuit_type = DynamicModelMultipleChoiceField(
        queryset=CircuitType.objects.all(), to_field_name="name", required=False
    )
    provider = DynamicModelMultipleChoiceField(queryset=Provider.objects.all(), to_field_name="name", required=False)
    provider_network = DynamicModelMultipleChoiceField(
        queryset=ProviderNetwork.objects.all(),
        required=False,
        query_params={"provider": "$provider"},
        to_field_name="name",
        label="Provider Network",
    )
    commit_rate = forms.IntegerField(required=False, min_value=0, label="Commit rate (Kbps)")
    tags = TagFilterField(model)


#
# Circuit terminations
#


class CircuitTerminationForm(LocatableModelFormMixin, NautobotModelForm):
    provider_network = DynamicModelChoiceField(
        queryset=ProviderNetwork.objects.all(), required=False, label="Provider Network"
    )

    class Meta:
        model = CircuitTermination
        fields = [
            "term_side",
            "location",
            "provider_network",
            "port_speed",
            "upstream_speed",
            "xconnect_id",
            "pp_info",
            "description",
            "tags",
        ]
        help_texts = {
            "port_speed": "Physical circuit speed",
            "xconnect_id": "ID of the local cross-connect",
            "pp_info": "Patch panel ID and port number(s)",
        }
        widgets = {
            "term_side": forms.HiddenInput(),
        }
