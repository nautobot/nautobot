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
    cluster_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = ClusterType
        fields = "__all__"


class ClusterGroupSerializer(NautobotModelSerializer):
    cluster_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = ClusterGroup
        fields = "__all__"


class ClusterSerializer(NautobotModelSerializer, TaggedModelSerializerMixin):
    device_count = serializers.IntegerField(read_only=True)
    virtualmachine_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Cluster
        fields = "__all__"


#
# Virtual machines
#


class VirtualMachineSerializer(NautobotModelSerializer, TaggedModelSerializerMixin):
    config_context = serializers.SerializerMethodField()

    class Meta:
        model = VirtualMachine
        fields = "__all__"
        validators = []

    def get_field_names(self, declared_fields, info):
        """Config context is expensive to compute and so it's opt-in only."""
        fields = list(super().get_field_names(declared_fields, info))
        self.extend_field_names(fields, "config_context", opt_in_only=True)
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
    mode = ChoiceField(choices=InterfaceModeChoices, allow_blank=True, required=False)
    mac_address = serializers.CharField(allow_blank=True, allow_null=True, required=False)

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
