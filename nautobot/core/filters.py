from copy import deepcopy
import logging
import uuid

from django import forms as django_forms
from django.conf import settings
from django.db import models
from django.forms.utils import ErrorDict, ErrorList
from django.utils.encoding import force_str
from django.utils.text import capfirst
import django_filters
from django_filters.constants import EMPTY_VALUES
from django_filters.utils import get_model_field, label_for_filter, resolve_field, verbose_lookup_expr
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema_field
import timezone_field

from nautobot.core import constants, forms
from nautobot.core.forms import widgets
from nautobot.core.models import fields as core_fields
from nautobot.core.utils import data as data_utils

logger = logging.getLogger(__name__)


def multivalue_field_factory(field_class, widget=django_forms.SelectMultiple):
    """
    Given a form field class, return a subclass capable of accepting multiple values. This allows us to OR on multiple
    filter values while maintaining the field's built-in validation. Example: GET /api/dcim/devices/?name=foo&name=bar
    """

    def to_python(self, value):
        if not value:
            return []

        # Make it a list if it's a string.
        if isinstance(value, (str, int)):
            value = [value]

        return [
            # Only append non-empty values (this avoids e.g. trying to cast '' as an integer)
            field_class.to_python(self, v)
            for v in value
            if v
        ]

    def validate(self, value):
        for v in value:
            field_class.validate(self, v)

    def run_validators(self, value):
        for v in value:
            field_class.run_validators(self, v)

    return type(
        f"MultiValue{field_class.__name__}",
        (field_class,),
        {
            "run_validators": run_validators,
            "to_python": to_python,
            "validate": validate,
            "widget": widget,
        },
    )


#
# Filters
#
# Note that for the various MultipleChoiceFilter subclasses below, they additionally inherit from `CharFilter`,
# `DateFilter`, `DateTimeFilter`, etc. This has no particular impact on the behavior of these filters (as we're
# explicitly overriding their `field_class` attribute anyway), but is done as a means of type hinting
# for generating a more accurate REST API OpenAPI schema for these filter types.
#


class MultiValueCharFilter(django_filters.CharFilter, django_filters.MultipleChoiceFilter):
    field_class = forms.MultiValueCharField


class MultiValueDateFilter(django_filters.DateFilter, django_filters.MultipleChoiceFilter):
    # TODO we don't currently have a MultiValueDatePicker widget
    field_class = multivalue_field_factory(django_forms.DateField, widget=forms.DatePicker)


class MultiValueDateTimeFilter(django_filters.DateTimeFilter, django_filters.MultipleChoiceFilter):
    # TODO we don't currently have a MultiValueDateTimePicker widget
    field_class = multivalue_field_factory(django_forms.DateTimeField, widget=forms.DateTimePicker)


class MultiValueNumberFilter(django_filters.NumberFilter, django_filters.MultipleChoiceFilter):
    field_class = multivalue_field_factory(django_forms.IntegerField)


class MultiValueBigNumberFilter(MultiValueNumberFilter):
    """Subclass of MultiValueNumberFilter used for BigInteger model fields."""


class MultiValueFloatFilter(django_filters.NumberFilter, django_filters.MultipleChoiceFilter):
    field_class = multivalue_field_factory(django_forms.FloatField)


class MultiValueDecimalFilter(django_filters.NumberFilter, django_filters.MultipleChoiceFilter):
    field_class = multivalue_field_factory(django_forms.DecimalField)


class MultiValueTimeFilter(django_filters.TimeFilter, django_filters.MultipleChoiceFilter):
    # TODO we don't currently have a MultiValueTimePicker widget
    field_class = multivalue_field_factory(django_forms.TimeField, widget=forms.TimePicker)


class MACAddressFilter(django_filters.CharFilter):
    field_class = forms.MACAddressField


class MultiValueMACAddressFilter(django_filters.MultipleChoiceFilter):
    # Don't use multivalue_field_factory(forms.MACAddressField) because that will reject partial substrings like
    # "aa:" or ":01:02", which would prevent us from using filters like `mac_address__isw` to their potential.
    field_class = forms.MultiValueCharField


class MultiValueUUIDFilter(django_filters.UUIDFilter, django_filters.MultipleChoiceFilter):
    field_class = multivalue_field_factory(django_forms.UUIDField, widget=widgets.MultiValueCharInput)


class RelatedMembershipBooleanFilter(django_filters.BooleanFilter):
    """
    BooleanFilter for related objects that will explicitly perform `isnull` lookups.
    The `field_name` argument is required and must be set to the related field on the
    model.

    This should be used instead of a default `BooleanFilter` paired `method=`
    argument to test for the existence of related objects.

    Example:

        has_modules = RelatedMembershipBooleanFilter(
            field_name="module_bays__installed_module",
            label="Has modules",
        )

        This would generate a filter that returns instances that have at least one module
        bay with an installed module. The `has_modules=False` filter would exclude instances
        with at least one module bay with an installed module.

        Set `exclude=True` to reverse the behavior of the filter. This __may__ be useful
        for filtering on null directly related fields but this filter is not smart enough
        to differentiate between `fieldA__fieldB__isnull` and `fieldA__isnull` so it's not
        suitable for cases like the `has_empty_module_bays` filter where an instance may
        not have any module bays.

        See the below table for more information:

        | value       | exclude          | Result
        |-------------|------------------|-------
        | True        | False (default)  | Return instances with at least one non-null match -- qs.filter(field_name__isnull=False)
        | False       | False (default)  | Exclude instances with at least one non-null match -- qs.exclude(field_name__isnull=False)
        | True        | True             | Return instances with at least one null match -- qs.filter(field_name__isnull=True)
        | False       | True             | Exclude instances with at least one null match -- qs.exclude(field_name__isnull=True)

    """

    def __init__(self, field_name=None, lookup_expr="isnull", *, label=None, method=None, distinct=True, **kwargs):
        if field_name is None:
            raise ValueError(f"Field name is required for {self.__class__.__name__}")

        super().__init__(
            field_name=field_name,
            lookup_expr=lookup_expr,
            label=label,
            method=method,
            distinct=distinct,
            widget=forms.StaticSelect2(choices=forms.BOOLEAN_CHOICES),
            **kwargs,
        )

    def filter(self, qs, value):
        if value in EMPTY_VALUES:
            return qs
        if self.distinct:
            qs = qs.distinct()
        lookup = f"{self.field_name}__{self.lookup_expr}"
        if bool(value):
            # if self.exclude=False, return instances with field populated
            return qs.filter(**{lookup: self.exclude})
        else:
            # if self.exclude=False, exclude instances with field populated
            return qs.exclude(**{lookup: self.exclude})


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
    Mixin to allow specifying a ContentType by <app_label>.<model> (e.g. "dcim.location").
    """

    def filter(self, qs, value):
        if value in EMPTY_VALUES:
            return qs

        if value.isdigit():
            return self.get_method(qs)(**{f"{self.field_name}__pk": value})
        try:
            app_label, model = value.lower().split(".")
        except ValueError:
            return qs.none()
        return self.get_method(qs)(
            **{
                f"{self.field_name}__app_label": app_label,
                f"{self.field_name}__model": model,
            }
        )


class ContentTypeFilter(ContentTypeFilterMixin, django_filters.CharFilter):
    """
    Allows character-based ContentType filtering by <app_label>.<model> (e.g. "dcim.location").

    Does not support limiting of choices. Can be used without arguments on a `FilterSet`:

        content_type = ContentTypeFilter()
    """


class ContentTypeChoiceFilter(ContentTypeFilterMixin, django_filters.ChoiceFilter):
    """
    Allows character-based ContentType filtering by <app_label>.<model> (e.g.
    "dcim.location") but an explicit set of choices must be provided.

    Example use on a `FilterSet`:

        content_type = ContentTypeChoiceFilter(
            choices=FeatureQuery("dynamic_groups").get_choices,
        )

    In most cases you should use `ContentTypeMultipleChoiceFilter` instead.
    """


class ContentTypeMultipleChoiceFilter(django_filters.MultipleChoiceFilter):
    """
    Allows multiple-choice ContentType filtering by <app_label>.<model> (e.g. "dcim.location").

    Does NOT allow filtering by PK at this time; it would need to be reimplemented similar to
    NaturalKeyOrPKMultipleChoiceFilter as a breaking change.

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

    def get_filter_predicate(self, v):
        if v.isdigit():
            return {f"{self.field_name}__pk": v}
        try:
            app_label, model = v.lower().split(".")
        except ValueError:
            return {f"{self.field_name}__pk": v}
        return {f"{self.field_name}__app_label": app_label, f"{self.field_name}__model": model}


class MappedPredicatesFilterMixin:
    """
    A filter mixin to provide the ability to specify fields and lookup expressions to use for
    filtering.

    A mapping of filter predicates (field_name: lookup_expr) must be provided to the filter when
    declared on a filterset. This mapping is used to construct a `Q` query to filter based on the
    provided predicates.

    By default a predicate for `{"id": "iexact"}` (`id__exact`) will always be included.

    Example:

        q = SearchFilter(
            filter_predicates={
                "comments": "icontains",
                "name": "icontains",
            },
        )

    Optionally you may also provide a callable to use as a preprocessor for the filter predicate by
    providing the value as a nested dict with "lookup_expr" and "preprocessor" keys. For example:

        q = SearchFilter(
            filter_predicates={
                "asn": {
                    "lookup_expr": "exact",
                    "preprocessor": int,
                },
            },
        )

    This tells the filter to try to cast `asn` to an `int`. If it fails, this predicate will be
    skipped.
    """

    # Optional label for the form element generated for this filter
    label = None

    # Filter predicates that will always be included if not otherwise specified.
    default_filter_predicates = {"id": "iexact"}

    # Lookup expressions for which whitespace should be preserved.
    preserve_whitespace = ["icontains"]

    def __init__(self, filter_predicates=None, strip=False, *args, **kwargs):
        if not isinstance(filter_predicates, dict):
            raise TypeError("filter_predicates must be a dict")

        # Layer incoming filter_predicates on top of the defaults so that any overrides take
        # precedence.
        defaults = deepcopy(self.default_filter_predicates)
        defaults.update(filter_predicates)

        # Format: {field_name: lookup_expr, ...}
        self.filter_predicates = defaults

        # Try to use the label from the class if it is defined.
        kwargs.setdefault("label", self.label)

        # Whether to strip whtespace in the inner CharField form (default: False)
        kwargs.setdefault("strip", strip)

        super().__init__(*args, **kwargs)

        # Generate the query with a sentinel value to validate it and surface parse errors.
        self.generate_query(value="")

    def generate_query(self, value, **kwargs):
        """
        Given a `value`, return a `Q` object for 2-tuple of `predicate=value`. Filter predicates are
        read from the instance filter. Any `kwargs` are ignored.
        """

        def noop(v):
            """Pass through the value."""
            return v

        query = models.Q()
        for field_name, lookup_info in self.filter_predicates.items():
            # Unless otherwise specified, set the default prepreprocssor
            if isinstance(lookup_info, str):
                lookup_expr = lookup_info
                if lookup_expr in self.preserve_whitespace:
                    preprocessor = noop
                else:
                    preprocessor = str.strip

            # Or set it to what was defined by caller
            elif isinstance(lookup_info, dict):
                lookup_expr = lookup_info.get("lookup_expr")
                preprocessor = lookup_info.get("preprocessor")
                if not callable(preprocessor):
                    raise TypeError(f"Preprocessor {preprocessor} must be callable!")
            else:
                raise TypeError(f"Predicate value must be a str or a dict! Got: {type(lookup_info)}")

            # Try to preprocess the value or skip creating a predicate for it. In the event we try
            # to cast a value to an invalid type (e.g. `int("foo")` or `dict(42)`), ensure this
            # predicate is not included in the query.
            try:
                new_value = preprocessor(value)
            except (TypeError, ValueError):
                continue

            predicate = {f"{field_name}__{lookup_expr}": new_value}
            query |= models.Q(**predicate)

        # Return this for later use (such as introspection or debugging)
        return query

    def filter(self, qs, value):
        if value in EMPTY_VALUES:
            return qs

        # Evaluate the query and stash it for later use (such as introspection or debugging)
        query = self.generate_query(value=value)
        qs = self.get_method(qs)(query)
        self._most_recent_query = query
        return qs.distinct()


# TODO(timizuo): NaturalKeyOrPKMultipleChoiceFilter is not currently handling pk Integer field properly; resolve this in issue #3336
@extend_schema_field(OpenApiTypes.STR)
class NaturalKeyOrPKMultipleChoiceFilter(django_filters.ModelMultipleChoiceFilter):
    """
    Filter that supports filtering on values matching the `pk` field and another
    field of a foreign-key related object. The desired field is set using the `to_field_name`
    keyword argument on filter initialization (defaults to `name`).

    NOTE that the `to_field_name` field does not have to be a "true" natural key (ie. unique), it
    was just the best name we could come up with for this filter

    """

    field_class = forms.MultiMatchModelMultipleChoiceField

    def __init__(self, *args, prefers_id=False, **kwargs):
        """Initialize the NaturalKeyOrPKMultipleChoiceFilter.

        Args:
            prefers_id (bool, optional): Prefer PK (ID) over the 'to_field_name'. Defaults to False.
        """
        self.natural_key = kwargs.setdefault("to_field_name", "name")
        self.prefers_id = prefers_id
        super().__init__(*args, **kwargs)

    def get_filter_predicate(self, v):
        """
        Override base filter behavior to force the filter to use the `pk` field instead of
        the natural key in the generated filter.
        """

        # Null value filtering
        if v is None:
            return {f"{self.field_name}__isnull": True}

        # If value is a model instance, stringify it to a pk.
        if isinstance(v, models.Model):
            logger.debug("Model instance detected. Casting to a PK.")
            v = str(v.pk)

        # Try to cast the value to a UUID and set `is_pk` boolean.
        try:
            uuid.UUID(str(v))
        except (AttributeError, TypeError, ValueError):
            logger.debug("Non-UUID value detected: Filtering using natural key")
            is_pk = False
        else:
            v = str(v)  # Cast possible UUID instance to a string
            is_pk = True

        # If it's not a pk, then it's a name and the filter predicate needs to be nested (e.g.
        # `{"location__name": "ams01"}`) so that it can be usable in `Q` objects.
        if not is_pk:
            name = f"{self.field_name}__{self.field.to_field_name}"
        else:
            logger.debug("UUID detected: Filtering using field name")
            name = self.field_name

        if name and self.lookup_expr != django_filters.conf.settings.DEFAULT_LOOKUP_EXPR:
            name = "__".join([name, self.lookup_expr])

        return {name: v}


class SearchFilter(MappedPredicatesFilterMixin, django_filters.CharFilter):
    """
    Provide a search filter for use on filtersets as the `q=` parameter.

    See the docstring for `nautobot.core.filters.MappedPredicatesFilterMixin` for usage.
    """

    label = "Search"


class TagFilter(NaturalKeyOrPKMultipleChoiceFilter):
    """
    Match on one or more assigned tags. If multiple tags are specified (e.g. ?tag=foo&tag=bar), the queryset is filtered
    to objects matching all tags.
    """

    def __init__(self, *args, **kwargs):
        from nautobot.extras.models import Tag  # avoid circular import

        kwargs.setdefault("field_name", "tags")
        kwargs.setdefault("conjoined", True)
        kwargs.setdefault("label", "Tags")
        kwargs.setdefault("queryset", Tag.objects.all())

        super().__init__(*args, **kwargs)


class TreeNodeMultipleChoiceFilter(NaturalKeyOrPKMultipleChoiceFilter):
    """
    Filter that matches on the given model(s) (identified by name and/or pk) _as well as their tree descendants._

    For example, if we have:

        Location "Earth"
          Location "USA"
            Location "GA" <- Location "Athens"
            Location "NC" <- Location "Durham"

    a NaturalKeyOrPKMultipleChoiceFilter on Location for {"parent": "USA"} would only return "GA" and "NC"
    since that is the only two locations that have an immediate parent "USA"
    but a TreeNodeMultipleChoiceFilter on Location for {"parent": "USA"}
    would match both "Athens" and "Durham" in addition to "GA" and "NC".
    """

    def __init__(self, *args, **kwargs):
        kwargs.pop("lookup_expr", None)  # Disallow overloading of `lookup_expr`.
        super().__init__(*args, **kwargs)

    def generate_query(self, value, qs=None, **kwargs):
        """
        Given a filter value, return a `Q` object that accounts for nested tree node descendants.
        """
        if value:
            # django-tree-queries
            value = [node.descendants(include_self=True) if not isinstance(node, str) else node for node in value]

        # This new_value is going to be a list of querysets that needs to be flattened.
        value = list(data_utils.flatten_iterable(value))

        # Construct a list of filter predicates that will be used to generate the Q object.
        predicates = []
        for obj in value:
            # Get the exact instance by PK as we are nested from the original query,
            #   or just pass the object through, commonly the null case.
            val = getattr(obj, "pk", obj)
            if val == self.null_value:
                val = None
            predicates.append(self.get_filter_predicate(val))

        # Construct a nested OR query from the list of filter predicates derived from the flattened
        # listed of descendant objects.
        query = models.Q()
        for predicate in predicates:
            query |= models.Q(**predicate)

        return query

    def filter(self, qs, value):
        if value in EMPTY_VALUES:
            return qs

        # Fetch the generated Q object and filter the incoming qs with it before passing it along.
        query = self.generate_query(value)
        result = self.get_method(qs)(query)
        if self.distinct:
            result = result.distinct()
        return result


#
# FilterSets
#


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
            timezone_field.TimeZoneField: {"filter_class": MultiValueCharFilter},
        }
    )

    USE_CHAR_FILTER_FOR_LOOKUPS = [django_filters.MultipleChoiceFilter]

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
                ContentTypeFilter,
                ContentTypeChoiceFilter,
                ContentTypeMultipleChoiceFilter,
                MultiValueUUIDFilter,
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
        if filter_field.method is not None or filter_field.lookup_expr not in ["exact", "in", "iexact"]:
            return magic_filters

        # Choose the lookup expression map based on the filter type
        lookup_map = cls._get_filter_lookup_dict(filter_field)
        if lookup_map is None:
            # Do not augment this filter type with more lookup expressions
            return magic_filters

        # Get properties of the existing filter for later use
        field = get_model_field(cls._meta.model, filter_field.field_name)  # pylint: disable=no-member

        # If there isn't a model field, return.
        if field is None:
            return magic_filters

        # If the field allows null values, add an `isnull`` check
        if getattr(field, "null", None):
            # Use this method vs extend as the `lookup_map` variable is generally one of
            # the constants which we do not want to update
            lookup_map = dict(lookup_map, isnull="isnull")

        # Create new filters for each lookup expression in the map
        for lookup_name, lookup_expr in lookup_map.items():
            new_filter_name = f"{filter_name}__{lookup_name}"

            try:
                new_filter = cls._get_new_filter(filter_field, field, filter_name, lookup_expr)
            except django_filters.exceptions.FieldLookupError:
                # The filter could not be created because the lookup expression is not supported on the field
                continue

            if lookup_name.startswith("n"):
                # This is a negation filter which requires a queryset.exclude() clause
                # Of course setting the negation of the existing filter's exclude attribute handles both cases
                new_filter.exclude = not filter_field.exclude

            # If the base filter_field has a custom label, django_filters won't adjust it for the new_filter lookup,
            # so we have to do it.
            if filter_field.label and filter_field.label != label_for_filter(
                cls._meta.model,  # pylint: disable=no-member
                filter_field.field_name,
                filter_field.lookup_expr,
                filter_field.exclude,
            ):
                # Lightly adjusted from label_for_filter() implementation:
                verbose_expression = ["exclude", filter_field.label] if new_filter.exclude else [filter_field.label]
                if isinstance(lookup_expr, str):
                    verbose_expression.append(verbose_lookup_expr(lookup_expr))
                verbose_expression = [force_str(part) for part in verbose_expression if part]
                new_filter.label = capfirst(" ".join(verbose_expression))

            magic_filters[new_filter_name] = new_filter

        return magic_filters

    @classmethod
    def _should_use_char_filter_for_lookups(cls, filter_field):
        return type(filter_field) in cls.USE_CHAR_FILTER_FOR_LOOKUPS

    @classmethod
    def _get_new_filter(cls, filter_field, field, filter_name, lookup_expr):
        if cls._should_use_char_filter_for_lookups(filter_field):
            # For some cases like `MultiValueChoiceFilter(django_filters.MultipleChoiceFilter)`
            # we want to have choices field with no lookups and standard char field for lookups filtering.
            # Using a `choice` field for lookups blocks us from using `__re`, `__iew` or other "partial" filters.
            resolve_field(field, lookup_expr)  # Will raise FieldLookupError if the lookup is invalid
            return MultiValueCharFilter(
                field_name=filter_field.field_name,
                lookup_expr=lookup_expr,
                label=filter_field.label,
                exclude=filter_field.exclude,
                distinct=filter_field.distinct,
            )

        if filter_name in cls.declared_filters and lookup_expr not in {"isnull"}:  # pylint: disable=no-member
            # The filter field has been explicitly defined on the filterset class so we must manually
            # create the new filter with the same type because there is no guarantee the defined type
            # is the same as the default type for the field. This does not apply if the filter
            # should retain the original lookup_expr type, such as `isnull` using a boolean field on a
            # char or date object.
            resolve_field(field, lookup_expr)  # Will raise FieldLookupError if the lookup is invalid
            return type(filter_field)(
                field_name=filter_field.field_name,
                lookup_expr=lookup_expr,
                label=filter_field.label,
                exclude=filter_field.exclude,
                distinct=filter_field.distinct,
                **filter_field.extra,
            )

        # The filter field is listed in Meta.fields so we can safely rely on default behavior
        # Will raise FieldLookupError if the lookup is invalid
        return cls.filter_for_field(field, filter_field.field_name, lookup_expr)

    @classmethod
    def add_filter(cls, new_filter_name, new_filter_field):
        """
        Allow filters to be added post-generation on import.

        Will provide `<field_name>__<lookup_expr>` generation automagically.
        """
        if not isinstance(new_filter_field, django_filters.Filter):
            raise TypeError(f"Tried to add filter ({new_filter_name}) which is not an instance of Django Filter")

        if new_filter_name in cls.base_filters:  # pylint: disable=no-member
            raise AttributeError(
                f"There was a conflict with filter `{new_filter_name}`, the custom filter was ignored."
            )

        cls.base_filters[new_filter_name] = new_filter_field  # pylint: disable=no-member
        # django-filters has no concept of "abstract" filtersets, so we have to fake it
        if cls._meta.model is not None:  # pylint: disable=no-member
            cls.base_filters.update(  # pylint: disable=no-member
                cls._generate_lookup_expression_filters(filter_name=new_filter_name, filter_field=new_filter_field)
            )

    @classmethod
    def get_fields(cls):
        fields = super().get_fields()
        if "id" not in fields and (cls._meta.exclude is None or "id" not in cls._meta.exclude):  # pylint: disable=no-member
            # Add "id" as the first key in the `fields` dict
            fields = {"id": [django_filters.conf.settings.DEFAULT_LOOKUP_EXPR], **fields}
        return fields

    @classmethod
    def get_filters(cls):
        """
        Override filter generation to support dynamic lookup expressions for certain filter types.
        """
        filters = super().get_filters()

        # Remove any filters that may have been auto-generated from private model attributes
        for filter_name in list(filters.keys()):
            if filter_name.startswith("_"):
                del filters[filter_name]

        if getattr(cls._meta.model, "is_contact_associable_model", False):  # pylint: disable=no-member
            # Add "contacts" and "teams" filters
            from nautobot.extras.models import Contact, Team

            if "contacts" not in filters:
                filters["contacts"] = NaturalKeyOrPKMultipleChoiceFilter(
                    queryset=Contact.objects.all(),
                    field_name="associated_contacts__contact",
                    to_field_name="name",
                    label="Contacts (name or ID)",
                )
                cls.declared_filters["contacts"] = filters["contacts"]  # pylint: disable=no-member

            if "teams" not in filters:
                filters["teams"] = NaturalKeyOrPKMultipleChoiceFilter(
                    queryset=Team.objects.all(),
                    field_name="associated_contacts__team",
                    to_field_name="name",
                    label="Teams (name or ID)",
                )
                cls.declared_filters["teams"] = filters["teams"]  # pylint: disable=no-member

        if "dynamic_groups" not in filters and getattr(cls._meta.model, "is_dynamic_group_associable_model", False):  # pylint: disable=no-member
            if not hasattr(cls._meta.model, "static_group_association_set"):  # pylint: disable=no-member
                logger.warning(
                    "Model %s has 'is_dynamic_group_associable_model = True' but lacks "
                    "a 'static_group_association_set' attribute. Perhaps this is due to it inheriting from "
                    "the deprecated DynamicGroupMixin class instead of the preferred DynamicGroupsModelMixin?",
                    cls._meta.model,  # pylint: disable=no-member
                )
            else:
                # Add "dynamic_groups" field as the last key
                from nautobot.extras.models import DynamicGroup

                filters["dynamic_groups"] = NaturalKeyOrPKMultipleChoiceFilter(
                    queryset=DynamicGroup.objects.all(),
                    field_name="static_group_association_set__dynamic_group",
                    to_field_name="name",
                    query_params={"content_type": cls._meta.model._meta.label_lower},  # pylint: disable=no-member
                    label="Dynamic groups (name or ID)",
                )
                cls.declared_filters["dynamic_groups"] = filters["dynamic_groups"]  # pylint: disable=no-member

        # django-filters has no concept of "abstract" filtersets, so we have to fake it
        if cls._meta.model is not None:  # pylint: disable=no-member
            if "tags" in filters and isinstance(filters["tags"], TagFilter):
                filters["tags"].extra["query_params"] = {"content_types": [cls._meta.model._meta.label_lower]}  # pylint: disable=no-member

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
            if isinstance(field, timezone_field.TimeZoneField):
                return django_filters.MultipleChoiceFilter, {"choices": ((str(v), n) for v, n in field.choices)}
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
