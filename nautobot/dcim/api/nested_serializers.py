from rest_framework import serializers

from nautobot.core.api import WritableNestedSerializer
from nautobot.dcim import models

__all__ = [
    "NestedDeviceSerializer",
    "NestedInterfaceSerializer",
    "NestedRearPortSerializer",
]

#
# Devices
#


class NestedDeviceSerializer(WritableNestedSerializer):
    url = serializers.HyperlinkedIdentityField(view_name="dcim-api:device-detail")

    class Meta:
        model = models.Device
        fields = ["id", "url", "name"]


class NestedInterfaceSerializer(WritableNestedSerializer):
    device = NestedDeviceSerializer(read_only=True)
    url = serializers.HyperlinkedIdentityField(view_name="dcim-api:interface-detail")

    class Meta:
        model = models.Interface
        fields = ["id", "url", "device", "name", "cable"]


class NestedRearPortSerializer(WritableNestedSerializer):
    device = NestedDeviceSerializer(read_only=True)
    url = serializers.HyperlinkedIdentityField(view_name="dcim-api:rearport-detail")

    class Meta:
        model = models.RearPort
        fields = ["id", "url", "device", "name", "cable"]
