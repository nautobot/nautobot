from rest_framework import serializers
from drf_spectacular.utils import extend_schema_field

from nautobot.core.api import WritableNestedSerializer
from nautobot.tenancy.models import Tenant, TenantGroup
from nautobot.utilities.api import TreeModelSerializerMixin

__all__ = [
    "NestedTenantGroupSerializer",
    "NestedTenantSerializer",
]


#
# Tenants
#


class NestedTenantGroupSerializer(WritableNestedSerializer, TreeModelSerializerMixin):
    url = serializers.HyperlinkedIdentityField(view_name="tenancy-api:tenantgroup-detail")
    tenant_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = TenantGroup
        fields = ["id", "url", "name", "slug", "tenant_count", "tree_depth"]


class NestedTenantSerializer(WritableNestedSerializer):
    url = serializers.HyperlinkedIdentityField(view_name="tenancy-api:tenant-detail")

    class Meta:
        model = Tenant
        fields = ["id", "url", "name", "slug"]
