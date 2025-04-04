from django.db.models import Q
from django.forms import IntegerField
import django_filters

from nautobot.core.filters import (
    MultiValueCharFilter,
    MultiValueDateFilter,
    MultiValueNumberFilter,
)
from nautobot.core.forms import NullableDateField
from nautobot.core.utils.data import is_uuid
from nautobot.extras.choices import CustomFieldFilterLogicChoices, CustomFieldTypeChoices
from nautobot.extras.models import CustomFieldChoice

EXACT_FILTER_TYPES = (
    CustomFieldTypeChoices.TYPE_BOOLEAN,
    CustomFieldTypeChoices.TYPE_DATE,
    CustomFieldTypeChoices.TYPE_INTEGER,
    CustomFieldTypeChoices.TYPE_SELECT,
    CustomFieldTypeChoices.TYPE_MULTISELECT,
)


class CustomFieldFilterMixin:
    """
    Filter mixin for CustomField to handle CustomField.filter_logic setting
    and queryset.exclude filtering specific to the JSONField where CustomField data is stored.
    """

    def __init__(self, custom_field, *args, **kwargs):
        self.custom_field = custom_field
        if custom_field.type not in EXACT_FILTER_TYPES:
            if custom_field.filter_logic == CustomFieldFilterLogicChoices.FILTER_LOOSE:
                kwargs.setdefault("lookup_expr", "icontains")
        kwargs["widget"] = custom_field.to_form_field(set_initial=False, enforce_required=False).widget
        super().__init__(*args, **kwargs)
        self.field_name = f"_custom_field_data__{self.field_name}"

    def filter(self, qs, value):
        if value in django_filters.constants.EMPTY_VALUES:
            return qs

        if value == "null":
            return self.get_method(qs)(
                Q(**{f"{self.field_name}__exact": None}) | Q(**{f"{self.field_name}__isnull": True})
            )

        # Custom fields require special handling for exclude filtering.
        # Return custom fields that don't match the value and null custom fields
        if self.exclude:
            qs_null_custom_fields = qs.filter(**{f"{self.field_name}__isnull": True}).distinct()
            return super().filter(qs, value).distinct() | qs_null_custom_fields

        return super().filter(qs, value)


class CustomFieldBooleanFilter(CustomFieldFilterMixin, django_filters.BooleanFilter):
    """Custom field single value filter for backwards compatibility"""


class CustomFieldCharFilter(CustomFieldFilterMixin, django_filters.Filter):
    """Custom field single value filter for backwards compatibility"""


class CustomFieldDateFilter(CustomFieldFilterMixin, django_filters.DateFilter):
    """Custom field single value filter for backwards compatibility"""

    field_class = NullableDateField


class CustomFieldJSONFilter(CustomFieldFilterMixin, django_filters.Filter):
    """Custom field single value filter for backwards compatibility"""


class CustomFieldSelectFilter(CustomFieldFilterMixin, MultiValueCharFilter):
    """Filter for custom fields of type TYPE_SELECT."""

    def get_filter_predicate(self, v):
        if is_uuid(v):
            try:
                v = self.custom_field.custom_field_choices.get(pk=v).value
            except CustomFieldChoice.DoesNotExist:
                v = ""
        return super().get_filter_predicate(v)


class CustomFieldMultiSelectFilter(CustomFieldSelectFilter):
    """Filter for custom fields of type TYPE_MULTISELECT."""

    def __init__(self, *args, **kwargs):
        kwargs.setdefault("lookup_expr", "contains")
        super().__init__(*args, **kwargs)


class CustomFieldNumberFilter(CustomFieldFilterMixin, django_filters.Filter):
    """Custom field single value filter for backwards compatibility"""

    field_class = IntegerField


class CustomFieldMultiValueCharFilter(CustomFieldFilterMixin, MultiValueCharFilter):
    """Custom field multi value char filter for extended lookup expressions"""


class CustomFieldMultiValueDateFilter(CustomFieldFilterMixin, MultiValueDateFilter):
    """Custom field multi value date filter for extended lookup expressions"""


class CustomFieldMultiValueNumberFilter(CustomFieldFilterMixin, MultiValueNumberFilter):
    """Custom field multi value number filter for extended lookup expressions"""
