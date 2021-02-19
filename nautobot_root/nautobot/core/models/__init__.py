from django.db import models

from nautobot.utilities.querysets import RestrictedQuerySet


class BaseModel(models.Model):
    """
    Base model class that all models should inhert from.

    This abstract base provides globally common fields and functionality.
    """
    objects = RestrictedQuerySet.as_manager()

    class Meta:
        abstract = True
