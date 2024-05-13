"""
Class-modifying mixins that need to be standalone to avoid circular imports.
"""

from django.contrib.contenttypes.fields import GenericRelation
from django.db import models
from django.urls import NoReverseMatch, reverse

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
    Adds properties to a model to facilitate reversing DynamicGroup membership:

    - `dynamic_groups` - A QuerySet of `DynamicGroup` objects this instance is a member of, performs the most database queries.
    - `dynamic_groups_cached` - A QuerySet of `DynamicGroup` objects this instance is a member of, uses cached member list if available. Ideal for most use cases.
    - `dynamic_groups_list` - A list of `DynamicGroup` objects this instance is a member of, performs one less database query than `dynamic_groups`.
    - `dynamic_groups_list_cached` - A list of `DynamicGroup` objects this instance is a member of, uses cached member list if available. Performs no database queries in optimal conditions.

    All properties are cached on the instance after the first call. To clear the instance cache without re-instantiating the object, call `delattr(instance, "_[the_property_name]")`.
        EX: `delattr(instance, "_dynamic_groups")`
    """

    @property
    def dynamic_groups(self):
        """
        Return a queryset of `DynamicGroup` objects this instance is a member of.

        This will NOT use the cached member lists of the dynamic groups and will always query the database for each DynamicGroup.

        Additionally, this performs a final database query to turn the internal list into a queryset.
        """
        from nautobot.extras.models.groups import DynamicGroup

        if not hasattr(self, "_dynamic_groups"):
            queryset = DynamicGroup.objects.get_for_object(self)
            self._dynamic_groups = queryset

        return self._dynamic_groups

    @property
    def dynamic_groups_cached(self):
        """
        Return a queryset of `DynamicGroup` objects this instance is a member of.

        This will use the cached member lists of the dynamic groups if available.

        In optimal conditions this will incur a single database query to convert internal list into a queryset which is reasonably performant.

        This is the ideal property to use for most use cases.
        """
        from nautobot.extras.models.groups import DynamicGroup

        if not hasattr(self, "_dynamic_groups_cached"):
            queryset = DynamicGroup.objects.get_for_object(self, use_cache=True)
            self._dynamic_groups_cached = queryset

        return self._dynamic_groups_cached

    @property
    def dynamic_groups_list(self):
        """
        Return a list of `DynamicGroup` objects this instance is a member of.

        This will NOT use the cached member lists of the dynamic groups and will always query the database for each DynamicGroup.

        This saves a final query to turn the list into a queryset.
        """
        from nautobot.extras.models.groups import DynamicGroup

        if not hasattr(self, "_dynamic_groups_list"):
            dg_list = DynamicGroup.objects.get_list_for_object(self)
            self._dynamic_groups_list = dg_list

        return self._dynamic_groups_list

    @property
    def dynamic_groups_list_cached(self):
        """
        Return a list of `DynamicGroup` objects this instance is a member of.

        This will use the cached member lists of the dynamic groups if available.

        In optimal conditions this will incur no database queries.
        """

        from nautobot.extras.models.groups import DynamicGroup

        if not hasattr(self, "_dynamic_groups_list_cached"):
            dg_list = DynamicGroup.objects.get_list_for_object(self, use_cache=True)
            self._dynamic_groups_list_cached = dg_list

        return self._dynamic_groups_list_cached

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
        Returns a QuerySet of StaticGroups that have this object as a member.
        """
        from nautobot.extras.models.groups import StaticGroup

        return StaticGroup.objects.filter(pk__in=self.associated_static_groups.values_list("static_group", flat=True))
