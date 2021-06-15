import netaddr
from rest_framework import serializers

from nautobot.core.api import WritableNestedSerializer
from nautobot.core.api.serializers import ComputedFieldModelSerializer
from nautobot.ipam import models

__all__ = [
    "IPFieldSerializer",
    "NestedAggregateSerializer",
    "NestedIPAddressSerializer",
    "NestedPrefixSerializer",
    "NestedRIRSerializer",
    "NestedRoleSerializer",
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
            raise serializers.ValidationError("Invalid IP address format: {}".format(value))
        except (TypeError, ValueError) as e:
            raise serializers.ValidationError(e)


#
# VRFs
#


class NestedVRFSerializer(WritableNestedSerializer, ComputedFieldModelSerializer):
    url = serializers.HyperlinkedIdentityField(view_name="ipam-api:vrf-detail")
    prefix_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = models.VRF
        fields = ["id", "url", "name", "rd", "display", "prefix_count", "computed_fields"]
        opt_in_fields = ["computed_fields"]


#
# Route targets
#


class NestedRouteTargetSerializer(WritableNestedSerializer, ComputedFieldModelSerializer):
    url = serializers.HyperlinkedIdentityField(view_name="ipam-api:routetarget-detail")

    class Meta:
        model = models.RouteTarget
        fields = ["id", "url", "name", "computed_fields"]
        opt_in_fields = ["computed_fields"]


#
# RIRs/aggregates
#


class NestedRIRSerializer(WritableNestedSerializer, ComputedFieldModelSerializer):
    url = serializers.HyperlinkedIdentityField(view_name="ipam-api:rir-detail")
    aggregate_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = models.RIR
        fields = ["id", "url", "name", "slug", "aggregate_count", "computed_fields"]
        opt_in_fields = ["computed_fields"]


class NestedAggregateSerializer(WritableNestedSerializer, ComputedFieldModelSerializer):
    url = serializers.HyperlinkedIdentityField(view_name="ipam-api:aggregate-detail")
    family = serializers.IntegerField(read_only=True)
    prefix = IPFieldSerializer()

    class Meta:
        model = models.Aggregate
        fields = ["id", "url", "family", "prefix", "computed_fields"]
        opt_in_fields = ["computed_fields"]


#
# VLANs
#


class NestedRoleSerializer(WritableNestedSerializer, ComputedFieldModelSerializer):
    url = serializers.HyperlinkedIdentityField(view_name="ipam-api:role-detail")
    prefix_count = serializers.IntegerField(read_only=True)
    vlan_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = models.Role
        fields = ["id", "url", "name", "slug", "prefix_count", "vlan_count", "computed_fields"]
        opt_in_fields = ["computed_fields"]


class NestedVLANGroupSerializer(WritableNestedSerializer, ComputedFieldModelSerializer):
    url = serializers.HyperlinkedIdentityField(view_name="ipam-api:vlangroup-detail")
    vlan_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = models.VLANGroup
        fields = ["id", "url", "name", "slug", "vlan_count", "computed_fields"]
        opt_in_fields = ["computed_fields"]


class NestedVLANSerializer(WritableNestedSerializer, ComputedFieldModelSerializer):
    url = serializers.HyperlinkedIdentityField(view_name="ipam-api:vlan-detail")

    class Meta:
        model = models.VLAN
        fields = ["id", "url", "vid", "name", "computed_fields"]
        opt_in_fields = ["computed_fields"]


#
# Prefixes
#


class NestedPrefixSerializer(WritableNestedSerializer, ComputedFieldModelSerializer):
    url = serializers.HyperlinkedIdentityField(view_name="ipam-api:prefix-detail")
    family = serializers.IntegerField(read_only=True)
    prefix = IPFieldSerializer()

    class Meta:
        model = models.Prefix
        fields = ["id", "url", "family", "prefix", "computed_fields"]
        opt_in_fields = ["computed_fields"]


#
# IP addresses
#


class NestedIPAddressSerializer(WritableNestedSerializer, ComputedFieldModelSerializer):
    url = serializers.HyperlinkedIdentityField(view_name="ipam-api:ipaddress-detail")
    family = serializers.IntegerField(read_only=True)
    address = IPFieldSerializer()

    class Meta:
        model = models.IPAddress
        fields = ["id", "url", "family", "address", "computed_fields"]
        opt_in_fields = ["computed_fields"]


#
# Services
#


class NestedServiceSerializer(WritableNestedSerializer, ComputedFieldModelSerializer):
    url = serializers.HyperlinkedIdentityField(view_name="ipam-api:service-detail")

    class Meta:
        model = models.Service
        fields = ["id", "url", "name", "protocol", "ports", "computed_fields"]
        opt_in_fields = ["computed_fields"]
