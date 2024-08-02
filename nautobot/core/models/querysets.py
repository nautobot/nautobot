from django.db.models import Count, OuterRef, Q, QuerySet, Subquery
from django.db.models.functions import Coalesce

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


class CompositeKeyQuerySetMixin:
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

        :param user: User instance
        :param action: The action which must be permitted (e.g. "view" for "dcim.view_location"); default is 'view'
        """
        # Resolve the full name of the required permission
        app_label = self.model._meta.app_label
        model_name = self.model._meta.model_name
        permission_required = f"{app_label}.{action}_{model_name}"

        # Bypass restriction for superusers and exempt views
        if user.is_superuser or permissions.permission_is_exempt(permission_required):
            qs = self

        # User is anonymous or has not been granted the requisite permission
        elif not user.is_authenticated or permission_required not in user.get_all_permissions():
            qs = self.none()

        # Filter the queryset to include only objects with allowed attributes
        else:
            attrs = Q()
            tokens = {
                "$user": user,
            }

            attrs = permissions.qs_filter_from_constraints(user._object_perm_cache[permission_required], tokens)
            qs = self.filter(attrs)

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
