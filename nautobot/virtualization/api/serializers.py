from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from nautobot.core.api import (
    ChoiceField,
    NautobotModelSerializer,
)
from nautobot.dcim.api.serializers import InterfaceCommonSerializer
from nautobot.dcim.choices import InterfaceModeChoices
from nautobot.extras.api.mixins import (
    TaggedModelSerializerMixin,
)
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


class VirtualMachineSerializer(NautobotModelSerializer, TaggedModelSerializerMixin):
    url = serializers.HyperlinkedIdentityField(view_name="virtualization-api:virtualmachine-detail")

    class Meta:
        model = VirtualMachine
        fields = "__all__"
        validators = []


class VirtualMachineWithConfigContextSerializer(VirtualMachineSerializer):
    config_context = serializers.SerializerMethodField()

    def get_field_names(self, declared_fields, info):
        """Ensure that "config_contexts" is always included appropriately."""
        fields = list(super().get_field_names(declared_fields, info))
        self.extend_field_names(fields, "config_context")
        return fields

    @extend_schema_field(serializers.DictField)
    def get_config_context(self, obj):
        return obj.get_config_context()


#
# VM interfaces
#


class VMInterfaceSerializer(
    InterfaceCommonSerializer,
):
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
