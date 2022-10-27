import uuid

from django.db import models
from natural_keys import NaturalKeyModel, NaturalKeyModelManager

from nautobot.utilities.querysets import RestrictedQuerySet


class BaseManager(NaturalKeyModelManager):
    def get_queryset(self):
        return RestrictedQuerySet(self.model, using=self._db)

    def restrict(self, user, action="view"):
        return self.get_queryset().restrict(user, action=action)


class BaseModel(NaturalKeyModel):
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

    # objects = RestrictedQuerySet.as_manager()
    objects = BaseManager()

    @property
    def present_in_database(self):
        """
        True if the record exists in the database, False if it does not.
        """
        return not self._state.adding

    class Meta:
        abstract = True

    def validated_save(self):
        """
        Perform model validation during instance save.

        This is a convenience method that first calls `self.full_clean()` and then `self.save()`
        which in effect enforces model validation prior to saving the instance, without having
        to manually make these calls seperately. This is a slight departure from Django norms,
        but is intended to offer an optional, simplified interface for performing this common
        workflow. The indended use is for user defined Jobs and scripts run via the `nbshell`
        command.
        """
        self.full_clean()
        self.save()

    @classmethod
    def get_natural_key_def(cls):
        if hasattr(cls, "_natural_key"):
            return cls._natural_key

        for constraint in cls._meta.constraints:
            if isinstance(constraint, models.UniqueConstraint):
                return constraint.fields

        if cls._meta.unique_together:
            return cls._meta.unique_together[0]

        unique = [
            f
            for f in cls._meta.fields
            if f.unique
            and f.__class__.__name__
            not in [
                "AutoField",
                "BigAutoField",
                "UUIDField",
            ]
        ]
        if unique:
            return (unique[0].name,)

        raise Exception("Add a UniqueConstraint to use natural-keys")
