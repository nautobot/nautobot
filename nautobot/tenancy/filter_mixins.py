import django_filters

from nautobot.core.filters import NaturalKeyOrPKMultipleChoiceFilter, TreeNodeMultipleChoiceFilter
from nautobot.tenancy.models import Tenant, TenantGroup


class TenancyModelFilterSetMixin(django_filters.FilterSet):
    """
    An inheritable FilterSet for models which support Tenant assignment.
    """

    tenant_group = TreeNodeMultipleChoiceFilter(
        queryset=TenantGroup.objects.all(),
        field_name="tenant__tenant_group",
        to_field_name="name",
        label="Tenant Group (name or ID)",
    )
    tenant_id = django_filters.ModelMultipleChoiceFilter(
        queryset=Tenant.objects.all(),
        label='Tenant (ID) (deprecated, use "tenant" filter instead)',
    )
    tenant = NaturalKeyOrPKMultipleChoiceFilter(
        queryset=Tenant.objects.all(),
        to_field_name="name",
        label="Tenant (name or ID)",
    )
