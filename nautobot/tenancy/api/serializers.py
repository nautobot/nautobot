from rest_framework import serializers

from nautobot.core.api import TreeModelSerializerMixin
from nautobot.extras.api.serializers import NautobotModelSerializer, TaggedModelSerializerMixin
from nautobot.tenancy.models import Tenant, TenantGroup

#
# Tenants
#


class TenantGroupSerializer(NautobotModelSerializer, TreeModelSerializerMixin):
    url = serializers.HyperlinkedIdentityField(view_name="tenancy-api:tenantgroup-detail")
    tenant_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = TenantGroup
        fields = "__all__"
        extra_fields = ["tenant_count"]


class TenantSerializer(NautobotModelSerializer, TaggedModelSerializerMixin):
    url = serializers.HyperlinkedIdentityField(view_name="tenancy-api:tenant-detail")
    circuit_count = serializers.IntegerField(read_only=True)
    device_count = serializers.IntegerField(read_only=True)
    ipaddress_count = serializers.IntegerField(read_only=True)
    prefix_count = serializers.IntegerField(read_only=True)
    rack_count = serializers.IntegerField(read_only=True)
    virtualmachine_count = serializers.IntegerField(read_only=True)
    vlan_count = serializers.IntegerField(read_only=True)
    vrf_count = serializers.IntegerField(read_only=True)
    cluster_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Tenant
        fields = "__all__"
        extra_fields = [
            "circuit_count",
            "device_count",
            "ipaddress_count",
            "prefix_count",
            "rack_count",
            "virtualmachine_count",
            "vlan_count",
            "vrf_count",
            "cluster_count",
        ]
