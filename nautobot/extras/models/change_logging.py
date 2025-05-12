from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.core.serializers.json import DjangoJSONEncoder
from django.db import models
from django.urls import NoReverseMatch, reverse

from nautobot.core.celery import NautobotKombuJSONEncoder
from nautobot.core.models import BaseModel
from nautobot.core.models.utils import serialize_object, serialize_object_v2
from nautobot.core.utils.data import shallow_compare_dict
from nautobot.core.utils.lookup import get_route_for_model
from nautobot.extras.choices import ObjectChangeActionChoices, ObjectChangeEventContextChoices
from nautobot.extras.constants import CHANGELOG_MAX_CHANGE_CONTEXT_DETAIL, CHANGELOG_MAX_OBJECT_REPR
from nautobot.extras.utils import extras_features

#
# Change logging
#


class ChangeLoggedModel(models.Model):
    """
    An abstract model which adds fields to store the creation and last-updated times for an object. Both fields can be
    null to facilitate adding these fields to existing instances via a database migration.
    """

    created = models.DateTimeField(auto_now_add=True, blank=True, null=True)
    last_updated = models.DateTimeField(auto_now=True, blank=True, null=True)

    class Meta:
        abstract = True

    def to_objectchange(self, action, *, related_object=None, object_data_extra=None, object_data_exclude=None):
        """
        Return a new ObjectChange representing a change made to this object, or None if the object shouldn't be logged.

        This will typically be called automatically by ChangeLoggingMiddleware.
        """
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


@extras_features("graphql")
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
        related_name="object_changes",
        blank=True,
        null=True,
    )
    user_name = models.CharField(max_length=150, editable=False, db_index=True)
    request_id = models.UUIDField(editable=False, db_index=True)
    action = models.CharField(max_length=50, choices=ObjectChangeActionChoices)
    changed_object_type = models.ForeignKey(to=ContentType, on_delete=models.SET_NULL, null=True, related_name="+")
    changed_object_id = models.UUIDField(db_index=True)
    changed_object = GenericForeignKey(ct_field="changed_object_type", fk_field="changed_object_id")
    change_context = models.CharField(
        max_length=50,
        choices=ObjectChangeEventContextChoices,
        editable=False,
        db_index=True,
    )
    change_context_detail = models.CharField(max_length=CHANGELOG_MAX_CHANGE_CONTEXT_DETAIL, blank=True, editable=False)
    related_object_type = models.ForeignKey(
        to=ContentType,
        on_delete=models.SET_NULL,
        related_name="+",
        blank=True,
        null=True,
    )
    # todoindex:
    related_object_id = models.UUIDField(blank=True, null=True)
    related_object = GenericForeignKey(ct_field="related_object_type", fk_field="related_object_id")
    object_repr = models.CharField(max_length=CHANGELOG_MAX_OBJECT_REPR, editable=False)
    object_data = models.JSONField(encoder=DjangoJSONEncoder, editable=False)
    object_data_v2 = models.JSONField(encoder=NautobotKombuJSONEncoder, editable=False, null=True, blank=True)

    documentation_static_path = "docs/user-guide/platform-functionality/change-logging.html"
    natural_key_field_names = ["pk"]

    class Meta:
        ordering = ["-time"]
        get_latest_by = "time"
        # [request_id, changed_object_type, changed_object_id] is not sufficient to uniquely identify an ObjectChange,
        # as a single bulk-create or bulk-edit REST API request may modify the same object multiple times, such as in
        # the case of creating CircuitTerminations for both ends of a single Circuit in a single request.
        unique_together = [
            ["time", "request_id", "changed_object_type", "changed_object_id"],
        ]
        indexes = [
            models.Index(
                name="extras_objectchange_triple_idx",
                fields=["request_id", "changed_object_type_id", "changed_object_id"],
            ),
            models.Index(
                name="extras_objectchange_double_idx",
                fields=["request_id", "changed_object_type_id"],
            ),
            models.Index(
                name="extras_objectchange_rtime_idx",
                fields=["-time"],
            ),
            models.Index(
                name="changed_object_idx",
                fields=["changed_object_type", "changed_object_id"],
            ),
            models.Index(
                name="related_object_idx",
                fields=["related_object_type", "related_object_id"],
            ),
            models.Index(
                name="user_changed_object_idx",
                fields=["user", "changed_object_type", "changed_object_id"],
            ),
            models.Index(
                name="user_name_changed_object_idx",
                fields=["user_name", "changed_object_type", "changed_object_id"],
            ),
        ]

    def __str__(self):
        return f"{self.changed_object_type} {self.object_repr} {self.get_action_display().lower()} by {self.user_name}"

    def save(self, *args, **kwargs):
        # Record the user's name and the object's representation as static strings
        if not self.user_name:
            if self.user:
                self.user_name = self.user.username
            else:
                self.user_name = "Undefined"

        if not self.object_repr:
            self.object_repr = str(self.changed_object)[:CHANGELOG_MAX_OBJECT_REPR]

        return super().save(*args, **kwargs)

    def get_action_class(self):
        return ObjectChangeActionChoices.CSS_CLASSES.get(self.action)

    def get_next_change(self, user=None, only=None):
        """Return next change for this changed object, optionally restricting by user view permission"""
        related_changes = self.get_related_changes(user=user)
        if only:
            related_changes = related_changes.only(*only)
        return related_changes.filter(time__gt=self.time).order_by("time").first()

    def get_prev_change(self, user=None, only=None):
        """Return previous change for this changed object, optionally restricting by user view permission"""
        related_changes = self.get_related_changes(user=user)
        if only:
            related_changes = related_changes.only(*only)
        return related_changes.filter(time__lt=self.time).order_by("-time").first()

    def get_related_changes(self, user=None, permission="view"):
        """Return queryset of all ObjectChanges for this changed object, excluding this ObjectChange"""
        related_changes = ObjectChange.objects.filter(
            changed_object_type=self.changed_object_type,
            changed_object_id=self.changed_object_id,
        ).exclude(pk=self.pk)
        if user is not None:
            return related_changes.restrict(user, permission)
        return related_changes

    def get_snapshots(self, pre_object_data=None, pre_object_data_v2=None):
        """
        Return a dictionary with the changed object's serialized data before and after this change
        occurred and a key with a shallow diff of those dictionaries.

        Returns:
        {
            "prechange": dict(),
            "postchange": dict(),
            "differences": {
                "removed": dict(),
                "added": dict(),
            }
        }
        """
        prechange = None
        postchange = None
        prior_change = None

        # Populate the prechange field, create actions do not need to have a prechange field
        if self.action != ObjectChangeActionChoices.ACTION_CREATE:
            prior_change = self.get_prev_change(only=["object_data_v2", "object_data"])
            # Deal with the cases where we are trying to capture an object deletion/update and there is no prior change record.
            # This can happen when the object is first created and the changelog for that object creation action is deleted.
            if prior_change is not None:
                prechange = prior_change.object_data_v2 or prior_change.object_data
            elif self.action == ObjectChangeActionChoices.ACTION_DELETE:
                prechange = self.object_data_v2 or self.object_data
            else:
                prechange = pre_object_data_v2 or pre_object_data

        # Populate the postchange field, delete actions do not need to have a postchange field
        if self.action != ObjectChangeActionChoices.ACTION_DELETE:
            postchange = self.object_data_v2
            if postchange is None:
                postchange = self.object_data

        if prechange and postchange:
            if self.object_data_v2 is None or (prior_change and prior_change.object_data_v2 is None):
                prechange = prior_change.object_data
                postchange = self.object_data
            diff_added = shallow_compare_dict(prechange, postchange, exclude=["last_updated"])
            diff_removed = {x: prechange.get(x) for x in diff_added}
        elif prechange and not postchange:
            diff_added, diff_removed = None, prechange
        else:
            diff_added, diff_removed = postchange, None

        return {
            "prechange": prechange,
            "postchange": postchange,
            "differences": {"removed": diff_removed, "added": diff_added},
        }
