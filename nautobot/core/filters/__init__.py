from nautobot.core.filters.mixins import RoleFilter, RoleModelFilterSetMixin
from nautobot.extras.filters import NautobotFilterSet
from nautobot.extras.models import Role
from nautobot.extras.utils import RoleModelsQuery
from nautobot.utilities.filters import ContentTypeMultipleChoiceFilter, SearchFilter

__all__ = ("RoleFilter", "RoleFilterSet", "RoleModelFilterSetMixin")
#
# Roles
#


class RoleFilterSet(NautobotFilterSet):
    """API filter for filtering custom role object fields."""

    q = SearchFilter(
        filter_predicates={
            "name": "icontains",
            "slug": "icontains",
            "content_types__model": "icontains",
        },
    )
    content_types = ContentTypeMultipleChoiceFilter(
        choices=RoleModelsQuery().get_choices,
    )

    class Meta:
        model = Role
        fields = [
            "id",
            "content_types",
            "color",
            "name",
            "slug",
            "weight",
            "created",
            "last_updated",
        ]
