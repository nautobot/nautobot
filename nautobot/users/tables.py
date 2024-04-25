import django_tables2 as tables

from nautobot.core.tables import BaseTable, ButtonsColumn, ToggleColumn
from nautobot.users.models import SavedView


class SavedViewTable(BaseTable):
    pk = ToggleColumn()
    name = tables.Column(linkify=True)
    owner = tables.Column()
    list_view_name = tables.Column()
    actions = ButtonsColumn(SavedView)

    class Meta(BaseTable.Meta):
        model = SavedView
        fields = (
            "pk",
            "name",
            "owner",
            "list_view_name",
            "table_config",
            "pagination_count",
            "filter_params",
            "sort_order",
            "actions",
        )
        default_columns = (
            "pk",
            "name",
            "owner",
            "list_view_name",
            "actions",
        )
