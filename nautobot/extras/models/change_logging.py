from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.core.serializers.json import DjangoJSONEncoder
from django.db import models
from django.urls import reverse

from nautobot.utilities.utils import serialize_object
from nautobot.core.models import BaseModel
from nautobot.extras.choices import *


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

    def to_objectchange(self, action):
        """
        Return a new ObjectChange representing a change made to this object. This will typically be called automatically
        by ChangeLoggingMiddleware.
        """
        return ObjectChange(
            changed_object=self,
            object_repr=str(self),
            action=action,
            object_data=serialize_object(self),
        )


class ObjectChange(BaseModel):
    """
    Record a change to an object and the user account associated with that change. A change record may optionally
    indicate an object related to the one being changed. For example, a change to an interface may also indicate the
    parent device. This will ensure changes made to component models appear in the parent model's changelog.
    """

    time = models.DateTimeField(auto_now_add=True, editable=False, db_index=True)
    user = models.ForeignKey(
        to=settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="changes",
        blank=True,
        null=True,
    )
    user_name = models.CharField(max_length=150, editable=False)
    request_id = models.UUIDField(editable=False)
    action = models.CharField(max_length=50, choices=ObjectChangeActionChoices)
    changed_object_type = models.ForeignKey(to=ContentType, on_delete=models.PROTECT, related_name="+")
    changed_object_id = models.UUIDField()
    changed_object = GenericForeignKey(ct_field="changed_object_type", fk_field="changed_object_id")
    related_object_type = models.ForeignKey(
        to=ContentType,
        on_delete=models.PROTECT,
        related_name="+",
        blank=True,
        null=True,
    )
    related_object_id = models.UUIDField(blank=True, null=True)
    related_object = GenericForeignKey(ct_field="related_object_type", fk_field="related_object_id")
    object_repr = models.CharField(max_length=200, editable=False)
    object_data = models.JSONField(encoder=DjangoJSONEncoder, editable=False)

    csv_headers = [
        "time",
        "user",
        "user_name",
        "request_id",
        "action",
        "changed_object_type",
        "changed_object_id",
        "related_object_type",
        "related_object_id",
        "object_repr",
        "object_data",
    ]

    class Meta:
        ordering = ["-time"]

    def __str__(self):
        return "{} {} {} by {}".format(
            self.changed_object_type,
            self.object_repr,
            self.get_action_display().lower(),
            self.user_name,
        )

    def save(self, *args, **kwargs):

        # Record the user's name and the object's representation as static strings
        if not self.user_name:
            if self.user:
                self.user_name = self.user.username
            else:
                self.user_name = "Undefined"

        if not self.object_repr:
            self.object_repr = str(self.changed_object)

        return super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("extras:objectchange", args=[self.pk])

    def to_csv(self):
        return (
            self.time,
            self.user,
            self.user_name,
            self.request_id,
            self.get_action_display(),
            self.changed_object_type,
            self.changed_object_id,
            self.related_object_type,
            self.related_object_id,
            self.object_repr,
            self.object_data,
        )

    def get_action_class(self):
        return ObjectChangeActionChoices.CSS_CLASSES.get(self.action)
