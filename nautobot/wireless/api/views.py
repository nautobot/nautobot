from nautobot.extras.api.views import NautobotModelViewSet
from nautobot.wireless import filters, models

from . import serializers


class AccessPointGroupViewSet(NautobotModelViewSet):
    queryset = models.AccessPointGroup.objects.all()
    serializer_class = serializers.AccessPointGroupSerializer
    filterset_class = filters.AccessPointGroupFilterSet


class SupportedDataRateViewSet(NautobotModelViewSet):
    queryset = models.SupportedDataRate.objects.all()
    serializer_class = serializers.SupportedDataRateSerializer
    filterset_class = filters.SupportedDataRateFilterSet


class RadioProfileViewSet(NautobotModelViewSet):
    queryset = models.RadioProfile.objects.all()
    serializer_class = serializers.RadioProfileSerializer
    filterset_class = filters.RadioProfileFilterSet


class WirelessNetworkViewSet(NautobotModelViewSet):
    queryset = models.WirelessNetwork.objects.all()
    serializer_class = serializers.WirelessNetworkSerializer
    filterset_class = filters.WirelessNetworkFilterSet


class AccessPointGroupWirelessNetworkAssignmentViewSet(NautobotModelViewSet):
    queryset = models.AccessPointGroupWirelessNetworkAssignment.objects.all()
    serializer_class = serializers.AccessPointGroupWirelessNetworkAssignmentSerializer
    filterset_class = filters.AccessPointGroupWirelessNetworkAssignmentFilterSet


class AccessPointGroupRadioProfileAssignmentViewSet(NautobotModelViewSet):
    queryset = models.AccessPointGroupRadioProfileAssignment.objects.all()
    serializer_class = serializers.AccessPointGroupRadioProfileAssignmentSerializer
    filterset_class = filters.AccessPointGroupRadioProfileAssignmentFilterSet
