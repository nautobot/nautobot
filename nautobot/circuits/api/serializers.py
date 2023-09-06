from rest_framework import serializers

from nautobot.circuits.models import Provider, Circuit, CircuitTermination, CircuitType, ProviderNetwork
from nautobot.core.api import NautobotModelSerializer
from nautobot.dcim.api.serializers import (
    CableTerminationModelSerializerMixin,
    PathEndpointModelSerializerMixin,
)
from nautobot.extras.api.mixins import (
    TaggedModelSerializerMixin,
)

#
# Providers
#


class ProviderSerializer(NautobotModelSerializer, TaggedModelSerializerMixin):
    circuit_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Provider
        fields = "__all__"


#
# Provider Network
#


class ProviderNetworkSerializer(NautobotModelSerializer, TaggedModelSerializerMixin):
    class Meta:
        model = ProviderNetwork
        fields = "__all__"


#
# Circuits
#


class CircuitTypeSerializer(NautobotModelSerializer):
    circuit_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = CircuitType
        fields = "__all__"


class CircuitSerializer(NautobotModelSerializer, TaggedModelSerializerMixin):
    class Meta:
        model = Circuit
        fields = "__all__"


class CircuitTerminationSerializer(
    NautobotModelSerializer,
    CableTerminationModelSerializerMixin,
    PathEndpointModelSerializerMixin,
):
    class Meta:
        model = CircuitTermination
        fields = "__all__"
        extra_kwargs = {"cable": {"read_only": True}}
