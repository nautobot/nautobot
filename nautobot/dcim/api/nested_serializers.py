from rest_framework import serializers

from nautobot.core.api import WritableNestedSerializer
from nautobot.dcim import models

__all__ = [
    "NestedDeviceSerializer",
]

#
# Devices
#


class NestedDeviceSerializer(WritableNestedSerializer):
    url = serializers.HyperlinkedIdentityField(view_name="dcim-api:device-detail")

    class Meta:
        model = models.Device
        fields = ["id", "url", "name"]
