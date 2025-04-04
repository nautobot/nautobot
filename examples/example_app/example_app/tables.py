import django_tables2 as tables

from nautobot.apps.tables import (
    BaseTable,
    ButtonsColumn,
    ToggleColumn,
)

from example_app.models import AnotherExampleModel, ExampleModel


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
