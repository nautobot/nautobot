from nautobot.circuits import filters
from nautobot.circuits.models import Circuit, CircuitTermination, CircuitType, Provider, ProviderNetwork
from nautobot.core.models.querysets import count_related
from nautobot.dcim.api.views import PathEndpointMixin
from nautobot.extras.api.views import NautobotModelViewSet

from . import serializers

#
# Providers
#


class ProviderViewSet(NautobotModelViewSet):
    queryset = Provider.objects.annotate(circuit_count=count_related(Circuit, "provider"))
    serializer_class = serializers.ProviderSerializer
    filterset_class = filters.ProviderFilterSet


#
#  Circuit Types
#


class CircuitTypeViewSet(NautobotModelViewSet):
    queryset = CircuitType.objects.annotate(circuit_count=count_related(Circuit, "circuit_type"))
    serializer_class = serializers.CircuitTypeSerializer
    filterset_class = filters.CircuitTypeFilterSet


#
# Circuits
#


class CircuitViewSet(NautobotModelViewSet):
    queryset = Circuit.objects.all()
    serializer_class = serializers.CircuitSerializer
    filterset_class = filters.CircuitFilterSet


#
# Circuit Terminations
#


class CircuitTerminationViewSet(PathEndpointMixin, NautobotModelViewSet):
    queryset = CircuitTermination.objects.prefetch_related("_path__destination")
    serializer_class = serializers.CircuitTerminationSerializer
    filterset_class = filters.CircuitTerminationFilterSet


#
# Provider Networks
#


class ProviderNetworkViewSet(NautobotModelViewSet):
    queryset = ProviderNetwork.objects.all()
    serializer_class = serializers.ProviderNetworkSerializer
    filterset_class = filters.ProviderNetworkFilterSet
