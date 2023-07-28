from django import forms
from django_filters.utils import get_model_field

from nautobot.apps.filters import FilterExtension, MultiValueCharFilter
from nautobot.ipam.filters import PrefixFilterSet
from nautobot.utilities.forms import DynamicModelMultipleChoiceField
from example_plugin.models import ClassificationGroupsModel



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
    """Test instance showing both filterset_fields and filterform_fields in action."""

    model = "ipam.prefix"

    the_field = get_model_field(
        PrefixFilterSet._meta.model,
        "destination_for_associations__source_example_plugin_classificationgroupsmodel__environment__name",
    )

    filter_field = PrefixFilterSet.filter_for_field(
        the_field,
        "destination_for_associations__source_example_plugin_classificationgroupsmodel__environment__name",
        "exact",
    )

    form_field = DynamicModelMultipleChoiceField(
        queryset=ClassificationGroupsModel.objects.all(),
        required=False,
        label="Classification Group Environment Name",
        to_field_name="name",
    )

    filterset_fields = {
        "example_plugin_classification_group_environment_value": MultiValueCharFilter(
            field_name="destination_for_associations__source_example_plugin_classificationgroupsmodel__environment__value__exact",
            label="Classification Group Environment Value",
        ),
        "example_plugin_classification_group_environment_name": filter_field,
    }

    filterform_fields = {
        "example_plugin_classification_group_environment_value": forms.CharField(
            required=False, label="Classification Group Environment Value"
        ),
        "example_plugin_classification_group_environment_name": form_field,
    }


filter_extensions = [TenantFilterExtension, DeviceFilterExtension, PrefixFilterExtension]
