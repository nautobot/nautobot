from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from nautobot.core.api import (
    ChoiceField,
    SerializedPKRelatedField,
)
from nautobot.dcim.api.nested_serializers import (
    NestedLocationSerializer,
    NestedPlatformSerializer,
)
from nautobot.dcim.api.serializers import InterfaceCommonSerializer
from nautobot.dcim.choices import InterfaceModeChoices
from nautobot.extras.api.serializers import (
    NautobotModelSerializer,
    RoleModelSerializerMixin,
    StatusModelSerializerMixin,
    TaggedModelSerializerMixin,
)
from nautobot.extras.api.nested_serializers import NestedConfigContextSchemaSerializer
from nautobot.ipam.api.nested_serializers import (
    NestedIPAddressSerializer,
    NestedVLANSerializer,
)
from nautobot.ipam.models import IPAddress, VLAN
from nautobot.tenancy.api.nested_serializers import NestedTenantSerializer
from nautobot.virtualization.models import (
    Cluster,
    ClusterGroup,
    ClusterType,
    VirtualMachine,
    VMInterface,
)

# Not all of these variable(s) are not actually used anywhere in this file, but required for the
# automagically replacing a Serializer with its corresponding NestedSerializer.
from .nested_serializers import (  # noqa: F401
    NestedClusterGroupSerializer,
    NestedClusterSerializer,
    NestedClusterTypeSerializer,
    NestedVirtualMachineSerializer,
    NestedVMInterfaceSerializer,
)

#
# Clusters
#


class ClusterTypeSerializer(NautobotModelSerializer):
    url = serializers.HyperlinkedIdentityField(view_name="virtualization-api:clustertype-detail")
    cluster_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = ClusterType
        fields = [
            "url",
            "name",
            "slug",
            "description",
            "cluster_count",
        ]


class ClusterGroupSerializer(NautobotModelSerializer):
    url = serializers.HyperlinkedIdentityField(view_name="virtualization-api:clustergroup-detail")
    cluster_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = ClusterGroup
        fields = [
            "url",
            "name",
            "slug",
            "description",
            "cluster_count",
        ]


class ClusterSerializer(NautobotModelSerializer, TaggedModelSerializerMixin):
    url = serializers.HyperlinkedIdentityField(view_name="virtualization-api:cluster-detail")
    cluster_type = NestedClusterTypeSerializer()
    cluster_group = NestedClusterGroupSerializer(required=False, allow_null=True)
    tenant = NestedTenantSerializer(required=False, allow_null=True)
    location = NestedLocationSerializer(required=False, allow_null=True)
    device_count = serializers.IntegerField(read_only=True)
    virtualmachine_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Cluster
        fields = [
            "url",
            "name",
            "cluster_type",
            "cluster_group",
            "tenant",
            "location",
            "comments",
            "tags",
            "device_count",
            "virtualmachine_count",
        ]


#
# Virtual machines
#


class VirtualMachineSerializer(
    NautobotModelSerializer, TaggedModelSerializerMixin, StatusModelSerializerMixin, RoleModelSerializerMixin
):
    url = serializers.HyperlinkedIdentityField(view_name="virtualization-api:virtualmachine-detail")
    location = NestedLocationSerializer(read_only=True, required=False, allow_null=True)
    cluster = NestedClusterSerializer()
    tenant = NestedTenantSerializer(required=False, allow_null=True)
    platform = NestedPlatformSerializer(required=False, allow_null=True)
    primary_ip = NestedIPAddressSerializer(read_only=True)
    primary_ip4 = NestedIPAddressSerializer(required=False, allow_null=True)
    primary_ip6 = NestedIPAddressSerializer(required=False, allow_null=True)
    local_config_context_schema = NestedConfigContextSchemaSerializer(required=False, allow_null=True)

    class Meta:
        model = VirtualMachine
        fields = [
            "url",
            "name",
            "status",
            "location",
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


class VirtualMachineWithConfigContextSerializer(VirtualMachineSerializer):
    config_context = serializers.SerializerMethodField()
    local_config_context_schema = NestedConfigContextSchemaSerializer(required=False, allow_null=True)

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
    virtual_machine = NestedVirtualMachineSerializer()
    mode = ChoiceField(choices=InterfaceModeChoices, allow_blank=True, required=False)
    untagged_vlan = NestedVLANSerializer(required=False, allow_null=True)
    tagged_vlans = SerializedPKRelatedField(
        queryset=VLAN.objects.all(),
        serializer=NestedVLANSerializer,
        required=False,
        many=True,
    )
    ip_addresses = SerializedPKRelatedField(
        queryset=IPAddress.objects.all(),
        serializer=NestedIPAddressSerializer,
        required=False,
        many=True,
    )
    parent_interface = NestedVMInterfaceSerializer(required=False, allow_null=True)
    bridge = NestedVMInterfaceSerializer(required=False, allow_null=True)

    class Meta:
        model = VMInterface
        fields = [
            "url",
            "virtual_machine",
            "name",
            "status",
            "enabled",
            "parent_interface",
            "bridge",
            "mtu",
            "mac_address",
            "ip_addresses",
            "description",
            "mode",
            "untagged_vlan",
            "tagged_vlans",
            "tags",
        ]

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
