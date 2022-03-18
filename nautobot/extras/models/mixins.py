"""
Class-modifying mixins that need to be standalone to avoid circular imports.
"""


class DynamicGroupMixin:
    """
    Adds a `dynamic_groups` property that returns a queryset of `DynamicGroup` membership.
    """

    @property
    def dynamic_groups(self):
        """Return a `DynamicGroup` queryset for this instance."""
        from nautobot.extras.models.groups import DynamicGroup

        if not hasattr(self, "_dynamic_group_queryset"):
            queryset = DynamicGroup.objects.get_for_object(self)
            self._dynamic_group_queryset = queryset

        return self._dynamic_group_queryset
