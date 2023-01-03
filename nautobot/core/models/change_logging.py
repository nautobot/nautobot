from django.db import models
from django.urls import NoReverseMatch, reverse

from nautobot.core.utils import get_route_for_model, serialize_object, serialize_object_v2

#
# Change logging
#


class ChangeLoggedModel(models.Model):
    """
    An abstract model which adds fields to store the creation and last-updated times for an object. Both fields can be
    null to facilitate adding these fields to existing instances via a database migration.
    """

    created = models.DateField(auto_now_add=True, blank=True, null=True)
    last_updated = models.DateTimeField(auto_now=True, blank=True, null=True)

    class Meta:
        abstract = True

    def to_objectchange(self, action, *, related_object=None, object_data_extra=None, object_data_exclude=None):
        """
        Return a new ObjectChange representing a change made to this object. This will typically be called automatically
        by ChangeLoggingMiddleware.
        """

        from nautobot.extras.constants import CHANGELOG_MAX_OBJECT_REPR
        from nautobot.extras.models import ObjectChange

        return ObjectChange(
            changed_object=self,
            object_repr=str(self)[:CHANGELOG_MAX_OBJECT_REPR],
            action=action,
            object_data=serialize_object(self, extra=object_data_extra, exclude=object_data_exclude),
            object_data_v2=serialize_object_v2(self),
            related_object=related_object,
        )

    def get_changelog_url(self):
        """Return the changelog URL for this object."""
        route = get_route_for_model(self, "changelog")

        # Iterate the pk-like fields and try to get a URL, or return None.
        fields = ["pk", "slug"]
        for field in fields:
            if not hasattr(self, field):
                continue

            try:
                return reverse(route, kwargs={field: getattr(self, field)})
            except NoReverseMatch:
                continue

        return None
