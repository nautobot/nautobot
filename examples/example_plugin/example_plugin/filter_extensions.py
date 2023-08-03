from django import forms

from nautobot.apps.filters import FilterExtension, MultiValueCharFilter
from nautobot.tenancy.models import Tenant
from nautobot.utilities.forms import DynamicModelMultipleChoiceField


def suffix_search(queryset, name, value):
    return queryset.filter(description=f"{value[0]}.nautobot.com")


class TenantFilterExtension(FilterExtension):
    """Test instance showing both filterset_fields and filterform_fields in action."""

    model = "tenancy.tenant"

    filterset_fields = {
        "example_plugin_description": MultiValueCharFilter(field_name="description", label="Description"),
        "example_plugin_sdescrip": MultiValueCharFilter(
            field_name="description", label="Description", method=suffix_search
        ),
        "example_plugin_dtype": MultiValueCharFilter(
            field_name="sites__devices__device_type__slug", label="Device Type"
        ),
    }

    filterform_fields = {
        "example_plugin_description": forms.CharField(required=False, label="Description"),
        "example_plugin_dtype": forms.CharField(required=False, label="Device Type"),
        "slug__ic": forms.CharField(required=False, label="Slug Contains"),
        "example_plugin_sdescrip": forms.CharField(required=False, label="Suffix Description"),
    }


class DeviceFilterExtension(FilterExtension):
    """Created to test that filterset_fields and filterform_fields being empty dicts is fine."""

    model = "dcim.device"


class PrefixFilterExtension(FilterExtension):
    """Created to test filter extensions and Dynamic Group support."""

    model = "ipam.prefix"

    filterset_fields = {
        "example_plugin_prefix_tenant_name": MultiValueCharFilter(field_name="tenant__name", label="Tenant Name"),
    }

    filterform_fields = {
        "example_plugin_prefix_tenant_name": DynamicModelMultipleChoiceField(
            queryset=Tenant.objects.all(),
            to_field_name="name",
            required=False,
            label="Tenant Name",
        )
    }


filter_extensions = [TenantFilterExtension, DeviceFilterExtension, PrefixFilterExtension]
