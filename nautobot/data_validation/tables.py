"""Tables for data_validation."""

from django.utils.html import format_html
import django_tables2 as tables

from nautobot.core.tables import BaseTable, BooleanColumn, TagColumn, ToggleColumn
from nautobot.data_validation.models import (
    DataCompliance,
    MinMaxValidationRule,
    RegularExpressionValidationRule,
    RequiredValidationRule,
    UniqueValidationRule,
)

#
# RegularExpressionValidationRules
#


class RegularExpressionValidationRuleTable(BaseTable):
    """Base table for the RegularExpressionValidationRule model."""

    pk = ToggleColumn()
    name = tables.Column(linkify=True, order_by=("name",))
    enabled = BooleanColumn()
    context_processing = BooleanColumn()
    tags = TagColumn()

    class Meta(BaseTable.Meta):
        """Table metadata for the RegularExpressionValidationRule model."""

        model = RegularExpressionValidationRule
        fields = (
            "pk",
            "name",
            "enabled",
            "content_type",
            "field",
            "regular_expression",
            "context_processing",
            "error_message",
            "tags",
        )
        default_columns = (
            "pk",
            "name",
            "enabled",
            "content_type",
            "field",
            "regular_expression",
            "context_processing",
            "error_message",
        )


#
# MinMaxValidationRules
#


class MinMaxValidationRuleTable(BaseTable):
    """Base table for the MinMaxValidationRule model."""

    pk = ToggleColumn()
    name = tables.Column(linkify=True, order_by=("name",))
    enabled = BooleanColumn()
    tags = TagColumn()

    class Meta(BaseTable.Meta):
        """Table metadata for the MinMaxValidationRuleTable model."""

        model = MinMaxValidationRule
        fields = (
            "pk",
            "name",
            "enabled",
            "content_type",
            "field",
            "min",
            "max",
            "error_message",
            "tags",
        )
        default_columns = (
            "pk",
            "name",
            "enabled",
            "content_type",
            "field",
            "min",
            "max",
            "error_message",
        )


#
# RequiredValidationRules
#


class RequiredValidationRuleTable(BaseTable):
    """Base table for the RequiredValidationRule model."""

    pk = ToggleColumn()
    name = tables.Column(linkify=True, order_by=("name",))
    enabled = BooleanColumn()
    tags = TagColumn()

    class Meta(BaseTable.Meta):
        """Table metadata for the RequiredValidationRuleTable model."""

        model = RequiredValidationRule
        fields = (
            "pk",
            "name",
            "enabled",
            "content_type",
            "field",
            "error_message",
            "tags",
        )
        default_columns = (
            "pk",
            "name",
            "enabled",
            "content_type",
            "field",
            "error_message",
        )


#
# UniqueValidationRules
#


class UniqueValidationRuleTable(BaseTable):
    """Base table for the UniqueValidationRule model."""

    pk = ToggleColumn()
    name = tables.Column(linkify=True, order_by=("name",))
    enabled = BooleanColumn()
    tags = TagColumn()

    class Meta(BaseTable.Meta):
        """Table metadata for the UniqueValidationRuleTable model."""

        model = UniqueValidationRule
        fields = (
            "pk",
            "name",
            "enabled",
            "content_type",
            "field",
            "max_instances",
            "error_message",
            "tags",
        )
        default_columns = (
            "pk",
            "name",
            "enabled",
            "content_type",
            "field",
            "max_instances",
            "error_message",
        )


#
# DataCompliance
#


class ValidatedAttributeColumn(tables.Column):
    """Column that links to the object's attribute if it is linkable."""

    def render(self, value, record):  # pylint: disable=W0221
        """Generate a link to a validated attribute if it is linkable, otherwise return the attribute."""
        if hasattr(record.validated_object, value) and hasattr(
            getattr(record.validated_object, value), "get_absolute_url"
        ):
            return format_html('<a href="{}">{}</a>', getattr(record.validated_object, value).get_absolute_url(), value)
        return value


class DataComplianceTable(BaseTable):
    """Base table for viewing all DataCompliance objects."""

    pk = ToggleColumn()
    id = tables.Column(linkify=True, verbose_name="ID")
    validated_object = tables.RelatedLinkColumn()
    validated_attribute = ValidatedAttributeColumn()
    valid = BooleanColumn()

    def order_validated_object(self, queryset, is_descending):
        """Reorder table by string representation of validated_object."""
        qs = queryset.order_by(("-" if is_descending else "") + "validated_object_str")
        return (qs, True)

    class Meta(BaseTable.Meta):
        """Meta class for DataComplianceTable."""

        model = DataCompliance
        fields = [
            "pk",
            "id",
            "content_type",
            "compliance_class_name",
            "last_validation_date",
            "validated_object",
            "validated_attribute",
            "validated_attribute_value",
            "valid",
            "message",
        ]
        default_columns = [
            "pk",
            "id",
            "content_type",
            "compliance_class_name",
            "last_validation_date",
            "validated_object",
            "validated_attribute",
            "validated_attribute_value",
            "valid",
            "message",
        ]


class DataComplianceTableTab(BaseTable):
    """Base table for viewing the DataCompliance related to a single object."""

    validated_attribute = ValidatedAttributeColumn()
    valid = BooleanColumn()

    class Meta(BaseTable.Meta):
        """Meta class for DataComplianceTableTab."""

        model = DataCompliance
        order_by = ("compliance_class_name", "validated_attribute")
        fields = [
            "content_type",
            "compliance_class_name",
            "last_validation_date",
            "validated_attribute",
            "validated_attribute_value",
            "valid",
            "message",
        ]
        default_columns = [
            "content_type",
            "compliance_class_name",
            "last_validation_date",
            "validated_attribute",
            "validated_attribute_value",
            "valid",
            "message",
        ]
