from django import forms

from nautobot.extras.plugins import PluginFilterExtension
from nautobot.utilities.filters import MultiValueCharFilter


def suffix_search(queryset, name, value):
    return queryset.filter(description=f"{value[0]}.nautobot.com")


class TenantFilterSetExtension(PluginFilterExtension):
    model = "tenancy.tenant"

    _fsf_description = MultiValueCharFilter(field_name="description", label="Description")  # Creation of a new filter
    _fsf_sdescrip = MultiValueCharFilter(
        field_name="description", label="Description", method=suffix_search
    )  # Creation of new filter with custom method
    _fsf_dtype = MultiValueCharFilter(
        field_name="sites__devices__device_type__slug", label="Device Type"
    )  # Creation of a nested filter

    filterset_fields = {
        "example_plugin_description": _fsf_description,
        "example_plugin_dtype": _fsf_dtype,
        "example_plugin_sdescrip": _fsf_sdescrip,
    }

    _fff_description = forms.CharField(required=False, label="Description")  # Leveraging a custom filter
    _fff_dtype = forms.CharField(required=False, label="Device Type")  # Leveraging a custom and nested filter
    _fff_slug__ic = forms.CharField(required=False, label="Slug Contains")  # Leveraging an existing filter
    _fff_sdescrip = forms.CharField(
        required=False, label="Suffix Description"
    )  # Leveraging a custom method search filter

    filterform_fields = {
        "example_plugin_description": _fff_description,
        "example_plugin_dtype": _fff_dtype,
        "slug__ic": _fff_slug__ic,
        "example_plugin_sdescrip": _fff_sdescrip,
    }


# created to test that filterset and filter_form being None is fine
class DeviceFilterSetExtension(PluginFilterExtension):
    model = "dcim.device"


filter_extensions = [TenantFilterSetExtension, DeviceFilterSetExtension]
