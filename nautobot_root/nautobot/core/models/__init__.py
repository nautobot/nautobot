import uuid

from django.db import models

from nautobot.utilities.querysets import RestrictedQuerySet


class BaseModel(models.Model):
    """
    Base model class that all models should inhert from.

    This abstract base provides globally common fields and functionality.

    Here we define the primary key to be a UUID field and set its default to
    automatically generate a random UUID value. Note however, this does not
    operate in the same way as a traditional auto incrementing field for which
    the value is issued by the database upon initial insert. In the case of
    the UUID field, Django creates the value upon object instantiation. This
    means the canonical pattern in Django of checking `self.pk is None` to tell
    if an object has been created in the actual database does not work because
    the object will always have the value populated prior to being saved to the
    database for the first time. An alternate pattern of checking `self._state.adding`
    can be used for the same purpose in most cases.
    """
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        unique=True,
        editable=False
    )

    objects = RestrictedQuerySet.as_manager()

    class Meta:
        abstract = True
