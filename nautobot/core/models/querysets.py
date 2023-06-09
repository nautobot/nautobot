from django.db.models import Count, OuterRef, Q, QuerySet, Subquery
from django.db.models.functions import Coalesce

from nautobot.core.models.utils import deconstruct_composite_key
from nautobot.core.utils import permissions


def count_related(model, field):
    """
    Return a Subquery suitable for annotating a child object count.
    """
    subquery = Subquery(
        model.objects.filter(**{field: OuterRef("pk")}).order_by().values(field).annotate(c=Count("*")).values("c")
    )

    return Coalesce(subquery, 0)


class RestrictedQuerySet(QuerySet):
    def restrict(self, user, action="view"):
        """
        Filter the QuerySet to return only objects on which the specified user has been granted the specified
        permission.

        :param user: User instance
        :param action: The action which must be permitted (e.g. "view" for "dcim.view_site"); default is 'view'
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
            for perm_attrs in user._object_perm_cache[permission_required]:
                if isinstance(perm_attrs, list):
                    for p in perm_attrs:
                        attrs |= Q(**p)
                elif perm_attrs:
                    attrs |= Q(**perm_attrs)
                else:
                    # Any permission with null constraints grants access to _all_ instances
                    attrs = Q()
                    break
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
          action (str): The action which must be permitted (e.g. "view" for "dcim.view_site"); default is 'view'

        Returns:
          bool: Whether the action is permitted or not
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
            *fields: Optional positional arguments which specify field names.
            flat (bool): Set to True to return a QuerySet of individual values instead of a QuerySet of tuples.
                Defaults to False.
            named (bool): Set to True to return a QuerySet of namedtuples. Defaults to False.

        Returns:
            QuerySet object: A QuerySet of tuples or, if `flat` is set to True, a queryset of individual values.

        """
        return self.order_by().values_list(*fields, flat=flat, named=named).distinct()

    def filter(self, *args, **kwargs):
        """
        Extend base queryset with support for filtering by `composite_key=...`.

        This is an enhanced version of natural-key slug support from django-natural-keys.
        Counterpart to BaseModel.composite_key property.
        """
        composite_key = kwargs.pop("composite_key", None)
        if composite_key and isinstance(composite_key, str):
            values = deconstruct_composite_key(composite_key)
            kwargs.update(self.model.natural_key_args_to_kwargs(values))

        return super().filter(*args, **kwargs)
