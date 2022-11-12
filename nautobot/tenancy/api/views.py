from rest_framework.routers import APIRootView

from nautobot.circuits.models import Circuit
from nautobot.dcim.models import Device, Rack, Site
from nautobot.extras.api.views import NautobotModelViewSet
from nautobot.ipam.models import IPAddress, Prefix, VLAN, VRF
from nautobot.tenancy import filters
from nautobot.tenancy.models import Tenant, TenantGroup
from nautobot.utilities.utils import count_related
from nautobot.virtualization.models import VirtualMachine
from . import serializers


class TenancyRootView(APIRootView):
    """
    Tenancy API root view
    """

    def get_view_name(self):
        return "Tenancy"


#
# Tenant Groups
#


class TenantGroupViewSet(NautobotModelViewSet):
    queryset = TenantGroup.objects.add_related_count(
        TenantGroup.objects.all(), Tenant, "group", "tenant_count", cumulative=True
    )
    serializer_class = serializers.TenantGroupSerializer
    filterset_class = filters.TenantGroupFilterSet


#
# Tenants
#


class TenantViewSet(NautobotModelViewSet):
    # v2 TODO(jathan): Replace prefetch_related with select_related (it should stay for tags)
    queryset = Tenant.objects.prefetch_related("group", "tags").annotate(
        circuit_count=count_related(Circuit, "tenant"),
        device_count=count_related(Device, "tenant"),
        ipaddress_count=count_related(IPAddress, "tenant"),
        prefix_count=count_related(Prefix, "tenant"),
        rack_count=count_related(Rack, "tenant"),
        site_count=count_related(Site, "tenant"),
        virtualmachine_count=count_related(VirtualMachine, "tenant"),
        vlan_count=count_related(VLAN, "tenant"),
        vrf_count=count_related(VRF, "tenant"),
    )
    serializer_class = serializers.TenantSerializer
    filterset_class = filters.TenantFilterSet
