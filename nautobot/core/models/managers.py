import logging
import uuid

from django.db import transaction
from django.db.models import Manager
from taggit.managers import _TaggableManager

logger = logging.getLogger(__name__)


class BaseManager(Manager):
    """
    Base manager class corresponding to BaseModel and RestrictedQuerySet.

    Adds built-in natural key support, loosely based on `django-natural-keys`.
    """

    def bulk_create_with_changelog(
        self,
        objs,
        batch_size=None,
        ignore_conflicts=False,
        user=None,
        request_id=None,
    ):
        """
        Implementation for `bulk_create` that automatically creates `ObjectChange` objects.

        Args:
            objs: Objects to bulk create, see Django docs.
            batch_size: Size of `INSERT` batches, see Django docs.
            ignore_conflicts: Ignore conflicts with existing rows, see Django docs.
            user: User to associate the change log objects with, defaults to None.
            request_id: Request ID for the change log objects, defaults to a random UUID for all objects created.

        Returns: A tuple of the form `created_object, created_object_change_objects`.
        """
        # Resolve circular imports
        from nautobot.extras.choices import ObjectChangeActionChoices
        from nautobot.extras.models import ChangeLoggedModel, ObjectChange

        if not issubclass(self.model, ChangeLoggedModel):
            raise ValueError(
                "`bulk_create_with_changelog` can only be used on classes that inherit from `ChangeLoggedModel`."
            )

        # If not request ID was passed, generate a random one. This merely needs to be consistent over all the objects
        # so that they are groupable.
        request_id = request_id or uuid.uuid4()
        with transaction.atomic():
            created_objects = super().bulk_create(
                objs=objs,
                batch_size=batch_size,
                ignore_conflicts=ignore_conflicts,
            )
            object_changes = []
            for obj in created_objects:
                object_change = obj.to_objectchange(action=ObjectChangeActionChoices.ACTION_CREATE)
                object_change.request_id = request_id
                object_change.user = user
                object_changes.append(object_change)
            created_change_log_objects = ObjectChange.objects.bulk_create(object_changes, batch_size=batch_size)
        return created_objects, created_change_log_objects

    def get_by_natural_key(self, *args):
        """
        Return the object corresponding to the provided natural key.

        Generic implementation that depends on the model being a BaseModel subclass or otherwise implementing our
        `natural_key_field_lookups` property API. Loosely based on implementation from `django-natural-keys`.
        """
        if len(args) == 1 and isinstance(args[0], (list, tuple)):
            logger.warning(
                "%s.objects.get_by_natural_key() was called with a single %s as its args, "
                "instead of a list of individual args. Did you forget a '*' in your call?",
                self.model.__name__,
                type(args[0]).__name__,
            )
            args = args[0]

        base_kwargs = self.model.natural_key_args_to_kwargs(args)

        # django-natural-keys had a pattern where it would replace nested related field lookups
        # (parent__namespace__name="Global", parent__prefix="10.0.0.0/8") with calls to get_by_natural_key()
        # (parent=Prefix.objects.get_by_natural_key("Global", "10.0.0.0/8")).
        # We initially followed this pattern, but it had the downside that an object's natural key could therefore
        # **only** reference related objects by their own natural keys, which is unnecessarily rigid.
        # We instead just do the simple thing and let Django follow the nested lookups as appropriate:
        return self.get(**base_kwargs)


class TagsManager(_TaggableManager, BaseManager):
    """Manager class for model 'tags' fields."""
