import django_filters

from nautobot.apps.filters import BaseFilterSet, SearchFilter

from example_app.models import AnotherExampleModel, ExampleModel, ProxyExampleModel


class ExampleModelFilterSet(BaseFilterSet):
    """API filter for filtering example model objects."""

    q = SearchFilter(
        filter_predicates={
            "name": "icontains",
            "number": "icontains",
        },
    )
    # Filters whose names collide with reserved `graphene.Field.__init__` keyword arguments.
    # These exercise the relocation logic in `get_filtering_args_from_filterset()` so the
    # GraphQL schema can be built without crashing (NTC-5456 / #9021).
    default_value = django_filters.NumberFilter(field_name="number")
    required = django_filters.NumberFilter(field_name="number")
    resolver = django_filters.NumberFilter(field_name="number")

    class Meta:
        model = ExampleModel
        fields = [
            "name",
            "number",
        ]


class ProxyExampleModelFilterSet(BaseFilterSet):
    """API filter for filtering proxy example model objects."""

    q = SearchFilter(
        filter_predicates={
            "name": "icontains",
            "number": "icontains",
        },
    )

    class Meta:
        model = ProxyExampleModel
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
