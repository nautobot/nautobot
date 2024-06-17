import django_tables2 as tables

from nautobot.core.tables import BaseTable, BooleanColumn, ButtonsColumn
from nautobot.core.templatetags.helpers import render_json
from nautobot.users.models import SavedView


class SavedViewTable(BaseTable):
    name = tables.Column(linkify=True)
    actions = ButtonsColumn(SavedView)
    is_global_default = BooleanColumn()
    is_shared = BooleanColumn()

    class Meta(BaseTable.Meta):
        model = SavedView
        fields = (
            "name",
            "owner",
            "view",
            "config",
            "is_global_default",
            "is_shared",
            "actions",
        )
        default_columns = (
            "name",
            "owner",
            "view",
            "is_global_default",
            "actions",
        )

    def render_config(self, record):
        if record.config:
            return render_json(record.config, pretty_print=True)
        return self.default
