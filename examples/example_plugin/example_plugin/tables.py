import django_tables2 as tables

from nautobot.apps.tables import (
    BaseTable,
    ButtonsColumn,
    ToggleColumn,
)

from example_plugin.models import AnotherExampleModel, ExampleModel, ValueModel, ClassificationGroupsModel


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


class ValueModelTable(BaseTable):
    """Table for list view of `ValueModel` objects."""

    pk = ToggleColumn()
    name = tables.LinkColumn()
    actions = ButtonsColumn(ValueModel)

    class Meta(BaseTable.Meta):
        model = ValueModel
        fields = ["pk", "name", "value", "value_type"]


class ClassificationGroupsModelTable(BaseTable):
    """Table for list view of `ClassificationGroupsModel` objects."""

    pk = ToggleColumn()
    name = tables.LinkColumn()
    actions = ButtonsColumn(ClassificationGroupsModel)

    class Meta(BaseTable.Meta):
        model = ClassificationGroupsModel
        fields = ["pk", "name", "environment", "asset_tag", "network"]
