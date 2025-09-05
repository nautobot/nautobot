import binascii
import os

from django.conf import settings
from django.contrib.auth.models import AbstractUser, Group, UserManager as UserManager_
from django.contrib.contenttypes.models import ContentType
from django.core.serializers.json import DjangoJSONEncoder
from django.core.validators import MinLengthValidator
from django.db import models
from django.db.models import Q
from django.utils import timezone

from nautobot.core.constants import CHARFIELD_MAX_LENGTH
from nautobot.core.models import BaseManager, BaseModel, CompositeKeyQuerySetMixin
from nautobot.core.models.fields import JSONArrayField
from nautobot.core.utils.data import flatten_dict
from nautobot.extras.models.change_logging import ChangeLoggedModel

__all__ = (
    "AdminGroup",
    "ObjectPermission",
    "Token",
    "User",
)


#
# Custom User model
#


class UserQuerySet(CompositeKeyQuerySetMixin, models.QuerySet):
    """
    Add support for composite-keys to the User queryset.

    Note that this is *NOT* based around RestrictedQuerySet.
    """


class UserManager(BaseManager, UserManager_):
    """
    Natural-key subclass of Django's UserManager.
    """

    def get_queryset(self):
        return UserQuerySet(self.model, using=self._db)


class User(BaseModel, AbstractUser):
    """
    Nautobot implements its own User model to suport several specific use cases.

    This model also implements the user configuration (preferences) data store functionality.
    """

    config_data = models.JSONField(encoder=DjangoJSONEncoder, default=dict, blank=True)
    default_saved_views = models.ManyToManyField(
        to="extras.SavedView",
        related_name="users",
        through="extras.UserSavedViewAssociation",
        through_fields=("user", "saved_view"),
        blank=True,
        verbose_name="user-specific default saved views",
        help_text="User specific default saved views",
    )

    # TODO: we don't currently have a general "Users" guide.
    documentation_static_path = "docs/development/core/user-preferences.html"
    objects = UserManager()
    is_metadata_associable_model = False

    class Meta:
        db_table = "auth_user"
        ordering = ["username"]

    def get_config(self, path, default=None):
        """
        Retrieve a configuration parameter specified by its dotted path. Example:

            user.get_config('foo.bar.baz')

        :param path: Dotted path to the configuration key. For example, 'foo.bar' returns self.config_data['foo']['bar'].
        :param default: Default value to return for a nonexistent key (default: None).
        """
        d = self.config_data
        keys = path.split(".")

        # Iterate down the hierarchy, returning the default value if any invalid key is encountered
        for key in keys:
            if isinstance(d, dict) and key in d:
                d = d.get(key)
            else:
                return default

        return d

    def all_config(self):
        """
        Return a dictionary of all defined keys and their values.
        """
        return flatten_dict(self.config_data)

    def set_config(self, path, value, commit=False):
        """
        Define or overwrite a configuration parameter. Example:

            user.set_config('foo.bar.baz', 123)

        Leaf nodes (those which are not dictionaries of other nodes) cannot be overwritten as dictionaries. Similarly,
        branch nodes (dictionaries) cannot be overwritten as single values. (A TypeError exception will be raised.) In
        both cases, the existing key must first be cleared. This safeguard is in place to help avoid inadvertently
        overwriting the wrong key.

        :param path: Dotted path to the configuration key. For example, 'foo.bar' sets self.config_data['foo']['bar'].
        :param value: The value to be written. This can be any type supported by JSON.
        :param commit: If true, the UserConfig instance will be saved once the new value has been applied.
        """
        d = self.config_data
        keys = path.split(".")

        # Iterate through the hierarchy to find the key we're setting. Raise TypeError if we encounter any
        # interim leaf nodes (keys which do not contain dictionaries).
        for i, key in enumerate(keys[:-1]):
            if key in d and isinstance(d[key], dict):
                d = d[key]
            elif key in d:
                err_path = ".".join(path.split(".")[: i + 1])
                raise TypeError(f"Key '{err_path}' is a leaf node; cannot assign new keys")
            else:
                d = d.setdefault(key, {})

        # Set a key based on the last item in the path. Raise TypeError if attempting to overwrite a non-leaf node.
        key = keys[-1]
        if key in d and isinstance(d[key], dict):
            raise TypeError(f"Key '{path}' has child keys; cannot assign a value")
        else:
            d[key] = value

        if commit:
            self.save()

    set_config.alters_data = True

    def clear_config(self, path, commit=False):
        """
        Delete a configuration parameter specified by its dotted path. The key and any child keys will be deleted.
        Example:

            user.clear_config('foo.bar.baz')

        Invalid keys will be ignored silently.

        :param path: Dotted path to the configuration key. For example, 'foo.bar' deletes self.config_data['foo']['bar'].
        :param commit: If true, the UserConfig instance will be saved once the new value has been applied.
        """
        d = self.config_data
        keys = path.split(".")

        for key in keys[:-1]:
            if key not in d:
                break
            if isinstance(d[key], dict):
                d = d[key]

        key = keys[-1]
        d.pop(key, None)  # Avoid a KeyError on invalid keys

        if commit:
            self.save()

    clear_config.alters_data = True


#
# Proxy models for admin
#


class AdminGroup(Group):
    """
    Proxy contrib.auth.models.Group for the admin UI
    """

    class Meta:
        verbose_name = "Group"
        proxy = True


#
# REST API
#


class Token(BaseModel):
    """
    An API token used for user authentication. This extends the stock model to allow each user to have multiple tokens.
    It also supports setting an expiration time and toggling write ability.
    """

    user = models.ForeignKey(to=settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="tokens")
    created = models.DateTimeField(auto_now_add=True)
    expires = models.DateTimeField(blank=True, null=True)
    key = models.CharField(max_length=40, unique=True, validators=[MinLengthValidator(40)])
    write_enabled = models.BooleanField(default=True, help_text="Permit create/update/delete operations using this key")
    description = models.CharField(max_length=CHARFIELD_MAX_LENGTH, blank=True)

    documentation_static_path = "docs/user-guide/platform-functionality/users/token.html"
    natural_key_field_names = ["pk"]  # default would be `["key"]`, which is obviously not ideal!
    is_metadata_associable_model = False

    class Meta:
        ordering = ["created"]

    def __str__(self):
        # Only display the last 24 bits of the token to avoid accidental exposure.
        return f"{self.key[-6:]} ({self.user})"

    def save(self, *args, **kwargs):
        if not self.key:
            self.key = self.generate_key()
        return super().save(*args, **kwargs)

    @staticmethod
    def generate_key():
        # Generate a random 160-bit key expressed in hexadecimal.
        return binascii.hexlify(os.urandom(20)).decode()

    @property
    def is_expired(self):
        if self.expires is None or timezone.now() < self.expires:
            return False
        return True


#
# Permissions
#


class ObjectPermission(BaseModel, ChangeLoggedModel):
    """
    A mapping of view, add, change, and/or delete permission for users and/or groups to an arbitrary set of objects
    identified by ORM query parameters.
    """

    name = models.CharField(max_length=CHARFIELD_MAX_LENGTH, unique=True)
    description = models.CharField(max_length=CHARFIELD_MAX_LENGTH, blank=True)
    enabled = models.BooleanField(default=True)
    # TODO: Remove pylint disable after issue is resolved (see: https://github.com/PyCQA/pylint/issues/7381)
    # pylint: disable=unsupported-binary-operation
    object_types = models.ManyToManyField(
        to=ContentType,
        limit_choices_to=Q(
            ~Q(
                app_label__in=[
                    "admin",
                    "auth",
                    "contenttypes",
                    "sessions",
                    "taggit",
                    "users",
                ]
            )
            | Q(app_label="admin", model__in=["logentry"])
            | Q(app_label="auth", model__in=["group"])
            | Q(app_label="users", model__in=["objectpermission", "token", "user"])
        ),
        related_name="object_permissions",
    )
    # pylint: enable=unsupported-binary-operation
    groups = models.ManyToManyField(to=Group, blank=True, related_name="object_permissions")
    users = models.ManyToManyField(to=settings.AUTH_USER_MODEL, blank=True, related_name="object_permissions")
    actions = JSONArrayField(
        base_field=models.CharField(max_length=30),
        help_text="The list of actions granted by this permission",
    )
    constraints = models.JSONField(
        encoder=DjangoJSONEncoder,
        blank=True,
        null=True,
        help_text="Queryset filter matching the applicable objects of the selected type(s)",
    )

    documentation_static_path = "docs/user-guide/platform-functionality/users/objectpermission.html"
    is_metadata_associable_model = False

    class Meta:
        ordering = ["name"]
        verbose_name = "permission"

    def __str__(self):
        return self.name

    def list_constraints(self):
        """
        Return all constraint sets as a list (even if only a single set is defined).
        """
        if not isinstance(self.constraints, list):
            return [self.constraints]
        return self.constraints
