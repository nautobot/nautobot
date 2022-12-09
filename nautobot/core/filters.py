from nautobot.core import models
from nautobot.extras import filters as extras_filters
from nautobot.extras import utils as extras_utils
from nautobot.utilities import filters as utilities_filters

__all__ = (
    "DynamicGroupFilterSet",
    "DynamicGroupMembershipFilterSet",
)


#
# Dynamic Groups
#


class DynamicGroupFilterSet(extras_filters.NautobotFilterSet):
    q = utilities_filters.SearchFilter(
        filter_predicates={
            "name": "icontains",
            "slug": "icontains",
            "description": "icontains",
            "content_type__app_label": "icontains",
            "content_type__model": "icontains",
        },
    )
    content_type = utilities_filters.ContentTypeMultipleChoiceFilter(
        choices=extras_utils.FeatureQuery("dynamic_groups").get_choices, conjoined=False
    )

    class Meta:
        model = models.dynamic_groups.DynamicGroup
        fields = ("id", "name", "slug", "description")


class DynamicGroupMembershipFilterSet(extras_filters.NautobotFilterSet):
    q = utilities_filters.SearchFilter(
        filter_predicates={
            "operator": "icontains",
            "group__name": "icontains",
            "group__slug": "icontains",
            "parent_group__name": "icontains",
            "parent_group__slug": "icontains",
        },
    )
    group = utilities_filters.NaturalKeyOrPKMultipleChoiceFilter(
        queryset=models.dynamic_groups.DynamicGroup.objects.all(),
        label="Group (slug or ID)",
    )
    parent_group = utilities_filters.NaturalKeyOrPKMultipleChoiceFilter(
        queryset=models.dynamic_groups.DynamicGroup.objects.all(),
        label="Parent Group (slug or ID)",
    )

    class Meta:
        model = models.dynamic_groups.DynamicGroupMembership
        fields = ("id", "group", "parent_group", "operator", "weight")
