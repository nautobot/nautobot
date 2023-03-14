import uuid
from urllib.parse import quote_plus

from django.contrib.contenttypes.models import ContentType
from django.db import models
from natural_keys import NaturalKeyModel, NaturalKeyModelManager
from natural_keys.models import extract_nested_key

from nautobot.core.models.querysets import RestrictedQuerySet


class BaseManager(NaturalKeyModelManager):
    def get_queryset(self):
        return self._queryset_class(self.model, using=self._db, hints=self._hints)

    def get_by_natural_key(self, *args):
        """
        Return the object corresponding to the provided natural key.

        (Extension of django-natural-keys implementation of this generic Django API.)
        """
        kwargs = self.natural_key_kwargs(*args)

        # Since kwargs already has __ lookups in it, we could just do "return self.get(**kwargs)"
        # But django-natural-keys wants to call each related model's get_by_natural_key in case it's overridden:
        for name, rel_to in self.model.get_natural_key_info():
            if not rel_to:
                # Not a related object, no processing needed
                continue

            # Extract natural key for related object
            try:
                nested_key = extract_nested_key(kwargs, rel_to, name)
            except AttributeError:
                # Handle case where rel_to isn't a NaturalKeyModel, e.g. ContentType
                nested_key = []
                for key in kwargs.keys():
                    if key.startswith(f"{name}__"):
                        nested_key.append(kwargs[key])
                if all(key is None for key in nested_key):
                    nested_key = None

            if nested_key:
                # Update kwargs with related object
                try:
                    kwargs[name] = rel_to.objects.get_by_natural_key(*nested_key)
                except rel_to.DoesNotExist as exc:
                    raise self.model.DoesNotExist() from exc
            else:
                kwargs[name] = None

        return self.get(**kwargs)


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

    objects = BaseManager.from_queryset(RestrictedQuerySet)()

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
        workflow. The intended use is for user defined Jobs and scripts run via the `nautobot-server nbshell`
        command.
        """
        self.full_clean()
        self.save()

    def natural_key(self):
        """
        Smarter default implementation of natural key construction.

        1. Handles nullable foreign keys (https://github.com/wq/django-natural-keys/issues/18)
        2. Handles variadic natural-keys (e.g. Location model - [name, parent__name, parent__parent__name, ...].)
        """
        vals = []
        for name_list in [name.split("__") for name in self.get_natural_key_fields()]:
            val = self
            for attr_name in name_list:
                val = getattr(val, attr_name)
                if val is None:
                    break
            vals.append(val)
        # Strip trailing Nones from vals
        cleaned_vals = []
        for val in reversed(vals):
            if val is None and not cleaned_vals:
                continue
            cleaned_vals = [val] + cleaned_vals
        return cleaned_vals

    natural_key_separator = "/"

    @property
    def natural_key_slug(self):
        """Less naive implementation than django-natural-keys provides by default, based around URL percent-encoding."""
        return self.natural_key_separator.join(
            quote_plus(str(value) if value is not None else "\0") for value in self.natural_key()
        )

    @classmethod
    def get_natural_key_def(cls):
        """
        Extend django-natural-keys implementation to recognize that UUIDFields are not relevant to the natural key.
        """
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

        raise Exception(
            f"Unable to identify an intrinsic natural-key definition for {cls.__name__}. "
            "If there isn't at least one UniqueConstraint, unique_together, or field with unique=True, "
            "you probably need to explicitly declare a natural-key for this model."
        )

    @classmethod
    def get_natural_key_fields(cls):
        """
        Determine actual natural key field list, incorporating the natural keys of related objects as needed.

        Extends django-natural-key's implementation to handle related objects without natural keys (e.g. ContentType).
        """
        natural_key_fields = []
        for name, rel_to in cls.get_natural_key_info():
            if not rel_to:
                natural_key_fields.append(name)
            else:
                try:
                    nested_key = rel_to.get_natural_key_fields()
                except AttributeError:
                    if rel_to == ContentType:
                        nested_key = ["app_label", "model"]
                    else:
                        raise
                natural_key_fields.extend([name + "__" + nname for nname in nested_key])
        return natural_key_fields
