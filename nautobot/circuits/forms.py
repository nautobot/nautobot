from django import forms

from nautobot.dcim.models import Region, Site
from nautobot.extras.forms import (
    AddRemoveTagsForm,
    CustomFieldBulkEditForm,
    CustomFieldFilterForm,
    CustomFieldModelForm,
    CustomFieldModelCSVForm,
    RelationshipModelForm,
    StatusBulkEditFormMixin,
    StatusModelCSVFormMixin,
    StatusFilterFormMixin,
)
from nautobot.extras.models import Tag
from nautobot.tenancy.forms import TenancyFilterForm, TenancyForm
from nautobot.tenancy.models import Tenant
from nautobot.utilities.forms import (
    BootstrapMixin,
    CommentField,
    CSVModelChoiceField,
    DatePicker,
    DynamicModelChoiceField,
    DynamicModelMultipleChoiceField,
    SmallTextarea,
    SlugField,
    TagFilterField,
)
from .models import Circuit, CircuitTermination, CircuitType, Provider


#
# Providers
#


class ProviderForm(BootstrapMixin, CustomFieldModelForm, RelationshipModelForm):
    slug = SlugField()
    comments = CommentField()
    tags = DynamicModelMultipleChoiceField(queryset=Tag.objects.all(), required=False)

    class Meta:
        model = Provider
        fields = [
            "name",
            "slug",
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


class ProviderCSVForm(CustomFieldModelCSVForm):
    slug = SlugField()

    class Meta:
        model = Provider
        fields = Provider.csv_headers


class ProviderBulkEditForm(BootstrapMixin, AddRemoveTagsForm, CustomFieldBulkEditForm):
    pk = forms.ModelMultipleChoiceField(queryset=Provider.objects.all(), widget=forms.MultipleHiddenInput)
    asn = forms.IntegerField(required=False, label="ASN")
    account = forms.CharField(max_length=30, required=False, label="Account number")
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


class ProviderFilterForm(BootstrapMixin, CustomFieldFilterForm):
    model = Provider
    q = forms.CharField(required=False, label="Search")
    region = DynamicModelMultipleChoiceField(queryset=Region.objects.all(), to_field_name="slug", required=False)
    site = DynamicModelMultipleChoiceField(
        queryset=Site.objects.all(),
        to_field_name="slug",
        required=False,
        query_params={"region": "$region"},
    )
    asn = forms.IntegerField(required=False, label="ASN")
    tag = TagFilterField(model)


#
# Circuit types
#


class CircuitTypeForm(BootstrapMixin, CustomFieldModelForm, RelationshipModelForm):
    slug = SlugField()

    class Meta:
        model = CircuitType
        fields = [
            "name",
            "slug",
            "description",
        ]


class CircuitTypeCSVForm(CustomFieldModelCSVForm):
    slug = SlugField()

    class Meta:
        model = CircuitType
        fields = CircuitType.csv_headers
        help_texts = {
            "name": "Name of circuit type",
        }


#
# Circuits
#


class CircuitForm(BootstrapMixin, TenancyForm, CustomFieldModelForm, RelationshipModelForm):
    provider = DynamicModelChoiceField(queryset=Provider.objects.all())
    type = DynamicModelChoiceField(queryset=CircuitType.objects.all())
    comments = CommentField()
    tags = DynamicModelMultipleChoiceField(queryset=Tag.objects.all(), required=False)

    class Meta:
        model = Circuit
        fields = [
            "cid",
            "type",
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


class CircuitCSVForm(StatusModelCSVFormMixin, CustomFieldModelCSVForm):
    provider = CSVModelChoiceField(
        queryset=Provider.objects.all(),
        to_field_name="name",
        help_text="Assigned provider",
    )
    type = CSVModelChoiceField(
        queryset=CircuitType.objects.all(),
        to_field_name="name",
        help_text="Type of circuit",
    )
    tenant = CSVModelChoiceField(
        queryset=Tenant.objects.all(),
        required=False,
        to_field_name="name",
        help_text="Assigned tenant",
    )

    class Meta:
        model = Circuit
        fields = [
            "cid",
            "provider",
            "type",
            "status",
            "tenant",
            "install_date",
            "commit_rate",
            "description",
            "comments",
        ]


class CircuitBulkEditForm(BootstrapMixin, AddRemoveTagsForm, StatusBulkEditFormMixin, CustomFieldBulkEditForm):
    pk = forms.ModelMultipleChoiceField(queryset=Circuit.objects.all(), widget=forms.MultipleHiddenInput)
    type = DynamicModelChoiceField(queryset=CircuitType.objects.all(), required=False)
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


class CircuitFilterForm(BootstrapMixin, TenancyFilterForm, StatusFilterFormMixin, CustomFieldFilterForm):
    model = Circuit
    field_order = [
        "q",
        "type",
        "provider",
        "status",
        "region",
        "site",
        "tenant_group",
        "tenant",
        "commit_rate",
    ]
    q = forms.CharField(required=False, label="Search")
    type = DynamicModelMultipleChoiceField(queryset=CircuitType.objects.all(), to_field_name="slug", required=False)
    provider = DynamicModelMultipleChoiceField(queryset=Provider.objects.all(), to_field_name="slug", required=False)
    region = DynamicModelMultipleChoiceField(queryset=Region.objects.all(), to_field_name="slug", required=False)
    site = DynamicModelMultipleChoiceField(
        queryset=Site.objects.all(),
        to_field_name="slug",
        required=False,
        query_params={"region": "$region"},
    )
    commit_rate = forms.IntegerField(required=False, min_value=0, label="Commit rate (Kbps)")
    tag = TagFilterField(model)


#
# Circuit terminations
#


class CircuitTerminationForm(BootstrapMixin, RelationshipModelForm):
    region = DynamicModelChoiceField(queryset=Region.objects.all(), required=False, initial_params={"sites": "$site"})
    site = DynamicModelChoiceField(queryset=Site.objects.all(), query_params={"region_id": "$region"})

    class Meta:
        model = CircuitTermination
        fields = [
            "term_side",
            "region",
            "site",
            "port_speed",
            "upstream_speed",
            "xconnect_id",
            "pp_info",
            "description",
        ]
        help_texts = {
            "port_speed": "Physical circuit speed",
            "xconnect_id": "ID of the local cross-connect",
            "pp_info": "Patch panel ID and port number(s)",
        }
        widgets = {
            "term_side": forms.HiddenInput(),
        }
