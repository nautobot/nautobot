from rest_framework import serializers

from nautobot.circuits.models import Provider, Circuit, CircuitTermination, CircuitType, ProviderNetwork
from nautobot.core.api import WritableNestedSerializer
from nautobot.dcim.api.nested_serializers import (
    NestedCableSerializer,
    NestedInterfaceSerializer,
    NestedLocationSerializer,
    NestedSiteSerializer,
)
from nautobot.dcim.api.serializers import (
    CableTerminationModelSerializerMixin,
    PathEndpointModelSerializerMixin,
)
from nautobot.extras.api.serializers import (
    NautobotModelSerializer,
    NotesSerializerMixin,
    StatusModelSerializerMixin,
    TaggedModelSerializerMixin,
)
from nautobot.tenancy.api.nested_serializers import NestedTenantSerializer

# Not all of these variable(s) are not actually used anywhere in this file, but required for the
# automagically replacing a Serializer with its corresponding NestedSerializer.
from .nested_serializers import (  # noqa: F401
    NestedCircuitSerializer,
    NestedCircuitTerminationSerializer,
    NestedCircuitTypeSerializer,
    NestedProviderNetworkSerializer,
    NestedProviderSerializer,
)

#
# Providers
#


class ProviderSerializer(NautobotModelSerializer, TaggedModelSerializerMixin):
    url = serializers.HyperlinkedIdentityField(view_name="circuits-api:provider-detail")
    circuit_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Provider
        fields = [
            "url",
            "name",
            "slug",
            "asn",
            "account",
            "portal_url",
            "noc_contact",
            "admin_contact",
            "comments",
            "circuit_count",
        ]


#
# Provider Network
#


class ProviderNetworkSerializer(NautobotModelSerializer, TaggedModelSerializerMixin):
    url = serializers.HyperlinkedIdentityField(view_name="circuits-api:providernetwork-detail")
    provider = NestedProviderSerializer()

    class Meta:
        model = ProviderNetwork
        fields = [
            "url",
            "provider",
            "name",
            "slug",
            "description",
            "comments",
        ]


#
# Circuits
#


class CircuitTypeSerializer(NautobotModelSerializer):
    url = serializers.HyperlinkedIdentityField(view_name="circuits-api:circuittype-detail")
    circuit_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = CircuitType
        fields = [
            "url",
            "name",
            "slug",
            "description",
            "circuit_count",
        ]


class CircuitCircuitTerminationSerializer(WritableNestedSerializer, NotesSerializerMixin):
    url = serializers.HyperlinkedIdentityField(view_name="circuits-api:circuittermination-detail")
    site = NestedSiteSerializer()
    location = NestedLocationSerializer(required=False, allow_null=True)
    provider_network = NestedProviderNetworkSerializer()
    connected_endpoint = NestedInterfaceSerializer()

    class Meta:
        model = CircuitTermination
        fields = [
            "id",
            "url",
            "site",
            "location",
            "provider_network",
            "connected_endpoint",
            "port_speed",
            "upstream_speed",
            "xconnect_id",
        ]


class CircuitSerializer(NautobotModelSerializer, StatusModelSerializerMixin, TaggedModelSerializerMixin):
    url = serializers.HyperlinkedIdentityField(view_name="circuits-api:circuit-detail")
    provider = NestedProviderSerializer()
    type = NestedCircuitTypeSerializer()
    tenant = NestedTenantSerializer(required=False, allow_null=True)
    termination_a = CircuitCircuitTerminationSerializer(read_only=True)
    termination_z = CircuitCircuitTerminationSerializer(read_only=True)

    class Meta:
        model = Circuit
        fields = [
            "url",
            "cid",
            "provider",
            "type",
            "status",
            "tenant",
            "install_date",
            "commit_rate",
            "description",
            "termination_a",
            "termination_z",
            "comments",
        ]


class CircuitTerminationSerializer(
    NautobotModelSerializer,
    CableTerminationModelSerializerMixin,
    PathEndpointModelSerializerMixin,
):
    url = serializers.HyperlinkedIdentityField(view_name="circuits-api:circuittermination-detail")
    circuit = NestedCircuitSerializer()
    site = NestedSiteSerializer(required=False, allow_null=True)
    location = NestedLocationSerializer(required=False, allow_null=True)
    provider_network = NestedProviderNetworkSerializer(required=False, allow_null=True)
    cable = NestedCableSerializer(read_only=True)

    class Meta:
        model = CircuitTermination
        fields = [
            "url",
            "circuit",
            "term_side",
            "site",
            "location",
            "provider_network",
            "port_speed",
            "upstream_speed",
            "xconnect_id",
            "pp_info",
            "description",
            "cable",
            "cable_peer",
            "cable_peer_type",
            "connected_endpoint",
            "connected_endpoint_type",
            "connected_endpoint_reachable",
        ]
