import django_tables2 as tables

from nautobot.core.tables import BaseTable, ButtonsColumn, ToggleColumn
from nautobot.users.models import SavedView


class SavedViewTable(BaseTable):
    pk = ToggleColumn()
    name = tables.Column(linkify=True)
    owner = tables.Column()
    view = tables.Column()
    actions = ButtonsColumn(SavedView, buttons=("changelog", "delete"))

    class Meta(BaseTable.Meta):
        model = SavedView
        fields = (
            "pk",
            "name",
            "owner",
            "view",
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
            "view",
            "actions",
        )
