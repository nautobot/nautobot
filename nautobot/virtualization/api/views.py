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
    queryset = Cluster.objects.annotate(
        device_count=count_related(Device, "cluster"),
        virtualmachine_count=count_related(VirtualMachine, "cluster"),
    )
    serializer_class = serializers.ClusterSerializer
    filterset_class = filters.ClusterFilterSet


#
# Virtual machines
#


class VirtualMachineViewSet(ConfigContextQuerySetMixin, NautobotModelViewSet):
    queryset = VirtualMachine.objects.select_related("cluster__location")
    serializer_class = serializers.VirtualMachineSerializer
    filterset_class = filters.VirtualMachineFilterSet


class VMInterfaceViewSet(NotesViewSetMixin, ModelViewSet):
    queryset = VMInterface.objects.all()
    serializer_class = serializers.VMInterfaceSerializer
    filterset_class = filters.VMInterfaceFilterSet
