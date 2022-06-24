import django_filters

from nautobot.dcim.models import Region, Site, Location
from nautobot.utilities.filters import NaturalKeyOrPKMultipleChoiceFilter, TreeNodeMultipleChoiceFilter


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
