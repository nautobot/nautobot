from django.db.models import Q
import django_filters

from nautobot.core.filters import (
    MultiValueCharFilter,
    MultiValueUUIDFilter,
    NaturalKeyOrPKMultipleChoiceFilter,
    NameSearchFilterSet,
    RelatedMembershipBooleanFilter,
    SearchFilter,
    TreeNodeMultipleChoiceFilter,
)
from nautobot.dcim.models import Cable, Device, DeviceType, Location
from nautobot.extras.filters import CustomFieldModelFilterSetMixin


class CableTerminationModelFilterSetMixin(django_filters.FilterSet):
    has_cable = RelatedMembershipBooleanFilter(
        field_name="cable",
        label="Has cable",
    )
    cable = django_filters.ModelMultipleChoiceFilter(
        queryset=Cable.objects.all(),
        label="Cable",
    )


class DeviceComponentTemplateModelFilterSetMixin(NameSearchFilterSet, CustomFieldModelFilterSetMixin):
    device_type = NaturalKeyOrPKMultipleChoiceFilter(
        queryset=DeviceType.objects.all(),
        to_field_name="model",
        label="Device type (model or ID)",
    )
    label = MultiValueCharFilter(label="Label")
    description = MultiValueCharFilter(label="Description")
    id = MultiValueUUIDFilter(label="ID")
    name = MultiValueCharFilter(label="Name")


class DeviceComponentModelFilterSetMixin(CustomFieldModelFilterSetMixin):
    q = SearchFilter(
        filter_predicates={
            "name": "icontains",
            "label": "icontains",
            "description": "icontains",
        },
    )
    location = NaturalKeyOrPKMultipleChoiceFilter(
        field_name="device__location",
        queryset=Location.objects.all(),
        to_field_name="name",
        label="Location (name or ID)",
    )
    device = NaturalKeyOrPKMultipleChoiceFilter(
        queryset=Device.objects.all(),
        to_field_name="name",
        label="Device (name or ID)",
    )


class LocatableModelFilterSetMixin(django_filters.FilterSet):
    """Mixin to add `location` filter fields to a FilterSet.

    The expectation is that the linked model has `location` FK fields.
    """

    location = TreeNodeMultipleChoiceFilter(
        queryset=Location.objects.all(),
        to_field_name="name",
        label="Location (name or ID)",
    )


class PathEndpointModelFilterSetMixin(django_filters.FilterSet):
    connected = django_filters.BooleanFilter(method="filter_connected", label="Connected status (bool)")

    def filter_connected(self, queryset, name, value):
        if value:
            return queryset.filter(_path__is_active=True)
        else:
            return queryset.filter(Q(_path__isnull=True) | Q(_path__is_active=False))
