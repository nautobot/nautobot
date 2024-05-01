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

    def render_config(self, record):
        if record.config:
            return render_json(record.config, pretty_print=True)
        return self.default
