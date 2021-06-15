from rest_framework import serializers

from nautobot.core.api import BaseModelSerializer, WritableNestedSerializer
from nautobot.dcim import models
from nautobot.core.api.serializers import ComputedFieldModelSerializer

__all__ = [
    "NestedCableSerializer",
    "NestedConsolePortSerializer",
    "NestedConsolePortTemplateSerializer",
    "NestedConsoleServerPortSerializer",
    "NestedConsoleServerPortTemplateSerializer",
    "NestedDeviceBaySerializer",
    "NestedDeviceBayTemplateSerializer",
    "NestedDeviceRoleSerializer",
    "NestedDeviceSerializer",
    "NestedDeviceTypeSerializer",
    "NestedFrontPortSerializer",
    "NestedFrontPortTemplateSerializer",
    "NestedInterfaceSerializer",
    "NestedInterfaceTemplateSerializer",
    "NestedInventoryItemSerializer",
    "NestedManufacturerSerializer",
    "NestedPlatformSerializer",
    "NestedPowerFeedSerializer",
    "NestedPowerOutletSerializer",
    "NestedPowerOutletTemplateSerializer",
    "NestedPowerPanelSerializer",
    "NestedPowerPortSerializer",
    "NestedPowerPortTemplateSerializer",
    "NestedRackGroupSerializer",
    "NestedRackReservationSerializer",
    "NestedRackRoleSerializer",
    "NestedRackSerializer",
    "NestedRearPortSerializer",
    "NestedRearPortTemplateSerializer",
    "NestedRegionSerializer",
    "NestedSiteSerializer",
    "NestedVirtualChassisSerializer",
]


#
# Regions/sites
#


class NestedRegionSerializer(WritableNestedSerializer, ComputedFieldModelSerializer):
    url = serializers.HyperlinkedIdentityField(view_name="dcim-api:region-detail")
    site_count = serializers.IntegerField(read_only=True)
    _depth = serializers.IntegerField(source="level", read_only=True)

    class Meta:
        model = models.Region
        fields = ["id", "url", "name", "slug", "site_count", "_depth", "computed_fields"]
        opt_in_fields = ["computed_fields"]


class NestedSiteSerializer(WritableNestedSerializer, ComputedFieldModelSerializer):
    url = serializers.HyperlinkedIdentityField(view_name="dcim-api:site-detail")

    class Meta:
        model = models.Site
        fields = ["id", "url", "name", "slug", "computed_fields"]
        opt_in_fields = ["computed_fields"]


#
# Racks
#


class NestedRackGroupSerializer(WritableNestedSerializer, ComputedFieldModelSerializer):
    url = serializers.HyperlinkedIdentityField(view_name="dcim-api:rackgroup-detail")
    rack_count = serializers.IntegerField(read_only=True)
    _depth = serializers.IntegerField(source="level", read_only=True)

    class Meta:
        model = models.RackGroup
        fields = ["id", "url", "name", "slug", "rack_count", "_depth", "computed_fields"]
        opt_in_fields = ["computed_fields"]


class NestedRackRoleSerializer(WritableNestedSerializer, ComputedFieldModelSerializer):
    url = serializers.HyperlinkedIdentityField(view_name="dcim-api:rackrole-detail")
    rack_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = models.RackRole
        fields = ["id", "url", "name", "slug", "rack_count", "computed_fields"]
        opt_in_fields = ["computed_fields"]


class NestedRackSerializer(WritableNestedSerializer, ComputedFieldModelSerializer):
    url = serializers.HyperlinkedIdentityField(view_name="dcim-api:rack-detail")
    device_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = models.Rack
        fields = ["id", "url", "name", "device_count", "computed_fields"]
        opt_in_fields = ["computed_fields"]


class NestedRackReservationSerializer(WritableNestedSerializer, ComputedFieldModelSerializer):
    url = serializers.HyperlinkedIdentityField(view_name="dcim-api:rackreservation-detail")
    user = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = models.RackReservation
        fields = ["id", "url", "user", "units", "computed_fields"]
        opt_in_fields = ["computed_fields"]

    def get_user(self, obj):
        return obj.user.username


#
# Device types
#


class NestedManufacturerSerializer(WritableNestedSerializer, ComputedFieldModelSerializer):
    url = serializers.HyperlinkedIdentityField(view_name="dcim-api:manufacturer-detail")
    devicetype_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = models.Manufacturer
        fields = ["id", "url", "name", "slug", "devicetype_count", "computed_fields"]
        opt_in_fields = ["computed_fields"]


class NestedDeviceTypeSerializer(WritableNestedSerializer, ComputedFieldModelSerializer):
    url = serializers.HyperlinkedIdentityField(view_name="dcim-api:devicetype-detail")
    manufacturer = NestedManufacturerSerializer(read_only=True)
    device_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = models.DeviceType
        fields = ["id", "url", "manufacturer", "model", "slug", "device_count", "computed_fields"]
        opt_in_fields = ["computed_fields"]


class NestedConsolePortTemplateSerializer(WritableNestedSerializer, ComputedFieldModelSerializer):
    url = serializers.HyperlinkedIdentityField(view_name="dcim-api:consoleporttemplate-detail")

    class Meta:
        model = models.ConsolePortTemplate
        fields = ["id", "url", "name", "computed_fields"]
        opt_in_fields = ["computed_fields"]


class NestedConsoleServerPortTemplateSerializer(WritableNestedSerializer):
    url = serializers.HyperlinkedIdentityField(view_name="dcim-api:consoleserverporttemplate-detail")

    class Meta:
        model = models.ConsoleServerPortTemplate
        fields = ["id", "url", "name"]


class NestedPowerPortTemplateSerializer(WritableNestedSerializer, ComputedFieldModelSerializer):
    url = serializers.HyperlinkedIdentityField(view_name="dcim-api:powerporttemplate-detail")

    class Meta:
        model = models.PowerPortTemplate
        fields = ["id", "url", "name", "computed_fields"]
        opt_in_fields = ["computed_fields"]


class NestedPowerOutletTemplateSerializer(WritableNestedSerializer, ComputedFieldModelSerializer):
    url = serializers.HyperlinkedIdentityField(view_name="dcim-api:poweroutlettemplate-detail")

    class Meta:
        model = models.PowerOutletTemplate
        fields = ["id", "url", "name", "computed_fields"]
        opt_in_fields = ["computed_fields"]


class NestedInterfaceTemplateSerializer(WritableNestedSerializer, ComputedFieldModelSerializer):
    url = serializers.HyperlinkedIdentityField(view_name="dcim-api:interfacetemplate-detail")

    class Meta:
        model = models.InterfaceTemplate
        fields = ["id", "url", "name", "computed_fields"]
        opt_in_fields = ["computed_fields"]


class NestedRearPortTemplateSerializer(WritableNestedSerializer):
    url = serializers.HyperlinkedIdentityField(view_name="dcim-api:rearporttemplate-detail")

    class Meta:
        model = models.RearPortTemplate
        fields = ["id", "url", "name"]


class NestedFrontPortTemplateSerializer(WritableNestedSerializer, ComputedFieldModelSerializer):
    url = serializers.HyperlinkedIdentityField(view_name="dcim-api:frontporttemplate-detail")

    class Meta:
        model = models.FrontPortTemplate
        fields = ["id", "url", "name", "computed_fields"]
        opt_in_fields = ["computed_fields"]


class NestedDeviceBayTemplateSerializer(WritableNestedSerializer, ComputedFieldModelSerializer):
    url = serializers.HyperlinkedIdentityField(view_name="dcim-api:devicebaytemplate-detail")

    class Meta:
        model = models.DeviceBayTemplate
        fields = ["id", "url", "name", "computed_fields"]
        opt_in_fields = ["computed_fields"]


#
# Devices
#


class NestedDeviceRoleSerializer(WritableNestedSerializer, ComputedFieldModelSerializer):
    url = serializers.HyperlinkedIdentityField(view_name="dcim-api:devicerole-detail")
    device_count = serializers.IntegerField(read_only=True)
    virtualmachine_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = models.DeviceRole
        fields = ["id", "url", "name", "slug", "device_count", "virtualmachine_count", "computed_fields"]
        opt_in_fields = ["computed_fields"]


class NestedPlatformSerializer(WritableNestedSerializer, ComputedFieldModelSerializer):
    url = serializers.HyperlinkedIdentityField(view_name="dcim-api:platform-detail")
    device_count = serializers.IntegerField(read_only=True)
    virtualmachine_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = models.Platform
        fields = ["id", "url", "name", "slug", "device_count", "virtualmachine_count", "computed_fields"]
        opt_in_fields = ["computed_fields"]


class NestedDeviceSerializer(WritableNestedSerializer, ComputedFieldModelSerializer):
    url = serializers.HyperlinkedIdentityField(view_name="dcim-api:device-detail")

    class Meta:
        model = models.Device
        fields = ["id", "url", "name", "computed_fields"]
        opt_in_fields = ["computed_fields"]


class NestedConsoleServerPortSerializer(WritableNestedSerializer, ComputedFieldModelSerializer):
    url = serializers.HyperlinkedIdentityField(view_name="dcim-api:consoleserverport-detail")
    device = NestedDeviceSerializer(read_only=True)

    class Meta:
        model = models.ConsoleServerPort
        fields = ["id", "url", "device", "name", "cable", "computed_fields"]
        opt_in_fields = ["computed_fields"]


class NestedConsolePortSerializer(WritableNestedSerializer, ComputedFieldModelSerializer):
    url = serializers.HyperlinkedIdentityField(view_name="dcim-api:consoleport-detail")
    device = NestedDeviceSerializer(read_only=True)

    class Meta:
        model = models.ConsolePort
        fields = ["id", "url", "device", "name", "cable", "computed_fields"]
        opt_in_fields = ["computed_fields"]


class NestedPowerOutletSerializer(WritableNestedSerializer, ComputedFieldModelSerializer):
    url = serializers.HyperlinkedIdentityField(view_name="dcim-api:poweroutlet-detail")
    device = NestedDeviceSerializer(read_only=True)

    class Meta:
        model = models.PowerOutlet
        fields = ["id", "url", "device", "name", "cable", "computed_fields"]
        opt_in_fields = ["computed_fields"]


class NestedPowerPortSerializer(WritableNestedSerializer, ComputedFieldModelSerializer):
    url = serializers.HyperlinkedIdentityField(view_name="dcim-api:powerport-detail")
    device = NestedDeviceSerializer(read_only=True)

    class Meta:
        model = models.PowerPort
        fields = ["id", "url", "device", "name", "cable", "computed_fields"]
        opt_in_fields = ["computed_fields"]


class NestedInterfaceSerializer(WritableNestedSerializer, ComputedFieldModelSerializer):
    device = NestedDeviceSerializer(read_only=True)
    url = serializers.HyperlinkedIdentityField(view_name="dcim-api:interface-detail")

    class Meta:
        model = models.Interface
        fields = ["id", "url", "device", "name", "cable", "computed_fields"]
        opt_in_fields = ["computed_fields"]


class NestedRearPortSerializer(WritableNestedSerializer, ComputedFieldModelSerializer):
    device = NestedDeviceSerializer(read_only=True)
    url = serializers.HyperlinkedIdentityField(view_name="dcim-api:rearport-detail")

    class Meta:
        model = models.RearPort
        fields = ["id", "url", "device", "name", "cable", "computed_fields"]
        opt_in_fields = ["computed_fields"]


class NestedFrontPortSerializer(WritableNestedSerializer, ComputedFieldModelSerializer):
    device = NestedDeviceSerializer(read_only=True)
    url = serializers.HyperlinkedIdentityField(view_name="dcim-api:frontport-detail")

    class Meta:
        model = models.FrontPort
        fields = ["id", "url", "device", "name", "cable", "computed_fields"]
        opt_in_fields = ["computed_fields"]


class NestedDeviceBaySerializer(WritableNestedSerializer, ComputedFieldModelSerializer):
    url = serializers.HyperlinkedIdentityField(view_name="dcim-api:devicebay-detail")
    device = NestedDeviceSerializer(read_only=True)

    class Meta:
        model = models.DeviceBay
        fields = ["id", "url", "device", "name", "computed_fields"]
        opt_in_fields = ["computed_fields"]


class NestedInventoryItemSerializer(WritableNestedSerializer, ComputedFieldModelSerializer):
    url = serializers.HyperlinkedIdentityField(view_name="dcim-api:inventoryitem-detail")
    device = NestedDeviceSerializer(read_only=True)
    _depth = serializers.IntegerField(source="level", read_only=True)

    class Meta:
        model = models.InventoryItem
        fields = ["id", "url", "device", "name", "_depth", "computed_fields"]
        opt_in_fields = ["computed_fields"]


#
# Cables
#


class NestedCableSerializer(BaseModelSerializer, ComputedFieldModelSerializer):
    url = serializers.HyperlinkedIdentityField(view_name="dcim-api:cable-detail")

    class Meta:
        model = models.Cable
        fields = ["id", "url", "label"]


#
# Virtual chassis
#


class NestedVirtualChassisSerializer(WritableNestedSerializer, ComputedFieldModelSerializer):
    url = serializers.HyperlinkedIdentityField(view_name="dcim-api:virtualchassis-detail")
    master = NestedDeviceSerializer()
    member_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = models.VirtualChassis
        fields = ["id", "name", "url", "master", "member_count", "computed_fields"]
        opt_in_fields = ["computed_fields"]


#
# Power panels/feeds
#


class NestedPowerPanelSerializer(WritableNestedSerializer, ComputedFieldModelSerializer):
    url = serializers.HyperlinkedIdentityField(view_name="dcim-api:powerpanel-detail")
    powerfeed_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = models.PowerPanel
        fields = ["id", "url", "name", "powerfeed_count", "computed_fields"]
        opt_in_fields = ["computed_fields"]


class NestedPowerFeedSerializer(WritableNestedSerializer, ComputedFieldModelSerializer):
    url = serializers.HyperlinkedIdentityField(view_name="dcim-api:powerfeed-detail")

    class Meta:
        model = models.PowerFeed
        fields = ["id", "url", "name", "cable", "computed_fields"]
        opt_in_fields = ["computed_fields"]
