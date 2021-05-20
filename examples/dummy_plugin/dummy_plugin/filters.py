import django_filters
from django.db.models import Q

from nautobot.extras.filters import CreatedUpdatedFilterSet, CustomFieldModelFilterSet
from nautobot.utilities.filters import BaseFilterSet

from .models import DummyModel


class DummyModelFilterSet(BaseFilterSet, CreatedUpdatedFilterSet, CustomFieldModelFilterSet):
    """API filter for filtering dummy model objects."""

    q = django_filters.CharFilter(
        method="search",
        label="Search",
    )

    class Meta:
        model = DummyModel
        fields = [
            "name",
            "number",
        ]

    def search(self, queryset, name, value):
        if not value.strip():
            return queryset
        return queryset.filter(
            Q(name__icontains=value) | Q(number__icontains=value)
        ).distinct()
