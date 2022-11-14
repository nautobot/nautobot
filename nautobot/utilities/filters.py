from collections import OrderedDict
from copy import deepcopy
import logging
import uuid

from django import forms
from django.conf import settings
from django.core.validators import MaxValueValidator
from django.db import models
from django.forms.utils import ErrorDict, ErrorList

import django_filters
from django_filters.constants import EMPTY_VALUES
from django_filters.utils import get_model_field, resolve_field

from mptt.models import MPTTModel
from tree_queries.models import TreeNode

from nautobot.dcim.fields import MACAddressCharField
from nautobot.dcim.forms import MACAddressField
from nautobot.extras.models import Tag
from nautobot.utilities.constants import (
    FILTER_CHAR_BASED_LOOKUP_MAP,
    FILTER_NEGATION_LOOKUP_MAP,
    FILTER_NUMERIC_BASED_LOOKUP_MAP,
)
from nautobot.utilities.forms.fields import MultiMatchModelMultipleChoiceField, MultiValueCharField
from nautobot.utilities.utils import flatten_iterable


from taggit.managers import TaggableManager


logger = logging.getLogger(__name__)


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
                super(field_class, self).to_python(v)  # pylint: disable=bad-super-call
                for v in value
                if v
            ]

    return type(f"MultiValue{field_class.__name__}", (NewField,), {})


#
# Filters
#
# Note that for the various MultipleChoiceFilter subclasses below, they additionally inherit from `CharFilter`,
# `DateFilter`, `DateTimeFilter`, etc. This has no particular impact on the behavior of these filters (as we're
# explicitly overriding their `field_class` attribute anyway), but is done as a means of type hinting
# for generating a more accurate REST API OpenAPI schema for these filter types.
#


class MultiValueCharFilter(django_filters.CharFilter, django_filters.MultipleChoiceFilter):
    field_class = MultiValueCharField


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


class NullableCharFieldFilter(django_filters.CharFilter):
    """
    Allow matching on null field values by passing a special string used to signify NULL.
    """

    def filter(self, qs, value):
        if value != settings.FILTERS_NULL_CHOICE_VALUE:
            return super().filter(qs, value)
        qs = self.get_method(qs)(**{f"{self.field_name}__isnull": True})
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
        self.generate_query(value="", filter_predicates=self.filter_predicates)

    def generate_query(self, value, filter_predicates=None, **kwargs):
        """
        Given a mapping of `filter_predicates` and a `value`, return a `Q` object for 2-tuple of
        predicate=value.
        """

        def noop(v):
            """Pass through the value."""
            return v

        query = models.Q()
        for field_name, lookup_info in filter_predicates.items():
            # Unless otherwise specified, set the default prepreprocssor
            if isinstance(lookup_info, str):
                lookup_expr = lookup_info
                if lookup_expr in self.preserve_whitespace:
                    preprocessor = noop
                else:
                    preprocessor = str.strip

            # Or set it to what was defined by caller
            elif isinstance(lookup_info, dict):
                lookup_expr = lookup_info["lookup_expr"]
                preprocessor = lookup_info.get("preprocessor")
                if not callable(preprocessor):
                    raise TypeError("Preprocessor {preprocessor} must be callable!")
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
        query = self.generate_query(value=value, filter_predicates=self.filter_predicates)
        qs = self.get_method(qs)(query)
        self._most_recent_query = query
        return qs.distinct()


class NaturalKeyOrPKMultipleChoiceFilter(django_filters.ModelMultipleChoiceFilter):
    """
    Filter that supports filtering on values matching the `pk` field and another
    field of a foreign-key related object. The desired field is set using the `to_field_name`
    keyword argument on filter initialization (defaults to `slug`).
    """

    field_class = MultiMatchModelMultipleChoiceField

    def __init__(self, *args, **kwargs):
        self.natural_key = kwargs.setdefault("to_field_name", "slug")
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

        # If it's not a pk, then it's a slug and the filter predicate needs to be nested (e.g.
        # `{"site__slug": "ams01"}`) so that it can be usable in `Q` objects.
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

    See the docstring for `nautobot.utilities.filters.MappedPredicatesFilterMixin` for usage.
    """

    label = "Search"


class TreeNodeMultipleChoiceFilter(NaturalKeyOrPKMultipleChoiceFilter):
    """
    Filter that matches on the given model(s) (identified by slug and/or pk) _as well as their tree descendants._

    For example, if we have:

        Region "Earth"
          Region "USA"
            Region "GA" <- Site "Athens"
            Region "NC" <- Site "Durham"

    a NaturalKeyOrPKMultipleChoiceFilter on Site for {"region": "USA"} would have no matches,
    since there are no Sites whose immediate Region is "USA",
    but a TreeNodeMultipleChoiceFilter on Site for {"region": "USA"} or {"region": "Earth"}
    would match both "Athens" and "Durham".
    """

    def __init__(self, *args, **kwargs):
        kwargs.pop("lookup_expr", None)  # Disallow overloading of `lookup_expr`.
        super().__init__(*args, **kwargs)

    def generate_query(self, value, qs=None, **kwargs):
        """
        Given a filter value, return a `Q` object that accounts for nested tree node descendants.
        """
        if value:
            if any(isinstance(node, TreeNode) for node in value):
                # django-tree-queries
                value = [node.descendants(include_self=True) if not isinstance(node, str) else node for node in value]
            elif any(isinstance(node, MPTTModel) for node in value):
                # django-mptt
                value = [
                    node.get_descendants(include_self=True) if not isinstance(node, str) else node for node in value
                ]

        # This new_value is going to be a list of querysets that needs to be flattened.
        value = list(flatten_iterable(value))

        # Construct a list of filter predicates that will be used to generate the Q object.
        predicates = []
        for obj in value:
            # Try to get the `to_field_name` (e.g. `slug`) or just pass the object through.
            val = getattr(obj, self.field.to_field_name, obj)
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
        return self.get_method(qs)(query)


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
            models.DecimalField: {"filter_class": MultiValueNumberFilter},
            models.EmailField: {"filter_class": MultiValueCharFilter},
            models.FloatField: {"filter_class": MultiValueNumberFilter},
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
            MACAddressCharField: {"filter_class": MultiValueMACAddressFilter},
            TaggableManager: {"filter_class": TagFilter},
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

        # If there isn't a model field, return.
        if field is None:
            return magic_filters

        # Create new filters for each lookup expression in the map
        for lookup_name, lookup_expr in lookup_map.items():
            new_filter_name = f"{filter_name}__{lookup_name}"

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
                f"There was a conflict with filter `{new_filter_name}`, the custom filter was ignored."
            )

        cls.base_filters[new_filter_name] = new_filter_field
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

        new_filters = {}
        for existing_filter_name, existing_filter in filters.items():
            new_filters.update(
                cls._generate_lookup_expression_filters(filter_name=existing_filter_name, filter_field=existing_filter)
            )

        filters.update(new_filters)
        return filters

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


class NameSlugSearchFilterSet(django_filters.FilterSet):
    """
    A base class for adding the search method to models which only expose the `name` and `slug` fields
    """

    q = SearchFilter(filter_predicates={"name": "icontains", "slug": "icontains"})
