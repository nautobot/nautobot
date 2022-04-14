from copy import deepcopy

from django import forms
from django.conf import settings
from django.core.validators import MaxValueValidator
from django.db import models
import django_filters
from django_filters.constants import EMPTY_VALUES
from django_filters.utils import get_model_field, resolve_field

from nautobot.dcim.forms import MACAddressField
from nautobot.extras.models import Tag
from nautobot.utilities.constants import (
    FILTER_CHAR_BASED_LOOKUP_MAP,
    FILTER_NEGATION_LOOKUP_MAP,
    FILTER_NUMERIC_BASED_LOOKUP_MAP,
    FILTER_TREENODE_NEGATION_LOOKUP_MAP,
)


def multivalue_field_factory(field_class):
    """
    Given a form field class, return a subclass capable of accepting multiple values. This allows us to OR on multiple
    filter values while maintaining the field's built-in validation. Example: GET /api/dcim/devices/?name=foo&name=bar
    """

    class NewField(field_class):
        widget = forms.SelectMultiple

        def to_python(self, value):
            if not value:
                return []

            # Make it a list if it's a string.
            if isinstance(value, str):
                value = [value]

            return [
                # Only append non-empty values (this avoids e.g. trying to cast '' as an integer)
                super(field_class, self).to_python(v)
                for v in value
                if v
            ]

    return type("MultiValue{}".format(field_class.__name__), (NewField,), dict())


#
# Filters
#
# Note that for the various MultipleChoiceFilter subclasses below, they additionally inherit from `CharFilter`,
# `DateFilter`, `DateTimeFilter`, etc. This has no particular impact on the behavior of these filters (as we're
# explicitly overriding their `field_class` attribute anyway), but is done as a means of type hinting
# for generating a more accurate REST API OpenAPI schema for these filter types.
#


class MultiValueCharFilter(django_filters.CharFilter, django_filters.MultipleChoiceFilter):
    field_class = multivalue_field_factory(forms.CharField)


class MultiValueDateFilter(django_filters.DateFilter, django_filters.MultipleChoiceFilter):
    field_class = multivalue_field_factory(forms.DateField)


class MultiValueDateTimeFilter(django_filters.DateTimeFilter, django_filters.MultipleChoiceFilter):
    field_class = multivalue_field_factory(forms.DateTimeField)


class MultiValueNumberFilter(django_filters.NumberFilter, django_filters.MultipleChoiceFilter):
    field_class = multivalue_field_factory(forms.IntegerField)

    class MultiValueMaxValueValidator(MaxValueValidator):
        """As django.core.validators.MaxValueValidator, but apply to a list of values rather than a single value."""

        def compare(self, values, limit_value):
            return any(int(value) > limit_value for value in values)

    def get_max_validator(self):
        """Like django_filters.NumberFilter, limit the maximum value for any single entry as an anti-DoS measure."""
        return self.MultiValueMaxValueValidator(1e50)


class MultiValueBigNumberFilter(MultiValueNumberFilter):
    """Subclass of MultiValueNumberFilter used for BigInteger model fields."""


class MultiValueTimeFilter(django_filters.TimeFilter, django_filters.MultipleChoiceFilter):
    field_class = multivalue_field_factory(forms.TimeField)


class MACAddressFilter(django_filters.CharFilter):
    field_class = MACAddressField


class MultiValueMACAddressFilter(django_filters.MultipleChoiceFilter):
    field_class = multivalue_field_factory(MACAddressField)


class MultiValueUUIDFilter(django_filters.UUIDFilter, django_filters.MultipleChoiceFilter):
    field_class = multivalue_field_factory(forms.UUIDField)


class RelatedMembershipBooleanFilter(django_filters.BooleanFilter):
    """
    BooleanFilter for related objects that will explicitly perform `exclude=True` and `isnull`
    lookups. The `field_name` argument is required and must be set to the related field on the
    model.

    This should be used instead of a default `BooleanFilter` paired `method=`
    argument to test for the existence of related objects.

    Example:

        has_interfaces = RelatedMembershipBooleanFilter(
            field_name="interfaces",
            label="Has interfaces",
        )
    """

    def __init__(
        self, field_name=None, lookup_expr="isnull", *, label=None, method=None, distinct=False, exclude=True, **kwargs
    ):
        if field_name is None:
            raise ValueError(f"Field name is required for {self.__class__.__name__}")

        super().__init__(
            field_name=field_name,
            lookup_expr=lookup_expr,
            label=label,
            method=method,
            distinct=distinct,
            exclude=exclude,
            **kwargs,
        )


class TreeNodeMultipleChoiceFilter(django_filters.ModelMultipleChoiceFilter):
    """
    Filters for a set of Models, including all descendant models within a Tree.  Example: [<Region: R1>,<Region: R2>]
    """

    def get_filter_predicate(self, v):
        # Null value filtering
        if v is None:
            return {f"{self.field_name}__isnull": True}
        return super().get_filter_predicate(v)

    def filter(self, qs, value):
        value = [node.get_descendants(include_self=True) if not isinstance(node, str) else node for node in value]
        return super().filter(qs, value)


class NullableCharFieldFilter(django_filters.CharFilter):
    """
    Allow matching on null field values by passing a special string used to signify NULL.
    """

    def filter(self, qs, value):
        if value != settings.FILTERS_NULL_CHOICE_VALUE:
            return super().filter(qs, value)
        qs = self.get_method(qs)(**{"{}__isnull".format(self.field_name): True})
        return qs.distinct() if self.distinct else qs


class TagFilter(django_filters.ModelMultipleChoiceFilter):
    """
    Match on one or more assigned tags. If multiple tags are specified (e.g. ?tag=foo&tag=bar), the queryset is filtered
    to objects matching all tags.
    """

    def __init__(self, *args, **kwargs):

        kwargs.setdefault("field_name", "tags__slug")
        kwargs.setdefault("to_field_name", "slug")
        kwargs.setdefault("conjoined", True)
        kwargs.setdefault("queryset", Tag.objects.all())

        super().__init__(*args, **kwargs)


class NumericArrayFilter(django_filters.NumberFilter):
    """
    Filter based on the presence of an integer within an ArrayField.
    """

    def filter(self, qs, value):
        if value:
            value = [value]
        return super().filter(qs, value)


class ContentTypeFilterMixin:
    """
    Mixin to allow specifying a ContentType by <app_label>.<model> (e.g. "dcim.site").
    """

    def filter(self, qs, value):
        if value in EMPTY_VALUES:
            return qs

        try:
            app_label, model = value.lower().split(".")
        except ValueError:
            return qs.none()

        return qs.filter(
            **{
                f"{self.field_name}__app_label": app_label,
                f"{self.field_name}__model": model,
            }
        )


class ContentTypeFilter(ContentTypeFilterMixin, django_filters.CharFilter):
    """
    Allows character-based ContentType filtering by <app_label>.<model> (e.g. "dcim.site").

    Does not support limiting of choices. Can be used without arguments on a `FilterSet`:

        content_type = ContentTypeFilter()
    """


class ContentTypeChoiceFilter(ContentTypeFilterMixin, django_filters.ChoiceFilter):
    """
    Allows character-based ContentType filtering by <app_label>.<model> (e.g.
    "dcim.site") but an explicit set of choices must be provided.

    Example use on a `FilterSet`:

        content_type = ContentTypeChoiceFilter(
            choices=FeatureQuery("dynamic_groups").get_choices,
        )
    """


class ContentTypeMultipleChoiceFilter(django_filters.MultipleChoiceFilter):
    """
    Allows multiple-choice ContentType filtering by <app_label>.<model> (e.g. "dcim.site").

    Defaults to joining multiple options with "AND". Pass `conjoined=False` to
    override this behavior to join with "OR" instead.

    Example use on a `FilterSet`:

        content_types = ContentTypeMultipleChoiceFilter(
            choices=FeatureQuery("statuses").get_choices,
        )
    """

    def __init__(self, *args, **kwargs):
        kwargs.setdefault("conjoined", True)
        super().__init__(*args, **kwargs)

    def filter(self, qs, value):
        """Filter on value, which should be list of content-type names.

        e.g. `['dcim.device', 'dcim.rack']`
        """
        if not self.conjoined:
            q = models.Q()

        for v in value:
            if self.conjoined:
                qs = ContentTypeFilter.filter(self, qs, v)
            else:
                # Similar to the ContentTypeFilter.filter() call above, but instead of narrowing the query each time
                # (a AND b AND c ...) we broaden the query each time (a OR b OR c ...).
                # Specifically, we're mapping a value like ['dcim.device', 'ipam.vlan'] to a query like
                # Q((field__app_label="dcim" AND field__model="device") OR (field__app_label="ipam" AND field__model="VLAN"))
                try:
                    app_label, model = v.lower().split(".")
                except ValueError:
                    continue
                q |= models.Q(
                    **{
                        f"{self.field_name}__app_label": app_label,
                        f"{self.field_name}__model": model,
                    }
                )

        if not self.conjoined:
            qs = qs.filter(q)

        return qs


#
# FilterSets
#


class BaseFilterSet(django_filters.FilterSet):
    """
    A base filterset which provides common functionaly to all Nautobot filtersets
    """

    FILTER_DEFAULTS = deepcopy(django_filters.filterset.FILTER_FOR_DBFIELD_DEFAULTS)
    FILTER_DEFAULTS.update(
        {
            models.AutoField: {"filter_class": MultiValueNumberFilter},
            models.BigIntegerField: {"filter_class": MultiValueBigNumberFilter},
            models.CharField: {"filter_class": MultiValueCharFilter},
            models.DateField: {"filter_class": MultiValueDateFilter},
            models.DateTimeField: {"filter_class": MultiValueDateTimeFilter},
            models.DecimalField: {"filter_class": MultiValueNumberFilter},
            models.EmailField: {"filter_class": MultiValueCharFilter},
            models.FloatField: {"filter_class": MultiValueNumberFilter},
            models.IntegerField: {"filter_class": MultiValueNumberFilter},
            # Ref: https://github.com/carltongibson/django-filter/issues/1107
            models.JSONField: {"filter_class": MultiValueCharFilter, "extra": lambda f: {"lookup_expr": ["icontains"]}},
            models.PositiveIntegerField: {"filter_class": MultiValueNumberFilter},
            models.PositiveSmallIntegerField: {"filter_class": MultiValueNumberFilter},
            models.SlugField: {"filter_class": MultiValueCharFilter},
            models.SmallIntegerField: {"filter_class": MultiValueNumberFilter},
            models.TextField: {"filter_class": MultiValueCharFilter},
            models.TimeField: {"filter_class": MultiValueTimeFilter},
            models.URLField: {"filter_class": MultiValueCharFilter},
            models.UUIDField: {"filter_class": MultiValueUUIDFilter},
            MACAddressField: {"filter_class": MultiValueMACAddressFilter},
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
                MultiValueNumberFilter,
                MultiValueTimeFilter,
            ),
        ):
            lookup_map = FILTER_NUMERIC_BASED_LOOKUP_MAP

        elif isinstance(existing_filter, (TreeNodeMultipleChoiceFilter,)):
            # TreeNodeMultipleChoiceFilter only support negation but must maintain the `in` lookup expression
            lookup_map = FILTER_TREENODE_NEGATION_LOOKUP_MAP

        # These filter types support only negation
        elif isinstance(
            existing_filter,
            (
                django_filters.ModelChoiceFilter,
                django_filters.ModelMultipleChoiceFilter,
                TagFilter,
            ),
        ):
            lookup_map = FILTER_NEGATION_LOOKUP_MAP
        # These filter types support only negation
        elif existing_filter.extra.get("choices"):
            lookup_map = FILTER_NEGATION_LOOKUP_MAP
        elif isinstance(
            existing_filter,
            (
                django_filters.filters.CharFilter,
                django_filters.MultipleChoiceFilter,
                MultiValueCharFilter,
                MultiValueMACAddressFilter,
            ),
        ):
            lookup_map = FILTER_CHAR_BASED_LOOKUP_MAP

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

        # Create new filters for each lookup expression in the map
        for lookup_name, lookup_expr in lookup_map.items():
            new_filter_name = "{}__{}".format(filter_name, lookup_name)

            try:
                if filter_name in cls.declared_filters:
                    # The filter field has been explicity defined on the filterset class so we must manually
                    # create the new filter with the same type because there is no guarantee the defined type
                    # is the same as the default type for the field
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
                    # The filter field is listed in Meta.fields so we can safely rely on default behaviour
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
                "There was a conflict with filter `%s`, the custom filter was ignored." % new_filter_name
            )

        cls.base_filters[new_filter_name] = new_filter_field
        cls.base_filters.update(
            cls._generate_lookup_expression_filters(filter_name=new_filter_name, filter_field=new_filter_field)
        )

    @classmethod
    def get_filters(cls):
        """
        Override filter generation to support dynamic lookup expressions for certain filter types.
        """
        filters = super().get_filters()

        new_filters = {}
        for existing_filter_name, existing_filter in filters.items():
            new_filters.update(
                cls._generate_lookup_expression_filters(filter_name=existing_filter_name, filter_field=existing_filter)
            )

        filters.update(new_filters)
        return filters


class NameSlugSearchFilterSet(django_filters.FilterSet):
    """
    A base class for adding the search method to models which only expose the `name` and `slug` fields
    """

    q = django_filters.CharFilter(
        method="search",
        label="Search",
    )

    def search(self, queryset, name, value):
        if not value.strip():
            return queryset
        return queryset.filter(models.Q(name__icontains=value) | models.Q(slug__icontains=value))
