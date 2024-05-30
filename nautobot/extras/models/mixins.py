"""
Class-modifying mixins that need to be standalone to avoid circular imports.
"""

from django.contrib.contenttypes.fields import GenericRelation
from django.db import models
from django.urls import NoReverseMatch, reverse

from nautobot.core.utils.deprecation import method_deprecated_in_favor_of
from nautobot.core.utils.lookup import get_route_for_model


class ContactMixin(models.Model):
    """Abstract mixin for enabling Contact/Team association to a given model class."""

    class Meta:
        abstract = True

    is_contact_associable_model = True

    # Reverse relation so that deleting a ContactMixin automatically deletes any ContactAssociations related to it.
    associated_contacts = GenericRelation(
        "extras.ContactAssociation",
        content_type_field="associated_object_type",
        object_id_field="associated_object_id",
        related_query_name="associated_contacts_%(app_label)s_%(class)s",  # e.g. 'associated_contacts_dcim_device'
    )


class DynamicGroupMixin:
    """
    Adds `dynamic_groups` property to a model to facilitate reversing (cached) DynamicGroup membership.

    If up-to-the-minute accuracy is necessary for your use case, it's up to you to call the
    `DynamicGroup.update_cached_members()` API on any relevant DynamicGroups before accessing this property.

    Other related properties added by this mixin should be considered obsolete.
    """

    @property
    def dynamic_groups(self):
        """
        Return a queryset of (cached) `DynamicGroup` objects this instance is a member of.
        """
        from nautobot.extras.models.groups import DynamicGroup

        return DynamicGroup.objects.get_for_object(self)

    @property
    @method_deprecated_in_favor_of(dynamic_groups.fget)
    def dynamic_groups_cached(self):
        """Deprecated - use `self.dynamic_groups` instead."""
        return self.dynamic_groups

    @property
    @method_deprecated_in_favor_of(dynamic_groups.fget)
    def dynamic_groups_list(self):
        """Deprecated - use `list(self.dynamic_groups)` instead."""
        return list(self.dynamic_groups)

    @property
    @method_deprecated_in_favor_of(dynamic_groups.fget)
    def dynamic_groups_list_cached(self):
        """Deprecated - use `list(self.dynamic_groups)` instead."""
        return self.dynamic_groups_list

    def get_dynamic_groups_url(self):
        """Return the dynamic groups URL for a given instance."""
        route = get_route_for_model(self, "dynamicgroups")

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


class NotesMixin:
    """
    Adds a `notes` property that returns a queryset of `Notes` membership.
    """

    @property
    def notes(self):
        """Return a `Notes` queryset for this instance."""
        from nautobot.extras.models.models import Note

        if not hasattr(self, "_notes_queryset"):
            queryset = Note.objects.get_for_object(self)
            self._notes_queryset = queryset

        return self._notes_queryset

    def get_notes_url(self, api=False):
        """Return the notes URL for a given instance."""
        route = get_route_for_model(self, "notes", api=api)

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


class StaticGroupMixin(models.Model):
    """Abstract mixin for enabling StaticGroup association to a given model class."""

    class Meta:
        abstract = True

    is_static_group_associable_model = True

    # Reverse relation so that deleting a StaticGroupMixin automatically deletes any related StaticGroupAssociations
    associated_static_groups = GenericRelation(
        "extras.StaticGroupAssociation",
        content_type_field="associated_object_type",
        object_id_field="associated_object_id",
        related_query_name="associated_static_groups_%(app_label)s_%(class)s",  # 'associated_static_groups_dcim_device'
    )

    @property
    def static_groups(self):
        """
        Returns a QuerySet of StaticGroups that have this object as a member. Does not include hidden groups.
        """
        from nautobot.extras.models.groups import StaticGroup

        return StaticGroup.objects.filter(pk__in=self.associated_static_groups.values_list("static_group", flat=True))
