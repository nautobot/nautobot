from django.db.models import Model
from nautobot.utilities.querysets import RestrictedQuerySet


class DynamicGroupQuerySet(RestrictedQuerySet):
    """Queryset for `DynamicGroup` objects that provides a `get_for_object` method."""

    # FIXME(jathan): Ideally replace this iteration with a reversible Q object
    # of some sort.
    def get_for_object(self, obj):
        """Return all `DynamicGroup` assigned to the given object."""
        if not isinstance(obj, Model):
            raise TypeError(f"{obj} is not an instance of Django Model class")

        # Get dynamic groups for this content_type using the discrete content_type fields to
        # optimize the query.
        # FIXME(jathan): Try to get the number of queries down. This will scale poorly.
        # TODO(jathan): 1 query
        eligible_groups = self.filter(
            content_type__app_label=obj._meta.app_label, content_type__model=obj._meta.model_name
        ).select_related("content_type")

        # Filter down to matching groups.
        my_groups = []
        # TODO(jathan): 3 queries per DynamicGroup instance
        for dynamic_group in eligible_groups.iterator():
            if obj.pk in dynamic_group.members.values_list("pk", flat=True):
                my_groups.append(dynamic_group.pk)

        # TODO(jathan): 1 query
        return self.filter(pk__in=my_groups)

    def get_by_natural_key(self, slug):
        return self.get(slug=slug)


class DynamicGroupMembershipQuerySet(RestrictedQuerySet):
    """Queryset for `DynamicGroupMembership` objects."""

    def get_by_natural_key(self, group_slug, parent_group_slug, operator, weight):
        return self.get(
            group__slug=group_slug,
            parent_group__slug=parent_group_slug,
            operator=operator,
            weight=weight,
        )
