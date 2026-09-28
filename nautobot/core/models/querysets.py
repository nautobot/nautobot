from typing import ClassVar

from django.db.models import Count, F, OuterRef, QuerySet, Subquery
from django.db.models.functions import Coalesce

from nautobot.core.models.sensitive_fields import (
    check_expression,
    check_lookup_path,
    get_sensitive_field_names,
    sensitive_field_alias,
    strict_sensitive_fields_enabled,
)
from nautobot.core.models.utils import deconstruct_composite_key
from nautobot.core.utils import permissions
from nautobot.core.utils.data import merge_dicts_without_collision


def count_related(model, field, *, filter_dict=None, manager_name="objects", distinct=False):
    """
    Return a Subquery suitable for annotating a child object count.

    Args:
        model (Model): The related model to aggregate
        field (str): The field on the related model which points back to the OuterRef model
        filter_dict (dict): Optional dict of filter key/value pairs to limit the Subquery
        manager_name (str): Name of the manager on the model to use
    """
    filters = {field: OuterRef("pk")}
    if filter_dict:
        filters.update(filter_dict)

    manager = getattr(model, manager_name)
    if hasattr(manager, "without_tree_fields"):
        manager = manager.without_tree_fields()
    qs = manager.filter(**filters).order_by().values(field)
    if distinct:
        qs = qs.annotate(c=Count("pk", distinct=distinct)).values("c")
    else:
        qs = qs.annotate(c=Count("*")).values("c")
    subquery = Subquery(qs)

    return Coalesce(subquery, 0)


class SensitiveFieldsQuerySetMixin:
    """
    Mixin blocking retrieval of fields declared in a model's `sensitive_fields`, via projection or traversal.

    `BaseModel.from_db()` scrubs sensitive values out of database-loaded *instances*, but `values()` and
    `values_list()` never build instances at all (`Query.set_values` even clears the deferred-loading mask),
    so the projection methods need their own check. That check must live on a mixin shared by every Nautobot
    queryset rather than on `RestrictedQuerySet` alone, because the query can *start* on any model:
    `User.objects.values_list("tokens__key")` has to be blocked even though `UserQuerySet` is not a
    `RestrictedQuerySet` and `Token.objects` is never involved.

    Filtering is intentionally not checked. The contract is that a sensitive value is never *returned*, not
    that the column cannot be referenced, and API token authentication looks a token up by its key.
    """

    # Sensitive field names the caller has explicitly opted in to on this chain, via `with_sensitive_fields()`.
    _sensitive_fields_allowed: ClassVar[frozenset] = frozenset()

    def _clone(self):
        """Ensures that we pass along the sensitive fields allowed on this chain when cloning to a new queryset.

        Django calls this method internally when cloning a queryset (e.g., .filter(), .annotate(), .values(), etc.).
        For example: `User.objects.with_sensitive_fields("key").filter(pk=1).with_sensitive_fields("key").values("key")`
        Without this, the second `with_sensitive_fields("key")` would not be aware of the sensitive field allowed
        on the first, and would raise an error.
        """
        clone = super()._clone()
        clone._sensitive_fields_allowed = self._sensitive_fields_allowed
        return clone

    def _check_field_names(self, field_names):
        """Raise `SensitiveFieldError` for any lookup path in `field_names` reaching a sensitive field."""
        if not strict_sensitive_fields_enabled():
            return
        for field_name in field_names:
            check_lookup_path(self.model, field_name, self._sensitive_fields_allowed)

    def _check_expressions(self, expressions):
        """Raise `SensitiveFieldError` for any expression in `expressions` referencing a sensitive field."""
        if not strict_sensitive_fields_enabled():
            return
        for expression in expressions:
            check_expression(self.model, expression, self._sensitive_fields_allowed)

    def _non_sensitive_field_names(self):
        """Return this model's concrete field attnames minus any withheld sensitive fields, or None.

        Used to give bare `values()`/`values_list()` a sane result on a model that declares sensitive
        fields: raising instead would make such a model unusable with a call that generic Nautobot code
        makes routinely. Returns None when there is nothing to withhold, so that the overwhelmingly common
        case passes through to Django untouched rather than having its field list rebuilt here.

        Uses `attname` rather than `name` to match the keys Django's own bare `values()` produces, which
        for a foreign key is `<name>_id` holding the raw key rather than `<name>` holding the instance.
        """
        if not strict_sensitive_fields_enabled():
            return None
        withheld = get_sensitive_field_names(self.model) - self._sensitive_fields_allowed
        if not withheld:
            return None
        return [field.attname for field in self.model._meta.concrete_fields if field.attname not in withheld]

    def with_sensitive_fields(self, *field_names):
        """Return a queryset that will retrieve the named sensitive fields of this queryset's model.

        At least one field name is required. Callers that genuinely need to suspend the protection
        wholesale want `sensitive_fields_exempt()` instead.

        The values are carried past `BaseModel.from_db()`'s scrub as query annotations, which
        `ModelIterable` applies to each instance after `from_db()` has returned, so no additional query is
        issued.

        This is deliberately explicit and greppable: every place Nautobot legitimately needs a sensitive
        value should show up in a search for this method name.
        """
        if not field_names:
            raise ValueError(
                f"with_sensitive_fields() requires at least one field name; "
                f"{self.model._meta.label}.sensitive_fields declares "
                f"{', '.join(sorted(get_sensitive_field_names(self.model))) or 'none'}"
            )
        declared = get_sensitive_field_names(self.model)
        requested = frozenset(field_names)
        unknown = sorted(requested - declared)
        if unknown:
            raise ValueError(
                f"{', '.join(unknown)} {'are' if len(unknown) > 1 else 'is'} not declared in "
                f"{self.model._meta.label}.sensitive_fields"
            )
        clone = self._chain()
        clone._sensitive_fields_allowed = self._sensitive_fields_allowed | requested
        # Annotating after widening the allow-set means this queryset's own `annotate()` check permits
        # the `F()` references, and `_clone()` carries the allow-set onto the annotated queryset.
        clone = clone.annotate(**{sensitive_field_alias(field_name): F(field_name) for field_name in sorted(requested)})
        return clone

    with_sensitive_fields.do_not_call_in_templates = True

    def values(self, *fields, **expressions):
        if not fields and not expressions:
            fields = self._non_sensitive_field_names() or ()
        else:
            self._check_field_names(fields)
            self._check_expressions(expressions.values())
        return super().values(*fields, **expressions)

    def values_list(self, *fields, **kwargs):
        # `values_list()` reaches `Query.set_values()` without going through `values()`, so it needs its own check.
        if not fields:
            fields = self._non_sensitive_field_names() or ()
        else:
            self._check_field_names(fields)
        return super().values_list(*fields, **kwargs)

    def annotate(self, *args, **kwargs):
        self._check_expressions(args)
        self._check_expressions(kwargs.values())
        return super().annotate(*args, **kwargs)

    def alias(self, *args, **kwargs):
        # Checked separately from `annotate()`, or `alias(x=F("key")).values("x")` would walk straight through.
        self._check_expressions(args)
        self._check_expressions(kwargs.values())
        return super().alias(*args, **kwargs)

    def aggregate(self, *args, **kwargs):
        self._check_expressions(args)
        self._check_expressions(kwargs.values())
        return super().aggregate(*args, **kwargs)

    def order_by(self, *field_names):
        # Sorting can indirectly disclose sensitive fields, so we check ordering but expect no legitimate use.
        self._check_field_names(field_names)
        self._check_expressions([field for field in field_names if not isinstance(field, str)])
        return super().order_by(*field_names)

    def distinct(self, *field_names):
        # `DISTINCT ON` discloses the same comparison information as ordering.
        self._check_field_names(field_names)
        return super().distinct(*field_names)


class CompositeKeyQuerySetMixin(SensitiveFieldsQuerySetMixin):
    """
    Mixin to extend a base queryset class with support for filtering by `composite_key=...` as a virtual parameter.

    Example:

        >>> Location.objects.last().composite_key
        'Durham;AMER'

    Note that `Location.composite_key` is a `@property`, *not* a database field, and so would not normally be usable in
    a `QuerySet` query, but because `RestrictedQuerySet` inherits from this mixin, the following "just works":

        >>> Location.objects.get(composite_key="Durham;AMER")
        <Location: Durham>

    This is a shorthand for what would otherwise be a multi-step process:

        >>> from nautobot.core.models.utils import deconstruct_composite_key
        >>> deconstruct_composite_key("Durham;AMER")
        ['Durham', 'AMER']
        >>> Location.natural_key_args_to_kwargs(['Durham', 'AMER'])
        {'name': 'Durham', 'parent__name': 'AMER'}
        >>> Location.objects.get(name="Durham", parent__name="AMER")
        <Location: Durham>

    This works for QuerySet `filter()` and `exclude()` as well:

        >>> Location.objects.filter(composite_key='Durham;AMER')
        <LocationQuerySet [<Location: Durham>]>
        >>> Location.objects.exclude(composite_key='Durham;AMER')
        <LocationQuerySet [<Location: AMER>]>

    `composite_key` can also be used in combination with other query parameters:

        >>> Location.objects.filter(composite_key='Durham;AMER', status__name='Planned')
        <LocationQuerySet []>

    It will raise a ValueError if the deconstructed composite key collides with another query parameter:

        >>> Location.objects.filter(composite_key='Durham;AMER', name='Raleigh')
        ValueError: Conflicting values for key "name": ('Durham', 'Raleigh')

    See also `BaseModel.composite_key` and `utils.construct_composite_key()`/`utils.deconstruct_composite_key()`.
    """

    def split_composite_key_into_kwargs(self, composite_key=None, **kwargs):
        """
        Helper method abstracting a common need from filter() and exclude().

        Subclasses may need to call this directly if they also have special processing of other filter/exclude params.
        """
        if composite_key and isinstance(composite_key, str):
            natural_key_values = deconstruct_composite_key(composite_key)
            return merge_dicts_without_collision(self.model.natural_key_args_to_kwargs(natural_key_values), kwargs)
        return kwargs

    def filter(self, *args, composite_key=None, **kwargs):
        """
        Explicitly handle `filter(composite_key="...")` by decomposing the composite-key into natural key parameters.

        Counterpart to BaseModel.composite_key property.
        """
        return super().filter(*args, **self.split_composite_key_into_kwargs(composite_key, **kwargs))

    def exclude(self, *args, composite_key=None, **kwargs):
        """
        Explicitly handle `exclude(composite_key="...")` by decomposing the composite-key into natural key parameters.

        Counterpart to BaseModel.composite_key property.
        """
        return super().exclude(*args, **self.split_composite_key_into_kwargs(composite_key, **kwargs))


class RestrictedQuerySet(CompositeKeyQuerySetMixin, QuerySet):
    def restrict(self, user, action="view"):
        """
        Filter the QuerySet to return only objects on which the specified user has been granted the specified
        permission.

        Args:
            user (User): User instance
            action (str): The action which must be permitted (e.g. "view" for "dcim.view_location"); default is 'view'
        """
        # Resolve the full name of the required permission
        app_label = self.model._meta.app_label
        model_name = self.model._meta.model_name
        permission_required = f"{app_label}.{action}_{model_name}"

        # Bypass restriction for superusers and exempt views
        if user.is_superuser or permissions.permission_is_exempt(permission_required):
            # This is a cache buster to ensure that we always return a new QuerySet
            qs = self.all()

        # User is anonymous or has not been granted the requisite permission
        elif not user.is_authenticated or permission_required not in user.get_all_permissions():
            qs = self.none()

        # Filter the queryset to include only objects with allowed attributes
        else:
            tokens = {
                "$user": user,
            }

            attrs = permissions.qs_filter_from_constraints(user._object_perm_cache[permission_required], tokens)
            if attrs:
                # Use a subquery to avoid duplicate results when constraints span many-to-many joins
                # (e.g. tags__name__regex matching multiple tags on the same object).
                # See: https://github.com/nautobot/nautobot/issues/8690
                inner_qs = self.model._default_manager.filter(attrs)
                if hasattr(inner_qs, "without_tree_fields"):
                    inner_qs.without_tree_fields()
                qs = self.filter(pk__in=inner_qs.values("pk"))
            else:
                qs = self.all()

        return qs

    def check_perms(self, user, *, instance=None, pk=None, action="view"):
        """
        Check whether the given user can perform the given action with regard to the given instance of this model.

        Either instance or pk must be specified, but not both.

        Args:
          user (User): User instance
          instance (self.model): Instance of this queryset's model to check, if pk is not provided
          pk (uuid): Primary key of the desired instance to check for, if instance is not provided
          action (str): The action which must be permitted (e.g. "view" for "dcim.view_location"); default is 'view'

        Returns:
            (bool): Whether the action is permitted or not
        """
        if instance is not None and pk is not None and instance.pk != pk:
            raise RuntimeError("Should not be called with both instance and pk specified!")
        if instance is None and pk is None:
            raise ValueError("Either instance or pk must be specified!")
        if instance is not None and not isinstance(instance, self.model):
            raise TypeError(f"{instance} is not a {self.model}")
        if pk is None:
            pk = instance.pk

        return self.restrict(user, action).filter(pk=pk).exists()

    def distinct_values_list(self, *fields, flat=False, named=False):
        """Wrapper for `QuerySet.values_list()` that adds the `distinct()` query to return a list of unique values.

        Note:
            Uses `QuerySet.order_by()` to disable ordering, preventing unexpected behavior when using `values_list` described
            in the Django `distinct()` documentation at https://docs.djangoproject.com/en/stable/ref/models/querysets/#distinct

        Args:
            *fields (str): Optional positional arguments which specify field names.
            flat (bool): Set to True to return a QuerySet of individual values instead of a QuerySet of tuples.
                Defaults to False.
            named (bool): Set to True to return a QuerySet of namedtuples. Defaults to False.

        Returns:
            (QuerySet): A QuerySet of tuples or, if `flat` is set to True, a queryset of individual values.

        """
        return self.order_by().values_list(*fields, flat=flat, named=named).distinct()


class BaseManyToManyQuerySetMixin:
    """
    Base mixin to provide backward compatibility for fields that have been changed from ForeignKey to ManyToManyField.

    Subclasses should define FIELD_MAP as a dictionary of field mappings, where the key is the old field name
    and the value is the new field name.
    """

    FIELD_MAP: ClassVar[dict[str, str]] = {}

    def __init_subclass__(cls, **kwargs):
        """Combine FIELD_MAP from all parent classes into a single dictionary."""
        super().__init_subclass__(**kwargs)
        combined_field_map = {}
        for base in reversed(cls.__mro__):
            if hasattr(base, "FIELD_MAP") and isinstance(getattr(base, "FIELD_MAP"), dict):
                combined_field_map.update(base.FIELD_MAP)
        cls.FIELD_MAP = combined_field_map

    def _convert_to_m2m_field(self, kwargs):
        field_mappings = self.FIELD_MAP
        if not field_mappings:
            return kwargs

        updated_kwargs = {}

        for field, value in kwargs.items():
            converted = False

            # Check each field mapping
            for old_field, new_field in field_mappings.items():
                if field == old_field:
                    # Direct field query becomes __in for ManyToMany
                    updated_kwargs[f"{new_field}__in"] = [value]
                    converted = True
                    break
                elif field.startswith(f"{old_field}__"):
                    # Replace old field prefix with new field prefix
                    updated_kwargs[field.replace(old_field, new_field, 1)] = value
                    converted = True
                    break

            if not converted:
                updated_kwargs[field] = value

        return updated_kwargs

    def filter(self, *args, **kwargs):
        kwargs = self._convert_to_m2m_field(kwargs)
        return super().filter(*args, **kwargs)

    def exclude(self, *args, **kwargs):
        kwargs = self._convert_to_m2m_field(kwargs)
        return super().exclude(*args, **kwargs)


class LocationToLocationsQuerySetMixin(BaseManyToManyQuerySetMixin):
    """
    Mixin to convert 'location' to 'locations' in queryset parameters.
    """

    FIELD_MAP = {"location": "locations"}


class ClusterToClustersQuerySetMixin(BaseManyToManyQuerySetMixin):
    """
    Mixin to convert 'cluster' to 'clusters' in queryset parameters.
    """

    FIELD_MAP = {"cluster": "clusters"}
