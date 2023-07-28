from nautobot.apps.filters import BaseFilterSet, SearchFilter

from example_plugin.models import AnotherExampleModel, ExampleModel, ValueModel, ClassificationGroupsModel


class ExampleModelFilterSet(BaseFilterSet):
    """API filter for filtering example model objects."""

    q = SearchFilter(
        filter_predicates={
            "name": "icontains",
            "number": "icontains",
        },
    )

    class Meta:
        model = ExampleModel
        fields = [
            "name",
            "number",
        ]


class AnotherExampleModelFilterSet(BaseFilterSet):
    """API filter for filtering another example model objects."""

    q = SearchFilter(
        filter_predicates={
            "name": "icontains",
            "number": "icontains",
        },
    )

    class Meta:
        model = AnotherExampleModel
        fields = [
            "name",
            "number",
        ]


class ValueModelFilterSet(BaseFilterSet):
    """API filter for filtering Value model objects."""

    q = SearchFilter(
        filter_predicates={
            "name": "icontains",
            "value": "icontains",
        },
    )

    class Meta:
        model = ValueModel
        fields = [
            "name",
            "value",
            "value_type",
        ]


class ClassificationGroupsModelFilterSet(BaseFilterSet):
    """API filter for filtering ClassificationGroups model objects."""

    q = SearchFilter(
        filter_predicates={
            "name": "icontains",
        },
    )

    class Meta:
        model = ClassificationGroupsModel
        fields = [
            "name",
            "environment",
            "asset_tag",
            "network",
        ]
