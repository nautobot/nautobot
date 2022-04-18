from drf_spectacular.utils import extend_schema_view, extend_schema
from rest_framework.routers import APIRootView

from nautobot.dcim.models import Device
from nautobot.extras.api.views import (
    ConfigContextQuerySetMixin,
    CustomFieldModelViewSet,
    ModelViewSet,
    StatusViewSetMixin,
)
from nautobot.utilities.utils import count_related
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


class ClusterTypeViewSet(CustomFieldModelViewSet):
    queryset = ClusterType.objects.annotate(cluster_count=count_related(Cluster, "type"))
    serializer_class = serializers.ClusterTypeSerializer
    filterset_class = filters.ClusterTypeFilterSet


class ClusterGroupViewSet(CustomFieldModelViewSet):
    queryset = ClusterGroup.objects.annotate(cluster_count=count_related(Cluster, "group"))
    serializer_class = serializers.ClusterGroupSerializer
    filterset_class = filters.ClusterGroupFilterSet


class ClusterViewSet(CustomFieldModelViewSet):
    queryset = Cluster.objects.prefetch_related("type", "group", "tenant", "site", "tags").annotate(
        device_count=count_related(Device, "cluster"),
        virtualmachine_count=count_related(VirtualMachine, "cluster"),
    )
    serializer_class = serializers.ClusterSerializer
    filterset_class = filters.ClusterFilterSet


#
# Virtual machines
#


class VirtualMachineViewSet(ConfigContextQuerySetMixin, StatusViewSetMixin, CustomFieldModelViewSet):
    queryset = VirtualMachine.objects.prefetch_related(
        "cluster__site",
        "platform",
        "primary_ip4",
        "primary_ip6",
        "status",
        "role",
        "tenant",
        "tags",
    )
    filterset_class = filters.VirtualMachineFilterSet

    def get_serializer_class(self):
        """
        Select the specific serializer based on the request context.

        If the `brief` query param equates to True, return the NestedVirtualMachineSerializer

        If the `exclude` query param includes `config_context` as a value, return the VirtualMachineSerializer

        Else, return the VirtualMachineWithConfigContextSerializer
        """

        request = self.get_serializer_context()["request"]
        if request is not None and request.query_params.get("brief", False):
            return serializers.NestedVirtualMachineSerializer

        elif request is not None and "config_context" in request.query_params.get("exclude", []):
            return serializers.VirtualMachineSerializer

        return serializers.VirtualMachineWithConfigContextSerializer


@extend_schema_view(
    bulk_update=extend_schema(responses={"200": serializers.VMInterfaceSerializer(many=True)}, versions=["1.2"]),
    bulk_partial_update=extend_schema(
        responses={"200": serializers.VMInterfaceSerializer(many=True)}, versions=["1.2"]
    ),
    create=extend_schema(responses={"201": serializers.VMInterfaceSerializer}, versions=["1.2"]),
    partial_update=extend_schema(responses={"200": serializers.VMInterfaceSerializer}, versions=["1.2"]),
    update=extend_schema(responses={"200": serializers.VMInterfaceSerializer}, versions=["1.2"]),
    list=extend_schema(responses={"200": serializers.VMInterfaceSerializer(many=True)}, versions=["1.2"]),
    retrieve=extend_schema(responses={"200": serializers.VMInterfaceSerializer}, versions=["1.2"]),
)
class VMInterfaceViewSet(ModelViewSet):
    queryset = VMInterface.objects.prefetch_related("virtual_machine", "parent", "tags", "tagged_vlans")
    serializer_class = serializers.VMInterfaceSerializerVersion3
    filterset_class = filters.VMInterfaceFilterSet
    brief_prefetch_fields = ["virtual_machine"]

    def is_not_version13(self):
        return (
            not self.brief
            and not getattr(self, "swagger_fake_view", False)
            and (
                not hasattr(self.request, "major_version")
                or self.request.major_version > 1
                or (self.request.major_version == 1 and self.request.minor_version < 3)
            )
        )

    def get_queryset(self):
        if self.is_not_version13:
            return VMInterface.objects.prefetch_related("virtual_machine", "tags", "tagged_vlans")
        return super().get_queryset()

    def get_serializer_class(self):
        if self.is_not_version13():
            return serializers.VMInterfaceSerializer
        return super().get_serializer_class()
