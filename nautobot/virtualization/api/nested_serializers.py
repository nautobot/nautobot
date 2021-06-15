from rest_framework import serializers

from nautobot.core.api import WritableNestedSerializer
from nautobot.core.api.serializers import ComputedFieldModelSerializer
from nautobot.dcim.models import Interface
from nautobot.virtualization.models import (
    Cluster,
    ClusterGroup,
    ClusterType,
    VirtualMachine,
)

__all__ = [
    "NestedClusterGroupSerializer",
    "NestedClusterSerializer",
    "NestedClusterTypeSerializer",
    "NestedVMInterfaceSerializer",
    "NestedVirtualMachineSerializer",
]

#
# Clusters
#


class NestedClusterTypeSerializer(WritableNestedSerializer, ComputedFieldModelSerializer):
    url = serializers.HyperlinkedIdentityField(view_name="virtualization-api:clustertype-detail")
    cluster_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = ClusterType
        fields = ["id", "url", "name", "slug", "cluster_count", "computed_fields"]
        opt_in_fields = ["computed_fields"]


class NestedClusterGroupSerializer(WritableNestedSerializer, ComputedFieldModelSerializer):
    url = serializers.HyperlinkedIdentityField(view_name="virtualization-api:clustergroup-detail")
    cluster_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = ClusterGroup
        fields = ["id", "url", "name", "slug", "cluster_count", "computed_fields"]
        opt_in_fields = ["computed_fields"]


class NestedClusterSerializer(WritableNestedSerializer, ComputedFieldModelSerializer):
    url = serializers.HyperlinkedIdentityField(view_name="virtualization-api:cluster-detail")
    virtualmachine_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Cluster
        fields = ["id", "url", "name", "virtualmachine_count", "computed_fields"]
        opt_in_fields = ["computed_fields"]


#
# Virtual machines
#


class NestedVirtualMachineSerializer(WritableNestedSerializer, ComputedFieldModelSerializer):
    url = serializers.HyperlinkedIdentityField(view_name="virtualization-api:virtualmachine-detail")

    class Meta:
        model = VirtualMachine
        fields = ["id", "url", "name", "computed_fields"]
        opt_in_fields = ["computed_fields"]


class NestedVMInterfaceSerializer(WritableNestedSerializer, ComputedFieldModelSerializer):
    url = serializers.HyperlinkedIdentityField(view_name="virtualization-api:vminterface-detail")
    virtual_machine = NestedVirtualMachineSerializer(read_only=True)

    class Meta:
        model = Interface
        fields = ["id", "url", "virtual_machine", "name", "computed_fields"]
        opt_in_fields = ["computed_fields"]
