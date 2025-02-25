from rest_framework import serializers

from nautobot.core.api import ChoiceField, NautobotModelSerializer, ValidatedModelSerializer
from nautobot.extras.api.mixins import (
    TaggedModelSerializerMixin,
)
from nautobot.wireless import models
from nautobot.wireless.choices import RadioProfileChannelWidthChoices


class SupportedDataRateSerializer(TaggedModelSerializerMixin, NautobotModelSerializer):
    class Meta:
        model = models.SupportedDataRate
        fields = "__all__"


class RadioProfileSerializer(TaggedModelSerializerMixin, NautobotModelSerializer):
    channel_width = serializers.ListField(
        child=ChoiceField(choices=RadioProfileChannelWidthChoices),
        allow_empty=True,
        required=False,
    )
    allowed_channel_list = serializers.ListField(
        child=serializers.IntegerField(required=False),
        allow_empty=True,
        required=False,
    )

    class Meta:
        model = models.RadioProfile
        fields = "__all__"


class WirelessNetworkSerializer(TaggedModelSerializerMixin, NautobotModelSerializer):
    class Meta:
        model = models.WirelessNetwork
        fields = "__all__"


class ControllerManagedDeviceGroupWirelessNetworkAssignmentSerializer(ValidatedModelSerializer):
    class Meta:
        model = models.ControllerManagedDeviceGroupWirelessNetworkAssignment
        fields = "__all__"


class ControllerManagedDeviceGroupRadioProfileAssignmentSerializer(ValidatedModelSerializer):
    class Meta:
        model = models.ControllerManagedDeviceGroupRadioProfileAssignment
        fields = "__all__"
