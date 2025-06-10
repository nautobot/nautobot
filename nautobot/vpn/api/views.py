"""API views for the vpn models."""

from nautobot.apps.api import ModelViewSet, NautobotModelViewSet

from .. import filters, models
from ..api import serializers


class VPNProfileViewSet(NautobotModelViewSet):  # pylint: disable=too-many-ancestors
    """VPNProfile viewset."""

    queryset = models.VPNProfile.objects.all()
    serializer_class = serializers.VPNProfileSerializer
    filterset_class = filters.VPNProfileFilterSet


class VPNPhase1PolicyViewSet(NautobotModelViewSet):  # pylint: disable=too-many-ancestors
    """VPNPhase1Policy viewset."""

    queryset = models.VPNPhase1Policy.objects.all()
    serializer_class = serializers.VPNPhase1PolicySerializer
    filterset_class = filters.VPNPhase1PolicyFilterSet


class VPNPhase2PolicyViewSet(NautobotModelViewSet):  # pylint: disable=too-many-ancestors
    """VPNPhase2Policy viewset."""

    queryset = models.VPNPhase2Policy.objects.all()
    serializer_class = serializers.VPNPhase2PolicySerializer
    filterset_class = filters.VPNPhase2PolicyFilterSet


class VPNProfilePhase1PolicyAssignmentViewSet(ModelViewSet):  # pylint: disable=too-many-ancestors
    """VPNProfilePhase1PolicyAssignment viewset."""

    queryset = models.VPNProfilePhase1PolicyAssignment.objects.all()
    serializer_class = serializers.VPNProfilePhase1PolicyAssignmentSerializer
    filterset_class = filters.VPNProfilePhase1PolicyAssignmentFilterSet


class VPNProfilePhase2PolicyAssignmentViewSet(ModelViewSet):  # pylint: disable=too-many-ancestors
    """VPNProfilePhase2PolicyAssignment viewset."""

    queryset = models.VPNProfilePhase2PolicyAssignment.objects.all()
    serializer_class = serializers.VPNProfilePhase2PolicyAssignmentSerializer
    filterset_class = filters.VPNProfilePhase2PolicyAssignmentFilterSet


class VPNViewSet(NautobotModelViewSet):  # pylint: disable=too-many-ancestors
    """VPN viewset."""

    queryset = models.VPN.objects.all()
    serializer_class = serializers.VPNSerializer
    filterset_class = filters.VPNFilterSet


class VPNTunnelViewSet(NautobotModelViewSet):  # pylint: disable=too-many-ancestors
    """VPNTunnel viewset."""

    queryset = models.VPNTunnel.objects.all()
    serializer_class = serializers.VPNTunnelSerializer
    filterset_class = filters.VPNTunnelFilterSet


class VPNTunnelEndpointViewSet(NautobotModelViewSet):  # pylint: disable=too-many-ancestors
    """VPNTunnelEndpoint viewset."""

    queryset = models.VPNTunnelEndpoint.objects.all()
    serializer_class = serializers.VPNTunnelEndpointSerializer
    filterset_class = filters.VPNTunnelEndpointFilterSet
