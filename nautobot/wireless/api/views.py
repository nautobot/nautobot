from nautobot.extras.api.views import ModelViewSet, NautobotModelViewSet
from nautobot.wireless import filters, models

from . import serializers


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


class ControllerManagedDeviceGroupWirelessNetworkAssignmentViewSet(ModelViewSet):
    queryset = models.ControllerManagedDeviceGroupWirelessNetworkAssignment.objects.all()
    serializer_class = serializers.ControllerManagedDeviceGroupWirelessNetworkAssignmentSerializer
    filterset_class = filters.ControllerManagedDeviceGroupWirelessNetworkAssignmentFilterSet


class ControllerManagedDeviceGroupRadioProfileAssignmentViewSet(ModelViewSet):
    queryset = models.ControllerManagedDeviceGroupRadioProfileAssignment.objects.all()
    serializer_class = serializers.ControllerManagedDeviceGroupRadioProfileAssignmentSerializer
    filterset_class = filters.ControllerManagedDeviceGroupRadioProfileAssignmentFilterSet
