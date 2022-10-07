from rest_framework.routers import APIRootView

from nautobot.circuits import filters
from nautobot.circuits.models import Provider, CircuitTermination, CircuitType, Circuit, ProviderNetwork
from nautobot.dcim.api.views import PathEndpointMixin
from nautobot.extras.api.views import NautobotModelViewSet, StatusViewSetMixin
from nautobot.utilities.utils import count_related
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
    queryset = CircuitType.objects.annotate(circuit_count=count_related(Circuit, "type"))
    serializer_class = serializers.CircuitTypeSerializer
    filterset_class = filters.CircuitTypeFilterSet


#
# Circuits
#


class CircuitViewSet(StatusViewSetMixin, NautobotModelViewSet):
    # v2 TODO(jathan): Replace prefetch_related with select_related (for tags it should stay)
    queryset = Circuit.objects.prefetch_related(
        "status", "type", "tenant", "provider", "termination_a", "termination_z"
    ).prefetch_related("tags")
    serializer_class = serializers.CircuitSerializer
    filterset_class = filters.CircuitFilterSet


#
# Circuit Terminations
#


class CircuitTerminationViewSet(PathEndpointMixin, NautobotModelViewSet):
    # v2 TODO(jathan): Replace prefetch_related with select_related
    queryset = CircuitTermination.objects.prefetch_related("circuit", "site", "_path__destination", "cable")
    serializer_class = serializers.CircuitTerminationSerializer
    filterset_class = filters.CircuitTerminationFilterSet
    brief_prefetch_fields = ["circuit"]


#
# Provider Networks
#


class ProviderNetworkViewSet(NautobotModelViewSet):
    queryset = ProviderNetwork.objects.prefetch_related("tags")
    serializer_class = serializers.ProviderNetworkSerializer
    filterset_class = filters.ProviderNetworkFilterSet
