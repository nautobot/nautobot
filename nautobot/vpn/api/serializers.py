from nautobot.apps.api import NautobotModelSerializer, TaggedModelSerializerMixin

from .. import models











class VPNProfileSerializer(TaggedModelSerializerMixin, NautobotModelSerializer):  # pylint: disable=too-many-ancestors
    """VPNProfile Serializer."""

    class Meta:
        """Meta attributes."""

        model = models.VPNProfile
        fields = "__all__"


class VPNPhase1PolicySerializer(TaggedModelSerializerMixin, NautobotModelSerializer):  # pylint: disable=too-many-ancestors
    """VPNPhase1Policy Serializer."""

    class Meta:
        """Meta attributes."""

        model = models.VPNPhase1Policy
        fields = "__all__"


class VPNPhase2PolicySerializer(TaggedModelSerializerMixin, NautobotModelSerializer):  # pylint: disable=too-many-ancestors
    """VPNPhase2Policy Serializer."""

    class Meta:
        """Meta attributes."""

        model = models.VPNPhase2Policy
        fields = "__all__"


class VPNSerializer(TaggedModelSerializerMixin, NautobotModelSerializer):  # pylint: disable=too-many-ancestors
    """VPN Serializer."""

    class Meta:
        """Meta attributes."""

        model = models.VPN
        fields = "__all__"


class VPNTunnelSerializer(TaggedModelSerializerMixin, NautobotModelSerializer):  # pylint: disable=too-many-ancestors
    """VPNTunnel Serializer."""

    class Meta:
        """Meta attributes."""

        model = models.VPNTunnel
        fields = "__all__"


class VPNTunnelEndpointSerializer(TaggedModelSerializerMixin, NautobotModelSerializer):  # pylint: disable=too-many-ancestors
    """VPNTunnelEndpoint Serializer."""

    class Meta:
        """Meta attributes."""

        model = models.VPNTunnelEndpoint
        fields = "__all__"

