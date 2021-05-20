import django_tables2 as tables

from nautobot.utilities.tables import (
    BaseTable,
    ButtonsColumn,
    ToggleColumn,
)

from .models import DummyModel


class DummyModelTable(BaseTable):
    """Table for list view of `DummyModel` objects."""

    pk = ToggleColumn()
    name = tables.LinkColumn()
    actions = ButtonsColumn(DummyModel)

    class Meta(BaseTable.Meta):
        model = DummyModel
        fields = ["pk", "name", "number"]
