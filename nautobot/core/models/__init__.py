import uuid

from django.db import models, IntegrityError, transaction
from django.db.models.utils import resolve_callables

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
