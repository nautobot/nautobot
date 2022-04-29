import django_tables2 as tables

from nautobot.utilities.tables import (
    BaseTable,
    ButtonsColumn,
    ToggleColumn,
)

from example_plugin.models import AnotherExampleModel, ExampleModel


class ExampleModelTable(BaseTable):
    """Table for list view of `ExampleModel` objects."""

    pk = ToggleColumn()
    name = tables.LinkColumn()
    actions = ButtonsColumn(ExampleModel)

    class Meta(BaseTable.Meta):
        model = ExampleModel
        fields = ["pk", "name", "number"]


class AnotherExampleModelTable(BaseTable):
    """Table for list view of `AnotherExampleModel` objects."""

    pk = ToggleColumn()
    name = tables.LinkColumn()
    actions = ButtonsColumn(AnotherExampleModel)

    class Meta(BaseTable.Meta):
        model = AnotherExampleModel
        fields = ["pk", "name", "number"]
