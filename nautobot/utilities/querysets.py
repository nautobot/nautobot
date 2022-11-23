from django.db.models import (
    Q,
    QuerySet,
    ForeignKey,
    OneToOneField,
    OneToOneRel,
    ManyToOneRel,
    ManyToManyField,
    ManyToManyRel,
)

from nautobot.utilities.permissions import permission_is_exempt


class RestrictedQuerySet(QuerySet):
    def with_related(self, *fields):
        """
        Convenience method to call selected_related or prefetch_related on the passed fields.
        :param fields: Names of fields for which the related data should be selected/pre-fetched.
        """
        select_related_fields = []
        prefetch_related_fields = []
        for field_name in fields:
            field = self.model._meta.get_field(field_name)
            if isinstance(field, (ForeignKey, OneToOneField, OneToOneRel)):
                select_related_fields.append(field_name)
            elif isinstance(field, (ManyToOneRel, ManyToManyField, ManyToManyRel)):
                prefetch_related_fields.append(field_name)
            else:
                appropriate_fields = [
                    "ForeignKey",
                    "OneToOneField",
                    "OneToOneRel",
                    "ManyToOneRel",
                    "ManyToManyField",
                    "ManyToManyRel",
                ]
                raise ValueError(
                    f"Fields passed to 'with_related' need to be one of the following: {', '.join(appropriate_fields)}"
                )
        qs = self._chain()
        # Only call the *_related methods if we actually have fields, we don't want to clear out the existing ones.
        if select_related_fields:
            qs = qs.select_related(*select_related_fields)
        if prefetch_related_fields:
            qs = qs.prefetch_related(*prefetch_related_fields)
        return qs

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
        if user.is_superuser or permission_is_exempt(permission_required):
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
