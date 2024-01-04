from collections import OrderedDict
from copy import deepcopy
import logging

from django.conf import settings
from django.db import models
from django.forms.utils import ErrorDict, ErrorList
import django_filters
from django_filters.utils import get_model_field, resolve_field

from nautobot.core import constants
from nautobot.core.models import fields as core_fields

from .filters import (
    MultiValueBigNumberFilter,
    MultiValueCharFilter,
    MultiValueDateFilter,
    MultiValueDateTimeFilter,
    MultiValueDecimalFilter,
    MultiValueFloatFilter,
    MultiValueMACAddressFilter,
    MultiValueNumberFilter,
    MultiValueTimeFilter,
    MultiValueUUIDFilter,
    SearchFilter,
    TagFilter,
    TreeNodeMultipleChoiceFilter,
)

logger = logging.getLogger(__name__)


class BaseFilterSet(django_filters.FilterSet):
    """
    A base filterset which provides common functionality to all Nautobot filtersets.
    """

    FILTER_DEFAULTS = deepcopy(django_filters.filterset.FILTER_FOR_DBFIELD_DEFAULTS)
    FILTER_DEFAULTS.update(
        {
            models.AutoField: {"filter_class": MultiValueNumberFilter},
            models.BigIntegerField: {"filter_class": MultiValueBigNumberFilter},
            models.CharField: {"filter_class": MultiValueCharFilter},
            models.DateField: {"filter_class": MultiValueDateFilter},
            models.DateTimeField: {"filter_class": MultiValueDateTimeFilter},
            models.DecimalField: {"filter_class": MultiValueDecimalFilter},
            models.EmailField: {"filter_class": MultiValueCharFilter},
            models.FloatField: {"filter_class": MultiValueFloatFilter},
            models.IntegerField: {"filter_class": MultiValueNumberFilter},
            # Ref: https://github.com/carltongibson/django-filter/issues/1107
            models.JSONField: {"filter_class": MultiValueCharFilter, "extra": lambda f: {"lookup_expr": "icontains"}},
            models.PositiveIntegerField: {"filter_class": MultiValueNumberFilter},
            models.PositiveSmallIntegerField: {"filter_class": MultiValueNumberFilter},
            models.SlugField: {"filter_class": MultiValueCharFilter},
            models.SmallIntegerField: {"filter_class": MultiValueNumberFilter},
            models.TextField: {"filter_class": MultiValueCharFilter},
            models.TimeField: {"filter_class": MultiValueTimeFilter},
            models.URLField: {"filter_class": MultiValueCharFilter},
            models.UUIDField: {"filter_class": MultiValueUUIDFilter},
            core_fields.MACAddressCharField: {"filter_class": MultiValueMACAddressFilter},
            core_fields.TagsField: {"filter_class": TagFilter},
        }
    )

    @staticmethod
    def _get_filter_lookup_dict(existing_filter):
        # Choose the lookup expression map based on the filter type
        if isinstance(
            existing_filter,
            (
                MultiValueDateFilter,
                MultiValueDateTimeFilter,
                MultiValueDecimalFilter,
                MultiValueFloatFilter,
                MultiValueNumberFilter,
                MultiValueTimeFilter,
            ),
        ):
            lookup_map = constants.FILTER_NUMERIC_BASED_LOOKUP_MAP

        # These filter types support only negation
        elif isinstance(
            existing_filter,
            (
                django_filters.ModelChoiceFilter,
                django_filters.ModelMultipleChoiceFilter,
                TagFilter,
                TreeNodeMultipleChoiceFilter,
            ),
        ):
            lookup_map = constants.FILTER_NEGATION_LOOKUP_MAP

        elif isinstance(
            existing_filter,
            (
                django_filters.filters.CharFilter,
                django_filters.MultipleChoiceFilter,
                MultiValueCharFilter,
                MultiValueMACAddressFilter,
            ),
        ):
            lookup_map = constants.FILTER_CHAR_BASED_LOOKUP_MAP

        else:
            lookup_map = None

        return lookup_map

    @classmethod
    def _generate_lookup_expression_filters(cls, filter_name, filter_field):
        """
        For specific filter types, new filters are created based on defined lookup expressions in
        the form `<field_name>__<lookup_expr>`
        """
        magic_filters = {}
        if filter_field.method is not None or filter_field.lookup_expr not in ["exact", "in"]:
            return magic_filters

        # Choose the lookup expression map based on the filter type
        lookup_map = cls._get_filter_lookup_dict(filter_field)
        if lookup_map is None:
            # Do not augment this filter type with more lookup expressions
            return magic_filters

        # Get properties of the existing filter for later use
        field_name = filter_field.field_name
        field = get_model_field(cls._meta.model, field_name)

        # If there isn't a model field, return.
        if field is None:
            return magic_filters

        # If the field allows null values, add an `isnull`` check
        if getattr(field, "null", None):
            # Use this method vs extend as the `lookup_map` variable is generally one of
            # the constants which we do not want to update
            lookup_map = dict(lookup_map, **{"isnull": "isnull"})

        # Create new filters for each lookup expression in the map
        for lookup_name, lookup_expr in lookup_map.items():
            new_filter_name = f"{filter_name}__{lookup_name}"

            try:
                if filter_name in cls.declared_filters and lookup_expr not in {"isnull"}:
                    # The filter field has been explicitly defined on the filterset class so we must manually
                    # create the new filter with the same type because there is no guarantee the defined type
                    # is the same as the default type for the field. This does not apply if the filter
                    # should retain the original lookup_expr type, such as `isnull` using a boolean field on a
                    # char or date object.
                    resolve_field(field, lookup_expr)  # Will raise FieldLookupError if the lookup is invalid
                    new_filter = type(filter_field)(
                        field_name=field_name,
                        lookup_expr=lookup_expr,
                        label=filter_field.label,
                        exclude=filter_field.exclude,
                        distinct=filter_field.distinct,
                        **filter_field.extra,
                    )
                else:
                    # The filter field is listed in Meta.fields so we can safely rely on default behavior
                    # Will raise FieldLookupError if the lookup is invalid
                    new_filter = cls.filter_for_field(field, field_name, lookup_expr)
            except django_filters.exceptions.FieldLookupError:
                # The filter could not be created because the lookup expression is not supported on the field
                continue

            if lookup_name.startswith("n"):
                # This is a negation filter which requires a queryset.exclude() clause
                # Of course setting the negation of the existing filter's exclude attribute handles both cases
                new_filter.exclude = not filter_field.exclude

            magic_filters[new_filter_name] = new_filter

        return magic_filters

    @classmethod
    def add_filter(cls, new_filter_name, new_filter_field):
        """
        Allow filters to be added post-generation on import.

        Will provide `<field_name>__<lookup_expr>` generation automagically.
        """
        if not isinstance(new_filter_field, django_filters.Filter):
            raise TypeError(f"Tried to add filter ({new_filter_name}) which is not an instance of Django Filter")

        if new_filter_name in cls.base_filters:
            raise AttributeError(
                f"There was a conflict with filter `{new_filter_name}`, the custom filter was ignored."
            )

        cls.base_filters[new_filter_name] = new_filter_field
        # django-filters has no concept of "abstract" filtersets, so we have to fake it
        if cls._meta.model is not None:
            cls.base_filters.update(
                cls._generate_lookup_expression_filters(filter_name=new_filter_name, filter_field=new_filter_field)
            )

    @classmethod
    def get_fields(cls):
        fields = super().get_fields()
        if "id" not in fields and (cls._meta.exclude is None or "id" not in cls._meta.exclude):
            # Add "id" as the first key in the `fields` OrderedDict
            fields = OrderedDict(id=[django_filters.conf.settings.DEFAULT_LOOKUP_EXPR], **fields)
        return fields

    @classmethod
    def get_filters(cls):
        """
        Override filter generation to support dynamic lookup expressions for certain filter types.
        """
        filters = super().get_filters()

        # django-filters has no concept of "abstract" filtersets, so we have to fake it
        if cls._meta.model is not None:
            new_filters = {}
            for existing_filter_name, existing_filter in filters.items():
                new_filters.update(
                    cls._generate_lookup_expression_filters(
                        filter_name=existing_filter_name,
                        filter_field=existing_filter,
                    )
                )

            filters.update(new_filters)

        return filters

    @classmethod
    def filter_for_lookup(cls, field, lookup_type):
        """Override filter_for_lookup method to set ChoiceField Filter to MultipleChoiceFilter.

        Note: Any CharField or IntegerField with choices set is a ChoiceField.
        """
        if lookup_type == "exact" and getattr(field, "choices", None):
            return django_filters.MultipleChoiceFilter, {"choices": field.choices}
        return super().filter_for_lookup(field, lookup_type)

    def __init__(self, data=None, queryset=None, *, request=None, prefix=None):
        super().__init__(data, queryset, request=request, prefix=prefix)
        self._is_valid = None
        self._errors = None

    def is_valid(self):
        """Extend FilterSet.is_valid() to potentially enforce settings.STRICT_FILTERING."""
        if self._is_valid is None:
            self._is_valid = super().is_valid()
            if settings.STRICT_FILTERING:
                self._is_valid = self._is_valid and set(self.form.data.keys()).issubset(self.form.cleaned_data.keys())
            else:
                # Trigger warning logs associated with generating self.errors
                self.errors
        return self._is_valid

    @property
    def errors(self):
        """Extend FilterSet.errors to potentially include additional errors from settings.STRICT_FILTERING."""
        if self._errors is None:
            self._errors = ErrorDict(self.form.errors)
            for extra_key in set(self.form.data.keys()).difference(self.form.cleaned_data.keys()):
                # If a given field was invalid, it will be omitted from cleaned_data; don't report extra errors
                if extra_key not in self._errors:
                    if settings.STRICT_FILTERING:
                        self._errors.setdefault(extra_key, ErrorList()).append("Unknown filter field")
                    else:
                        logger.warning('%s: Unknown filter field "%s"', self.__class__.__name__, extra_key)

        return self._errors


class NameSearchFilterSet(django_filters.FilterSet):
    """
    A base class for adding the search method to models which only expose the `name` field in searches.
    """

    q = SearchFilter(filter_predicates={"name": "icontains"})
