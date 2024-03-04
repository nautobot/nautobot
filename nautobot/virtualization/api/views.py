from rest_framework.routers import APIRootView

from nautobot.core.models.querysets import count_related
from nautobot.dcim.models import Device
from nautobot.extras.api.views import (
    ConfigContextQuerySetMixin,
    ModelViewSet,
    NautobotModelViewSet,
    NotesViewSetMixin,
)
from nautobot.virtualization import filters
from nautobot.virtualization.models import (
    Cluster,
    ClusterGroup,
    ClusterType,
    VirtualMachine,
    VMInterface,
)

from . import serializers


class VirtualizationRootView(APIRootView):
    """
    Virtualization API root view
    """

    def get_view_name(self):
        return "Virtualization"


#
# Clusters
#


class ClusterTypeViewSet(NautobotModelViewSet):
    queryset = ClusterType.objects.annotate(cluster_count=count_related(Cluster, "cluster_type"))
    serializer_class = serializers.ClusterTypeSerializer
    filterset_class = filters.ClusterTypeFilterSet


class ClusterGroupViewSet(NautobotModelViewSet):
    queryset = ClusterGroup.objects.annotate(cluster_count=count_related(Cluster, "cluster_group"))
    serializer_class = serializers.ClusterGroupSerializer
    filterset_class = filters.ClusterGroupFilterSet


class ClusterViewSet(NautobotModelViewSet):
    queryset = (
        Cluster.objects.select_related("cluster_type", "cluster_group", "tenant", "location")
        .prefetch_related("tags")
        .annotate(
            device_count=count_related(Device, "cluster"),
            virtualmachine_count=count_related(VirtualMachine, "cluster"),
        )
    )
    serializer_class = serializers.ClusterSerializer
    filterset_class = filters.ClusterFilterSet


#
# Virtual machines
#


class VirtualMachineViewSet(ConfigContextQuerySetMixin, NautobotModelViewSet):
    queryset = VirtualMachine.objects.select_related(
        "cluster__location",
        "platform",
        "primary_ip4",
        "primary_ip6",
        "status",
        "role",
        "software_version",
        "tenant",
    ).prefetch_related("tags")
    serializer_class = serializers.VirtualMachineSerializer
    filterset_class = filters.VirtualMachineFilterSet


class VMInterfaceViewSet(NotesViewSetMixin, ModelViewSet):
    queryset = VMInterface.objects.select_related(
        "virtual_machine",
        "parent_interface",
        "bridge",
        "status",
        "untagged_vlan",
    ).prefetch_related("tags", "ip_addresses", "tagged_vlans")
    serializer_class = serializers.VMInterfaceSerializer
    filterset_class = filters.VMInterfaceFilterSet
