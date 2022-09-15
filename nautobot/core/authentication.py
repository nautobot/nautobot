import logging
from collections import defaultdict

from django.conf import settings
from django.contrib.auth.backends import (
    ModelBackend,
    RemoteUserBackend as _RemoteUserBackend,
)
from django.contrib.auth.models import Group
from django.db.models import Q

from nautobot.users.models import ObjectPermission
from nautobot.utilities.permissions import (
    permission_is_exempt,
    resolve_permission,
    resolve_permission_ct,
)

logger = logging.getLogger("nautobot.authentication")


class ObjectPermissionBackend(ModelBackend):
    def get_all_permissions(self, user_obj, obj=None):
        if not user_obj.is_active or user_obj.is_anonymous:
            return {}
        if not hasattr(user_obj, "_object_perm_cache"):
            user_obj._object_perm_cache = self.get_object_permissions(user_obj)
        return user_obj._object_perm_cache

    def get_object_permissions(self, user_obj):
        """
        Return all permissions granted to the user by an ObjectPermission.
        """
        # Retrieve all assigned and enabled ObjectPermissions
        # v2 TODO(jathan): Replace prefetch_related with select_related
        object_permissions = ObjectPermission.objects.filter(
            Q(users=user_obj) | Q(groups__user=user_obj), enabled=True
        ).prefetch_related("object_types")

        # Create a dictionary mapping permissions to their constraints
        perms = defaultdict(list)
        for obj_perm in object_permissions:
            for object_type in obj_perm.object_types.all():
                for action in obj_perm.actions:
                    perm_name = f"{object_type.app_label}.{action}_{object_type.model}"
                    perms[perm_name].extend(obj_perm.list_constraints())

        return perms

    def has_perm(self, user_obj, perm, obj=None):
        if perm == "is_staff":
            return user_obj.is_active and (user_obj.is_staff or user_obj.is_superuser)

        app_label, _action, model_name = resolve_permission(perm)

        if app_label == "users" and model_name == "admingroup":
            perm = perm.replace("users", "auth").replace("admingroup", "group")

        # Superusers implicitly have all permissions
        if user_obj.is_active and user_obj.is_superuser:
            return True

        # Permission is exempt from enforcement (i.e. listed in EXEMPT_VIEW_PERMISSIONS)
        if permission_is_exempt(perm):
            return True

        # Handle inactive/anonymous users
        if not user_obj.is_active or user_obj.is_anonymous:
            return False

        # If no applicable ObjectPermissions have been created for this user/permission, deny permission
        if perm not in self.get_all_permissions(user_obj):
            return False

        # If no object has been specified, grant permission. (The presence of a permission in this set tells
        # us that the user has permission for *some* objects, but not necessarily a specific object.)
        if obj is None:
            return True

        # Sanity check: Ensure that the requested permission applies to the specified object
        model = obj._meta.model
        if model._meta.label_lower != ".".join((app_label, model_name)):
            raise ValueError(f"Invalid permission {perm} for model {model}")

        # Compile a query filter that matches all instances of the specified model
        obj_perm_constraints = self.get_all_permissions(user_obj)[perm]
        constraints = Q()
        for perm_constraints in obj_perm_constraints:
            if perm_constraints:
                constraints |= Q(**perm_constraints)
            else:
                # Found ObjectPermission with null constraints; allow model-level access
                constraints = Q()
                break

        # Permission to perform the requested action on the object depends on whether the specified object matches
        # the specified constraints. Note that this check is made against the *database* record representing the object,
        # not the instance itself.
        return model.objects.filter(constraints, pk=obj.pk).exists()


class RemoteUserBackend(_RemoteUserBackend):
    """
    Custom implementation of Django's RemoteUserBackend which provides configuration hooks for basic customization.
    """

    @property
    def create_unknown_user(self):
        return settings.REMOTE_AUTH_AUTO_CREATE_USER

    def has_perm(self, user_obj, perm, obj=None):
        return False


def assign_groups_to_user(user, groups=None):
    """
    Assign a specified user a given list of groups.

    :param user: The user to assign the permissions
    :param group: A list of group names to add the user to
    """
    if groups is None:
        groups = []
    group_list = []
    for name in groups:
        try:
            group_list.append(Group.objects.get(name=name))
        except Group.DoesNotExist:
            logging.error(f"Could not assign group {name} to remotely-authenticated user {user}: Group not found")
    if group_list:
        user.groups.add(*group_list)
        logger.debug(f"Assigned groups to remotely-authenticated user {user}: {group_list}")


def assign_permissions_to_user(user, permissions=None):
    """
    Assign a specified user a given set of permissions.

    :param user: The user to assign the permissions
    :param permissions: A dictionary of permissions, with the permission name <app_label>.<action>_<model> as the key and constraints as values
    """
    if permissions is None:
        permissions = {}
    permissions_list = []
    for permission_name, constraints in permissions.items():
        try:
            object_type, action = resolve_permission_ct(permission_name)
            # TODO: Merge multiple actions into a single ObjectPermission per content type
            obj_perm = ObjectPermission(name=permission_name, actions=[action], constraints=constraints)
            obj_perm.save()
            obj_perm.users.add(user)
            obj_perm.object_types.add(object_type)
            permissions_list.append(permission_name)
        except ValueError:
            logging.error(
                f"Invalid permission name: '{permission_name}'. Permissions must be in the form "
                "<app>.<action>_<model>. (Example: dcim.add_site)"
            )
    if permissions_list:
        logger.debug(f"Assigned permissions to remotely-authenticated user {user}: {permissions_list}")
