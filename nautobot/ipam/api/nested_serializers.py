import netaddr
from rest_framework import serializers

from nautobot.core.api import WritableNestedSerializer
from nautobot.ipam import models

__all__ = [
    "IPFieldSerializer",
    "NestedIPAddressSerializer",
    "NestedPrefixSerializer",
    "NestedRIRSerializer",
    "NestedRouteTargetSerializer",
    "NestedServiceSerializer",
    "NestedVLANGroupSerializer",
    "NestedVLANSerializer",
    "NestedVRFSerializer",
]


class IPFieldSerializer(serializers.CharField):
    def to_representation(self, value):
        """Convert internal (IPNetwork) representation to API (string) representation."""
        return str(value)

    def to_internal_value(self, value):
        """Convert API (string) representation to internal (IPNetwork) representation."""
        try:
            return netaddr.IPNetwork(value)
        except netaddr.AddrFormatError:
            raise serializers.ValidationError(f"Invalid IP address format: {value}")
        except (TypeError, ValueError) as e:
            raise serializers.ValidationError(e)


#
# VRFs
#


class NestedVRFSerializer(WritableNestedSerializer):
    url = serializers.HyperlinkedIdentityField(view_name="ipam-api:vrf-detail")
    prefix_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = models.VRF
        fields = ["id", "url", "name", "rd", "display", "prefix_count"]


#
# Route targets
#


class NestedRouteTargetSerializer(WritableNestedSerializer):
    url = serializers.HyperlinkedIdentityField(view_name="ipam-api:routetarget-detail")

    class Meta:
        model = models.RouteTarget
        fields = ["id", "url", "name"]


#
# RIRs
#


class NestedRIRSerializer(WritableNestedSerializer):
    url = serializers.HyperlinkedIdentityField(view_name="ipam-api:rir-detail")
    assigned_prefix_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = models.RIR
        fields = ["id", "url", "name", "slug", "assigned_prefix_count"]


#
# VLANs
#


class NestedVLANGroupSerializer(WritableNestedSerializer):
    url = serializers.HyperlinkedIdentityField(view_name="ipam-api:vlangroup-detail")
    vlan_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = models.VLANGroup
        fields = ["id", "url", "name", "slug", "vlan_count"]


class NestedVLANSerializer(WritableNestedSerializer):
    url = serializers.HyperlinkedIdentityField(view_name="ipam-api:vlan-detail")

    class Meta:
        model = models.VLAN
        fields = [
            "id",
            "url",
            "vid",
            "name",
        ]


#
# Prefixes
#


class NestedPrefixSerializer(WritableNestedSerializer):
    url = serializers.HyperlinkedIdentityField(view_name="ipam-api:prefix-detail")
    family = serializers.IntegerField(read_only=True)
    prefix = IPFieldSerializer()

    class Meta:
        model = models.Prefix
        fields = ["id", "url", "family", "prefix"]


#
# IP addresses
#


class NestedIPAddressSerializer(WritableNestedSerializer):
    url = serializers.HyperlinkedIdentityField(view_name="ipam-api:ipaddress-detail")
    family = serializers.IntegerField(read_only=True)
    address = IPFieldSerializer()

    class Meta:
        model = models.IPAddress
        fields = ["id", "url", "family", "address"]


#
# Services
#


class NestedServiceSerializer(WritableNestedSerializer):
    url = serializers.HyperlinkedIdentityField(view_name="ipam-api:service-detail")

    class Meta:
        model = models.Service
        fields = ["id", "url", "name", "protocol", "ports"]
