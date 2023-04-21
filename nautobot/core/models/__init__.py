import uuid

from django.db import models
from django.urls import NoReverseMatch, reverse

from nautobot.core.models.querysets import RestrictedQuerySet
from nautobot.core.utils.lookup import get_route_for_model


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

    def get_absolute_url(self):
        """
        Return the canonical URL for this object.
        """

        # Iterate the pk-like fields and try to get a URL, or return None.
        fields = ["pk", "slug"]  # TODO: Eventually all PKs
        actions = ["retrieve", "detail", ""]  # TODO: Eventually all retrieve

        for field in fields:
            if not hasattr(self, field):
                continue

            for action in actions:
                route = get_route_for_model(self, action)

                try:
                    return reverse(route, kwargs={field: getattr(self, field)})
                except NoReverseMatch:
                    continue

        return AttributeError(f"Cannot find a URL for {self} ({self._meta.app_label}.{self._meta.model_name})")

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
