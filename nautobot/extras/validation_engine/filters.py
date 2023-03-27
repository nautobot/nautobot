import django_filters as filters
from nautobot.extras.validation_engine.models import ValidationResult

class ValidationResultFilterSet(filters.FilterSet):
    class_name = filters.CharFilter(field_name="class_name", lookup_expr="icontains")
    function_name = filters.CharFilter(field_name="function_name", lookup_expr="icontains")

    class Meta:
        model = ValidationResult
        fields = ["class_name", "function_name"]