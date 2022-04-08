from django.contrib.contenttypes.models import ContentType
from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers
from rest_framework.validators import UniqueTogetherValidator

from nautobot.core.api import (
    ChoiceField,
    ContentTypeField,
    SerializedPKRelatedField,
    TimeZoneSerializerField,
    ValidatedModelSerializer,
    WritableNestedSerializer,
)

from nautobot.dcim.choices import (
    CableLengthUnitChoices,
    ConsolePortTypeChoices,
    DeviceFaceChoices,
    InterfaceModeChoices,
    InterfaceTypeChoices,
    PortTypeChoices,
    PowerFeedPhaseChoices,
    PowerFeedSupplyChoices,
    PowerFeedTypeChoices,
    PowerOutletFeedLegChoices,
    PowerOutletTypeChoices,
    PowerPortTypeChoices,
    RackDimensionUnitChoices,
    RackElevationDetailRenderChoices,
    RackTypeChoices,
    RackWidthChoices,
    SubdeviceRoleChoices,
)
from nautobot.dcim.constants import CABLE_TERMINATION_MODELS, RACK_ELEVATION_LEGEND_WIDTH_DEFAULT
from nautobot.dcim.models import (
    Cable,
    CablePath,
    ConsolePort,
    ConsolePortTemplate,
    ConsoleServerPort,
    ConsoleServerPortTemplate,
    Device,
    DeviceBay,
    DeviceBayTemplate,
    DeviceType,
    DeviceRole,
    FrontPort,
    FrontPortTemplate,
    Interface,
    InterfaceTemplate,
    Manufacturer,
    InventoryItem,
    Platform,
    PowerFeed,
    PowerOutlet,
    PowerOutletTemplate,
    PowerPanel,
    PowerPort,
    PowerPortTemplate,
    Rack,
    RackGroup,
    RackReservation,
    RackRole,
    RearPort,
    RearPortTemplate,
    Region,
    Site,
    VirtualChassis,
)
from nautobot.extras.api.customfields import CustomFieldModelSerializer
from nautobot.extras.api.serializers import (
    StatusModelSerializerMixin,
    TaggedObjectSerializer,
)
from nautobot.extras.api.nested_serializers import NestedConfigContextSchemaSerializer, NestedSecretsGroupSerializer
from nautobot.ipam.api.nested_serializers import (
    NestedIPAddressSerializer,
    NestedVLANSerializer,
)
from nautobot.ipam.models import VLAN
from nautobot.tenancy.api.nested_serializers import NestedTenantSerializer
from nautobot.users.api.nested_serializers import NestedUserSerializer
from nautobot.utilities.api import get_serializer_for_model
from nautobot.utilities.config import get_settings_or_config
from nautobot.virtualization.api.nested_serializers import NestedClusterSerializer

# Not all of these variable(s) are not actually used anywhere in this file, but required for the
# automagically replacing a Serializer with its corresponding NestedSerializer.
from .nested_serializers import (  # noqa: F401
    NestedCableSerializer,
    NestedConsolePortSerializer,
    NestedConsolePortTemplateSerializer,
    NestedConsoleServerPortSerializer,
    NestedConsoleServerPortTemplateSerializer,
    NestedDeviceBaySerializer,
    NestedDeviceBayTemplateSerializer,
    NestedDeviceRoleSerializer,
    NestedDeviceSerializer,
    NestedDeviceTypeSerializer,
    NestedFrontPortSerializer,
    NestedFrontPortTemplateSerializer,
    NestedInterfaceSerializer,
    NestedInterfaceTemplateSerializer,
    NestedInventoryItemSerializer,
    NestedManufacturerSerializer,
    NestedPlatformSerializer,
    NestedPowerFeedSerializer,
    NestedPowerOutletSerializer,
    NestedPowerOutletTemplateSerializer,
    NestedPowerPanelSerializer,
    NestedPowerPortSerializer,
    NestedPowerPortTemplateSerializer,
    NestedRackGroupSerializer,
    NestedRackReservationSerializer,
    NestedRackRoleSerializer,
    NestedRackSerializer,
    NestedRearPortSerializer,
    NestedRearPortTemplateSerializer,
    NestedRegionSerializer,
    NestedSiteSerializer,
    NestedVirtualChassisSerializer,
)


class CableTerminationSerializer(serializers.ModelSerializer):
    cable_peer_type = serializers.SerializerMethodField(read_only=True)
    cable_peer = serializers.SerializerMethodField(read_only=True)

    @extend_schema_field(serializers.CharField(allow_null=True))
    def get_cable_peer_type(self, obj):
        if obj._cable_peer is not None:
            return f"{obj._cable_peer._meta.app_label}.{obj._cable_peer._meta.model_name}"
        return None

    @extend_schema_field(serializers.DictField(allow_null=True))
    def get_cable_peer(self, obj):
        """
        Return the appropriate serializer for the cable termination model.
        """
        if obj._cable_peer is not None:
            serializer = get_serializer_for_model(obj._cable_peer, prefix="Nested")
            context = {"request": self.context["request"]}
            return serializer(obj._cable_peer, context=context).data
        return None


class ConnectedEndpointSerializer(ValidatedModelSerializer):
    connected_endpoint_type = serializers.SerializerMethodField(read_only=True)
    connected_endpoint = serializers.SerializerMethodField(read_only=True)
    connected_endpoint_reachable = serializers.SerializerMethodField(read_only=True)

    @extend_schema_field(serializers.CharField(allow_null=True))
    def get_connected_endpoint_type(self, obj):
        if obj._path is not None and obj._path.destination is not None:
            return f"{obj._path.destination._meta.app_label}.{obj._path.destination._meta.model_name}"
        return None

    @extend_schema_field(serializers.DictField(allow_null=True))
    def get_connected_endpoint(self, obj):
        """
        Return the appropriate serializer for the type of connected object.
        """
        if obj._path is not None and obj._path.destination is not None:
            serializer = get_serializer_for_model(obj._path.destination, prefix="Nested")
            context = {"request": self.context["request"]}
            return serializer(obj._path.destination, context=context).data
        return None

    @extend_schema_field(serializers.BooleanField(allow_null=True))
    def get_connected_endpoint_reachable(self, obj):
        if obj._path is not None:
            return obj._path.is_active
        return None


#
# Regions/sites
#


class RegionSerializer(CustomFieldModelSerializer):
    url = serializers.HyperlinkedIdentityField(view_name="dcim-api:region-detail")
    parent = NestedRegionSerializer(required=False, allow_null=True)
    site_count = serializers.IntegerField(read_only=True)
    _depth = serializers.IntegerField(source="level", read_only=True)

    class Meta:
        model = Region
        fields = [
            "id",
            "url",
            "name",
            "slug",
            "parent",
            "description",
            "site_count",
            "_depth",
            "custom_fields",
            "created",
            "last_updated",
            "computed_fields",
        ]
        opt_in_fields = ["computed_fields"]


class SiteSerializer(TaggedObjectSerializer, StatusModelSerializerMixin, CustomFieldModelSerializer):
    url = serializers.HyperlinkedIdentityField(view_name="dcim-api:site-detail")
    region = NestedRegionSerializer(required=False, allow_null=True)
    tenant = NestedTenantSerializer(required=False, allow_null=True)
    time_zone = TimeZoneSerializerField(required=False, allow_null=True)
    circuit_count = serializers.IntegerField(read_only=True)
    device_count = serializers.IntegerField(read_only=True)
    prefix_count = serializers.IntegerField(read_only=True)
    rack_count = serializers.IntegerField(read_only=True)
    virtualmachine_count = serializers.IntegerField(read_only=True)
    vlan_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Site
        fields = [
            "id",
            "url",
            "name",
            "slug",
            "status",
            "region",
            "tenant",
            "facility",
            "asn",
            "time_zone",
            "description",
            "physical_address",
            "shipping_address",
            "latitude",
            "longitude",
            "contact_name",
            "contact_phone",
            "contact_email",
            "comments",
            "tags",
            "custom_fields",
            "created",
            "last_updated",
            "circuit_count",
            "device_count",
            "prefix_count",
            "rack_count",
            "virtualmachine_count",
            "vlan_count",
            "computed_fields",
        ]
        opt_in_fields = ["computed_fields"]


#
# Racks
#


class RackGroupSerializer(CustomFieldModelSerializer):
    url = serializers.HyperlinkedIdentityField(view_name="dcim-api:rackgroup-detail")
    site = NestedSiteSerializer()
    parent = NestedRackGroupSerializer(required=False, allow_null=True)
    rack_count = serializers.IntegerField(read_only=True)
    _depth = serializers.IntegerField(source="level", read_only=True)

    class Meta:
        model = RackGroup
        fields = [
            "id",
            "url",
            "name",
            "slug",
            "site",
            "parent",
            "description",
            "rack_count",
            "_depth",
            "custom_fields",
            "created",
            "last_updated",
            "computed_fields",
        ]
        opt_in_fields = ["computed_fields"]
        # Omit the UniqueTogetherValidator that would be automatically added to validate (site, slug). This
        # prevents slug from being interpreted as a required field.
        # TODO: Remove if/when slug is globally unique. This would be a breaking change.
        validators = [UniqueTogetherValidator(queryset=RackGroup.objects.all(), fields=("site", "name"))]

    def validate(self, data):
        # Validate uniqueness of (site, slug) since we omitted the automatically-created validator from Meta.
        # TODO: Remove if/when slug is globally unique. This would be a breaking change.
        if data.get("slug", None):
            validator = UniqueTogetherValidator(queryset=RackGroup.objects.all(), fields=("site", "slug"))
            validator(data, self)

        # Enforce model validation
        super().validate(data)

        return data


class RackRoleSerializer(CustomFieldModelSerializer):
    url = serializers.HyperlinkedIdentityField(view_name="dcim-api:rackrole-detail")
    rack_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = RackRole
        fields = [
            "id",
            "url",
            "name",
            "slug",
            "color",
            "description",
            "rack_count",
            "custom_fields",
            "created",
            "last_updated",
            "computed_fields",
        ]
        opt_in_fields = ["computed_fields"]


class RackSerializer(TaggedObjectSerializer, StatusModelSerializerMixin, CustomFieldModelSerializer):
    url = serializers.HyperlinkedIdentityField(view_name="dcim-api:rack-detail")
    site = NestedSiteSerializer()
    group = NestedRackGroupSerializer(required=False, allow_null=True, default=None)
    tenant = NestedTenantSerializer(required=False, allow_null=True)
    role = NestedRackRoleSerializer(required=False, allow_null=True)
    type = ChoiceField(choices=RackTypeChoices, allow_blank=True, required=False)
    width = ChoiceField(choices=RackWidthChoices, required=False)
    outer_unit = ChoiceField(choices=RackDimensionUnitChoices, allow_blank=True, required=False)
    device_count = serializers.IntegerField(read_only=True)
    powerfeed_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Rack
        fields = [
            "id",
            "url",
            "name",
            "facility_id",
            "site",
            "group",
            "tenant",
            "status",
            "role",
            "serial",
            "asset_tag",
            "type",
            "width",
            "u_height",
            "desc_units",
            "outer_width",
            "outer_depth",
            "outer_unit",
            "comments",
            "tags",
            "custom_fields",
            "created",
            "last_updated",
            "device_count",
            "powerfeed_count",
            "computed_fields",
        ]
        # Omit the UniqueTogetherValidator that would be automatically added to validate (group, facility_id). This
        # prevents facility_id from being interpreted as a required field.
        validators = [UniqueTogetherValidator(queryset=Rack.objects.all(), fields=("group", "name"))]
        opt_in_fields = ["computed_fields"]

    def validate(self, data):
        # Validate uniqueness of (group, facility_id) since we omitted the automatically-created validator from Meta.
        if data.get("facility_id", None):
            validator = UniqueTogetherValidator(queryset=Rack.objects.all(), fields=("group", "facility_id"))
            validator(data, self)

        # Enforce model validation
        super().validate(data)

        return data


class RackUnitSerializer(serializers.Serializer):
    """
    A rack unit is an abstraction formed by the set (rack, position, face); it does not exist as a row in the database.
    """

    id = serializers.IntegerField(read_only=True)
    name = serializers.CharField(read_only=True)
    face = ChoiceField(choices=DeviceFaceChoices, read_only=True)
    device = NestedDeviceSerializer(read_only=True)
    occupied = serializers.BooleanField(read_only=True)


class RackReservationSerializer(TaggedObjectSerializer, CustomFieldModelSerializer):
    url = serializers.HyperlinkedIdentityField(view_name="dcim-api:rackreservation-detail")
    rack = NestedRackSerializer()
    user = NestedUserSerializer()
    tenant = NestedTenantSerializer(required=False, allow_null=True)

    class Meta:
        model = RackReservation
        fields = [
            "id",
            "url",
            "rack",
            "units",
            "created",
            "user",
            "tenant",
            "description",
            "tags",
            "custom_fields",
            "computed_fields",
        ]
        opt_in_fields = ["computed_fields"]


class RackElevationDetailFilterSerializer(serializers.Serializer):
    q = serializers.CharField(required=False, default=None)
    face = serializers.ChoiceField(choices=DeviceFaceChoices, default=DeviceFaceChoices.FACE_FRONT)
    render = serializers.ChoiceField(
        choices=RackElevationDetailRenderChoices,
        default=RackElevationDetailRenderChoices.RENDER_JSON,
    )
    unit_width = serializers.IntegerField(required=False)
    unit_height = serializers.IntegerField(required=False)
    legend_width = serializers.IntegerField(default=RACK_ELEVATION_LEGEND_WIDTH_DEFAULT)
    exclude = serializers.UUIDField(required=False, default=None)
    expand_devices = serializers.BooleanField(required=False, default=True)
    include_images = serializers.BooleanField(required=False, default=True)

    def validate(self, attrs):
        attrs.setdefault("unit_width", get_settings_or_config("RACK_ELEVATION_DEFAULT_UNIT_WIDTH"))
        attrs.setdefault("unit_height", get_settings_or_config("RACK_ELEVATION_DEFAULT_UNIT_HEIGHT"))
        return attrs


#
# Device types
#


class ManufacturerSerializer(CustomFieldModelSerializer):
    url = serializers.HyperlinkedIdentityField(view_name="dcim-api:manufacturer-detail")
    devicetype_count = serializers.IntegerField(read_only=True)
    inventoryitem_count = serializers.IntegerField(read_only=True)
    platform_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Manufacturer
        fields = [
            "id",
            "url",
            "name",
            "slug",
            "description",
            "devicetype_count",
            "inventoryitem_count",
            "platform_count",
            "custom_fields",
            "created",
            "last_updated",
            "computed_fields",
        ]
        opt_in_fields = ["computed_fields"]


class DeviceTypeSerializer(TaggedObjectSerializer, CustomFieldModelSerializer):
    url = serializers.HyperlinkedIdentityField(view_name="dcim-api:devicetype-detail")
    manufacturer = NestedManufacturerSerializer()
    subdevice_role = ChoiceField(choices=SubdeviceRoleChoices, allow_blank=True, required=False)
    device_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = DeviceType
        fields = [
            "id",
            "url",
            "manufacturer",
            "model",
            "slug",
            "part_number",
            "u_height",
            "is_full_depth",
            "subdevice_role",
            "front_image",
            "rear_image",
            "comments",
            "tags",
            "custom_fields",
            "created",
            "last_updated",
            "device_count",
            "computed_fields",
        ]
        opt_in_fields = ["computed_fields"]
        # Omit the UniqueTogetherValidator that would be automatically added to validate (manufacturer, slug). This
        # prevents slug from being interpreted as a required field.
        # TODO: Remove if/when slug is globally unique. This would be a breaking change.
        validators = [UniqueTogetherValidator(queryset=DeviceType.objects.all(), fields=("manufacturer", "model"))]

    def validate(self, data):
        # Validate uniqueness of (manufacturer, slug) since we omitted the automatically-created validator from Meta.
        # TODO: Remove if/when slug is globally unique. This would be a breaking change.
        if data.get("slug", None):
            validator = UniqueTogetherValidator(queryset=DeviceType.objects.all(), fields=("manufacturer", "slug"))
            validator(data, self)

        # Enforce model validation
        super().validate(data)

        return data


class ConsolePortTemplateSerializer(CustomFieldModelSerializer):
    url = serializers.HyperlinkedIdentityField(view_name="dcim-api:consoleporttemplate-detail")
    device_type = NestedDeviceTypeSerializer()
    type = ChoiceField(choices=ConsolePortTypeChoices, allow_blank=True, required=False)

    class Meta:
        model = ConsolePortTemplate
        fields = [
            "id",
            "url",
            "device_type",
            "name",
            "label",
            "type",
            "description",
            "custom_fields",
            "computed_fields",
        ]
        opt_in_fields = ["computed_fields"]


class ConsoleServerPortTemplateSerializer(CustomFieldModelSerializer):
    url = serializers.HyperlinkedIdentityField(view_name="dcim-api:consoleserverporttemplate-detail")
    device_type = NestedDeviceTypeSerializer()
    type = ChoiceField(choices=ConsolePortTypeChoices, allow_blank=True, required=False)

    class Meta:
        model = ConsoleServerPortTemplate
        fields = [
            "id",
            "url",
            "device_type",
            "name",
            "label",
            "type",
            "description",
            "custom_fields",
        ]


class PowerPortTemplateSerializer(CustomFieldModelSerializer):
    url = serializers.HyperlinkedIdentityField(view_name="dcim-api:powerporttemplate-detail")
    device_type = NestedDeviceTypeSerializer()
    type = ChoiceField(choices=PowerPortTypeChoices, allow_blank=True, required=False)

    class Meta:
        model = PowerPortTemplate
        fields = [
            "id",
            "url",
            "device_type",
            "name",
            "label",
            "type",
            "maximum_draw",
            "allocated_draw",
            "description",
            "custom_fields",
            "computed_fields",
        ]
        opt_in_fields = ["computed_fields"]


class PowerOutletTemplateSerializer(CustomFieldModelSerializer):
    url = serializers.HyperlinkedIdentityField(view_name="dcim-api:poweroutlettemplate-detail")
    device_type = NestedDeviceTypeSerializer()
    type = ChoiceField(choices=PowerOutletTypeChoices, allow_blank=True, required=False)
    power_port = NestedPowerPortTemplateSerializer(required=False)
    feed_leg = ChoiceField(choices=PowerOutletFeedLegChoices, allow_blank=True, required=False)

    class Meta:
        model = PowerOutletTemplate
        fields = [
            "id",
            "url",
            "device_type",
            "name",
            "label",
            "type",
            "power_port",
            "feed_leg",
            "description",
            "custom_fields",
            "computed_fields",
        ]
        opt_in_fields = ["computed_fields"]


class InterfaceTemplateSerializer(CustomFieldModelSerializer):
    url = serializers.HyperlinkedIdentityField(view_name="dcim-api:interfacetemplate-detail")
    device_type = NestedDeviceTypeSerializer()
    type = ChoiceField(choices=InterfaceTypeChoices)

    class Meta:
        model = InterfaceTemplate
        fields = [
            "id",
            "url",
            "device_type",
            "name",
            "label",
            "type",
            "mgmt_only",
            "description",
            "custom_fields",
            "computed_fields",
        ]
        opt_in_fields = ["computed_fields"]


class RearPortTemplateSerializer(CustomFieldModelSerializer):
    url = serializers.HyperlinkedIdentityField(view_name="dcim-api:rearporttemplate-detail")
    device_type = NestedDeviceTypeSerializer()
    type = ChoiceField(choices=PortTypeChoices)

    class Meta:
        model = RearPortTemplate
        fields = [
            "id",
            "url",
            "device_type",
            "name",
            "label",
            "type",
            "positions",
            "description",
            "custom_fields",
        ]


class FrontPortTemplateSerializer(CustomFieldModelSerializer):
    url = serializers.HyperlinkedIdentityField(view_name="dcim-api:frontporttemplate-detail")
    device_type = NestedDeviceTypeSerializer()
    type = ChoiceField(choices=PortTypeChoices)
    rear_port = NestedRearPortTemplateSerializer()

    class Meta:
        model = FrontPortTemplate
        fields = [
            "id",
            "url",
            "device_type",
            "name",
            "label",
            "type",
            "rear_port",
            "rear_port_position",
            "description",
            "custom_fields",
            "computed_fields",
        ]
        opt_in_fields = ["computed_fields"]


class DeviceBayTemplateSerializer(CustomFieldModelSerializer):
    url = serializers.HyperlinkedIdentityField(view_name="dcim-api:devicebaytemplate-detail")
    device_type = NestedDeviceTypeSerializer()

    class Meta:
        model = DeviceBayTemplate
        fields = [
            "id",
            "url",
            "device_type",
            "name",
            "label",
            "description",
            "custom_fields",
            "computed_fields",
        ]
        opt_in_fields = ["computed_fields"]


#
# Devices
#


class DeviceRoleSerializer(CustomFieldModelSerializer):
    url = serializers.HyperlinkedIdentityField(view_name="dcim-api:devicerole-detail")
    device_count = serializers.IntegerField(read_only=True)
    virtualmachine_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = DeviceRole
        fields = [
            "id",
            "url",
            "name",
            "slug",
            "color",
            "vm_role",
            "description",
            "device_count",
            "virtualmachine_count",
            "custom_fields",
            "created",
            "last_updated",
            "computed_fields",
        ]
        opt_in_fields = ["computed_fields"]


class PlatformSerializer(CustomFieldModelSerializer):
    url = serializers.HyperlinkedIdentityField(view_name="dcim-api:platform-detail")
    manufacturer = NestedManufacturerSerializer(required=False, allow_null=True)
    device_count = serializers.IntegerField(read_only=True)
    virtualmachine_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Platform
        fields = [
            "id",
            "url",
            "name",
            "slug",
            "manufacturer",
            "napalm_driver",
            "napalm_args",
            "description",
            "device_count",
            "virtualmachine_count",
            "custom_fields",
            "created",
            "last_updated",
            "computed_fields",
        ]
        opt_in_fields = ["computed_fields"]


class DeviceSerializer(TaggedObjectSerializer, StatusModelSerializerMixin, CustomFieldModelSerializer):
    url = serializers.HyperlinkedIdentityField(view_name="dcim-api:device-detail")
    device_type = NestedDeviceTypeSerializer()
    device_role = NestedDeviceRoleSerializer()
    tenant = NestedTenantSerializer(required=False, allow_null=True)
    platform = NestedPlatformSerializer(required=False, allow_null=True)
    site = NestedSiteSerializer()
    rack = NestedRackSerializer(required=False, allow_null=True)
    face = ChoiceField(choices=DeviceFaceChoices, allow_blank=True, required=False)
    primary_ip = NestedIPAddressSerializer(read_only=True)
    primary_ip4 = NestedIPAddressSerializer(required=False, allow_null=True)
    primary_ip6 = NestedIPAddressSerializer(required=False, allow_null=True)
    parent_device = serializers.SerializerMethodField()
    secrets_group = NestedSecretsGroupSerializer(required=False, allow_null=True)
    cluster = NestedClusterSerializer(required=False, allow_null=True)
    virtual_chassis = NestedVirtualChassisSerializer(required=False, allow_null=True)
    local_context_schema = NestedConfigContextSchemaSerializer(required=False, allow_null=True)

    class Meta:
        model = Device
        fields = [
            "id",
            "url",
            "name",
            "device_type",
            "device_role",
            "tenant",
            "platform",
            "serial",
            "asset_tag",
            "site",
            "rack",
            "position",
            "face",
            "parent_device",
            "status",
            "primary_ip",
            "primary_ip4",
            "primary_ip6",
            "secrets_group",
            "cluster",
            "virtual_chassis",
            "vc_position",
            "vc_priority",
            "comments",
            "local_context_schema",
            "local_context_data",
            "tags",
            "custom_fields",
            "created",
            "last_updated",
            "computed_fields",
        ]
        opt_in_fields = ["computed_fields"]
        validators = []

    def validate(self, data):

        # Validate uniqueness of (rack, position, face) since we omitted the automatically-created validator from Meta.
        if data.get("rack") and data.get("position") and data.get("face"):
            validator = UniqueTogetherValidator(queryset=Device.objects.all(), fields=("rack", "position", "face"))
            validator(data, self)

        # Enforce model validation
        super().validate(data)

        return data

    @extend_schema_field(NestedDeviceSerializer)
    def get_parent_device(self, obj):
        try:
            device_bay = obj.parent_bay
        except DeviceBay.DoesNotExist:
            return None
        context = {"request": self.context["request"]}
        data = NestedDeviceSerializer(instance=device_bay.device, context=context).data
        data["device_bay"] = NestedDeviceBaySerializer(instance=device_bay, context=context).data
        return data


class DeviceWithConfigContextSerializer(DeviceSerializer):
    config_context = serializers.SerializerMethodField()

    class Meta(DeviceSerializer.Meta):
        fields = [
            "id",
            "url",
            "name",
            "device_type",
            "device_role",
            "tenant",
            "platform",
            "serial",
            "asset_tag",
            "site",
            "rack",
            "position",
            "face",
            "parent_device",
            "status",
            "primary_ip",
            "primary_ip4",
            "primary_ip6",
            "secrets_group",
            "cluster",
            "virtual_chassis",
            "vc_position",
            "vc_priority",
            "comments",
            "local_context_schema",
            "local_context_data",
            "tags",
            "computed_fields",
            "custom_fields",
            "config_context",
            "created",
            "last_updated",
        ]
        opt_in_fields = ["computed_fields"]

    @extend_schema_field(serializers.DictField)
    def get_config_context(self, obj):
        return obj.get_config_context()


class DeviceNAPALMSerializer(serializers.Serializer):
    method = serializers.DictField()


class ConsoleServerPortSerializer(
    TaggedObjectSerializer,
    CableTerminationSerializer,
    ConnectedEndpointSerializer,
    CustomFieldModelSerializer,
):
    url = serializers.HyperlinkedIdentityField(view_name="dcim-api:consoleserverport-detail")
    device = NestedDeviceSerializer()
    type = ChoiceField(choices=ConsolePortTypeChoices, allow_blank=True, required=False)
    cable = NestedCableSerializer(read_only=True)

    class Meta:
        model = ConsoleServerPort
        fields = [
            "id",
            "url",
            "device",
            "name",
            "label",
            "type",
            "description",
            "cable",
            "cable_peer",
            "cable_peer_type",
            "connected_endpoint",
            "connected_endpoint_type",
            "connected_endpoint_reachable",
            "tags",
            "custom_fields",
            "computed_fields",
        ]
        opt_in_fields = ["computed_fields"]


class ConsolePortSerializer(
    TaggedObjectSerializer,
    CableTerminationSerializer,
    ConnectedEndpointSerializer,
    CustomFieldModelSerializer,
):
    url = serializers.HyperlinkedIdentityField(view_name="dcim-api:consoleport-detail")
    device = NestedDeviceSerializer()
    type = ChoiceField(choices=ConsolePortTypeChoices, allow_blank=True, required=False)
    cable = NestedCableSerializer(read_only=True)

    class Meta:
        model = ConsolePort
        fields = [
            "id",
            "url",
            "device",
            "name",
            "label",
            "type",
            "description",
            "cable",
            "cable_peer",
            "cable_peer_type",
            "connected_endpoint",
            "connected_endpoint_type",
            "connected_endpoint_reachable",
            "tags",
            "custom_fields",
            "computed_fields",
        ]
        opt_in_fields = ["computed_fields"]


class PowerOutletSerializer(
    TaggedObjectSerializer,
    CableTerminationSerializer,
    ConnectedEndpointSerializer,
    CustomFieldModelSerializer,
):
    url = serializers.HyperlinkedIdentityField(view_name="dcim-api:poweroutlet-detail")
    device = NestedDeviceSerializer()
    type = ChoiceField(choices=PowerOutletTypeChoices, allow_blank=True, required=False)
    power_port = NestedPowerPortSerializer(required=False)
    feed_leg = ChoiceField(choices=PowerOutletFeedLegChoices, allow_blank=True, required=False)
    cable = NestedCableSerializer(read_only=True)

    class Meta:
        model = PowerOutlet
        fields = [
            "id",
            "url",
            "device",
            "name",
            "label",
            "type",
            "power_port",
            "feed_leg",
            "description",
            "cable",
            "cable_peer",
            "cable_peer_type",
            "connected_endpoint",
            "connected_endpoint_type",
            "connected_endpoint_reachable",
            "tags",
            "custom_fields",
            "computed_fields",
        ]
        opt_in_fields = ["computed_fields"]


class PowerPortSerializer(
    TaggedObjectSerializer,
    CableTerminationSerializer,
    ConnectedEndpointSerializer,
    CustomFieldModelSerializer,
):
    url = serializers.HyperlinkedIdentityField(view_name="dcim-api:powerport-detail")
    device = NestedDeviceSerializer()
    type = ChoiceField(choices=PowerPortTypeChoices, allow_blank=True, required=False)
    cable = NestedCableSerializer(read_only=True)

    class Meta:
        model = PowerPort
        fields = [
            "id",
            "url",
            "device",
            "name",
            "label",
            "type",
            "maximum_draw",
            "allocated_draw",
            "description",
            "cable",
            "cable_peer",
            "cable_peer_type",
            "connected_endpoint",
            "connected_endpoint_type",
            "connected_endpoint_reachable",
            "tags",
            "custom_fields",
            "computed_fields",
        ]
        opt_in_fields = ["computed_fields"]


class InterfaceSerializer(
    TaggedObjectSerializer,
    CableTerminationSerializer,
    ConnectedEndpointSerializer,
    CustomFieldModelSerializer,
):
    url = serializers.HyperlinkedIdentityField(view_name="dcim-api:interface-detail")
    device = NestedDeviceSerializer()
    type = ChoiceField(choices=InterfaceTypeChoices)
    lag = NestedInterfaceSerializer(required=False, allow_null=True)
    mode = ChoiceField(choices=InterfaceModeChoices, allow_blank=True, required=False)
    untagged_vlan = NestedVLANSerializer(required=False, allow_null=True)
    tagged_vlans = SerializedPKRelatedField(
        queryset=VLAN.objects.all(),
        serializer=NestedVLANSerializer,
        required=False,
        many=True,
    )
    cable = NestedCableSerializer(read_only=True)
    count_ipaddresses = serializers.IntegerField(read_only=True)

    class Meta:
        model = Interface
        fields = [
            "id",
            "url",
            "device",
            "name",
            "label",
            "type",
            "enabled",
            "lag",
            "mtu",
            "mac_address",
            "mgmt_only",
            "description",
            "mode",
            "untagged_vlan",
            "tagged_vlans",
            "cable",
            "cable_peer",
            "cable_peer_type",
            "connected_endpoint",
            "connected_endpoint_type",
            "connected_endpoint_reachable",
            "tags",
            "count_ipaddresses",
            "custom_fields",
            "computed_fields",
        ]
        opt_in_fields = ["computed_fields"]

    def validate(self, data):

        # Validate many-to-many VLAN assignments
        device = self.instance.device if self.instance else data.get("device")
        for vlan in data.get("tagged_vlans", []):
            if vlan.site not in [device.site, None]:
                raise serializers.ValidationError(
                    {
                        "tagged_vlans": f"VLAN {vlan} must belong to the same site as the interface's parent device, or "
                        f"it must be global."
                    }
                )

        return super().validate(data)


class RearPortSerializer(TaggedObjectSerializer, CableTerminationSerializer, CustomFieldModelSerializer):
    url = serializers.HyperlinkedIdentityField(view_name="dcim-api:rearport-detail")
    device = NestedDeviceSerializer()
    type = ChoiceField(choices=PortTypeChoices)
    cable = NestedCableSerializer(read_only=True)

    class Meta:
        model = RearPort
        fields = [
            "id",
            "url",
            "device",
            "name",
            "label",
            "type",
            "positions",
            "description",
            "cable",
            "cable_peer",
            "cable_peer_type",
            "tags",
            "custom_fields",
            "computed_fields",
        ]
        opt_in_fields = ["computed_fields"]


class FrontPortRearPortSerializer(WritableNestedSerializer):
    """
    NestedRearPortSerializer but with parent device omitted (since front and rear ports must belong to same device)
    """

    url = serializers.HyperlinkedIdentityField(view_name="dcim-api:rearport-detail")

    class Meta:
        model = RearPort
        fields = ["id", "url", "name", "label"]


class FrontPortSerializer(TaggedObjectSerializer, CableTerminationSerializer, CustomFieldModelSerializer):
    url = serializers.HyperlinkedIdentityField(view_name="dcim-api:frontport-detail")
    device = NestedDeviceSerializer()
    type = ChoiceField(choices=PortTypeChoices)
    rear_port = FrontPortRearPortSerializer()
    cable = NestedCableSerializer(read_only=True)

    class Meta:
        model = FrontPort
        fields = [
            "id",
            "url",
            "device",
            "name",
            "label",
            "type",
            "rear_port",
            "rear_port_position",
            "description",
            "cable",
            "cable_peer",
            "cable_peer_type",
            "tags",
            "custom_fields",
            "computed_fields",
        ]
        opt_in_fields = ["computed_fields"]


class DeviceBaySerializer(TaggedObjectSerializer, CustomFieldModelSerializer):
    url = serializers.HyperlinkedIdentityField(view_name="dcim-api:devicebay-detail")
    device = NestedDeviceSerializer()
    installed_device = NestedDeviceSerializer(required=False, allow_null=True)

    class Meta:
        model = DeviceBay
        fields = [
            "id",
            "url",
            "device",
            "name",
            "label",
            "description",
            "installed_device",
            "tags",
            "custom_fields",
            "computed_fields",
        ]
        opt_in_fields = ["computed_fields"]


#
# Inventory items
#


class InventoryItemSerializer(TaggedObjectSerializer, CustomFieldModelSerializer):
    url = serializers.HyperlinkedIdentityField(view_name="dcim-api:inventoryitem-detail")
    device = NestedDeviceSerializer()
    # Provide a default value to satisfy UniqueTogetherValidator
    parent = serializers.PrimaryKeyRelatedField(queryset=InventoryItem.objects.all(), allow_null=True, default=None)
    manufacturer = NestedManufacturerSerializer(required=False, allow_null=True, default=None)
    _depth = serializers.IntegerField(source="level", read_only=True)

    class Meta:
        model = InventoryItem
        fields = [
            "id",
            "url",
            "device",
            "parent",
            "name",
            "label",
            "manufacturer",
            "part_id",
            "serial",
            "asset_tag",
            "discovered",
            "description",
            "tags",
            "_depth",
            "custom_fields",
            "computed_fields",
        ]
        opt_in_fields = ["computed_fields"]


#
# Cables
#


class CableSerializer(TaggedObjectSerializer, StatusModelSerializerMixin, CustomFieldModelSerializer):
    url = serializers.HyperlinkedIdentityField(view_name="dcim-api:cable-detail")
    termination_a_type = ContentTypeField(queryset=ContentType.objects.filter(CABLE_TERMINATION_MODELS))
    termination_b_type = ContentTypeField(queryset=ContentType.objects.filter(CABLE_TERMINATION_MODELS))
    termination_a = serializers.SerializerMethodField(read_only=True)
    termination_b = serializers.SerializerMethodField(read_only=True)
    length_unit = ChoiceField(choices=CableLengthUnitChoices, allow_blank=True, required=False)

    class Meta:
        model = Cable
        fields = [
            "id",
            "url",
            "termination_a_type",
            "termination_a_id",
            "termination_a",
            "termination_b_type",
            "termination_b_id",
            "termination_b",
            "type",
            "status",
            "label",
            "color",
            "length",
            "length_unit",
            "tags",
            "custom_fields",
            "computed_fields",
        ]
        opt_in_fields = ["computed_fields"]

    def _get_termination(self, obj, side):
        """
        Serialize a nested representation of a termination.
        """
        if side.lower() not in ["a", "b"]:
            raise ValueError("Termination side must be either A or B.")
        termination = getattr(obj, "termination_{}".format(side.lower()))
        if termination is None:
            return None
        serializer = get_serializer_for_model(termination, prefix="Nested")
        context = {"request": self.context["request"]}
        data = serializer(termination, context=context).data

        return data

    @extend_schema_field(serializers.DictField(allow_null=True))
    def get_termination_a(self, obj):
        return self._get_termination(obj, "a")

    @extend_schema_field(serializers.DictField(allow_null=True))
    def get_termination_b(self, obj):
        return self._get_termination(obj, "b")


class TracedCableSerializer(StatusModelSerializerMixin, serializers.ModelSerializer):
    """
    Used only while tracing a cable path.
    """

    url = serializers.HyperlinkedIdentityField(view_name="dcim-api:cable-detail")

    class Meta:
        model = Cable
        fields = [
            "id",
            "url",
            "type",
            "status",
            "label",
            "color",
            "length",
            "length_unit",
        ]


class CablePathSerializer(serializers.ModelSerializer):
    origin_type = ContentTypeField(read_only=True)
    origin = serializers.SerializerMethodField(read_only=True)
    destination_type = ContentTypeField(read_only=True)
    destination = serializers.SerializerMethodField(read_only=True)
    path = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = CablePath
        fields = [
            "id",
            "origin_type",
            "origin",
            "destination_type",
            "destination",
            "path",
            "is_active",
            "is_split",
        ]

    @extend_schema_field(serializers.DictField)
    def get_origin(self, obj):
        """
        Return the appropriate serializer for the origin.
        """
        serializer = get_serializer_for_model(obj.origin, prefix="Nested")
        context = {"request": self.context["request"]}
        return serializer(obj.origin, context=context).data

    @extend_schema_field(serializers.DictField(allow_null=True))
    def get_destination(self, obj):
        """
        Return the appropriate serializer for the destination, if any.
        """
        if obj.destination_id is not None:
            serializer = get_serializer_for_model(obj.destination, prefix="Nested")
            context = {"request": self.context["request"]}
            return serializer(obj.destination, context=context).data
        return None

    @extend_schema_field(serializers.ListField)
    def get_path(self, obj):
        ret = []
        for node in obj.get_path():
            serializer = get_serializer_for_model(node, prefix="Nested")
            context = {"request": self.context["request"]}
            ret.append(serializer(node, context=context).data)
        return ret


#
# Interface connections
#


class InterfaceConnectionSerializer(ValidatedModelSerializer):
    interface_a = serializers.SerializerMethodField()
    interface_b = NestedInterfaceSerializer(source="connected_endpoint")
    connected_endpoint_reachable = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Interface
        fields = ["interface_a", "interface_b", "connected_endpoint_reachable"]

    @extend_schema_field(NestedInterfaceSerializer)
    def get_interface_a(self, obj):
        context = {"request": self.context["request"]}
        return NestedInterfaceSerializer(instance=obj, context=context).data

    @extend_schema_field(serializers.BooleanField(allow_null=True))
    def get_connected_endpoint_reachable(self, obj):
        if obj._path is not None:
            return obj._path.is_active
        return None


#
# Virtual chassis
#


class VirtualChassisSerializer(TaggedObjectSerializer, CustomFieldModelSerializer):
    url = serializers.HyperlinkedIdentityField(view_name="dcim-api:virtualchassis-detail")
    master = NestedDeviceSerializer(required=False, allow_null=True)
    member_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = VirtualChassis
        fields = [
            "id",
            "url",
            "name",
            "domain",
            "master",
            "tags",
            "custom_fields",
            "member_count",
            "computed_fields",
        ]
        opt_in_fields = ["computed_fields"]


#
# Power panels
#


class PowerPanelSerializer(TaggedObjectSerializer, CustomFieldModelSerializer):
    url = serializers.HyperlinkedIdentityField(view_name="dcim-api:powerpanel-detail")
    site = NestedSiteSerializer()
    rack_group = NestedRackGroupSerializer(required=False, allow_null=True, default=None)
    powerfeed_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = PowerPanel
        fields = [
            "id",
            "url",
            "site",
            "rack_group",
            "name",
            "tags",
            "custom_fields",
            "powerfeed_count",
            "computed_fields",
        ]
        opt_in_fields = ["computed_fields"]


class PowerFeedSerializer(
    TaggedObjectSerializer,
    CableTerminationSerializer,
    ConnectedEndpointSerializer,
    StatusModelSerializerMixin,
    CustomFieldModelSerializer,
):
    url = serializers.HyperlinkedIdentityField(view_name="dcim-api:powerfeed-detail")
    power_panel = NestedPowerPanelSerializer()
    rack = NestedRackSerializer(required=False, allow_null=True, default=None)
    type = ChoiceField(choices=PowerFeedTypeChoices, default=PowerFeedTypeChoices.TYPE_PRIMARY)
    supply = ChoiceField(choices=PowerFeedSupplyChoices, default=PowerFeedSupplyChoices.SUPPLY_AC)
    phase = ChoiceField(choices=PowerFeedPhaseChoices, default=PowerFeedPhaseChoices.PHASE_SINGLE)
    cable = NestedCableSerializer(read_only=True)

    class Meta:
        model = PowerFeed
        fields = [
            "id",
            "url",
            "power_panel",
            "rack",
            "name",
            "status",
            "type",
            "supply",
            "phase",
            "voltage",
            "amperage",
            "max_utilization",
            "comments",
            "cable",
            "cable_peer",
            "cable_peer_type",
            "connected_endpoint",
            "connected_endpoint_type",
            "connected_endpoint_reachable",
            "tags",
            "custom_fields",
            "created",
            "last_updated",
            "computed_fields",
        ]
        opt_in_fields = ["computed_fields"]
