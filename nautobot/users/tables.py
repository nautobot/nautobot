import django_tables2 as tables

from nautobot.core.tables import BaseTable, ButtonsColumn, ToggleColumn
from nautobot.core.templatetags.helpers import render_json
from nautobot.users.models import SavedView


class SavedViewTable(BaseTable):
    pk = ToggleColumn()
    name = tables.Column(linkify=True)
    actions = ButtonsColumn(SavedView, buttons=("changelog", "delete"))

    class Meta(BaseTable.Meta):
        model = SavedView
        fields = (
            "pk",
            "name",
            "owner",
            "view",
            "config",
            "actions",
        )
        default_columns = (
            "pk",
            "name",
            "owner",
            "view",
            "actions",
        )

    def render_table_config(self, record):
        if record.table_config:
            return render_json(record.table_config)
        return self.default

    def render_filter_params(self, record):
        if record.filter_params:
            return render_json(record.filter_params)
        return self.default

    def render_sort_order(self, record):
        if record.sort_order:
            return render_json(record.sort_order)
        return self.default
