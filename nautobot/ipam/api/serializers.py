from collections import OrderedDict

from rest_framework import serializers
from rest_framework.validators import UniqueTogetherValidator

from nautobot.core.api import (
    ChoiceField,
    NautobotModelSerializer,
)
from nautobot.extras.api.mixins import TaggedModelSerializerMixin
from nautobot.ipam.api.fields import IPFieldSerializer
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
    family = ChoiceField(choices=IPAddressFamilyChoices, read_only=True)
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
            "family": {"read_only": True},
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


class IPAddressSerializer(NautobotModelSerializer, TaggedModelSerializerMixin):
    family = ChoiceField(choices=IPAddressFamilyChoices, read_only=True)
    address = IPFieldSerializer()

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
            "family": {"read_only": True},
            "prefix_length": {"read_only": True},
            "nat_outside_list": {"read_only": True},
        }

    def get_field_names(self, declared_fields, info):
        """Add nat_outside_list reverse relation to the automatically discovered fields."""
        fields = list(super().get_field_names(declared_fields, info))
        self.extend_field_names(fields, "nat_outside_list")
        return fields


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
        extra_kwargs = {
            "device": {"help_text": "Required if no virtual_machine is specified"},
            "virtual_machine": {"help_text": "Required if no device is specified"},
        }
        # TODO(jathan): We need to account for the "parent" field from the `ServiceTable` which is
        # an either/or column for `device` or `virtual_machine`. For now it's hard-coded to
        # `device`.
        # list_display_fields = ["name", "parent", "protocol", "ports", "description"]
        list_display_fields = ["name", "device", "protocol", "ports", "description"]
