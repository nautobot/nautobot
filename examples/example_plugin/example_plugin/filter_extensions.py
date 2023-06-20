from django import forms

from nautobot.apps.filters import FilterExtension, MultiValueCharFilter


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
            field_name="locations__devices__device_type__model", label="Device Type (model)"
        ),
    }

    filterform_fields = {
        "example_plugin_description": forms.CharField(required=False, label="Description"),
        "example_plugin_dtype": forms.CharField(required=False, label="Device Type"),
        "name__ic": forms.CharField(required=False, label="Name Contains"),
        "example_plugin_sdescrip": forms.CharField(required=False, label="Suffix Description"),
    }


class DeviceFilterExtension(FilterExtension):
    """Created to test that filterset_fields and filterform_fields being empty dicts is fine."""

    model = "dcim.device"


filter_extensions = [TenantFilterExtension, DeviceFilterExtension]
