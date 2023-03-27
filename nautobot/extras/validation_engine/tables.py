import django_tables2 as tables
from django.utils.safestring import mark_safe
from nautobot.core.tables import BaseTable
from nautobot.extras.validation_engine.models import ValidationResult

class ValidatedAttributeColumn(tables.Column):
    def render(self, value, record):
        if hasattr(record.validated_object, value) and hasattr(getattr(record.validated_object, value), "get_absolute_url"):
            return mark_safe(f'<a href="{getattr(record.validated_object, value).get_absolute_url()}">{value}</a>')
        else:
            return value

class AllValidationsResultTable(BaseTable):
    validated_object = tables.RelatedLinkColumn()
    validated_object_attribute = ValidatedAttributeColumn()

    class Meta(BaseTable.Meta):
        model = ValidationResult
        fields = [
            "class_name",
            "function_name",
            "last_validation_date",
            "validated_object",
            "validated_object_attribute",
            "valid",
            "message"
        ]

class ObjectValidationResultTable(BaseTable):
    validated_object_attribute = ValidatedAttributeColumn()

    class Meta(BaseTable.Meta):
        model = ValidationResult
        fields = [
            "class_name",
            "function_name",
            "last_validation_date",
            "validated_object_attribute",
            "valid",
            "message"
        ]