import django_filters

from nautobot.extras.models import Role
from nautobot.utilities.filters import NaturalKeyOrPKMultipleChoiceFilter


class RoleFilter(NaturalKeyOrPKMultipleChoiceFilter):
    """Limit role choices to the available role choices for self.model"""

    def __init__(self, *args, **kwargs):

        kwargs.setdefault("field_name", kwargs.get("field_name", "role"))
        kwargs.setdefault("to_field_name", "slug")
        kwargs.setdefault("queryset", Role.objects.all())
        kwargs.setdefault("label", "Role (slug or ID)")

        super().__init__(*args, **kwargs)

    def get_queryset(self, request):
        return self.queryset.get_for_model(self.model)


class RoleModelFilterSetMixin(django_filters.FilterSet):
    """
    Mixin to add a `role` filter field to a FilterSet.
    """

    role = RoleFilter()
