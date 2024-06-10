from nautobot.cloud import filters, models
from nautobot.extras.api.views import NautobotModelViewSet

from . import serializers

#
# Cloud Account
#


class CloudAccountViewSet(NautobotModelViewSet):
    queryset = models.CloudAccount.objects.select_related("provider", "secrets_group")
    serializer_class = serializers.CloudAccountSerializer
    filterset_class = filters.CloudAccountFilterSet


class CloudTypeViewSet(NautobotModelViewSet):
    queryset = models.CloudType.objects.select_related("provider")
    serializer_class = serializers.CloudTypeSerializer
    filterset_class = filters.CloudTypeFilterSet


class CloudNetworkViewSet(NautobotModelViewSet):
    queryset = models.CloudNetwork.objects.select_related("cloud_type", "cloud_account", "parent").prefetch_related(
        "prefixes"
    )
    serializer_class = serializers.CloudNetworkSerializer
    filterset_class = filters.CloudNetworkFilterSet


class CloudNetworkPrefixAssignmentViewSet(NautobotModelViewSet):
    queryset = models.CloudNetworkPrefixAssignment.objects.select_related("cloud_network", "prefix")
    serializer_class = serializers.CloudNetworkPrefixAssignmentSerializer
    filterset_class = filters.CloudNetworkPrefixAssignmentFilterSet
