from rest_framework.serializers import ChoiceField, ListField

from nautobot.apps.api import NautobotModelSerializer, TaggedModelSerializerMixin

from .. import choices, models


class VPNProfileSerializer(TaggedModelSerializerMixin, NautobotModelSerializer):  # pylint: disable=too-many-ancestors
    """VPNProfile Serializer."""

    class Meta:
        """Meta attributes."""

        model = models.VPNProfile
        fields = "__all__"


class VPNPhase1PolicySerializer(TaggedModelSerializerMixin, NautobotModelSerializer):  # pylint: disable=too-many-ancestors
    """VPNPhase1Policy Serializer."""

    encryption_algorithm = ListField(
        child=ChoiceField(choices=choices.EncryptionAlgorithmChoices),
        allow_empty=True,
        required=False,
    )
    integrity_algorithm = ListField(
        child=ChoiceField(choices=choices.IntegrityAlgorithmChoices),
        allow_empty=True,
        required=False,
    )
    dh_group = ListField(
        child=ChoiceField(choices=choices.DhGroupChoices),
        allow_empty=True,
        required=False,
    )

    class Meta:
        """Meta attributes."""

        model = models.VPNPhase1Policy
        fields = "__all__"


class VPNPhase2PolicySerializer(TaggedModelSerializerMixin, NautobotModelSerializer):  # pylint: disable=too-many-ancestors
    """VPNPhase2Policy Serializer."""

    encryption_algorithm = ListField(
        child=ChoiceField(choices=choices.EncryptionAlgorithmChoices),
        allow_empty=True,
        required=False,
    )
    integrity_algorithm = ListField(
        child=ChoiceField(choices=choices.IntegrityAlgorithmChoices),
        allow_empty=True,
        required=False,
    )
    pfs_group = ListField(
        child=ChoiceField(choices=choices.DhGroupChoices),
        allow_empty=True,
        required=False,
    )

    class Meta:
        """Meta attributes."""

        model = models.VPNPhase2Policy
        fields = "__all__"


class VPNProfilePhase1PolicyAssignmentSerializer(NautobotModelSerializer):
    """Serializer for `VPNProfilePhase1PolicyAssignment` objects."""

    class Meta:
        model = models.VPNProfilePhase1PolicyAssignment
        fields = "__all__"


class VPNProfilePhase2PolicyAssignmentSerializer(NautobotModelSerializer):
    """Serializer for `VPNProfilePhase2PolicyAssignment` objects."""

    class Meta:
        model = models.VPNProfilePhase2PolicyAssignment
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
