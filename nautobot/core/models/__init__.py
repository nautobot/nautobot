import uuid

from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.core.cache import cache
from django.db import models
from django.utils.functional import classproperty

from nautobot.utilities.querysets import RestrictedQuerySet


class BaseModel(models.Model):
    """
    Base model class that all models should inherit from.

    This abstract base provides globally common fields and functionality.

    Here we define the primary key to be a UUID field and set its default to
    automatically generate a random UUID value. Note however, this does not
    operate in the same way as a traditional auto incrementing field for which
    the value is issued by the database upon initial insert. In the case of
    the UUID field, Django creates the value upon object instantiation. This
    means the canonical pattern in Django of checking `self.pk is None` to tell
    if an object has been created in the actual database does not work because
    the object will always have the value populated prior to being saved to the
    database for the first time. An alternate pattern of checking `not self.present_in_database`
    can be used for the same purpose in most cases.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, unique=True, editable=False)

    objects = RestrictedQuerySet.as_manager()

    @property
    def present_in_database(self):
        """
        True if the record exists in the database, False if it does not.
        """
        return not self._state.adding

    @classproperty  # https://github.com/PyCQA/pylint-django/issues/240
    def _content_type(cls):  # pylint: disable=no-self-argument
        """
        Return the ContentType of the object, never cached.
        """
        return ContentType.objects.get_for_model(cls)

    @classproperty  # https://github.com/PyCQA/pylint-django/issues/240
    def _content_type_cache_key(cls):  # pylint: disable=no-self-argument
        """
        Return the cache key for the ContentType of the object.

        Necessary for use with _content_type_cached and management commands.
        """
        return f"{cls._meta.label_lower}._content_type"

    @classproperty  # https://github.com/PyCQA/pylint-django/issues/240
    def _content_type_cached(cls):  # pylint: disable=no-self-argument
        """
        Return the ContentType of the object, cached.
        """

        return cache.get_or_set(cls._content_type_cache_key, cls._content_type, settings.CONTENT_TYPE_CACHE_TIMEOUT)

    class Meta:
        abstract = True

    def validated_save(self, *args, **kwargs):
        """
        Perform model validation during instance save.

        This is a convenience method that first calls `self.full_clean()` and then `self.save()`
        which in effect enforces model validation prior to saving the instance, without having
        to manually make these calls seperately. This is a slight departure from Django norms,
        but is intended to offer an optional, simplified interface for performing this common
        workflow. The intended use is for user defined Jobs and scripts run via the `nbshell`
        command.
        """
        self.full_clean()
        self.save(*args, **kwargs)
