from nautobot.utilities.filters import BaseFilterSet, SearchFilter

from example_plugin.models import AnotherExampleModel, ExampleModel


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
