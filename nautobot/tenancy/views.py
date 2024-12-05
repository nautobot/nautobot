from django_tables2 import RequestConfig

from nautobot.circuits.models import Circuit
from nautobot.core.ui.choices import SectionChoices
from nautobot.core.ui.object_detail import ObjectDetailContent, ObjectFieldsPanel, StatsPanel
from nautobot.core.views import generic
from nautobot.core.views.paginator import EnhancedPaginator, get_paginate_count
from nautobot.dcim.models import Controller, ControllerManagedDeviceGroup, Device, Location, Rack, RackReservation
from nautobot.extras.models import DynamicGroup
from nautobot.ipam.models import IPAddress, Prefix, VLAN, VRF
from nautobot.virtualization.models import Cluster, VirtualMachine

from . import filters, forms, tables
from .models import Tenant, TenantGroup

#
# Tenant groups
#


class TenantGroupListView(generic.ObjectListView):
    queryset = TenantGroup.objects.all()
    filterset = filters.TenantGroupFilterSet
    filterset_form = forms.TenantGroupFilterForm
    table = tables.TenantGroupTable


class TenantGroupView(generic.ObjectView):
    queryset = TenantGroup.objects.all()

    def get_extra_context(self, request, instance):
        # Tenants
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

        return {"tenant_table": tenant_table, **super().get_extra_context(request, instance)}


class TenantGroupEditView(generic.ObjectEditView):
    queryset = TenantGroup.objects.all()
    model_form = forms.TenantGroupForm


class TenantGroupDeleteView(generic.ObjectDeleteView):
    queryset = TenantGroup.objects.all()


class TenantGroupBulkImportView(generic.BulkImportView):  # 3.0 TODO: remove, unused
    queryset = TenantGroup.objects.all()
    table = tables.TenantGroupTable


class TenantGroupBulkDeleteView(generic.BulkDeleteView):
    queryset = TenantGroup.objects.all()
    table = tables.TenantGroupTable
    filterset = filters.TenantGroupFilterSet


#
#  Tenants
#


class TenantListView(generic.ObjectListView):
    queryset = Tenant.objects.all()
    filterset = filters.TenantFilterSet
    filterset_form = forms.TenantFilterForm
    table = tables.TenantTable


class TenantView(generic.ObjectView):
    queryset = Tenant.objects.select_related("tenant_group")
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


class TenantEditView(generic.ObjectEditView):
    queryset = Tenant.objects.all()
    model_form = forms.TenantForm
    template_name = "tenancy/tenant_edit.html"


class TenantDeleteView(generic.ObjectDeleteView):
    queryset = Tenant.objects.all()


class TenantBulkImportView(generic.BulkImportView):  # 3.0 TODO: remove, unused
    queryset = Tenant.objects.all()
    table = tables.TenantTable


class TenantBulkEditView(generic.BulkEditView):
    queryset = Tenant.objects.select_related("tenant_group")
    filterset = filters.TenantFilterSet
    table = tables.TenantTable
    form = forms.TenantBulkEditForm


class TenantBulkDeleteView(generic.BulkDeleteView):
    queryset = Tenant.objects.select_related("tenant_group")
    filterset = filters.TenantFilterSet
    table = tables.TenantTable
