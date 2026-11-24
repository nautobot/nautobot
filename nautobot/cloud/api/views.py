from nautobot.cloud import filters, models
from nautobot.extras.api.views import ModelViewSet, NautobotModelViewSet

from . import serializers

#
# Cloud Account
#


class CloudAccountViewSet(NautobotModelViewSet):
    queryset = models.CloudAccount.objects.all()
    serializer_class = serializers.CloudAccountSerializer
    filterset_class = filters.CloudAccountFilterSet


class CloudAccountGroupViewSet(NautobotModelViewSet):
    queryset = models.CloudAccountGroup.objects.all()
    serializer_class = serializers.CloudAccountGroupSerializer
    filterset_class = filters.CloudAccountGroupFilterSet


class CloudResourceGroupViewSet(NautobotModelViewSet):
    queryset = models.CloudResourceGroup.objects.all()
    serializer_class = serializers.CloudResourceGroupSerializer
    filterset_class = filters.CloudResourceGroupFilterSet


class CloudResourceTypeViewSet(NautobotModelViewSet):
    queryset = models.CloudResourceType.objects.all()
    serializer_class = serializers.CloudResourceTypeSerializer
    filterset_class = filters.CloudResourceTypeFilterSet


class CloudNetworkViewSet(NautobotModelViewSet):
    queryset = models.CloudNetwork.objects.all()
    serializer_class = serializers.CloudNetworkSerializer
    filterset_class = filters.CloudNetworkFilterSet


class CloudNetworkPrefixAssignmentViewSet(ModelViewSet):
    queryset = models.CloudNetworkPrefixAssignment.objects.all()
    serializer_class = serializers.CloudNetworkPrefixAssignmentSerializer
    filterset_class = filters.CloudNetworkPrefixAssignmentFilterSet


class CloudServiceViewSet(NautobotModelViewSet):
    queryset = models.CloudService.objects.all()
    serializer_class = serializers.CloudServiceSerializer
    filterset_class = filters.CloudServiceFilterSet


class CloudServiceNetworkAssignmentViewSet(ModelViewSet):
    queryset = models.CloudServiceNetworkAssignment.objects.all()
    serializer_class = serializers.CloudServiceNetworkAssignmentSerializer
    filterset_class = filters.CloudServiceNetworkAssignmentFilterSet


class CloudServiceIPAddressAssignmentViewSet(ModelViewSet):
    queryset = models.CloudServiceIPAddressAssignment.objects.all()
    serializer_class = serializers.CloudServiceIPAddressAssignmentSerializer
    filterset_class = filters.CloudServiceIPAddressAssignmentFilterSet
