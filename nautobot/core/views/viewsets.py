from . import mixins


class NautobotUIViewSet(
    mixins.ObjectDetailViewMixin,
    mixins.ObjectListViewMixin,
    mixins.ObjectEditViewMixin,
    mixins.ObjectDestroyViewMixin,
    mixins.ObjectBulkDestroyViewMixin,
    mixins.ObjectBulkCreateViewMixin,  # 3.0 TODO: remove, no longer needed after ImportObjects system Job.
    mixins.ObjectBulkUpdateViewMixin,
    mixins.ObjectChangeLogViewMixin,
    mixins.ObjectNotesViewMixin,
    mixins.ObjectDataComplianceViewMixin,
):
    """
    Nautobot BaseViewSet that is intended for UI use only. It provides default Nautobot functionalities such as
    `create()`, `update()`, `partial_update()`, `bulk_update()`, `destroy()`, `bulk_destroy()`, `retrieve()`
    `notes()`, `changelog()`, `list()`, and `data_compliance()` actions.
    """
