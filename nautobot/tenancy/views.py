from django_tables2 import RequestConfig

from nautobot.circuits.models import Circuit
from nautobot.core.views import generic
from nautobot.dcim.models import Site, Rack, Device, RackReservation
from nautobot.ipam.models import IPAddress, Prefix, VLAN, VRF
from nautobot.utilities.paginator import EnhancedPaginator, get_paginate_count
from nautobot.virtualization.models import VirtualMachine, Cluster
from . import filters, forms, tables
from .models import Tenant, TenantGroup


#
# Tenant groups
#


class TenantGroupListView(generic.ObjectListView):
    queryset = TenantGroup.objects.add_related_count(
        TenantGroup.objects.all(), Tenant, "group", "tenant_count", cumulative=True
    )
    filterset = filters.TenantGroupFilterSet
    table = tables.TenantGroupTable


class TenantGroupView(generic.ObjectView):
    queryset = TenantGroup.objects.all()

    def get_extra_context(self, request, instance):

        # Tenants
        tenants = Tenant.objects.restrict(request.user, "view").filter(
            group__in=instance.get_descendants(include_self=True)
        )

        tenant_table = tables.TenantTable(tenants)
        tenant_table.columns.hide("group")

        paginate = {
            "paginator_class": EnhancedPaginator,
            "per_page": get_paginate_count(request),
        }
        RequestConfig(request, paginate).configure(tenant_table)

        return {
            "tenant_table": tenant_table,
        }


class TenantGroupEditView(generic.ObjectEditView):
    queryset = TenantGroup.objects.all()
    model_form = forms.TenantGroupForm


class TenantGroupDeleteView(generic.ObjectDeleteView):
    queryset = TenantGroup.objects.all()


class TenantGroupBulkImportView(generic.BulkImportView):
    queryset = TenantGroup.objects.all()
    model_form = forms.TenantGroupCSVForm
    table = tables.TenantGroupTable


class TenantGroupBulkDeleteView(generic.BulkDeleteView):
    queryset = TenantGroup.objects.add_related_count(
        TenantGroup.objects.all(), Tenant, "group", "tenant_count", cumulative=True
    )
    table = tables.TenantGroupTable


#
#  Tenants
#


class TenantListView(generic.ObjectListView):
    queryset = Tenant.objects.all()
    filterset = filters.TenantFilterSet
    filterset_form = forms.TenantFilterForm
    table = tables.TenantTable


class TenantView(generic.ObjectView):
    # v2 TODO(jathan): Replace prefetch_related with select_related
    queryset = Tenant.objects.prefetch_related("group")

    def get_extra_context(self, request, instance):
        stats = {
            "site_count": Site.objects.restrict(request.user, "view").filter(tenant=instance).count(),
            "rack_count": Rack.objects.restrict(request.user, "view").filter(tenant=instance).count(),
            "rackreservation_count": RackReservation.objects.restrict(request.user, "view")
            .filter(tenant=instance)
            .count(),
            "device_count": Device.objects.restrict(request.user, "view").filter(tenant=instance).count(),
            "vrf_count": VRF.objects.restrict(request.user, "view").filter(tenant=instance).count(),
            "prefix_count": Prefix.objects.restrict(request.user, "view").filter(tenant=instance).count(),
            "ipaddress_count": IPAddress.objects.restrict(request.user, "view").filter(tenant=instance).count(),
            "vlan_count": VLAN.objects.restrict(request.user, "view").filter(tenant=instance).count(),
            "circuit_count": Circuit.objects.restrict(request.user, "view").filter(tenant=instance).count(),
            "virtualmachine_count": VirtualMachine.objects.restrict(request.user, "view")
            .filter(tenant=instance)
            .count(),
            "cluster_count": Cluster.objects.restrict(request.user, "view").filter(tenant=instance).count(),
        }

        return {
            "stats": stats,
        }


class TenantEditView(generic.ObjectEditView):
    queryset = Tenant.objects.all()
    model_form = forms.TenantForm
    template_name = "tenancy/tenant_edit.html"


class TenantDeleteView(generic.ObjectDeleteView):
    queryset = Tenant.objects.all()


class TenantBulkImportView(generic.BulkImportView):
    queryset = Tenant.objects.all()
    model_form = forms.TenantCSVForm
    table = tables.TenantTable


class TenantBulkEditView(generic.BulkEditView):
    # v2 TODO(jathan): Replace prefetch_related with select_related
    queryset = Tenant.objects.prefetch_related("group")
    filterset = filters.TenantFilterSet
    table = tables.TenantTable
    form = forms.TenantBulkEditForm


class TenantBulkDeleteView(generic.BulkDeleteView):
    # v2 TODO(jathan): Replace prefetch_related with select_related
    queryset = Tenant.objects.prefetch_related("group")
    filterset = filters.TenantFilterSet
    table = tables.TenantTable
