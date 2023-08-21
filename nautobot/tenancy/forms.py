from django import forms

from nautobot.core.forms import (
    CommentField,
    DynamicModelChoiceField,
    DynamicModelMultipleChoiceField,
    TagFilterField,
)
from nautobot.extras.forms import (
    NautobotFilterForm,
    NautobotBulkEditForm,
    NautobotModelForm,
    TagsBulkEditFormMixin,
)
from .models import Tenant, TenantGroup


#
# Tenant groups
#


class TenantGroupForm(NautobotModelForm):
    parent = DynamicModelChoiceField(queryset=TenantGroup.objects.all(), required=False)

    class Meta:
        model = TenantGroup
        fields = [
            "parent",
            "name",
            "description",
        ]


#
# Tenants
#


class TenantForm(NautobotModelForm):
    tenant_group = DynamicModelChoiceField(queryset=TenantGroup.objects.all(), required=False)
    comments = CommentField()

    class Meta:
        model = Tenant
        fields = (
            "name",
            "tenant_group",
            "description",
            "comments",
            "tags",
        )


class TenantBulkEditForm(TagsBulkEditFormMixin, NautobotBulkEditForm):
    pk = forms.ModelMultipleChoiceField(queryset=Tenant.objects.all(), widget=forms.MultipleHiddenInput())
    tenant_group = DynamicModelChoiceField(queryset=TenantGroup.objects.all(), required=False)

    class Meta:
        nullable_fields = [
            "tenant_group",
        ]


class TenantFilterForm(NautobotFilterForm):
    model = Tenant
    q = forms.CharField(required=False, label="Search")
    tenant_group = DynamicModelMultipleChoiceField(
        queryset=TenantGroup.objects.all(),
        to_field_name="name",
        required=False,
        null_option="None",
    )
    tags = TagFilterField(model)


#
# Form extensions
#


class TenancyForm(forms.Form):
    tenant_group = DynamicModelChoiceField(
        queryset=TenantGroup.objects.all(),
        required=False,
        null_option="None",
        initial_params={"tenants": "$tenant"},
    )
    tenant = DynamicModelChoiceField(
        queryset=Tenant.objects.all(),
        required=False,
        query_params={"tenant_group": "$tenant_group"},
    )


class TenancyFilterForm(forms.Form):
    tenant_group = DynamicModelMultipleChoiceField(
        queryset=TenantGroup.objects.all(),
        to_field_name="name",
        required=False,
        null_option="None",
    )
    tenant = DynamicModelMultipleChoiceField(
        queryset=Tenant.objects.all(),
        to_field_name="name",
        required=False,
        null_option="None",
        query_params={"tenant_group": "$tenant_group"},
    )
