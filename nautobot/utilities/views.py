from django.contrib.auth.mixins import AccessMixin
from django.core.exceptions import ImproperlyConfigured
from django.urls import reverse
from django.urls.exceptions import NoReverseMatch
from django.utils.http import is_safe_url

from nautobot.utilities.utils import get_route_for_model
from .permissions import resolve_permission


#
# View Mixins
#


class ContentTypePermissionRequiredMixin(AccessMixin):
    """
    Similar to Django's built-in PermissionRequiredMixin, but extended to check model-level permission assignments.
    This is related to ObjectPermissionRequiredMixin, except that is does not enforce object-level permissions,
    and fits within Nautobot's custom permission enforcement system.

    additional_permissions: An optional iterable of statically declared permissions to evaluate in addition to those
                            derived from the object type
    """

    additional_permissions = []

    def get_required_permission(self):
        """
        Return the specific permission necessary to perform the requested action on an object.
        """
        raise NotImplementedError(f"{self.__class__.__name__} must implement get_required_permission()")

    def has_permission(self):
        user = self.request.user
        permission_required = self.get_required_permission()

        # Check that the user has been granted the required permission(s).
        if user.has_perms((permission_required, *self.additional_permissions)):
            return True

        return False

    def dispatch(self, request, *args, **kwargs):
        if not self.has_permission():
            return self.handle_no_permission()

        return super().dispatch(request, *args, **kwargs)


class AdminRequiredMixin(AccessMixin):
    """
    Allows access only to admin users.
    """

    def has_permission(self):
        return bool(
            self.request.user
            and self.request.user.is_active
            and (self.request.user.is_staff or self.request.user.is_superuser)
        )

    def dispatch(self, request, *args, **kwargs):
        if not self.has_permission():
            return self.handle_no_permission()

        return super().dispatch(request, *args, **kwargs)


class ObjectPermissionRequiredMixin(AccessMixin):
    """
    Similar to Django's built-in PermissionRequiredMixin, but extended to check for both model-level and object-level
    permission assignments. If the user has only object-level permissions assigned, the view's queryset is filtered
    to return only those objects on which the user is permitted to perform the specified action.

    additional_permissions: An optional iterable of statically declared permissions to evaluate in addition to those
                            derived from the object type
    """

    additional_permissions = []

    def get_required_permission(self):
        """
        Return the specific permission necessary to perform the requested action on an object.
        """
        raise NotImplementedError(f"{self.__class__.__name__} must implement get_required_permission()")

    def has_permission(self):
        user = self.request.user
        permission_required = self.get_required_permission()

        # Check that the user has been granted the required permission(s).
        if user.has_perms((permission_required, *self.additional_permissions)):

            # Update the view's QuerySet to filter only the permitted objects
            action = resolve_permission(permission_required)[1]
            self.queryset = self.queryset.restrict(user, action)

            return True

        return False

    def dispatch(self, request, *args, **kwargs):

        if not hasattr(self, "queryset"):
            raise ImproperlyConfigured(
                (
                    f"{self.__class__.__name__} has no queryset defined. "
                    "ObjectPermissionRequiredMixin may only be used on views which define a base queryset"
                )
            )

        if not self.has_permission():
            return self.handle_no_permission()

        return super().dispatch(request, *args, **kwargs)


class GetReturnURLMixin:
    """
    Provides logic for determining where a user should be redirected after processing a form.
    """

    default_return_url = None

    def get_return_url(self, request, obj=None):

        # First, see if `return_url` was specified as a query parameter or form data. Use this URL only if it's
        # considered safe.
        query_param = request.GET.get("return_url") or request.POST.get("return_url")
        if query_param and is_safe_url(url=query_param, allowed_hosts=request.get_host()):
            return query_param

        # Next, check if the object being modified (if any) has an absolute URL.
        # Note that the use of both `obj.present_in_database` and `obj.pk` is correct here because this conditional
        # handles all three of the create, update, and delete operations. When Django deletes an instance
        # from the DB, it sets the instance's PK field to None, regardless of the use of a UUID.
        if obj is not None and obj.present_in_database and obj.pk and hasattr(obj, "get_absolute_url"):
            return obj.get_absolute_url()

        # Fall back to the default URL (if specified) for the view.
        if self.default_return_url is not None:
            return reverse(self.default_return_url)

        # Attempt to dynamically resolve the list view for the object
        if hasattr(self, "queryset"):
            try:
                return reverse(get_route_for_model(self.queryset.model, "list"))
            except NoReverseMatch:
                pass

        # If all else fails, return home. Ideally this should never happen.
        return reverse("home")
