from django.db.models import Q
import django_filters

from nautobot.dcim.models import Cable, Device, DeviceType, Region, Site, Location
from nautobot.extras.filters import CustomFieldModelFilterSetMixin
from nautobot.utilities.filters import (
    MultiValueCharFilter,
    MultiValueUUIDFilter,
    NaturalKeyOrPKMultipleChoiceFilter,
    NameSlugSearchFilterSet,
    SearchFilter,
    TagFilter,
    TreeNodeMultipleChoiceFilter,
)


class CableTerminationModelFilterSetMixin(django_filters.FilterSet):
    cabled = django_filters.BooleanFilter(field_name="cable", lookup_expr="isnull", exclude=True)
    cable = django_filters.ModelMultipleChoiceFilter(
        queryset=Cable.objects.all(),
        label="Cable",
    )


class DeviceComponentTemplateModelFilterSetMixin(NameSlugSearchFilterSet, CustomFieldModelFilterSetMixin):
    devicetype_id = django_filters.ModelMultipleChoiceFilter(
        queryset=DeviceType.objects.all(),
        field_name="device_type_id",
        label="Device type (ID)",
    )
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
    region_id = TreeNodeMultipleChoiceFilter(
        queryset=Region.objects.all(),
        field_name="device__site__region",
        label="Region (ID)",
    )
    region = TreeNodeMultipleChoiceFilter(
        queryset=Region.objects.all(),
        field_name="device__site__region",
        label="Region (slug)",
    )
    site_id = django_filters.ModelMultipleChoiceFilter(
        field_name="device__site",
        queryset=Site.objects.all(),
        label="Site (ID)",
    )
    site = django_filters.ModelMultipleChoiceFilter(
        field_name="device__site__slug",
        queryset=Site.objects.all(),
        to_field_name="slug",
        label="Site name (slug)",
    )
    device_id = django_filters.ModelMultipleChoiceFilter(
        queryset=Device.objects.all(),
        label="Device (ID)",
    )
    device = django_filters.ModelMultipleChoiceFilter(
        field_name="device__name",
        queryset=Device.objects.all(),
        to_field_name="name",
        label="Device (name)",
    )
    tag = TagFilter()


class LocatableModelFilterSetMixin(django_filters.FilterSet):
    """Mixin to add `region`, `site`, and `location` filter fields to a FilterSet.

    The expectation is that the linked model has `site` and `location` FK fields,
    while `region` is indirectly associated via the `site`.
    """

    region_id = TreeNodeMultipleChoiceFilter(
        queryset=Region.objects.all(),
        field_name="site__region",
        label='Region (ID) (deprecated, use "region" filter instead)',
    )
    region = TreeNodeMultipleChoiceFilter(
        queryset=Region.objects.all(),
        field_name="site__region",
        label="Region (slug or ID)",
    )
    site_id = django_filters.ModelMultipleChoiceFilter(
        queryset=Site.objects.all(),
        label='Site (ID) (deprecated, use "site" filter instead)',
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
