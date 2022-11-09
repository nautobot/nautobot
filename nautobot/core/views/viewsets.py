from . import mixins


class NautobotUIViewSet(
    mixins.ObjectDetailViewMixin,
    mixins.ObjectListViewMixin,
    mixins.ObjectEditViewMixin,
    mixins.ObjectDestroyViewMixin,
    mixins.ObjectBulkDestroyViewMixin,
    mixins.ObjectBulkCreateViewMixin,
    mixins.ObjectBulkUpdateViewMixin,
    mixins.ObjectChangeLogViewMixin,
    mixins.ObjectNotesViewMixin,
):
    """
    Nautobot BaseViewSet that is intended for UI use only. It provides default Nautobot functionalities such as
    `create()`, `bulk_create()`, `update()`, `partial_update()`, `bulk_update()`, `destroy()`, `bulk_destroy()`, `retrieve()`
    `notes()`, `changelog()` and `list()` actions.
    """
