from rest_framework import serializers

from nautobot.extras.api.serializers import NautobotModelSerializer, TaggedObjectSerializer
from nautobot.tenancy.models import Tenant, TenantGroup

# Not all of these variable(s) are not actually used anywhere in this file, but required for the
# automagically replacing a Serializer with its corresponding NestedSerializer.
from .nested_serializers import NestedTenantGroupSerializer, NestedTenantSerializer  # noqa: F401

#
# Tenants
#


class TenantGroupSerializer(NautobotModelSerializer):
    url = serializers.HyperlinkedIdentityField(view_name="tenancy-api:tenantgroup-detail")
    parent = NestedTenantGroupSerializer(required=False, allow_null=True)
    tenant_count = serializers.IntegerField(read_only=True)
    _depth = serializers.IntegerField(source="level", read_only=True)

    class Meta:
        model = TenantGroup
        fields = [
            "url",
            "name",
            "slug",
            "parent",
            "description",
            "tenant_count",
            "_depth",
        ]


class TenantSerializer(NautobotModelSerializer, TaggedObjectSerializer):
    url = serializers.HyperlinkedIdentityField(view_name="tenancy-api:tenant-detail")
    group = NestedTenantGroupSerializer(required=False)
    circuit_count = serializers.IntegerField(read_only=True)
    device_count = serializers.IntegerField(read_only=True)
    ipaddress_count = serializers.IntegerField(read_only=True)
    prefix_count = serializers.IntegerField(read_only=True)
    rack_count = serializers.IntegerField(read_only=True)
    site_count = serializers.IntegerField(read_only=True)
    virtualmachine_count = serializers.IntegerField(read_only=True)
    vlan_count = serializers.IntegerField(read_only=True)
    vrf_count = serializers.IntegerField(read_only=True)
    cluster_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Tenant
        fields = [
            "url",
            "name",
            "slug",
            "group",
            "description",
            "comments",
            "circuit_count",
            "device_count",
            "ipaddress_count",
            "prefix_count",
            "rack_count",
            "site_count",
            "virtualmachine_count",
            "vlan_count",
            "vrf_count",
            "cluster_count",
        ]
