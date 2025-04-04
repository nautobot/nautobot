from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.db.models import F, Model, OuterRef, ProtectedError, Q, Subquery
from django.db.models.functions import JSONObject

from nautobot.core.models.query_functions import EmptyGroupByJSONBAgg
from nautobot.core.models.querysets import RestrictedQuerySet
from nautobot.extras.models.tags import TaggedItem


class ConfigContextQuerySet(RestrictedQuerySet):
    def get_for_object(self, obj):
        """
        Return all applicable ConfigContexts for a given object. Only active ConfigContexts will be included.
        """

        role = obj.role

        # `device_type` for Device; `type` for VirtualMachine
        device_type = getattr(obj, "device_type", None)

        # Virtualization cluster for VirtualMachine
        cluster = getattr(obj, "cluster", None)
        cluster_group = getattr(cluster, "cluster_group", None)

        device_redundancy_group = getattr(obj, "device_redundancy_group", None)

        # Get the group of the assigned tenant, if any
        tenant_group = obj.tenant.tenant_group if obj.tenant else None
        tenant = obj.tenant if obj.tenant else None

        if tenant_group:
            tenant_groups = tenant_group.ancestors(include_self=True)
        else:
            tenant_groups = []
        # Match against the directly assigned location as well as any parent locations
        location = getattr(obj, "location", None)
        if location:
            locations = location.ancestors(include_self=True)
        else:
            locations = []

        query = [
            Q(locations__in=locations) | Q(locations=None),
            Q(roles=role) | Q(roles=None),
            Q(device_types=device_type) | Q(device_types=None),
            Q(platforms=obj.platform) | Q(platforms=None),
            Q(cluster_groups=cluster_group) | Q(cluster_groups=None),
            Q(clusters=cluster) | Q(clusters=None),
            Q(device_redundancy_groups=device_redundancy_group) | Q(device_redundancy_groups=None),
            Q(tenant_groups__in=tenant_groups) | Q(tenant_groups=None),
            Q(tenants=tenant) | Q(tenants=None),
            Q(tags__name__in=obj.tags.names()) | Q(tags=None),
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

        Note that the underlying function of our JSONBAgg in MySQL, `JSONARRAY_AGG`, does not support an `ordering`,
        unlike PostgreSQL's implementation. This is why we include "weight" and "name" into the result so that we can
        sort it within Python to ensure correctness.

        Do not use this method by itself, use get_config_context() method directly on ConfigContextModel instead.
        """
        from nautobot.extras.models import ConfigContext

        return self.annotate(
            config_context_data=Subquery(
                ConfigContext.objects.filter(self._get_config_context_filters())
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
                .order_by()
            )
        ).distinct()

    def _get_config_context_filters(self):
        """
        This method is constructing the set of Q objects for the specific object types.
        """
        tag_query_filters = {
            "object_id": OuterRef(OuterRef("pk")),
            "content_type__app_label": self.model._meta.app_label,
            "content_type__model": self.model._meta.model_name,
        }
        base_query = Q(
            Q(platforms=OuterRef("platform")) | Q(platforms=None),
            Q(cluster_groups=OuterRef("cluster__cluster_group")) | Q(cluster_groups=None),
            Q(clusters=OuterRef("cluster")) | Q(clusters=None),
            Q(tenants=OuterRef("tenant")) | Q(tenants=None),
            Q(tags__pk__in=Subquery(TaggedItem.objects.filter(**tag_query_filters).values_list("tag_id", flat=True)))
            | Q(tags=None),
            is_active=True,
        )
        base_query.add((Q(roles=OuterRef("role")) | Q(roles=None)), Q.AND)

        from nautobot.dcim.models import Location
        from nautobot.tenancy.models import TenantGroup

        if self.model._meta.model_name == "device":
            location_query_string = "location"
            base_query.add((Q(device_types=OuterRef("device_type")) | Q(device_types=None)), Q.AND)
            base_query.add(
                (Q(device_redundancy_groups=OuterRef("device_redundancy_group")) | Q(device_redundancy_groups=None)),
                Q.AND,
            )
        else:
            location_query_string = "cluster__location"

        location_query = Q(locations=None) | Q(locations=OuterRef(location_query_string))
        for _ in range(Location.objects.max_depth + 1):
            location_query_string += "__parent"
            location_query |= Q(locations=OuterRef(location_query_string))

        base_query.add((location_query), Q.AND)

        tenant_group_query_string = "tenant__tenant_group"
        tenant_group_query = Q(tenant_groups=None) | Q(tenant_groups=OuterRef(tenant_group_query_string))
        for _ in range(TenantGroup.objects.max_depth + 1):
            tenant_group_query_string += "__parent"
            tenant_group_query |= Q(tenant_groups=OuterRef(tenant_group_query_string))
        base_query.add((tenant_group_query), Q.AND)
        return base_query


class DynamicGroupQuerySet(RestrictedQuerySet):
    """Queryset for `DynamicGroup` objects that provides `get_for_object` and `get_for_model` methods."""

    def get_for_model(self, model):
        """
        Return all DynamicGroups assignable to the given model class.
        """
        concrete_model = model._meta.concrete_model
        content_type = ContentType.objects.get_for_model(concrete_model)
        return self.filter(content_type=content_type)

    def get_list_for_object(self, obj, use_cache=False):
        """
        Return a (cached) list of `DynamicGroup` objects assigned to the given object.

        Args:
            obj: The object to seek dynamic groups membership by.
            use_cache: Obsolete; cache is always used. If truly necessary to get up-to-the-minute accuracy, you should
                call `[dg.update_cached_members() for dg in DynamicGroup.objects.filter(content_type=...)]` beforehand,
                but be aware that that's potentially quite expensive computationally.
        """
        return list(self.get_for_object(obj))

    def get_for_object(self, obj, use_cache=False):
        """
        Return a (cached) queryset of `DynamicGroup` objects that are assigned to the given object.

        Args:
            obj: The object to seek dynamic groups membership by.
            use_cache: Obsolete; cache is always used. If truly necessary to get up-to-the-minute accuracy, you should
                call `[dg.update_cached_members() for dg in DynamicGroup.objects.filter(content_type=...)]` beforehand,
                but be aware that's potentially quite expensive computationally.
        """
        if not isinstance(obj, Model):
            raise TypeError(f"{obj} is not an instance of Django Model class")

        return self.filter(
            content_type__app_label=obj._meta.app_label,
            content_type__model=obj._meta.model_name,
            static_group_associations__associated_object_id=obj.id,
        )

    def get_by_natural_key(self, slug):
        return self.get(slug=slug)


class DynamicGroupMembershipQuerySet(RestrictedQuerySet):
    """Queryset for `DynamicGroupMembership` objects."""


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

    def delete(self):
        for job in self:
            if job.module_name.startswith("nautobot."):
                raise ProtectedError(
                    f"Unable to delete Job {job}. System Job cannot be deleted",
                    [],
                )
        return super().delete()

    def get_for_class_path(self, class_path):
        try:
            module_name, job_class_name = class_path.rsplit(".", 1)
        except ValueError:  # not a class_path perhaps?
            raise self.model.DoesNotExist()
        return self.get(
            module_name=module_name,
            job_class_name=job_class_name,
        )


class ScheduledJobExtendedQuerySet(RestrictedQuerySet):
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
