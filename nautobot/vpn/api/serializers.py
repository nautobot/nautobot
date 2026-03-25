from django.contrib.contenttypes.models import ContentType
from rest_framework import serializers
from rest_framework.serializers import ChoiceField, ListField

from nautobot.apps.api import NautobotModelSerializer, TaggedModelSerializerMixin
from nautobot.core.api.fields import ContentTypeField
from nautobot.core.api.utils import get_nested_serializer_depth, return_nested_serializer_data_based_on_depth

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

#
# L2VPN Serializers
#

class L2VPNSerializer(TaggedModelSerializerMixin, NautobotModelSerializer):  # pylint: disable=too-many-ancestors
    """Serializer for L2VPN."""

    class Meta:
        model = models.L2VPN
        fields = "__all__"


class L2VPNTerminationSerializer(TaggedModelSerializerMixin, NautobotModelSerializer):  # pylint: disable=too-many-ancestors
    """Serializer for L2VPNTermination."""

    assigned_object_type = ContentTypeField(
        queryset=ContentType.objects.filter(
            model__in=["interface", "vlan", "vminterface"]
        ),
    )
    assigned_object = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = models.L2VPNTermination
        fields = "__all__"

    def get_assigned_object(self, obj):
        """Return the assigned object (Interface, VLAN, or VMInterface)."""
        if obj.assigned_object is None:
            return None
        try:
            depth = get_nested_serializer_depth(self)
            return return_nested_serializer_data_based_on_depth(
                self, depth, obj, obj.assigned_object
            )
        except (KeyError, AttributeError, TypeError):
            # Fallback when nested serializer lookup fails for this content type.
            # Returns minimal representation matching depth=0 format.
            depth = get_nested_serializer_depth(self)
            ct = obj.assigned_object_type
            result = {
                "id": str(obj.assigned_object_id),
                "object_type": f"{ct.app_label}.{ct.model}",
                "url": f"/api/{ct.app_label}/{ct.model}s/{obj.assigned_object_id}/",
            }
            if depth > 0:
                assigned_obj = obj.assigned_object
                if hasattr(assigned_obj, "name"):
                    result["display"] = str(assigned_obj)
            return result
