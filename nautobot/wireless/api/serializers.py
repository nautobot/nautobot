from rest_framework import serializers
from rest_framework.validators import UniqueTogetherValidator

from nautobot.core.api import ChoiceField, NautobotModelSerializer, ValidatedModelSerializer
from nautobot.extras.api.mixins import (
    TaggedModelSerializerMixin,
)
from nautobot.wireless import models
from nautobot.wireless.choices import RadioProfileChannelWidthChoices


class AccessPointGroupSerializer(TaggedModelSerializerMixin, NautobotModelSerializer):
    class Meta:
        model = models.AccessPointGroup
        fields = "__all__"
        validators = []

    def validate(self, data):
        """Validate the uniqueness of the controller and name together. This is required because the controller can be omitted."""
        if data.get("controller", None):
            validator = UniqueTogetherValidator(
                queryset=models.AccessPointGroup.objects.all(),
                fields=["controller", "name"],
            )
            validator(data, self)

        # Enforce model validation
        super().validate(data)

        return data


class SupportedDataRateSerializer(TaggedModelSerializerMixin, NautobotModelSerializer):
    class Meta:
        model = models.SupportedDataRate
        fields = "__all__"


class RadioProfileSerializer(TaggedModelSerializerMixin, NautobotModelSerializer):
    channel_width = serializers.ListField(child=ChoiceField(choices=RadioProfileChannelWidthChoices))
    allowed_channel_list = serializers.ListField(
        child=serializers.IntegerField(required=False),
        allow_empty=True,
    )

    class Meta:
        model = models.RadioProfile
        fields = "__all__"


class WirelessNetworkSerializer(TaggedModelSerializerMixin, NautobotModelSerializer):
    class Meta:
        model = models.WirelessNetwork
        fields = "__all__"


class AccessPointGroupWirelessNetworkAssignmentSerializer(ValidatedModelSerializer):
    class Meta:
        model = models.AccessPointGroupWirelessNetworkAssignment
        fields = "__all__"


class AccessPointGroupRadioProfileAssignmentSerializer(ValidatedModelSerializer):
    class Meta:
        model = models.AccessPointGroupRadioProfileAssignment
        fields = "__all__"
