from collections import OrderedDict

from rest_framework import serializers
from rest_framework.validators import UniqueTogetherValidator

from nautobot.core.api import (
    ChoiceField,
    NautobotModelSerializer,
    SerializedPKRelatedField,
)
from nautobot.dcim.api.nested_serializers import (
    NestedDeviceSerializer,
    NestedLocationSerializer,
)
from nautobot.extras.api.mixins import (
    RoleModelSerializerMixin,
    StatusModelSerializerMixin,
    TaggedModelSerializerMixin,
)
from nautobot.ipam.choices import IPAddressFamilyChoices, PrefixTypeChoices, ServiceProtocolChoices
from nautobot.ipam import constants
from nautobot.ipam.models import (
    IPAddress,
    Prefix,
    RIR,
    RouteTarget,
    Service,
    VLAN,
    VLANGroup,
    VRF,
)
from nautobot.tenancy.api.nested_serializers import NestedTenantSerializer
from nautobot.virtualization.api.nested_serializers import (
    NestedVirtualMachineSerializer,
)

# Not all of these variable(s) are actually used anywhere in this file, but are required for the
# automagically replacing a Serializer with its corresponding NestedSerializer.
from .nested_serializers import (  # noqa: F401
    IPFieldSerializer,
    NestedIPAddressSerializer,
    NestedPrefixSerializer,
    NestedRIRSerializer,
    NestedRouteTargetSerializer,
    NestedServiceSerializer,
    NestedVLANGroupSerializer,
    NestedVLANSerializer,
    NestedVRFSerializer,
)

#
# VRFs
#


class VRFSerializer(NautobotModelSerializer, TaggedModelSerializerMixin):
    url = serializers.HyperlinkedIdentityField(view_name="ipam-api:vrf-detail")
    import_targets = SerializedPKRelatedField(
        queryset=RouteTarget.objects.all(),
        serializer=NestedRouteTargetSerializer,
        required=False,
        many=True,
    )
    export_targets = SerializedPKRelatedField(
        queryset=RouteTarget.objects.all(),
        serializer=NestedRouteTargetSerializer,
        required=False,
        many=True,
    )
    ipaddress_count = serializers.IntegerField(read_only=True)
    prefix_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = VRF
        fields = [
            "url",
            "name",
            "rd",
            "tenant",
            "enforce_unique",
            "description",
            "import_targets",
            "export_targets",
            "ipaddress_count",
            "prefix_count",
        ]


#
# Route targets
#


class RouteTargetSerializer(NautobotModelSerializer, TaggedModelSerializerMixin):
    url = serializers.HyperlinkedIdentityField(view_name="ipam-api:routetarget-detail")

    class Meta:
        model = RouteTarget
        fields = "__all__"


#
# RIRs
#


class RIRSerializer(NautobotModelSerializer):
    url = serializers.HyperlinkedIdentityField(view_name="ipam-api:rir-detail")
    assigned_prefix_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = RIR
        fields = "__all__"
        extra_fields = ["assigned_prefix_count"]


#
# VLANs
#


class VLANGroupSerializer(NautobotModelSerializer):
    url = serializers.HyperlinkedIdentityField(view_name="ipam-api:vlangroup-detail")
    vlan_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = VLANGroup
        fields = "__all__"
        extra_fields = ["vlan_count"]
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


class VLANSerializer(
    NautobotModelSerializer, TaggedModelSerializerMixin, StatusModelSerializerMixin, RoleModelSerializerMixin
):
    url = serializers.HyperlinkedIdentityField(view_name="ipam-api:vlan-detail")
    prefix_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = VLAN
        fields = "__all__"
        extra_fields = ["prefix_count"]
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


class PrefixSerializer(
    NautobotModelSerializer, TaggedModelSerializerMixin, StatusModelSerializerMixin, RoleModelSerializerMixin
):
    url = serializers.HyperlinkedIdentityField(view_name="ipam-api:prefix-detail")
    family = ChoiceField(choices=IPAddressFamilyChoices, read_only=True)
    prefix = IPFieldSerializer()
    type = ChoiceField(choices=PrefixTypeChoices, default=PrefixTypeChoices.TYPE_NETWORK)

    class Meta:
        model = Prefix
        fields = "__all__"
        read_only_fields = ["family"]


class PrefixLengthSerializer(serializers.Serializer):
    prefix_length = serializers.IntegerField()

    def to_internal_value(self, data):
        requested_prefix = data.get("prefix_length")
        if requested_prefix is None:
            raise serializers.ValidationError({"prefix_length": "this field can not be missing"})
        if not isinstance(requested_prefix, int):
            raise serializers.ValidationError({"prefix_length": "this field must be int type"})

        prefix = self.context.get("prefix")
        if prefix.family == 4 and requested_prefix > 32:
            raise serializers.ValidationError({"prefix_length": f"Invalid prefix length ({requested_prefix}) for IPv4"})
        elif prefix.family == 6 and requested_prefix > 128:
            raise serializers.ValidationError({"prefix_length": f"Invalid prefix length ({requested_prefix}) for IPv6"})
        return data


class AvailablePrefixSerializer(serializers.Serializer):
    """
    Representation of a prefix which does not exist in the database.
    """

    family = serializers.IntegerField(read_only=True)
    prefix = serializers.CharField(read_only=True)

    def to_representation(self, instance):
        if self.context.get("vrf"):
            vrf = VRFSerializer(self.context["vrf"], context={"request": self.context["request"]}).data
        else:
            vrf = None
        return OrderedDict(
            [
                ("family", instance.version),
                ("prefix", str(instance)),
                ("vrf", vrf),
            ]
        )


#
# IP addresses
#


class IPAddressSerializer(
    NautobotModelSerializer, TaggedModelSerializerMixin, StatusModelSerializerMixin, RoleModelSerializerMixin
):
    url = serializers.HyperlinkedIdentityField(view_name="ipam-api:ipaddress-detail")
    family = ChoiceField(choices=IPAddressFamilyChoices, read_only=True)
    address = IPFieldSerializer()

    class Meta:
        model = IPAddress
        fields = "__all__"
        read_only_fields = ["family"]


class AvailableIPSerializer(serializers.Serializer):
    """
    Representation of an IP address which does not exist in the database.
    """

    family = serializers.IntegerField(read_only=True)
    address = serializers.CharField(read_only=True)

    def to_representation(self, instance):
        if self.context.get("vrf"):
            vrf = VRFSerializer(self.context["vrf"], context={"request": self.context["request"]}).data
        else:
            vrf = None
        return OrderedDict(
            [
                ("family", self.context["prefix"].version),
                ("address", f"{instance}/{self.context['prefix'].prefixlen}"),
                ("vrf", vrf),
            ]
        )


#
# Services
#


class ServiceSerializer(NautobotModelSerializer, TaggedModelSerializerMixin):
    url = serializers.HyperlinkedIdentityField(view_name="ipam-api:service-detail")
    protocol = ChoiceField(choices=ServiceProtocolChoices, required=False)
    ip_addresses = SerializedPKRelatedField(
        queryset=IPAddress.objects.all(),
        serializer=NestedIPAddressSerializer,
        required=False,
        many=True,
    )
    ports = serializers.ListField(
        child=serializers.IntegerField(
            min_value=constants.SERVICE_PORT_MIN,
            max_value=constants.SERVICE_PORT_MAX,
        )
    )

    class Meta:
        model = Service
        fields = "__all__"
