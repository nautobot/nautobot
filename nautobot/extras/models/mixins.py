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
    DEPRECATED - use DynamicGroupsModelMixin instead if you need to mark a model as supporting Dynamic Groups.

    This is necessary because DynamicGroupMixin was incorrectly not implemented as a subclass of models.Model,
    and so it cannot properly implement Model behaviors like the `static_group_association_set` ReverseRelation.
    However, adding this inheritance to DynamicGroupMixin itself would negatively impact existing migrations.
    So unfortunately our best option is to deprecate this class and gradually convert core and app models alike
    to the new DynamicGroupsModelMixin in its place.

    Adds `dynamic_groups` property to a model to facilitate reversing (cached) DynamicGroup membership.

    If up-to-the-minute accuracy is necessary for your use case, it's up to you to call the
    `DynamicGroup.update_cached_members()` API on any relevant DynamicGroups before accessing this property.

    Other related properties added by this mixin should be considered obsolete.
    """

    is_dynamic_group_associable_model = True

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

    # TODO may be able to remove this entirely???
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


class DynamicGroupsModelMixin(DynamicGroupMixin, models.Model):
    """
    Add this to models to make them fully support Dynamic Groups.
    """

    class Meta:
        abstract = True

    # Reverse relation so that deleting a DynamicGroupMixin automatically deletes any related StaticGroupAssociations
    static_group_association_set = GenericRelation(  # not "static_group_associations" as that'd collide on DynamicGroup
        "extras.StaticGroupAssociation",
        content_type_field="associated_object_type",
        object_id_field="associated_object_id",
        related_query_name="static_group_association_set_%(app_label)s_%(class)s",
    )


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


class SavedViewMixin(models.Model):
    """Abstract mixin for enabling Saved View functionality to a given model class."""

    class Meta:
        abstract = True

    is_saved_view_model = True
