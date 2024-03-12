from django.core.cache import cache
from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.db.models import Model, OuterRef, Subquery, Q, F
from django.db.models.functions import JSONObject
from django_celery_beat.managers import ExtendedQuerySet

from nautobot.extras.models.tags import TaggedItem
from nautobot.utilities.config import get_settings_or_config
from nautobot.utilities.query_functions import EmptyGroupByJSONBAgg
from nautobot.utilities.querysets import RestrictedQuerySet


class ConfigContextQuerySet(RestrictedQuerySet):
    def get_for_object(self, obj):
        """
        Return all applicable ConfigContexts for a given object. Only active ConfigContexts will be included.
        """

        # `device_role` for Device; `role` for VirtualMachine
        role = getattr(obj, "device_role", None) or obj.role

        # `device_type` for Device; `type` for VirtualMachine
        device_type = getattr(obj, "device_type", None)

        # Virtualization cluster for VirtualMachine
        cluster = getattr(obj, "cluster", None)
        cluster_group = getattr(cluster, "group", None)

        device_redundancy_group = getattr(obj, "device_redundancy_group", None)

        # Get the group of the assigned tenant, if any
        tenant_group = obj.tenant.group if obj.tenant else None
        if tenant_group:
            tenant_groups = tenant_group.get_ancestors(include_self=True)
        else:
            tenant_groups = []

        # Match against the directly assigned region as well as any parent regions.
        region = getattr(obj.site, "region", None)
        if region:
            regions = region.get_ancestors(include_self=True)
        else:
            regions = []

        # Match against the directly assigned location as well as any parent locations
        location = getattr(obj, "location", None)
        if location:
            locations = location.ancestors(include_self=True)
        else:
            locations = []

        query = [
            Q(regions__in=regions) | Q(regions=None),
            Q(sites=obj.site) | Q(sites=None),
            Q(locations__in=locations) | Q(locations=None),
            Q(roles=role) | Q(roles=None),
            Q(device_types=device_type) | Q(device_types=None),
            Q(platforms=obj.platform) | Q(platforms=None),
            Q(cluster_groups=cluster_group) | Q(cluster_groups=None),
            Q(clusters=cluster) | Q(clusters=None),
            Q(device_redundancy_groups=device_redundancy_group) | Q(device_redundancy_groups=None),
            Q(tenant_groups__in=tenant_groups) | Q(tenant_groups=None),
            Q(tenants=obj.tenant) | Q(tenants=None),
            Q(tags__slug__in=obj.tags.slugs()) | Q(tags=None),
        ]
        if settings.CONFIG_CONTEXT_DYNAMIC_GROUPS_ENABLED:
            query.append(Q(dynamic_groups__in=obj.dynamic_groups) | Q(dynamic_groups=None))

        queryset = (
            self.filter(
                *query,
                is_active=True,
            )
            .order_by("weight", "name")
            .distinct()
        )

        return queryset


class ConfigContextModelQuerySet(RestrictedQuerySet):
    """
    QuerySet manager used by models which support ConfigContext (device and virtual machine).

    Includes a method which appends an annotation of aggregated config context JSON data objects. This is
    implemented as a subquery which performs all the joins necessary to filter relevant config context objects.
    This offers a substantial performance gain over ConfigContextQuerySet.get_for_object() when dealing with
    multiple objects.

    This allows the annotation to be entirely optional.
    """

    def annotate_config_context_data(self):
        """
        Attach the subquery annotation to the base queryset.

        Order By clause in Subquery is not guaranteed to be respected within the aggregated JSON array, which is why
        we include "weight" and "name" into the result so that we can sort it within Python to ensure correctness.
        """
        from nautobot.extras.models import ConfigContext

        return self.annotate(
            config_context_data=Subquery(
                ConfigContext.objects.filter(self._get_config_context_filters())
                .order_by("weight", "name")
                .annotate(
                    _data=EmptyGroupByJSONBAgg(
                        JSONObject(
                            data=F("data"),
                            name=F("name"),
                            weight=F("weight"),
                        )
                    )
                )
                .values("_data")
            )
        ).distinct()

    def _get_config_context_filters(self):
        # Construct the set of Q objects for the specific object types
        tag_query_filters = {
            "object_id": OuterRef(OuterRef("pk")),
            "content_type__app_label": self.model._meta.app_label,
            "content_type__model": self.model._meta.model_name,
        }
        base_query = Q(
            Q(platforms=OuterRef("platform")) | Q(platforms=None),
            Q(cluster_groups=OuterRef("cluster__group")) | Q(cluster_groups=None),
            Q(clusters=OuterRef("cluster")) | Q(clusters=None),
            Q(tenants=OuterRef("tenant")) | Q(tenants=None),
            Q(tags__pk__in=Subquery(TaggedItem.objects.filter(**tag_query_filters).values_list("tag_id", flat=True)))
            | Q(tags=None),
            is_active=True,
        )
        tenant_group_field = "tenant__group"
        if self.model._meta.model_name == "device":
            base_query.add((Q(roles=OuterRef("device_role")) | Q(roles=None)), Q.AND)
            base_query.add((Q(device_types=OuterRef("device_type")) | Q(device_types=None)), Q.AND)
            base_query.add(
                (Q(device_redundancy_groups=OuterRef("device_redundancy_group")) | Q(device_redundancy_groups=None)),
                Q.AND,
            )
            base_query.add((Q(sites=OuterRef("site")) | Q(sites=None)), Q.AND)
            region_field = "site__region"

        elif self.model._meta.model_name == "virtualmachine":
            base_query.add((Q(roles=OuterRef("role")) | Q(roles=None)), Q.AND)
            base_query.add((Q(sites=OuterRef("cluster__site")) | Q(sites=None)), Q.AND)
            region_field = "cluster__site__region"

        base_query.add(
            (
                Q(
                    regions__tree_id=OuterRef(f"{region_field}__tree_id"),
                    regions__level__lte=OuterRef(f"{region_field}__level"),
                    regions__lft__lte=OuterRef(f"{region_field}__lft"),
                    regions__rght__gte=OuterRef(f"{region_field}__rght"),
                )
                | Q(regions=None)
            ),
            Q.AND,
        )
        base_query.add(
            (
                Q(
                    tenant_groups__tree_id=OuterRef(f"{tenant_group_field}__tree_id"),
                    tenant_groups__level__lte=OuterRef(f"{tenant_group_field}__level"),
                    tenant_groups__lft__lte=OuterRef(f"{tenant_group_field}__lft"),
                    tenant_groups__rght__gte=OuterRef(f"{tenant_group_field}__rght"),
                )
                | Q(tenant_groups=None)
            ),
            Q.AND,
        )

        return base_query


class DynamicGroupQuerySet(RestrictedQuerySet):
    """Queryset for `DynamicGroup` objects that provides a `get_for_object` method."""

    def get_list_for_object(self, obj, use_cache=False):
        """
        Return a list of `DynamicGroup` assigned to the given object. As opposed to `get_for_object`
        which will return a queryset but that is an additional query to the DB when you may just
        want a list.

        Args:
            obj: The object to seek dynamic groups membership by.
            use_cache: If True, use the cache and query the database directly.
        """
        if not isinstance(obj, Model):
            raise TypeError(f"{obj} is not an instance of Django Model class")

        # Get dynamic groups for this content_type using the discrete content_type fields to
        # optimize the query.
        eligible_groups = self._get_eligible_dynamic_groups(obj, use_cache=use_cache)

        # Filter down to matching groups.
        my_groups = []
        for dynamic_group in list(eligible_groups):
            if dynamic_group.has_member(obj, use_cache=use_cache):
                my_groups.append(dynamic_group)

        return my_groups

    def get_for_object(self, obj, use_cache=False):
        """
        Return a queryset of `DynamicGroup` objects that are assigned to the given object.

        Args:
            obj: The object to seek dynamic groups membership by.
            use_cache: If True, use the cache and query the database directly.
        """
        return self.filter(pk__in=[dg.pk for dg in self.get_list_for_object(obj, use_cache=use_cache)])

    def get_by_natural_key(self, slug):
        return self.get(slug=slug)

    @classmethod
    def _get_eligible_dynamic_groups_cache_key(cls, obj):
        """
        Return the cache key for the queryset of `DynamicGroup` objects that are eligible to potentially contain the
        given object.
        """
        return f"{obj._meta.label_lower}._get_eligible_dynamic_groups"

    def _get_eligible_dynamic_groups(self, obj, use_cache=False):
        """
        Return a queryset of `DynamicGroup` objects that are eligible to potentially contain the given object.
        """
        cache_key = self.__class__._get_eligible_dynamic_groups_cache_key(obj)

        def _query_eligible_dynamic_groups():
            """
            A callable to be used as the default value for the cache of which dynamic groups are
            eligible for a given object.
            """
            # Save a DB query if we can by using the _content_type field on the model which is a cached instance of the ContentType
            if use_cache and hasattr(type(obj), "_content_type"):
                return self.filter(content_type_id=type(obj)._content_type.id)
            return self.filter(
                content_type__app_label=obj._meta.app_label, content_type__model=obj._meta.model_name
            ).select_related("content_type")

        if not use_cache:
            eligible_dynamic_groups = _query_eligible_dynamic_groups()
            cache.set(cache_key, eligible_dynamic_groups, get_settings_or_config("DYNAMIC_GROUPS_MEMBER_CACHE_TIMEOUT"))
            return eligible_dynamic_groups

        return cache.get_or_set(
            cache_key, _query_eligible_dynamic_groups, get_settings_or_config("DYNAMIC_GROUPS_MEMBER_CACHE_TIMEOUT")
        )


class DynamicGroupMembershipQuerySet(RestrictedQuerySet):
    """Queryset for `DynamicGroupMembership` objects."""

    def get_by_natural_key(self, group_slug, parent_group_slug, operator, weight):
        return self.get(
            group__slug=group_slug,
            parent_group__slug=parent_group_slug,
            operator=operator,
            weight=weight,
        )


class NotesQuerySet(RestrictedQuerySet):
    """Queryset for `Notes` objects that provides a `get_for_object` method."""

    def get_for_object(self, obj):
        """Return all `Notes` assigned to the given object."""
        if not isinstance(obj, Model):
            raise TypeError(f"{obj} is not an instance of Django Model class")

        content_type = ContentType.objects.get_for_model(obj)
        return self.filter(assigned_object_id=obj.pk, assigned_object_type=content_type)


class JobQuerySet(RestrictedQuerySet):
    """
    Extend the standard queryset with a get_for_class_path method.
    """

    def get_for_class_path(self, class_path):
        try:
            source, module_name, job_class_name = class_path.split("/")
            repository_slug = None
            if source.startswith("git."):
                repository_slug = source[4:]
                source = "git"
        except ValueError:  # not a class_path perhaps?
            raise self.model.DoesNotExist()
        return self.get(
            source=source,
            module_name=module_name,
            job_class_name=job_class_name,
            git_repository__slug=repository_slug,
        )


class ScheduledJobExtendedQuerySet(RestrictedQuerySet, ExtendedQuerySet):
    """
    Base queryset used for the ScheduledJob class
    """

    def enabled(self):
        """
        Return only ScheduledJob instances that are enabled and approved (if approval required)
        """
        return self.filter(
            Q(enabled=True) & Q(Q(approval_required=True, approved_at__isnull=False) | Q(approval_required=False))
        )

    def approved(self):
        """
        Return only ScheduledJob instances that require approval and are approved
        """
        return self.filter(approval_required=True, approved_at__isnull=False)

    def needs_approved(self):
        """
        Return only ScheduledJob instances that require approval and are not approved
        """
        return self.filter(approval_required=True, approved_at__isnull=True).order_by("start_time")
