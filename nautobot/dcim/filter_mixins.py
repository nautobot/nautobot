import django_filters

from nautobot.dcim.models import Region, Site, Location
from nautobot.utilities.filters import SlugOrPKMultipleChoiceFilter, TreeNodeMultipleChoiceFilter


class LocatableModelFilterSetMixin(django_filters.FilterSet):
    """Mixin to add `region`, `site`, and `location` filter fields to a FilterSet.

    The expectation is that the linked model has `site` and `location` FK fields,
    while `region` is indirectly associated via the `site`.
    """

    region_id = TreeNodeMultipleChoiceFilter(
        queryset=Region.objects.all(),
        field_name="site__region",
        lookup_expr="in",
        label="Region (ID)",
    )
    region = TreeNodeMultipleChoiceFilter(
        queryset=Region.objects.all(),
        field_name="site__region",
        lookup_expr="in",
        to_field_name="slug",
        label="Region (slug)",
    )
    site_id = django_filters.ModelMultipleChoiceFilter(
        queryset=Site.objects.all(),
        label='Site (ID) (deprecated, use "site" filter instead)',
    )
    site = SlugOrPKMultipleChoiceFilter(
        queryset=Site.objects.all(),
        field_name="site__slug",
        to_field_name="slug",
        label="Site (slug or ID)",
    )
    location_id = TreeNodeMultipleChoiceFilter(
        queryset=Location.objects.all(),
        lookup_expr="in",
        label="Location (ID)",
    )
    location = TreeNodeMultipleChoiceFilter(
        queryset=Location.objects.all(),
        lookup_expr="in",
        to_field_name="slug",
        label="Location (slug)",
    )
