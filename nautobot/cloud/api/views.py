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


class CloudResourceTypeViewSet(NautobotModelViewSet):
    queryset = models.CloudResourceType.objects.select_related("provider")
    serializer_class = serializers.CloudResourceTypeSerializer
    filterset_class = filters.CloudResourceTypeFilterSet


class CloudNetworkViewSet(NautobotModelViewSet):
    queryset = models.CloudNetwork.objects.select_related(
        "cloud_resource_type", "cloud_account", "parent"
    ).prefetch_related("prefixes")
    serializer_class = serializers.CloudNetworkSerializer
    filterset_class = filters.CloudNetworkFilterSet


class CloudNetworkPrefixAssignmentViewSet(NautobotModelViewSet):
    queryset = models.CloudNetworkPrefixAssignment.objects.select_related("cloud_network", "prefix")
    serializer_class = serializers.CloudNetworkPrefixAssignmentSerializer
    filterset_class = filters.CloudNetworkPrefixAssignmentFilterSet


class CloudServiceViewSet(NautobotModelViewSet):
    queryset = models.CloudService.objects.select_related("cloud_account", "cloud_resource_type").prefetch_related(
        "cloud_networks"
    )
    serializer_class = serializers.CloudServiceSerializer
    filterset_class = filters.CloudServiceFilterSet


class CloudServiceNetworkAssignmentViewSet(NautobotModelViewSet):
    queryset = models.CloudServiceNetworkAssignment.objects.select_related("cloud_network", "cloud_service")
    serializer_class = serializers.CloudServiceNetworkAssignmentSerializer
    filterset_class = filters.CloudServiceNetworkAssignmentFilterSet
