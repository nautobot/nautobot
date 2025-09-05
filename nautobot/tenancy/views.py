from django_tables2 import RequestConfig

from nautobot.circuits.models import Circuit
from nautobot.core.ui.choices import SectionChoices
from nautobot.core.ui.object_detail import ObjectDetailContent, ObjectFieldsPanel, ObjectsTablePanel, StatsPanel
from nautobot.core.views.paginator import EnhancedPaginator, get_paginate_count
from nautobot.core.views.viewsets import NautobotUIViewSet
from nautobot.dcim.models import Controller, ControllerManagedDeviceGroup, Device, Location, Rack, RackReservation
from nautobot.extras.models import DynamicGroup
from nautobot.ipam.models import IPAddress, Prefix, VLAN, VRF
from nautobot.tenancy.api import serializers
from nautobot.virtualization.models import Cluster, VirtualMachine

from . import filters, forms, tables
from .models import Tenant, TenantGroup

#
# Tenant groups
#


class TenantGroupUIViewSet(NautobotUIViewSet):
    bulk_update_form_class = forms.TenantGroupBulkEditForm
    filterset_class = filters.TenantGroupFilterSet
    filterset_form_class = forms.TenantGroupFilterForm
    form_class = forms.TenantGroupForm
    queryset = TenantGroup.objects.all()
    serializer_class = serializers.TenantGroupSerializer
    table_class = tables.TenantGroupTable
    object_detail_content = ObjectDetailContent(
        panels=(
            ObjectFieldsPanel(
                section=SectionChoices.LEFT_HALF,
                weight=100,
                fields="__all__",
            ),
            ObjectsTablePanel(
                weight=100,
                section=SectionChoices.RIGHT_HALF,
                context_table_key="tenant_table",
                exclude_columns=["tenant_group"],
            ),
        )
    )

    def get_extra_context(self, request, instance):
        # Tenants
        context = super().get_extra_context(request, instance)
        if self.action == "retrieve":
            # ObjectsTablePanel usually handles the generation of this table, this is an exception here
            # Because we are filtering on its tenant_group as well as the tenant group's descendants
            # i.e. `instance.descendants(include_self=True)`
            tenants = Tenant.objects.restrict(request.user, "view").filter(
                tenant_group__in=instance.descendants(include_self=True)
            )

            tenant_table = tables.TenantTable(tenants)
            tenant_table.columns.hide("tenant_group")

            paginate = {
                "paginator_class": EnhancedPaginator,
                "per_page": get_paginate_count(request),
            }
            RequestConfig(request, paginate).configure(tenant_table)
            context["tenant_table"] = tenant_table
        return context


#
#  Tenants
#


class TenantUIViewSet(NautobotUIViewSet):
    bulk_update_form_class = forms.TenantBulkEditForm
    filterset_class = filters.TenantFilterSet
    filterset_form_class = forms.TenantFilterForm
    form_class = forms.TenantForm
    queryset = Tenant.objects.all()
    serializer_class = serializers.TenantSerializer
    table_class = tables.TenantTable
    object_detail_content = ObjectDetailContent(
        panels=(
            ObjectFieldsPanel(
                section=SectionChoices.LEFT_HALF,
                weight=100,
                fields="__all__",
            ),
            StatsPanel(
                label="Stats",
                filter_name="tenant",
                related_models=[
                    Circuit,
                    Cluster,
                    Controller,
                    ControllerManagedDeviceGroup,
                    Device,
                    DynamicGroup,
                    IPAddress,
                    # TODO: Should we include child locations of the filtered locations in the location_count below?
                    Location,
                    Prefix,
                    Rack,
                    RackReservation,
                    VirtualMachine,
                    VLAN,
                    VRF,
                ],
                section=SectionChoices.RIGHT_HALF,
                weight=100,
            ),
        )
    )
