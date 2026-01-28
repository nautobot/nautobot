"""API serializers for nautobot_load_balancer_models."""

from nautobot.core.api import NautobotModelSerializer, ValidatedModelSerializer
from nautobot.extras.api.mixins import TaggedModelSerializerMixin
from nautobot.load_balancers import models


class VirtualServerSerializer(TaggedModelSerializerMixin, NautobotModelSerializer):  # pylint: disable=too-many-ancestors
    """VirtualServer Serializer."""

    class Meta:
        """Meta attributes."""

        model = models.VirtualServer
        fields = "__all__"


class LoadBalancerPoolSerializer(TaggedModelSerializerMixin, NautobotModelSerializer):  # pylint: disable=too-many-ancestors
    """LoadBalancerPool Serializer."""

    class Meta:
        """Meta attributes."""

        model = models.LoadBalancerPool
        fields = "__all__"


class LoadBalancerPoolMemberSerializer(TaggedModelSerializerMixin, NautobotModelSerializer):  # pylint: disable=too-many-ancestors
    """LoadBalancerPoolMember Serializer."""

    class Meta:
        """Meta attributes."""

        model = models.LoadBalancerPoolMember
        fields = "__all__"


class HealthCheckMonitorSerializer(TaggedModelSerializerMixin, NautobotModelSerializer):  # pylint: disable=too-many-ancestors
    """HealthCheckMonitor Serializer."""

    class Meta:
        """Meta attributes."""

        model = models.HealthCheckMonitor
        fields = "__all__"


class CertificateProfileSerializer(TaggedModelSerializerMixin, NautobotModelSerializer):  # pylint: disable=too-many-ancestors
    """CertificateProfile Serializer."""

    class Meta:
        """Meta attributes."""

        model = models.CertificateProfile
        fields = "__all__"


class VirtualServerCertificateProfileAssignmentSerializer(ValidatedModelSerializer):  # pylint: disable=too-many-ancestors
    """VirtualServerCertificateProfileAssignment Serializer."""

    class Meta:
        """Meta attributes."""

        model = models.VirtualServerCertificateProfileAssignment
        fields = "__all__"


class LoadBalancerPoolMemberCertificateProfileAssignmentSerializer(ValidatedModelSerializer):  # pylint: disable=too-many-ancestors
    """LoadBalancerPoolMemberCertificateProfileAssignment Serializer."""

    class Meta:
        """Meta attributes."""

        model = models.LoadBalancerPoolMemberCertificateProfileAssignment
        fields = "__all__"
