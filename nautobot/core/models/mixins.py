from django.urls import NoReverseMatch, reverse

from nautobot.utilities import utils as utilities_utils


class DynamicGroupMixin:
    """
    Adds a `dynamic_groups` property that returns a queryset of `DynamicGroup` membership.
    """

    @property
    def dynamic_groups(self):
        """Return a `DynamicGroup` queryset for this instance."""
        from nautobot.core.models.groups import DynamicGroup

        if not hasattr(self, "_dynamic_group_queryset"):
            queryset = DynamicGroup.objects.get_for_object(self)
            self._dynamic_group_queryset = queryset

        return self._dynamic_group_queryset

    def get_dynamic_groups_url(self):
        """Return the dynamic groups URL for a given instance."""
        route = utilities_utils.get_route_for_model(self, "dynamicgroups")

        # Iterate the pk-like fields and try to get a URL, or return None.
        fields = ["pk", "slug"]
        for field in fields:
            if not hasattr(self, field):
                continue

            try:
                return reverse(route, kwargs={field: getattr(self, field)})
            except NoReverseMatch:
                continue

        return None
