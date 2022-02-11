import django_filters
from django.db.models import Q

from nautobot.utilities.filters import BaseFilterSet

from example_plugin.models import ExampleModel


class ExampleModelFilterSet(BaseFilterSet):
    """API filter for filtering example model objects."""

    q = django_filters.CharFilter(
        method="search",
        label="Search",
    )

    class Meta:
        model = ExampleModel
        fields = [
            "name",
            "number",
        ]

    def search(self, queryset, name, value):
        if not value.strip():
            return queryset
        return queryset.filter(Q(name__icontains=value) | Q(number__icontains=value)).distinct()
