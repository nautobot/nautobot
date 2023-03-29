from rest_framework import serializers

from nautobot.circuits.models import Provider, Circuit, CircuitTermination, CircuitType, ProviderNetwork
from nautobot.dcim.api.serializers import (
    CableTerminationModelSerializerMixin,
    PathEndpointModelSerializerMixin,
)
from nautobot.extras.api.serializers import (
    NautobotModelSerializer,
    StatusModelSerializerMixin,
    TaggedModelSerializerMixin,
)

#
# Providers
#


class ProviderSerializer(NautobotModelSerializer, TaggedModelSerializerMixin):
    url = serializers.HyperlinkedIdentityField(view_name="circuits-api:provider-detail")
    circuit_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Provider
        fields = "__all__"
        extra_fields = ["circuit_count"]


#
# Provider Network
#


class ProviderNetworkSerializer(NautobotModelSerializer, TaggedModelSerializerMixin):
    url = serializers.HyperlinkedIdentityField(view_name="circuits-api:providernetwork-detail")

    class Meta:
        model = ProviderNetwork
        fields = "__all__"


#
# Circuits
#


class CircuitTypeSerializer(NautobotModelSerializer):
    url = serializers.HyperlinkedIdentityField(view_name="circuits-api:circuittype-detail")
    circuit_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = CircuitType
        fields = "__all__"
        extra_fields = ["circuit_count"]


class CircuitSerializer(NautobotModelSerializer, StatusModelSerializerMixin, TaggedModelSerializerMixin):
    url = serializers.HyperlinkedIdentityField(view_name="circuits-api:circuit-detail")

    class Meta:
        model = Circuit
        fields = "__all__"


class CircuitTerminationSerializer(
    NautobotModelSerializer,
    CableTerminationModelSerializerMixin,
    PathEndpointModelSerializerMixin,
):
    url = serializers.HyperlinkedIdentityField(view_name="circuits-api:circuittermination-detail")

    class Meta:
        model = CircuitTermination
        fields = "__all__"
