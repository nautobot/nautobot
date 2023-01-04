class LimitQuerysetChoicesSerializerMixin:
    """Mixin field that restricts queryset choices to those accessible
    for the queryset model that implemented it."""

    def get_queryset(self):
        """Only emit options for this model/field combination."""
        queryset = super().get_queryset()
        # Get objects model e.g Site, Device... etc.
        # Tags model can be gotten using self.parent.parent, while others uses self.parent
        try:
            model = self.parent.Meta.model
        except AttributeError:
            model = self.parent.parent.Meta.model
        return queryset.get_for_model(model)
