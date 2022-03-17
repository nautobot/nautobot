from django.db import IntegrityError, transaction
from django.db.models import Q, QuerySet
from django.db.models.utils import resolve_callables

from nautobot.utilities.permissions import permission_is_exempt


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
        if user.is_superuser or permission_is_exempt(permission_required):
            qs = self

        # User is anonymous or has not been granted the requisite permission
        elif not user.is_authenticated or permission_required not in user.get_all_permissions():
            qs = self.none()

        # Filter the queryset to include only objects with allowed attributes
        else:
            attrs = Q()
            for perm_attrs in user._object_perm_cache[permission_required]:
                if type(perm_attrs) is list:
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

    def validated_create(self, **kwargs):
        """Overload of create() to call validated_save()."""
        obj = self.model(**kwargs)
        self._for_write = True
        obj.validated_save(force_insert=True, using=self.db)
        return obj

    def validated_get_or_create(self, defaults=None, **kwargs):
        """Overload of get_or_create() to call validated_create()."""
        # The get() needs to be targeted at the write database in order
        # to avoid potential transaction consistency problems.
        self._for_write = True
        try:
            return self.get(**kwargs), False
        except self.model.DoesNotExist:
            params = self._extract_model_params(defaults, **kwargs)
            # Try to create an object using passed params.
            try:
                with transaction.atomic(using=self.db):
                    params = dict(resolve_callables(params))
                    return self.validated_create(**params), True
            except IntegrityError:
                try:
                    return self.get(**kwargs), False
                except self.model.DoesNotExist:
                    pass
                raise

    def validated_update_or_create(self, defaults=None, **kwargs):
        """Overload of update_or_create() to call validated_create()."""
        defaults = defaults or {}
        self._for_write = True
        with transaction.atomic(using=self.db):
            # Lock the row so that a concurrent update is blocked until
            # update_or_create() has performed its save.
            obj, created = self.select_for_update().validated_get_or_create(defaults, **kwargs)
            if created:
                return obj, created
            for k, v in resolve_callables(defaults):
                setattr(obj, k, v)
            obj.save(using=self.db)
        return obj, False
