"""API views for nautobot_load_balancer_models."""

from nautobot.extras.api.views import ModelViewSet, NautobotModelViewSet
from nautobot.load_balancers import filters, models
from nautobot.load_balancers.api import serializers


class VirtualServerViewSet(NautobotModelViewSet):  # pylint: disable=too-many-ancestors
    """VirtualServer viewset."""

    queryset = models.VirtualServer.objects.all()
    serializer_class = serializers.VirtualServerSerializer
    filterset_class = filters.VirtualServerFilterSet


class LoadBalancerPoolViewSet(NautobotModelViewSet):  # pylint: disable=too-many-ancestors
    """LoadBalancerPool viewset."""

    queryset = models.LoadBalancerPool.objects.all()
    serializer_class = serializers.LoadBalancerPoolSerializer
    filterset_class = filters.LoadBalancerPoolFilterSet


class LoadBalancerPoolMemberViewSet(NautobotModelViewSet):  # pylint: disable=too-many-ancestors
    """LoadBalancerPoolMember viewset."""

    queryset = models.LoadBalancerPoolMember.objects.all()
    serializer_class = serializers.LoadBalancerPoolMemberSerializer
    filterset_class = filters.LoadBalancerPoolMemberFilterSet


class HealthCheckMonitorViewSet(NautobotModelViewSet):  # pylint: disable=too-many-ancestors
    """HealthCheckMonitor viewset."""

    queryset = models.HealthCheckMonitor.objects.all()
    serializer_class = serializers.HealthCheckMonitorSerializer
    filterset_class = filters.HealthCheckMonitorFilterSet


class CertificateProfileViewSet(NautobotModelViewSet):  # pylint: disable=too-many-ancestors
    """CertificateProfile viewset."""

    queryset = models.CertificateProfile.objects.all()
    serializer_class = serializers.CertificateProfileSerializer
    filterset_class = filters.CertificateProfileFilterSet


class VirtualServerCertificateProfileAssignmentViewSet(ModelViewSet):  # pylint: disable=too-many-ancestors
    """VirtualServerCertificateProfileAssignment viewset."""

    queryset = models.VirtualServerCertificateProfileAssignment.objects.all()
    serializer_class = serializers.VirtualServerCertificateProfileAssignmentSerializer
    filterset_class = filters.VirtualServerCertificateProfileAssignmentFilterSet


class LoadBalancerPoolMemberCertificateProfileAssignmentViewSet(ModelViewSet):  # pylint: disable=too-many-ancestors
    """LoadBalancerPoolMemberCertificateProfileAssignment viewset."""

    queryset = models.LoadBalancerPoolMemberCertificateProfileAssignment.objects.all()
    serializer_class = serializers.LoadBalancerPoolMemberCertificateProfileAssignmentSerializer
    filterset_class = filters.LoadBalancerPoolMemberCertificateProfileAssignmentFilterSet
