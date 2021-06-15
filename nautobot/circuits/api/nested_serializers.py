from rest_framework import serializers

from nautobot.circuits.models import Circuit, CircuitTermination, CircuitType, Provider
from nautobot.core.api import WritableNestedSerializer

__all__ = [
    "NestedCircuitSerializer",
    "NestedCircuitTerminationSerializer",
    "NestedCircuitTypeSerializer",
    "NestedProviderSerializer",
]


#
# Providers
#
from nautobot.core.api.serializers import ComputedFieldModelSerializer


class NestedProviderSerializer(WritableNestedSerializer, ComputedFieldModelSerializer):
    url = serializers.HyperlinkedIdentityField(view_name="circuits-api:provider-detail")
    circuit_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Provider
        fields = ["id", "url", "name", "slug", "circuit_count", "computed_fields"]
        opt_in_fields = ["computed_fields"]


#
# Circuits
#


class NestedCircuitTypeSerializer(WritableNestedSerializer, ComputedFieldModelSerializer):
    url = serializers.HyperlinkedIdentityField(view_name="circuits-api:circuittype-detail")
    circuit_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = CircuitType
        fields = ["id", "url", "name", "slug", "circuit_count", "computed_fields"]
        opt_in_fields = ["computed_fields"]


class NestedCircuitSerializer(WritableNestedSerializer, ComputedFieldModelSerializer):
    url = serializers.HyperlinkedIdentityField(view_name="circuits-api:circuit-detail")

    class Meta:
        model = Circuit
        fields = ["id", "url", "cid", "computed_fields"]
        opt_in_fields = ["computed_fields"]


class NestedCircuitTerminationSerializer(WritableNestedSerializer):
    url = serializers.HyperlinkedIdentityField(view_name="circuits-api:circuittermination-detail")
    circuit = NestedCircuitSerializer()

    class Meta:
        model = CircuitTermination
        fields = ["id", "url", "circuit", "term_side", "cable"]
