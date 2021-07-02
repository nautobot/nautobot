from drf_yasg.utils import swagger_serializer_method
from rest_framework import serializers

from nautobot.core.api import (
    ChoiceField,
    SerializedPKRelatedField,
    ValidatedModelSerializer,
)
from nautobot.dcim.api.nested_serializers import (
    NestedDeviceRoleSerializer,
    NestedPlatformSerializer,
    NestedSiteSerializer,
)
from nautobot.dcim.choices import InterfaceModeChoices
from nautobot.extras.api.customfields import CustomFieldModelSerializer
from nautobot.extras.api.serializers import (
    StatusModelSerializerMixin,
    TaggedObjectSerializer,
)
from nautobot.extras.api.nested_serializers import NestedConfigContextSchemaSerializer
from nautobot.ipam.api.nested_serializers import (
    NestedIPAddressSerializer,
    NestedVLANSerializer,
)
from nautobot.ipam.models import VLAN
from nautobot.tenancy.api.nested_serializers import NestedTenantSerializer
from nautobot.virtualization.choices import *
from nautobot.virtualization.models import (
    Cluster,
    ClusterGroup,
    ClusterType,
    VirtualMachine,
    VMInterface,
)
from .nested_serializers import *


#
# Clusters
#


class ClusterTypeSerializer(CustomFieldModelSerializer):
    url = serializers.HyperlinkedIdentityField(view_name="virtualization-api:clustertype-detail")
    cluster_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = ClusterType
        fields = [
            "id",
            "url",
            "name",
            "slug",
            "description",
            "cluster_count",
            "custom_fields",
            "created",
            "last_updated",
            "computed_fields",
        ]
        opt_in_fields = ["computed_fields"]


class ClusterGroupSerializer(CustomFieldModelSerializer):
    url = serializers.HyperlinkedIdentityField(view_name="virtualization-api:clustergroup-detail")
    cluster_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = ClusterGroup
        fields = [
            "id",
            "url",
            "name",
            "slug",
            "description",
            "cluster_count",
            "custom_fields",
            "created",
            "last_updated",
            "computed_fields",
        ]
        opt_in_fields = ["computed_fields"]


class ClusterSerializer(TaggedObjectSerializer, CustomFieldModelSerializer):
    url = serializers.HyperlinkedIdentityField(view_name="virtualization-api:cluster-detail")
    type = NestedClusterTypeSerializer()
    group = NestedClusterGroupSerializer(required=False, allow_null=True)
    tenant = NestedTenantSerializer(required=False, allow_null=True)
    site = NestedSiteSerializer(required=False, allow_null=True)
    device_count = serializers.IntegerField(read_only=True)
    virtualmachine_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Cluster
        fields = [
            "id",
            "url",
            "name",
            "type",
            "group",
            "tenant",
            "site",
            "comments",
            "tags",
            "custom_fields",
            "created",
            "last_updated",
            "device_count",
            "virtualmachine_count",
            "computed_fields",
        ]
        opt_in_fields = ["computed_fields"]


#
# Virtual machines
#


class VirtualMachineSerializer(TaggedObjectSerializer, StatusModelSerializerMixin, CustomFieldModelSerializer):
    url = serializers.HyperlinkedIdentityField(view_name="virtualization-api:virtualmachine-detail")
    site = NestedSiteSerializer(read_only=True)
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
            "id",
            "url",
            "name",
            "status",
            "site",
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
            "tags",
            "custom_fields",
            "created",
            "last_updated",
            "computed_fields",
        ]
        validators = []
        opt_in_fields = ["computed_fields"]


class VirtualMachineWithConfigContextSerializer(VirtualMachineSerializer):
    config_context = serializers.SerializerMethodField()
    local_context_schema = NestedConfigContextSchemaSerializer(required=False, allow_null=True)

    class Meta(VirtualMachineSerializer.Meta):
        fields = [
            "id",
            "url",
            "name",
            "status",
            "site",
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
            "tags",
            "custom_fields",
            "config_context",
            "created",
            "last_updated",
        ]

    @swagger_serializer_method(serializer_or_field=serializers.DictField)
    def get_config_context(self, obj):
        return obj.get_config_context()


#
# VM interfaces
#


class VMInterfaceSerializer(TaggedObjectSerializer, ValidatedModelSerializer):
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

    class Meta:
        model = VMInterface
        fields = [
            "id",
            "url",
            "virtual_machine",
            "name",
            "enabled",
            "mtu",
            "mac_address",
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
            if vlan.site not in [virtual_machine.site, None]:
                raise serializers.ValidationError(
                    {
                        "tagged_vlans": f"VLAN {vlan} must belong to the same site as the interface's parent virtual "
                        f"machine, or it must be global."
                    }
                )

        return super().validate(data)
