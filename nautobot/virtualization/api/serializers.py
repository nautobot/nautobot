from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from nautobot.core.api import (
    ChoiceField,
    SerializedPKRelatedField,
)
from nautobot.dcim.api.nested_serializers import (
    NestedDeviceRoleSerializer,
    NestedLocationSerializer,
    NestedPlatformSerializer,
    NestedSiteSerializer,
)
from nautobot.dcim.api.serializers import InterfaceCommonSerializer
from nautobot.dcim.choices import InterfaceModeChoices
from nautobot.extras.api.serializers import (
    NautobotModelSerializer,
    StatusModelSerializerMixin,
    TaggedModelSerializerMixin,
)
from nautobot.extras.api.nested_serializers import NestedConfigContextSchemaSerializer
from nautobot.extras.models import Status
from nautobot.ipam.api.nested_serializers import (
    NestedIPAddressSerializer,
    NestedVLANSerializer,
)
from nautobot.ipam.models import VLAN
from nautobot.tenancy.api.nested_serializers import NestedTenantSerializer
from nautobot.virtualization.choices import VMInterfaceStatusChoices
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
    type = NestedClusterTypeSerializer()
    group = NestedClusterGroupSerializer(required=False, allow_null=True)
    tenant = NestedTenantSerializer(required=False, allow_null=True)
    site = NestedSiteSerializer(required=False, allow_null=True)
    location = NestedLocationSerializer(required=False, allow_null=True)
    device_count = serializers.IntegerField(read_only=True)
    virtualmachine_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Cluster
        fields = [
            "url",
            "name",
            "type",
            "group",
            "tenant",
            "site",
            "location",
            "comments",
            "tags",
            "device_count",
            "virtualmachine_count",
        ]


#
# Virtual machines
#


class VirtualMachineSerializer(NautobotModelSerializer, TaggedModelSerializerMixin, StatusModelSerializerMixin):
    url = serializers.HyperlinkedIdentityField(view_name="virtualization-api:virtualmachine-detail")
    site = NestedSiteSerializer(read_only=True)
    location = NestedLocationSerializer(read_only=True, required=False, allow_null=True)
    cluster = NestedClusterSerializer()
    role = NestedDeviceRoleSerializer(required=False, allow_null=True)
    tenant = NestedTenantSerializer(required=False, allow_null=True)
    platform = NestedPlatformSerializer(required=False, allow_null=True)
    primary_ip = NestedIPAddressSerializer(read_only=True)
    primary_ip4 = NestedIPAddressSerializer(required=False, allow_null=True)
    primary_ip6 = NestedIPAddressSerializer(required=False, allow_null=True)
    local_context_schema = NestedConfigContextSchemaSerializer(required=False, allow_null=True)

    class Meta:
        model = VirtualMachine
        fields = [
            "url",
            "name",
            "status",
            "site",
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
            "local_context_data",
            "local_context_schema",
        ]
        validators = []


class VirtualMachineWithConfigContextSerializer(VirtualMachineSerializer):
    config_context = serializers.SerializerMethodField()
    local_context_schema = NestedConfigContextSchemaSerializer(required=False, allow_null=True)

    class Meta(VirtualMachineSerializer.Meta):
        fields = VirtualMachineSerializer.Meta.fields + ["config_context"]

    @extend_schema_field(serializers.DictField)
    def get_config_context(self, obj):
        return obj.get_config_context()


#
# VM interfaces
#


# 2.0 TODO: This becomes non-default in 2.0, removed in 2.2.
class VMInterfaceSerializerVersion12(InterfaceCommonSerializer):
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
    parent_interface = NestedVMInterfaceSerializer(required=False, allow_null=True)
    bridge = NestedVMInterfaceSerializer(required=False, allow_null=True)

    class Meta:
        model = VMInterface
        fields = [
            "url",
            "virtual_machine",
            "name",
            "enabled",
            "parent_interface",
            "bridge",
            "mtu",
            "mac_address",
            "description",
            "mode",
            "untagged_vlan",
            "tagged_vlans",
            "tags",
        ]

    def validate(self, data):

        # set vminterface status to active if status not provided
        if not data.get("status"):
            # status is currently required in the VMInterface model but not required in api_version < 1.4 serializers
            # which raises an error when validating except status is explicitly set here
            query = Status.objects.get_for_model(VMInterface)
            try:
                data["status"] = query.get(slug=VMInterfaceStatusChoices.STATUS_ACTIVE)
            except Status.DoesNotExist:
                raise serializers.ValidationError(
                    {
                        "status": "VMInterface default status 'active' does not exist, "
                        "create 'active' status for VMInterface or use the latest api_version"
                    }
                )

        # Validate many-to-many VLAN assignments
        virtual_machine = self.instance.virtual_machine if self.instance else data.get("virtual_machine")
        for vlan in data.get("tagged_vlans", []):
            if vlan.site not in [virtual_machine.site, None]:
                raise serializers.ValidationError(
                    {
                        "tagged_vlans": f"VLAN {vlan} must belong to the same site as the interface's parent virtual "
                        f"machine, or it must be global."
                    }
                )

        return super().validate(data)


class VMInterfaceSerializer(VMInterfaceSerializerVersion12, StatusModelSerializerMixin):
    class Meta:
        model = VMInterface
        fields = VMInterfaceSerializerVersion12.Meta.fields.copy()
        fields.insert(4, "status")
