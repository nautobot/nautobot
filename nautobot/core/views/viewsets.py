from . import mixins


class NautobotUIViewSet(
    mixins.ObjectDetailViewMixin,
    mixins.ObjectListViewMixin,
    mixins.ObjectEditViewMixin,
    mixins.ObjectDestroyViewMixin,
    mixins.ObjectBulkDestroyViewMixin,
    mixins.ObjectBulkCreateViewMixin,
    mixins.ObjectBulkUpdateViewMixin,
):
    """
    This is the UI BaseViewSet you should inherit.
    """
