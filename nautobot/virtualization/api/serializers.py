from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from nautobot.core.api import (
    ChoiceField,
    NautobotModelSerializer,
)
from nautobot.dcim.api.serializers import InterfaceCommonSerializer
from nautobot.dcim.choices import InterfaceModeChoices
from nautobot.extras.api.mixins import (
    StatusModelSerializerMixin,
    TaggedModelSerializerMixin,
)
from nautobot.ipam.api.serializers import IPAddressSerializer
from nautobot.virtualization.models import (
    Cluster,
    ClusterGroup,
    ClusterType,
    VirtualMachine,
    VMInterface,
)

#
# Clusters
#


class ClusterTypeSerializer(NautobotModelSerializer):
    url = serializers.HyperlinkedIdentityField(view_name="virtualization-api:clustertype-detail")
    cluster_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = ClusterType
        fields = "__all__"


class ClusterGroupSerializer(NautobotModelSerializer):
    url = serializers.HyperlinkedIdentityField(view_name="virtualization-api:clustergroup-detail")
    cluster_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = ClusterGroup
        fields = "__all__"


class ClusterSerializer(NautobotModelSerializer, TaggedModelSerializerMixin):
    url = serializers.HyperlinkedIdentityField(view_name="virtualization-api:cluster-detail")
    device_count = serializers.IntegerField(read_only=True)
    virtualmachine_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Cluster
        fields = "__all__"


#
# Virtual machines
#


class VirtualMachineSerializer(NautobotModelSerializer, TaggedModelSerializerMixin, StatusModelSerializerMixin):
    url = serializers.HyperlinkedIdentityField(view_name="virtualization-api:virtualmachine-detail")
    # TODO #3024 How to get rid of this?
    primary_ip = IPAddressSerializer(read_only=True)

    class Meta:
        model = VirtualMachine
        # TODO #3024 keeping this for the append on line 130
        fields = [
            "url",
            "name",
            "status",
            "cluster",
            "role",
            "tenant",
            "platform",
            "primary_ip",
            "primary_ip4",
            "primary_ip6",
            "vcpus",
            "memory",
            "disk",
            "comments",
            "local_config_context_data",
            "local_config_context_schema",
        ]
        validators = []

    # TODO #3024 I would argue you do not need this anymore because you can obtain a more comprehensive
    # location field on cluster with ?depth=2


class VirtualMachineWithConfigContextSerializer(VirtualMachineSerializer):
    config_context = serializers.SerializerMethodField()

    class Meta(VirtualMachineSerializer.Meta):
        fields = VirtualMachineSerializer.Meta.fields + ["config_context"]

    @extend_schema_field(serializers.DictField)
    def get_config_context(self, obj):
        return obj.get_config_context()


#
# VM interfaces
#


class VMInterfaceSerializer(InterfaceCommonSerializer, StatusModelSerializerMixin):
    url = serializers.HyperlinkedIdentityField(view_name="virtualization-api:vminterface-detail")
    mode = ChoiceField(choices=InterfaceModeChoices, allow_blank=True, required=False)

    class Meta:
        model = VMInterface
        fields = "__all__"

    def validate(self, data):
        # Validate many-to-many VLAN assignments
        virtual_machine = self.instance.virtual_machine if self.instance else data.get("virtual_machine")
        for vlan in data.get("tagged_vlans", []):
            if vlan.location not in [virtual_machine.location, None]:
                raise serializers.ValidationError(
                    {
                        "tagged_vlans": f"VLAN {vlan} must belong to the same location as the interface's parent virtual "
                        f"machine, or it must be global."
                    }
                )

        return super().validate(data)
