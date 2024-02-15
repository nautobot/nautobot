import contextvars
import logging
from uuid import UUID

from django.db import transaction
from django.db.models import Manager
from taggit.managers import _TaggableManager

logger = logging.getLogger(__name__)


class BaseManager(Manager):
    """
    Base manager class corresponding to BaseModel and RestrictedQuerySet.

    Adds built-in natural key support, loosely based on `django-natural-keys`.
    """

    def bulk_create(
        self,
        objs,
        batch_size=None,
        ignore_conflicts=False,
        change_log=False
    ):
        if not change_log:
            return super().bulk_create(objs, batch_size, ignore_conflicts)
        from nautobot.extras.choices import ObjectChangeActionChoices
        from nautobot.extras.models import ObjectChange, ChangeLoggedModel
        with transaction.atomic():
            created_objects = super().bulk_create(
                objs=objs,
                batch_size=batch_size,
                ignore_conflicts=ignore_conflicts,
            )
            object_changes = []
            for obj in created_objects:
                if not isinstance(obj, ChangeLoggedModel):
                    continue
                object_change = obj.to_objectchange(action=ObjectChangeActionChoices.ACTION_CREATE)
                object_change.request_id = obj.pk  # Hack, should probably be a common id for all the objects
                object_changes.append(object_change)
            ObjectChange.objects.bulk_create(object_changes, batch_size=batch_size, change_log=False)
        return created_objects

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
