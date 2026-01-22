from functools import reduce
import operator

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

    def generate_query(self, value):
        # This method may be called from extras.models.DynamicGroup._generate_query_for_filter method
        # to generate proper query for given field. But at this point, we don't know if the field will be negated or not
        # That's why we're preparing query that works both: for positional filtering and negated one.
        # For positional filtering, when we're expecting some value, the field must exists (key in custom field data JSONB)
        # and value can't be None (null in db)
        # For negated filtering we're expecting field without some value, but key may be missing or value can be None (null in db)
        # Please refer to the filter method below, for more context.
        if value == "null" or value == ["null"]:
            return Q(**{f"{self.field_name}__exact": None}) & Q(**{f"{self.field_name}__isnull": False})

        if isinstance(value, (list, tuple)):
            value_match = reduce(operator.or_, [Q(**{f"{self.field_name}__{self.lookup_expr}": v}) for v in value])
        else:
            value_match = Q(**{f"{self.field_name}__{self.lookup_expr}": value})
        value_is_not_none = ~Q(**{f"{self.field_name}__exact": None})
        key_is_present_in_jsonb = Q(
            **{f"{self.field_name}__isnull": False}
        )  # __isnull and __has_key has same output in case of JSONB fields

        return value_match & value_is_not_none & key_is_present_in_jsonb

    def filter(self, qs, value):
        if value in django_filters.constants.EMPTY_VALUES:
            return qs

        if value == "null" or value == ["null"]:
            return self.get_method(qs)(
                Q(**{f"{self.field_name}__exact": None}) & Q(**{f"{self.field_name}__isnull": False})
            )

        # Custom fields require special handling for exclude filtering.
        # Return custom fields that don't match the value, key is missing or value is set to null
        # For JSONB fields, like `_custom_field_data`:
        # __isnull and __has_key returns those records which has key
        # __isnull is not checking the actual value in JSONB!
        # to check for null value, we need to use exact
        # With exclude filtering we need to take into account all cases:
        # - no key - handled by __isnull check
        # - key is present with null - handled by __exact=None
        # - key is present with some value - handled by filter
        # - key is present with empty str - handled by filter
        if self.exclude:
            qs_null_custom_fields = qs.filter(
                Q(**{f"{self.field_name}__isnull": True}) | Q(**{f"{self.field_name}__exact": None})
            ).distinct()
            return super().filter(qs, value).distinct() | qs_null_custom_fields

        return super().filter(qs, value)


class CustomFieldBooleanFilter(CustomFieldFilterMixin, django_filters.BooleanFilter):
    """Custom field single value filter for backwards compatibility"""


class CustomFieldCharFilter(CustomFieldFilterMixin, django_filters.CharFilter):
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


class CustomFieldNumberFilter(CustomFieldFilterMixin, django_filters.NumberFilter):
    """Custom field single value filter for backwards compatibility"""

    field_class = IntegerField


class CustomFieldMultiValueCharFilter(CustomFieldFilterMixin, MultiValueCharFilter):
    """Custom field multi value char filter for extended lookup expressions"""


class CustomFieldMultiValueDateFilter(CustomFieldFilterMixin, MultiValueDateFilter):
    """Custom field multi value date filter for extended lookup expressions"""


class CustomFieldMultiValueNumberFilter(CustomFieldFilterMixin, MultiValueNumberFilter):
    """Custom field multi value number filter for extended lookup expressions"""
