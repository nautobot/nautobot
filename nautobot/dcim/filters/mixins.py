from django.db.models import Q
import django_filters

from nautobot.dcim.models import Cable, Device, DeviceType, Region, Site, Location
from nautobot.extras.filters import CustomFieldModelFilterSetMixin
from nautobot.utilities.filters import (
    MultiValueCharFilter,
    MultiValueUUIDFilter,
    NaturalKeyOrPKMultipleChoiceFilter,
    NameSlugSearchFilterSet,
    RelatedMembershipBooleanFilter,
    SearchFilter,
    TreeNodeMultipleChoiceFilter,
)


class CableTerminationModelFilterSetMixin(django_filters.FilterSet):
    has_cable = RelatedMembershipBooleanFilter(
        field_name="cable",
        label="Has cable",
    )
    cable = django_filters.ModelMultipleChoiceFilter(
        queryset=Cable.objects.all(),
        label="Cable",
    )


class DeviceComponentTemplateModelFilterSetMixin(NameSlugSearchFilterSet, CustomFieldModelFilterSetMixin):
    device_type = NaturalKeyOrPKMultipleChoiceFilter(
        queryset=DeviceType.objects.all(),
        label="Device type (slug or ID)",
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
    region = TreeNodeMultipleChoiceFilter(
        queryset=Region.objects.all(),
        field_name="device__site__region",
        label="Region (slug or ID)",
    )
    site = NaturalKeyOrPKMultipleChoiceFilter(
        field_name="device__site",
        queryset=Site.objects.all(),
        label="Site (slug or ID)",
    )
    device = NaturalKeyOrPKMultipleChoiceFilter(
        queryset=Device.objects.all(),
        to_field_name="name",
        label="Device (name or ID)",
    )


class LocatableModelFilterSetMixin(django_filters.FilterSet):
    """Mixin to add `region`, `site`, and `location` filter fields to a FilterSet.

    The expectation is that the linked model has `site` and `location` FK fields,
    while `region` is indirectly associated via the `site`.
    """

    region = TreeNodeMultipleChoiceFilter(
        queryset=Region.objects.all(),
        field_name="site__region",
        label="Region (slug or ID)",
    )
    site = NaturalKeyOrPKMultipleChoiceFilter(
        queryset=Site.objects.all(),
        label="Site (slug or ID)",
    )
    location = TreeNodeMultipleChoiceFilter(
        queryset=Location.objects.all(),
        label="Location (slug or ID)",
    )


class PathEndpointModelFilterSetMixin(django_filters.FilterSet):
    connected = django_filters.BooleanFilter(method="filter_connected", label="Connected status (bool)")

    def filter_connected(self, queryset, name, value):
        if value:
            return queryset.filter(_path__is_active=True)
        else:
            return queryset.filter(Q(_path__isnull=True) | Q(_path__is_active=False))
