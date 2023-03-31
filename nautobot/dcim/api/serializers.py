from django.contrib.contenttypes.models import ContentType
from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers
from rest_framework.validators import UniqueTogetherValidator

from nautobot.core.api import (
    ChoiceField,
    ContentTypeField,
    NautobotModelSerializer,
    SerializedPKRelatedField,
    TimeZoneSerializerField,
    TreeModelSerializerMixin,
    ValidatedModelSerializer,
    WritableNestedSerializer,
)
from nautobot.core.api.serializers import PolymorphicProxySerializer
from nautobot.core.api.utils import get_serializer_for_model, get_serializers_for_models
from nautobot.core.models.utils import get_all_concrete_models
from nautobot.core.utils.config import get_settings_or_config
from nautobot.core.utils.deprecation import class_deprecated_in_favor_of
from nautobot.dcim.choices import (
    CableLengthUnitChoices,
    ConsolePortTypeChoices,
    DeviceFaceChoices,
    DeviceRedundancyGroupFailoverStrategyChoices,
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
    CableTermination,
    ConsolePort,
    ConsolePortTemplate,
    ConsoleServerPort,
    ConsoleServerPortTemplate,
    Device,
    DeviceBay,
    DeviceBayTemplate,
    DeviceRedundancyGroup,
    DeviceType,
    FrontPort,
    FrontPortTemplate,
    Interface,
    InterfaceTemplate,
    InventoryItem,
    Location,
    LocationType,
    Manufacturer,
    PathEndpoint,
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
    RearPort,
    RearPortTemplate,
    VirtualChassis,
)
from nautobot.extras.api.mixins import (
    RoleModelSerializerMixin,
    RoleRequiredRoleModelSerializerMixin,
    StatusModelSerializerMixin,
    TaggedModelSerializerMixin,
)
from nautobot.extras.api.nested_serializers import NestedConfigContextSchemaSerializer, NestedSecretsGroupSerializer
from nautobot.extras.utils import FeatureQuery
from nautobot.ipam.api.nested_serializers import (
    NestedIPAddressSerializer,
    NestedVLANSerializer,
)
from nautobot.ipam.models import IPAddress, VLAN
from nautobot.tenancy.api.nested_serializers import NestedTenantSerializer
from nautobot.users.api.nested_serializers import NestedUserSerializer
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
    NestedDeviceRedundancyGroupSerializer,
    NestedDeviceSerializer,
    NestedDeviceTypeSerializer,
    NestedFrontPortSerializer,
    NestedFrontPortTemplateSerializer,
    NestedInterfaceSerializer,
    NestedInterfaceTemplateSerializer,
    NestedInventoryItemSerializer,
    NestedLocationSerializer,
    NestedLocationTypeSerializer,
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
    NestedRackSerializer,
    NestedRearPortSerializer,
    NestedRearPortTemplateSerializer,
    NestedVirtualChassisSerializer,
)


class CableTerminationModelSerializerMixin(serializers.ModelSerializer):
    cable_peer_type = serializers.SerializerMethodField(read_only=True)
    cable_peer = serializers.SerializerMethodField(read_only=True)

    @extend_schema_field(serializers.CharField(allow_null=True))
    def get_cable_peer_type(self, obj):
        if obj._cable_peer is not None:
            return f"{obj._cable_peer._meta.app_label}.{obj._cable_peer._meta.model_name}"
        return None

    @extend_schema_field(
        PolymorphicProxySerializer(
            component_name="CableTermination",
            resource_type_field_name="object_type",
            serializers=lambda: get_serializers_for_models(get_all_concrete_models(CableTermination), prefix="Nested"),
            allow_null=True,
        )
    )
    def get_cable_peer(self, obj):
        """
        Return the appropriate serializer for the cable termination model.
        """
        if obj._cable_peer is not None:
            serializer = get_serializer_for_model(obj._cable_peer, prefix="Nested")
            context = {"request": self.context["request"]}
            return serializer(obj._cable_peer, context=context).data
        return None


# TODO: remove in 2.2
@class_deprecated_in_favor_of(CableTerminationModelSerializerMixin)
class CableTerminationSerializer(CableTerminationModelSerializerMixin):
    pass


class PathEndpointModelSerializerMixin(ValidatedModelSerializer):
    connected_endpoint_type = serializers.SerializerMethodField(read_only=True)
    connected_endpoint = serializers.SerializerMethodField(read_only=True)
    connected_endpoint_reachable = serializers.SerializerMethodField(read_only=True)

    @extend_schema_field(serializers.CharField(allow_null=True))
    def get_connected_endpoint_type(self, obj):
        if obj._path is not None and obj._path.destination is not None:
            return f"{obj._path.destination._meta.app_label}.{obj._path.destination._meta.model_name}"
        return None

    @extend_schema_field(
        PolymorphicProxySerializer(
            component_name="PathEndpoint",
            resource_type_field_name="object_type",
            serializers=lambda: get_serializers_for_models(get_all_concrete_models(PathEndpoint), prefix="Nested"),
            allow_null=True,
        )
    )
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


# TODO: remove in 2.2
@class_deprecated_in_favor_of(PathEndpointModelSerializerMixin)
class ConnectedEndpointSerializer(PathEndpointModelSerializerMixin):
    pass


#
# Locations
#


class LocationTypeSerializer(NautobotModelSerializer, TreeModelSerializerMixin):
    url = serializers.HyperlinkedIdentityField(view_name="dcim-api:locationtype-detail")
    content_types = ContentTypeField(
        queryset=ContentType.objects.filter(FeatureQuery("locations").get_query()),
        required=False,
        many=True,
    )

    class Meta:
        model = LocationType
        fields = "__all__"
        extra_fields = ["url"]


class LocationSerializer(
    NautobotModelSerializer, TaggedModelSerializerMixin, StatusModelSerializerMixin, TreeModelSerializerMixin
):
    url = serializers.HyperlinkedIdentityField(view_name="dcim-api:location-detail")
    time_zone = TimeZoneSerializerField(required=False, allow_null=True)
    circuit_count = serializers.IntegerField(read_only=True)
    device_count = serializers.IntegerField(read_only=True)
    prefix_count = serializers.IntegerField(read_only=True)
    rack_count = serializers.IntegerField(read_only=True)
    virtual_machine_count = serializers.IntegerField(read_only=True)
    vlan_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Location
        fields = "__all__"
        extra_fields = [
            "url",
            "circuit_count",
            "device_count",
            "prefix_count",
            "rack_count",
            "virtual_machine_count",
            "vlan_count",
        ]
        # https://www.django-rest-framework.org/api-guide/validators/#optional-fields
        validators = []

    def validate(self, data):
        # Validate uniqueness of (parent, name) since we omitted the automatically created validator from Meta.
        if data.get("parent") and data.get("name"):
            validator = UniqueTogetherValidator(queryset=Location.objects.all(), fields=("parent", "name"))
            validator(data, self)

        super().validate(data)

        return data


#
# Racks
#


class RackGroupSerializer(NautobotModelSerializer, TreeModelSerializerMixin):
    url = serializers.HyperlinkedIdentityField(view_name="dcim-api:rackgroup-detail")
    rack_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = RackGroup
        fields = "__all__"
        extra_fields = ["rack_count"]
        # Omit the UniqueTogetherValidator that would be automatically added to validate (location, slug). This
        # prevents slug from being interpreted as a required field.
        # 2.0 TODO: Remove if/when slug is globally unique. This would be a breaking change.
        validators = [UniqueTogetherValidator(queryset=RackGroup.objects.all(), fields=("location", "name"))]

    def validate(self, data):
        # Validate uniqueness of (location, slug) since we omitted the automatically-created validator from Meta.
        # 2.0 TODO: Remove if/when slug is globally unique. This would be a breaking change.
        if data.get("slug", None):
            validator = UniqueTogetherValidator(queryset=RackGroup.objects.all(), fields=("location", "slug"))
            validator(data, self)

        # Enforce model validation
        super().validate(data)

        return data


class RackSerializer(
    NautobotModelSerializer, TaggedModelSerializerMixin, StatusModelSerializerMixin, RoleModelSerializerMixin
):
    url = serializers.HyperlinkedIdentityField(view_name="dcim-api:rack-detail")
    type = ChoiceField(choices=RackTypeChoices, allow_blank=True, required=False)
    width = ChoiceField(choices=RackWidthChoices, required=False)
    outer_unit = ChoiceField(choices=RackDimensionUnitChoices, allow_blank=True, required=False)
    device_count = serializers.IntegerField(read_only=True)
    power_feed_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Rack
        fields = "__all__"
        extra_fields = ["device_count", "power_feed_count"]
        # Omit the UniqueTogetherValidator that would be automatically added to validate (rack_group, facility_id).
        # This prevents facility_id from being interpreted as a required field.
        validators = [UniqueTogetherValidator(queryset=Rack.objects.all(), fields=("rack_group", "name"))]

    def validate(self, data):
        # Validate uniqueness of (rack_group, facility_id) since we omitted the automatically-created validator above.
        if data.get("facility_id", None):
            validator = UniqueTogetherValidator(queryset=Rack.objects.all(), fields=("rack_group", "facility_id"))
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
    occupied = serializers.BooleanField(read_only=True)


class RackReservationSerializer(NautobotModelSerializer, TaggedModelSerializerMixin):
    url = serializers.HyperlinkedIdentityField(view_name="dcim-api:rackreservation-detail")

    class Meta:
        model = RackReservation
        fields = "__all__"


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
    display_fullname = serializers.BooleanField(required=False, default=True)

    def validate(self, attrs):
        attrs.setdefault("unit_width", get_settings_or_config("RACK_ELEVATION_DEFAULT_UNIT_WIDTH"))
        attrs.setdefault("unit_height", get_settings_or_config("RACK_ELEVATION_DEFAULT_UNIT_HEIGHT"))
        return attrs


#
# Device types
#


class ManufacturerSerializer(NautobotModelSerializer):
    url = serializers.HyperlinkedIdentityField(view_name="dcim-api:manufacturer-detail")
    device_type_count = serializers.IntegerField(read_only=True)
    inventory_item_count = serializers.IntegerField(read_only=True)
    platform_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Manufacturer
        fields = "__all__"
        extra_fields = [
            "device_type_count",
            "inventory_item_count",
            "platform_count",
        ]


class DeviceTypeSerializer(NautobotModelSerializer, TaggedModelSerializerMixin):
    url = serializers.HyperlinkedIdentityField(view_name="dcim-api:devicetype-detail")
    subdevice_role = ChoiceField(choices=SubdeviceRoleChoices, allow_blank=True, required=False)
    device_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = DeviceType
        fields = "__all__"
        extra_fields = ["device_count"]
        # Omit the UniqueTogetherValidator that would be automatically added to validate (manufacturer, slug). This
        # prevents slug from being interpreted as a required field.
        # 2.0 TODO: Remove if/when slug is globally unique. This would be a breaking change.
        validators = [UniqueTogetherValidator(queryset=DeviceType.objects.all(), fields=("manufacturer", "model"))]

    def validate(self, data):
        # Validate uniqueness of (manufacturer, slug) since we omitted the automatically-created validator from Meta.
        # 2.0 TODO: Remove if/when slug is globally unique. This would be a breaking change.
        if data.get("slug", None):
            validator = UniqueTogetherValidator(queryset=DeviceType.objects.all(), fields=("manufacturer", "slug"))
            validator(data, self)

        # Enforce model validation
        super().validate(data)

        return data


class ConsolePortTemplateSerializer(NautobotModelSerializer):
    url = serializers.HyperlinkedIdentityField(view_name="dcim-api:consoleporttemplate-detail")
    type = ChoiceField(choices=ConsolePortTypeChoices, allow_blank=True, required=False)

    class Meta:
        model = ConsolePortTemplate
        fields = "__all__"


class ConsoleServerPortTemplateSerializer(NautobotModelSerializer):
    url = serializers.HyperlinkedIdentityField(view_name="dcim-api:consoleserverporttemplate-detail")
    type = ChoiceField(choices=ConsolePortTypeChoices, allow_blank=True, required=False)

    class Meta:
        model = ConsoleServerPortTemplate
        fields = "__all__"


class PowerPortTemplateSerializer(NautobotModelSerializer):
    url = serializers.HyperlinkedIdentityField(view_name="dcim-api:powerporttemplate-detail")
    type = ChoiceField(choices=PowerPortTypeChoices, allow_blank=True, required=False)

    class Meta:
        model = PowerPortTemplate
        fields = "__all__"


class PowerOutletTemplateSerializer(NautobotModelSerializer):
    url = serializers.HyperlinkedIdentityField(view_name="dcim-api:poweroutlettemplate-detail")
    type = ChoiceField(choices=PowerOutletTypeChoices, allow_blank=True, required=False)
    feed_leg = ChoiceField(choices=PowerOutletFeedLegChoices, allow_blank=True, required=False)

    class Meta:
        model = PowerOutletTemplate
        fields = "__all__"


class InterfaceTemplateSerializer(NautobotModelSerializer):
    url = serializers.HyperlinkedIdentityField(view_name="dcim-api:interfacetemplate-detail")
    type = ChoiceField(choices=InterfaceTypeChoices)

    class Meta:
        model = InterfaceTemplate
        fields = "__all__"


class RearPortTemplateSerializer(NautobotModelSerializer):
    url = serializers.HyperlinkedIdentityField(view_name="dcim-api:rearporttemplate-detail")
    type = ChoiceField(choices=PortTypeChoices)

    class Meta:
        model = RearPortTemplate
        fields = "__all__"


class FrontPortTemplateSerializer(NautobotModelSerializer):
    url = serializers.HyperlinkedIdentityField(view_name="dcim-api:frontporttemplate-detail")
    type = ChoiceField(choices=PortTypeChoices)

    class Meta:
        model = FrontPortTemplate
        fields = "__all__"


class DeviceBayTemplateSerializer(NautobotModelSerializer):
    url = serializers.HyperlinkedIdentityField(view_name="dcim-api:devicebaytemplate-detail")

    class Meta:
        model = DeviceBayTemplate
        fields = "__all__"


#
# Devices
#


class PlatformSerializer(NautobotModelSerializer):
    url = serializers.HyperlinkedIdentityField(view_name="dcim-api:platform-detail")
    device_count = serializers.IntegerField(read_only=True)
    virtual_machine_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Platform
        fields = "__all__"
        extra_fields = ["device_count", "virtual_machine_count"]


class DeviceSerializer(
    NautobotModelSerializer,
    TaggedModelSerializerMixin,
    StatusModelSerializerMixin,
    RoleRequiredRoleModelSerializerMixin,
):
    url = serializers.HyperlinkedIdentityField(view_name="dcim-api:device-detail")
    face = ChoiceField(choices=DeviceFaceChoices, allow_blank=True, required=False)
    parent_device = serializers.SerializerMethodField()

    class Meta:
        model = Device
        fields = "__all__"
        validators = []

    def validate(self, data):
        # Validate uniqueness of (rack, position, face) since we omitted the automatically-created validator from Meta.
        if data.get("rack") and data.get("position") and data.get("face"):
            validator = UniqueTogetherValidator(
                queryset=Device.objects.all(),
                fields=("rack", "position", "face"),
                message=f"The position and face is already occupied on this rack. {UniqueTogetherValidator.message}",
            )
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
        # TODO #3024: How to get rid of this?
        data = NestedDeviceSerializer(instance=device_bay.device, context=context).data
        data["device_bay"] = NestedDeviceBaySerializer(instance=device_bay, context=context).data
        return data


# class DeviceWithConfigContextSerializer(DeviceSerializer):
#     config_context = serializers.SerializerMethodField()

#     class Meta(DeviceSerializer.Meta):
#         fields = DeviceSerializer.Meta.fields + ["config_context"]

#     @extend_schema_field(serializers.DictField)
#     def get_config_context(self, obj):
#         return obj.get_config_context()


class DeviceNAPALMSerializer(serializers.Serializer):
    method = serializers.DictField()


class ConsoleServerPortSerializer(
    NautobotModelSerializer,
    TaggedModelSerializerMixin,
    CableTerminationModelSerializerMixin,
    PathEndpointModelSerializerMixin,
):
    url = serializers.HyperlinkedIdentityField(view_name="dcim-api:consoleserverport-detail")
    type = ChoiceField(choices=ConsolePortTypeChoices, allow_blank=True, required=False)

    class Meta:
        model = ConsoleServerPort
        fields = "__all__"


class ConsolePortSerializer(
    NautobotModelSerializer,
    TaggedModelSerializerMixin,
    CableTerminationModelSerializerMixin,
    PathEndpointModelSerializerMixin,
):
    url = serializers.HyperlinkedIdentityField(view_name="dcim-api:consoleport-detail")
    type = ChoiceField(choices=ConsolePortTypeChoices, allow_blank=True, required=False)

    class Meta:
        model = ConsolePort
        fields = "__all__"


class PowerOutletSerializer(
    NautobotModelSerializer,
    TaggedModelSerializerMixin,
    CableTerminationModelSerializerMixin,
    PathEndpointModelSerializerMixin,
):
    url = serializers.HyperlinkedIdentityField(view_name="dcim-api:poweroutlet-detail")
    type = ChoiceField(choices=PowerOutletTypeChoices, allow_blank=True, required=False)
    feed_leg = ChoiceField(choices=PowerOutletFeedLegChoices, allow_blank=True, required=False)

    class Meta:
        model = PowerOutlet
        fields = "__all__"


class PowerPortSerializer(
    NautobotModelSerializer,
    TaggedModelSerializerMixin,
    CableTerminationModelSerializerMixin,
    PathEndpointModelSerializerMixin,
):
    url = serializers.HyperlinkedIdentityField(view_name="dcim-api:powerport-detail")
    type = ChoiceField(choices=PowerPortTypeChoices, allow_blank=True, required=False)

    class Meta:
        model = PowerPort
        fields = "__all__"


class InterfaceCommonSerializer(NautobotModelSerializer, TaggedModelSerializerMixin):
    def validate(self, data):
        # Validate many-to-many VLAN assignments
        mode = data.get("mode", getattr(self.instance, "mode", None))

        if mode != InterfaceModeChoices.MODE_TAGGED:
            if data.get("tagged_vlans"):
                raise serializers.ValidationError(
                    {
                        "tagged_vlans": f"Mode must be set to {InterfaceModeChoices.MODE_TAGGED} when specifying tagged_vlans"
                    }
                )

            if data.get("tagged_vlans") != [] and self.instance and self.instance.tagged_vlans.exists():
                raise serializers.ValidationError({"tagged_vlans": f"Clear tagged_vlans to set mode to {mode}"})

        return super().validate(data)


class InterfaceSerializer(
    InterfaceCommonSerializer,
    CableTerminationModelSerializerMixin,
    PathEndpointModelSerializerMixin,
    StatusModelSerializerMixin,
):
    url = serializers.HyperlinkedIdentityField(view_name="dcim-api:interface-detail")
    type = ChoiceField(choices=InterfaceTypeChoices)
    mode = ChoiceField(choices=InterfaceModeChoices, allow_blank=True, required=False)
    tagged_vlans = SerializedPKRelatedField(
        queryset=VLAN.objects.all(),
        serializer=NestedVLANSerializer,
        required=False,
        many=True,
    )
    ip_address_count = serializers.IntegerField(read_only=True)
    ip_addresses = SerializedPKRelatedField(
        queryset=IPAddress.objects.all(),
        serializer=NestedIPAddressSerializer,
        required=False,
        many=True,
    )

    class Meta:
        model = Interface
        fields = "__all__"
        extra_fields = ["ip_address_count"]

    def validate(self, data):
        # Validate many-to-many VLAN assignments
        device = self.instance.device if self.instance else data.get("device")
        # TODO: after Location model replaced Site, which was not a hierarchical model, should we allow users to assign a VLAN belongs to
        # the parent Location or the child location of `device.location`?
        for vlan in data.get("tagged_vlans", []):
            if vlan.location not in [device.location, None]:
                raise serializers.ValidationError(
                    {
                        "tagged_vlans": f"VLAN {vlan} must belong to the same location as the interface's parent device, or "
                        f"it must be global."
                    }
                )

        return super().validate(data)


class RearPortSerializer(NautobotModelSerializer, TaggedModelSerializerMixin, CableTerminationModelSerializerMixin):
    url = serializers.HyperlinkedIdentityField(view_name="dcim-api:rearport-detail")
    type = ChoiceField(choices=PortTypeChoices)

    class Meta:
        model = RearPort
        fields = "__all__"


class FrontPortRearPortSerializer(WritableNestedSerializer):
    """
    NestedRearPortSerializer but with parent device omitted (since front and rear ports must belong to same device)
    """

    url = serializers.HyperlinkedIdentityField(view_name="dcim-api:rearport-detail")

    class Meta:
        model = RearPort
        fields = ["id", "url", "name", "label"]


class FrontPortSerializer(NautobotModelSerializer, TaggedModelSerializerMixin, CableTerminationModelSerializerMixin):
    url = serializers.HyperlinkedIdentityField(view_name="dcim-api:frontport-detail")
    type = ChoiceField(choices=PortTypeChoices)
    # TODO #3024: How to get rid of this?
    rear_port = FrontPortRearPortSerializer()

    class Meta:
        model = FrontPort
        fields = "__all__"


class DeviceBaySerializer(NautobotModelSerializer, TaggedModelSerializerMixin):
    url = serializers.HyperlinkedIdentityField(view_name="dcim-api:devicebay-detail")

    class Meta:
        model = DeviceBay
        fields = "__all__"


class DeviceRedundancyGroupSerializer(NautobotModelSerializer, TaggedModelSerializerMixin, StatusModelSerializerMixin):
    url = serializers.HyperlinkedIdentityField(view_name="dcim-api:deviceredundancygroup-detail")
    failover_strategy = ChoiceField(choices=DeviceRedundancyGroupFailoverStrategyChoices)

    class Meta:
        model = DeviceRedundancyGroup
        fields = "__all__"


#
# Inventory items
#


class InventoryItemSerializer(NautobotModelSerializer, TaggedModelSerializerMixin, TreeModelSerializerMixin):
    url = serializers.HyperlinkedIdentityField(view_name="dcim-api:inventoryitem-detail")

    class Meta:
        model = InventoryItem
        fields = "__all__"
        # https://www.django-rest-framework.org/api-guide/validators/#optional-fields
        validators = []

    def validate(self, data):
        # Validate uniqueness of (device, parent, name) since we omitted the automatically created validator from Meta.
        if data.get("device") and data.get("parent") and data.get("name"):
            validator = UniqueTogetherValidator(
                queryset=InventoryItem.objects.all(),
                fields=("device", "parent", "name"),
            )
            validator(data, self)

        super().validate(data)

        return data


#
# Cables
#


class CableSerializer(NautobotModelSerializer, TaggedModelSerializerMixin, StatusModelSerializerMixin):
    url = serializers.HyperlinkedIdentityField(view_name="dcim-api:cable-detail")
    termination_a_type = ContentTypeField(queryset=ContentType.objects.filter(CABLE_TERMINATION_MODELS))
    termination_b_type = ContentTypeField(queryset=ContentType.objects.filter(CABLE_TERMINATION_MODELS))
    termination_a = serializers.SerializerMethodField(read_only=True)
    termination_b = serializers.SerializerMethodField(read_only=True)
    length_unit = ChoiceField(choices=CableLengthUnitChoices, allow_blank=True, required=False)

    class Meta:
        model = Cable
        fields = "__all__"

    def _get_termination(self, obj, side):
        """
        Serialize a nested representation of a termination.
        """
        if side.lower() not in ["a", "b"]:
            raise ValueError("Termination side must be either A or B.")
        termination = getattr(obj, f"termination_{side.lower()}")
        serializer = get_serializer_for_model(termination, prefix="Nested")
        context = {"request": self.context["request"]}
        data = serializer(termination, context=context).data

        return data

    @extend_schema_field(
        PolymorphicProxySerializer(
            component_name="CableTermination",
            resource_type_field_name="object_type",
            serializers=lambda: get_serializers_for_models(get_all_concrete_models(CableTermination), prefix="Nested"),
        )
    )
    def get_termination_a(self, obj):
        return self._get_termination(obj, "a")

    @extend_schema_field(
        PolymorphicProxySerializer(
            component_name="CableTermination",
            resource_type_field_name="object_type",
            serializers=lambda: get_serializers_for_models(get_all_concrete_models(CableTermination), prefix="Nested"),
        )
    )
    def get_termination_b(self, obj):
        return self._get_termination(obj, "b")


class TracedCableSerializer(StatusModelSerializerMixin, serializers.ModelSerializer):
    """
    Used only while tracing a cable path.
    """

    url = serializers.HyperlinkedIdentityField(view_name="dcim-api:cable-detail")

    class Meta:
        model = Cable
        fields = "__all__"


class CablePathSerializer(serializers.ModelSerializer):
    origin_type = ContentTypeField(read_only=True)
    origin = serializers.SerializerMethodField(read_only=True)
    destination_type = ContentTypeField(read_only=True)
    destination = serializers.SerializerMethodField(read_only=True)
    path = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = CablePath
        fields = "__all__"

    @extend_schema_field(
        PolymorphicProxySerializer(
            component_name="PathEndpoint",
            resource_type_field_name="object_type",
            serializers=lambda: get_serializers_for_models(get_all_concrete_models(PathEndpoint), prefix="Nested"),
        )
    )
    def get_origin(self, obj):
        """
        Return the appropriate serializer for the origin.
        """
        serializer = get_serializer_for_model(obj.origin, prefix="Nested")
        context = {"request": self.context["request"]}
        return serializer(obj.origin, context=context).data

    @extend_schema_field(
        PolymorphicProxySerializer(
            component_name="PathEndpoint",
            resource_type_field_name="object_type",
            serializers=lambda: get_serializers_for_models(get_all_concrete_models(PathEndpoint), prefix="Nested"),
            allow_null=True,
        )
    )
    def get_destination(self, obj):
        """
        Return the appropriate serializer for the destination, if any.
        """
        if obj.destination_id is not None:
            serializer = get_serializer_for_model(obj.destination, prefix="Nested")
            context = {"request": self.context["request"]}
            return serializer(obj.destination, context=context).data
        return None

    @extend_schema_field(
        PolymorphicProxySerializer(
            component_name="CableTermination",
            resource_type_field_name="object_type",
            serializers=lambda: get_serializers_for_models(get_all_concrete_models(CableTermination), prefix="Nested"),
            many=True,
        )
    )
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

    # TODO #3024: How to get rid of this?
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


class VirtualChassisSerializer(NautobotModelSerializer, TaggedModelSerializerMixin):
    url = serializers.HyperlinkedIdentityField(view_name="dcim-api:virtualchassis-detail")
    member_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = VirtualChassis
        fields = "__all__"
        extra_fields = ["member_count"]


#
# Power panels
#


class PowerPanelSerializer(NautobotModelSerializer, TaggedModelSerializerMixin):
    url = serializers.HyperlinkedIdentityField(view_name="dcim-api:powerpanel-detail")
    power_feed_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = PowerPanel
        fields = "__all__"
        extra_fields = ["power_feed_count"]


class PowerFeedSerializer(
    NautobotModelSerializer,
    TaggedModelSerializerMixin,
    CableTerminationModelSerializerMixin,
    PathEndpointModelSerializerMixin,
    StatusModelSerializerMixin,
):
    url = serializers.HyperlinkedIdentityField(view_name="dcim-api:powerfeed-detail")
    type = ChoiceField(choices=PowerFeedTypeChoices, default=PowerFeedTypeChoices.TYPE_PRIMARY)
    supply = ChoiceField(choices=PowerFeedSupplyChoices, default=PowerFeedSupplyChoices.SUPPLY_AC)
    phase = ChoiceField(choices=PowerFeedPhaseChoices, default=PowerFeedPhaseChoices.PHASE_SINGLE)

    class Meta:
        model = PowerFeed
        fields = "__all__"
