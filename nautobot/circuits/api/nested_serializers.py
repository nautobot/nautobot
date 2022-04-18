from rest_framework import serializers

from nautobot.circuits.models import Circuit, CircuitTermination, CircuitType, Provider, ProviderNetwork
from nautobot.core.api import WritableNestedSerializer

__all__ = [
    "NestedCircuitSerializer",
    "NestedCircuitTerminationSerializer",
    "NestedCircuitTypeSerializer",
    "NestedProviderSerializer",
    "NestedProviderNetworkSerializer",
]

#
# Provider Networks
#


class NestedProviderNetworkSerializer(WritableNestedSerializer):
    url = serializers.HyperlinkedIdentityField(view_name="circuits-api:providernetwork-detail")

    class Meta:
        model = ProviderNetwork
        fields = ["id", "url", "name", "slug"]


#
# Providers
#


class NestedProviderSerializer(WritableNestedSerializer):
    url = serializers.HyperlinkedIdentityField(view_name="circuits-api:provider-detail")
    circuit_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Provider
        fields = ["id", "url", "name", "slug", "circuit_count"]


#
# Circuits
#


class NestedCircuitTypeSerializer(WritableNestedSerializer):
    url = serializers.HyperlinkedIdentityField(view_name="circuits-api:circuittype-detail")
    circuit_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = CircuitType
        fields = ["id", "url", "name", "slug", "circuit_count"]


class NestedCircuitSerializer(WritableNestedSerializer):
    url = serializers.HyperlinkedIdentityField(view_name="circuits-api:circuit-detail")

    class Meta:
        model = Circuit
        fields = ["id", "url", "cid"]


class NestedCircuitTerminationSerializer(WritableNestedSerializer):
    url = serializers.HyperlinkedIdentityField(view_name="circuits-api:circuittermination-detail")
    circuit = NestedCircuitSerializer()

    class Meta:
        model = CircuitTermination
        fields = ["id", "url", "circuit", "term_side", "cable"]
