from copy import deepcopy
import logging
import uuid

from django import forms as django_forms
from django.db import models
import django_filters
from django_filters.constants import EMPTY_VALUES
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema_field

from nautobot.core import forms
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
    field_class = multivalue_field_factory(django_forms.UUIDField, widget=forms.widgets.MultiValueCharInput)


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
            widget=forms.StaticSelect2(choices=forms.BOOLEAN_CHOICES),
            **kwargs,
        )


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
    """


class ContentTypeMultipleChoiceFilter(django_filters.MultipleChoiceFilter):
    """
    Allows multiple-choice ContentType filtering by <app_label>.<model> (e.g. "dcim.location").

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
    """

    field_class = forms.MultiMatchModelMultipleChoiceField

    def __init__(self, *args, **kwargs):
        self.natural_key = kwargs.setdefault("to_field_name", "name")
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
        return self.get_method(qs)(query)



