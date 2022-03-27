from django import forms

from nautobot.extras.plugins import PluginFilterExtension
from nautobot.utilities.filters import MultiValueCharFilter


def suffix_search(queryset, name, value):
    return queryset.filter(description=f"{value[0]}.nautobot.com")


class TenantFilterSetExtension(PluginFilterExtension):
    model = "tenancy.tenant"

    def filterset(self):
        description = MultiValueCharFilter(field_name="description", label="Description")  # Creation of a new filter
        sdescrip = MultiValueCharFilter(
            field_name="description", label="Description", method=suffix_search
        )  # Creation of new filter with custom method
        dtype = MultiValueCharFilter(
            field_name="sites__devices__device_type__slug", label="Device Type"
        )  # Creation of a nested filter
        return {
            "example_plugin_description": description,
            "example_plugin_dtype": dtype,
            "example_plugin_sdescrip": sdescrip,
        }

    def filter_form(self):
        description = forms.CharField(required=False, label="Description")  # Leveraging a custom filter
        dtype = forms.CharField(required=False, label="Device Type")  # Leveraging a custom and nested filter
        slug__ic = forms.CharField(required=False, label="Slug Contains")  # Leveraging an existing filter
        sdescrip = forms.CharField(
            required=False, label="Suffix Description"
        )  # Leveraging a custom method search filter
        return {
            "example_plugin_description": description,
            "example_plugin_dtype": dtype,
            "slug__ic": slug__ic,
            "example_plugin_sdescrip": sdescrip,
        }


# created to test that filterset and filter_form being None is fine
class DeviceFilterSetExtension(PluginFilterExtension):
    model = "dcim.device"


filter_extensions = [TenantFilterSetExtension, DeviceFilterSetExtension]
