from collections import OrderedDict

from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers
from rest_framework.validators import UniqueTogetherValidator

from nautobot.core.api import (
    ChoiceField,
    NautobotModelSerializer,
)
from nautobot.core.api.utils import get_nested_serializer_depth, return_nested_serializer_data_based_on_depth
from nautobot.extras.api.mixins import TaggedModelSerializerMixin
from nautobot.ipam.api.fields import IPFieldSerializer
from nautobot.ipam.choices import PrefixTypeChoices, ServiceProtocolChoices
from nautobot.ipam import constants
from nautobot.ipam.models import (
    IPAddress,
    Namespace,
    Prefix,
    RIR,
    RouteTarget,
    Service,
    VLAN,
    VLANGroup,
    VRF,
)


#
# Namespaces
#


class NamespaceSerializer(NautobotModelSerializer, TaggedModelSerializerMixin):
    url = serializers.HyperlinkedIdentityField(view_name="ipam-api:namespace-detail")

    class Meta:
        model = Namespace
        fields = ["url", "name", "description", "location"]


#
# VRFs
#


class VRFSerializer(NautobotModelSerializer, TaggedModelSerializerMixin):
    ipaddress_count = serializers.IntegerField(read_only=True)
    prefix_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = VRF
        fields = "__all__"
        list_display_fields = ["name", "rd", "tenant", "description"]


#
# Route targets
#


class RouteTargetSerializer(NautobotModelSerializer, TaggedModelSerializerMixin):
    class Meta:
        model = RouteTarget
        fields = "__all__"
        list_display_fields = ["name", "tenant", "description"]


#
# RIRs
#


class RIRSerializer(NautobotModelSerializer):
    assigned_prefix_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = RIR
        fields = "__all__"
        list_display_fields = [
            "name",
            "is_private",
            "assigned_prefix_count",
            "description",
        ]


#
# VLANs
#


class VLANGroupSerializer(NautobotModelSerializer):
    vlan_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = VLANGroup
        fields = "__all__"
        list_display_fields = ["name", "location", "vlan_count", "description"]
        # 2.0 TODO: Remove if/when slug is globally unique. This would be a breaking change.
        validators = []

    def validate(self, data):
        # Validate uniqueness of name and slug if a location has been assigned.
        # 2.0 TODO: Remove if/when slug is globally unique. This would be a breaking change.
        if data.get("location", None):
            for field in ["name", "slug"]:
                validator = UniqueTogetherValidator(queryset=VLANGroup.objects.all(), fields=("location", field))
                validator(data, self)

        # Enforce model validation
        super().validate(data)

        return data


class VLANSerializer(NautobotModelSerializer, TaggedModelSerializerMixin):
    prefix_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = VLAN
        # TODO(jathan): These were taken from VLANDetailTable and not VLANTable. Let's make sure
        # these are correct.
        fields = "__all__"
        list_display_fields = [
            "vid",
            "location",
            "vlan_group",
            "name",
            "prefixes",
            "tenant",
            "status",
            "role",
            "description",
        ]
        validators = []

    def validate(self, data):
        # Validate uniqueness of vid and name if a group has been assigned.
        if data.get("vlan_group", None):
            for field in ["vid", "name"]:
                validator = UniqueTogetherValidator(queryset=VLAN.objects.all(), fields=("vlan_group", field))
                validator(data, self)

        # Enforce model validation
        super().validate(data)

        return data


#
# Prefixes
#


class PrefixSerializer(NautobotModelSerializer, TaggedModelSerializerMixin):
    prefix = IPFieldSerializer()
    type = ChoiceField(choices=PrefixTypeChoices, default=PrefixTypeChoices.TYPE_NETWORK)

    class Meta:
        model = Prefix
        fields = "__all__"
        list_display_fields = [
            "prefix",
            "type",
            "status",
            "vrf",
            "tenant",
            "location",
            "vlan",
            "role",
            "description",
        ]
        extra_kwargs = {
            "ip_version": {"read_only": True},
            "prefix_length": {"read_only": True},
        }


class PrefixLengthSerializer(serializers.Serializer):
    prefix_length = serializers.IntegerField()

    def to_internal_value(self, data):
        requested_prefix = data.get("prefix_length")
        if requested_prefix is None:
            raise serializers.ValidationError({"prefix_length": "this field can not be missing"})
        if not isinstance(requested_prefix, int):
            raise serializers.ValidationError({"prefix_length": "this field must be int type"})

        prefix = self.context.get("prefix")
        if prefix.ip_version == 4 and requested_prefix > 32:
            raise serializers.ValidationError({"prefix_length": f"Invalid prefix length ({requested_prefix}) for IPv4"})
        elif prefix.ip_version == 6 and requested_prefix > 128:
            raise serializers.ValidationError({"prefix_length": f"Invalid prefix length ({requested_prefix}) for IPv6"})
        return data


class AvailablePrefixSerializer(serializers.Serializer):
    """
    Representation of a prefix which does not exist in the database.
    """

    ip_version = serializers.IntegerField(read_only=True)
    prefix = serializers.CharField(read_only=True)

    def to_representation(self, instance):
        return OrderedDict(
            [
                ("ip_version", instance.version),
                ("prefix", str(instance)),
                ("namepace", instance.namespace),
            ]
        )


#
# IP addresses
#


class IPAddressSerializer(NautobotModelSerializer, TaggedModelSerializerMixin):
    address = IPFieldSerializer()
    nat_outside_list = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = IPAddress
        fields = "__all__"
        list_display_fields = [
            "address",
            "vrf",
            "status",
            "role",
            "tenant",
            "dns_name",
            "description",
        ]
        extra_kwargs = {
            "ip_version": {"read_only": True},
            "prefix_length": {"read_only": True},
        }

    @extend_schema_field(str)
    def get_nat_outside_list(self, obj):
        try:
            nat_outside_list = obj.nat_outside_list
        except IPAddress.DoesNotExist:
            return None
        depth = get_nested_serializer_depth(self)
        data = return_nested_serializer_data_based_on_depth(
            IPAddressSerializer(nat_outside_list, context={"request": self.context.get("request")}),
            depth,
            obj,
            nat_outside_list,
            "nat_outside_list",
        )
        return data


class AvailableIPSerializer(serializers.Serializer):
    """
    Representation of an IP address which does not exist in the database.
    """

    ip_version = serializers.IntegerField(read_only=True)
    address = serializers.CharField(read_only=True)

    def to_representation(self, instance):
        return OrderedDict(
            [
                ("ip_verison", self.context["prefix"].version),
                ("address", f"{instance}/{self.context['prefix'].prefixlen}"),
                ("namespace", instance.namespace),
            ]
        )


#
# Services
#


class ServiceSerializer(NautobotModelSerializer, TaggedModelSerializerMixin):
    # TODO #3024 make a backlog item to rip out the choice field.
    protocol = ChoiceField(choices=ServiceProtocolChoices, required=False)
    ports = serializers.ListField(
        child=serializers.IntegerField(
            min_value=constants.SERVICE_PORT_MIN,
            max_value=constants.SERVICE_PORT_MAX,
        ),
    )

    class Meta:
        model = Service
        fields = "__all__"
        # TODO(jathan): We need to account for the "parent" field from the `ServiceTable` which is
        # an either/or column for `device` or `virtual_machine`. For now it's hard-coded to
        # `device`.
        # list_display_fields = ["name", "parent", "protocol", "ports", "description"]
        list_display_fields = ["name", "device", "protocol", "ports", "description"]
