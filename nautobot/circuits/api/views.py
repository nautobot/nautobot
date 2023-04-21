from rest_framework.routers import APIRootView

from nautobot.circuits import filters
from nautobot.circuits.models import Provider, CircuitTermination, CircuitType, Circuit, ProviderNetwork
from nautobot.core.models.querysets import count_related
from nautobot.dcim.api.views import PathEndpointMixin
from nautobot.extras.api.views import NautobotModelViewSet
from . import serializers


class CircuitsRootView(APIRootView):
    """
    Circuits API root view
    """

    def get_view_name(self):
        return "Circuits"


#
# Providers
#


class ProviderViewSet(NautobotModelViewSet):
    queryset = Provider.objects.prefetch_related("tags").annotate(circuit_count=count_related(Circuit, "provider"))
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
    queryset = Circuit.objects.select_related(
        "status", "circuit_type", "tenant", "provider", "circuit_termination_a", "circuit_termination_z"
    ).prefetch_related("tags")
    serializer_class = serializers.CircuitSerializer
    filterset_class = filters.CircuitFilterSet


#
# Circuit Terminations
#


class CircuitTerminationViewSet(PathEndpointMixin, NautobotModelViewSet):
    queryset = CircuitTermination.objects.select_related("circuit", "location", "cable").prefetch_related(
        "_path__destination"
    )
    serializer_class = serializers.CircuitTerminationSerializer
    filterset_class = filters.CircuitTerminationFilterSet


#
# Provider Networks
#


class ProviderNetworkViewSet(NautobotModelViewSet):
    queryset = ProviderNetwork.objects.prefetch_related("tags")
    serializer_class = serializers.ProviderNetworkSerializer
    filterset_class = filters.ProviderNetworkFilterSet
