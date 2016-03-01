from rest_framework import serializers

from ipam.models import IPAddress
from dcim.models import Site, Rack, RackGroup, Manufacturer, DeviceType, DeviceRole, Platform, Device, ConsolePort,\
    ConsoleServerPort, PowerPort, PowerOutlet, Interface, InterfaceConnection, RACK_FACE_FRONT, RACK_FACE_REAR


#
# Sites
#

class SiteSerializer(serializers.ModelSerializer):

    class Meta:
        model = Site
        fields = ['id', 'name', 'slug', 'facility', 'asn', 'physical_address', 'shipping_address', 'comments',
                  'count_prefixes', 'count_vlans', 'count_racks', 'count_devices', 'count_circuits']


class SiteNestedSerializer(SiteSerializer):

    class Meta(SiteSerializer.Meta):
        fields = ['id', 'name', 'slug']


#
# Rack groups
#

class RackGroupSerializer(serializers.ModelSerializer):
    site = SiteNestedSerializer()

    class Meta:
        model = RackGroup
        fields = ['id', 'name', 'slug', 'site']


class RackGroupNestedSerializer(SiteSerializer):

    class Meta(SiteSerializer.Meta):
        fields = ['id', 'name', 'slug']


#
# Racks
#


class RackSerializer(serializers.ModelSerializer):
    display_name = serializers.SerializerMethodField()
    site = SiteNestedSerializer()
    group = RackGroupNestedSerializer()

    class Meta:
        model = Rack
        fields = ['id', 'name', 'facility_id', 'display_name', 'site', 'group', 'u_height', 'comments']

    def get_display_name(self, obj):
        return str(obj)


class RackNestedSerializer(RackSerializer):

    class Meta(RackSerializer.Meta):
        fields = ['id', 'name', 'facility_id', 'display_name']


class RackDetailSerializer(RackSerializer):
    front_units = serializers.SerializerMethodField()
    rear_units = serializers.SerializerMethodField()

    class Meta(RackSerializer.Meta):
        fields = ['id', 'name', 'facility_id', 'display_name', 'site', 'group', 'u_height', 'comments', 'front_units',
                  'rear_units']

    def get_front_units(self, obj):
        units = obj.get_rack_units(face=RACK_FACE_FRONT)
        for u in units:
            u['device'] = DeviceNestedSerializer(u['device']).data if u['device'] else None
        return units

    def get_rear_units(self, obj):
        units = obj.get_rack_units(face=RACK_FACE_REAR)
        for u in units:
            u['device'] = DeviceNestedSerializer(u['device']).data if u['device'] else None
        return units


#
# Manufacturers
#

class ManufacturerSerializer(serializers.ModelSerializer):

    class Meta:
        model = Manufacturer
        fields = ['id', 'name', 'slug']


class ManufacturerNestedSerializer(ManufacturerSerializer):

    class Meta(ManufacturerSerializer.Meta):
        pass


#
# Device types
#

class DeviceTypeSerializer(serializers.ModelSerializer):
    manufacturer = ManufacturerNestedSerializer()

    class Meta:
        model = DeviceType
        fields = ['id', 'manufacturer', 'model', 'slug', 'u_height', 'is_console_server', 'is_pdu', 'is_network_device']


class DeviceTypeNestedSerializer(DeviceTypeSerializer):

    class Meta(DeviceTypeSerializer.Meta):
        fields = ['id', 'manufacturer', 'model', 'slug']


#
# Device roles
#

class DeviceRoleSerializer(serializers.ModelSerializer):

    class Meta:
        model = DeviceRole
        fields = ['id', 'name', 'slug', 'color']


class DeviceRoleNestedSerializer(DeviceRoleSerializer):

    class Meta(DeviceRoleSerializer.Meta):
        fields = ['id', 'name', 'slug']


#
# Platforms
#

class PlatformSerializer(serializers.ModelSerializer):

    class Meta:
        model = Platform
        fields = ['id', 'name', 'slug', 'rpc_client']


class PlatformNestedSerializer(PlatformSerializer):

    class Meta(PlatformSerializer.Meta):
        fields = ['id', 'name', 'slug']


#
# Devices
#

# Cannot import ipam.api.IPAddressNestedSerializer due to circular dependency
class DeviceIPAddressNestedSerializer(serializers.ModelSerializer):

    class Meta:
        model = IPAddress
        fields = ['id', 'family', 'address']


class DeviceSerializer(serializers.ModelSerializer):
    device_type = DeviceTypeNestedSerializer()
    device_role = DeviceRoleNestedSerializer()
    platform = PlatformNestedSerializer()
    rack = RackNestedSerializer()
    primary_ip = DeviceIPAddressNestedSerializer()

    class Meta:
        model = Device
        fields = ['id', 'name', 'display_name', 'device_type', 'device_role', 'platform', 'serial', 'rack', 'position',
                  'face', 'status', 'primary_ip', 'ro_snmp', 'comments']


class DeviceNestedSerializer(DeviceSerializer):

    class Meta(DeviceSerializer.Meta):
        model = Device
        fields = ['id', 'name']


#
# Console server ports
#

class ConsoleServerPortSerializer(serializers.ModelSerializer):
    device = DeviceNestedSerializer()

    class Meta:
        model = ConsoleServerPort
        fields = ['id', 'device', 'name', 'connected_console']


class ConsoleServerPortNestedSerializer(ConsoleServerPortSerializer):

    class Meta(ConsoleServerPortSerializer.Meta):
        fields = ['id', 'device', 'name']


#
# Console ports
#

class ConsolePortSerializer(serializers.ModelSerializer):
    device = DeviceNestedSerializer()
    cs_port = ConsoleServerPortNestedSerializer()

    class Meta:
        model = ConsolePort
        fields = ['id', 'device', 'name', 'cs_port', 'connection_status']


class ConsolePortNestedSerializer(ConsolePortSerializer):

    class Meta(ConsolePortSerializer.Meta):
        fields = ['id', 'device', 'name']


#
# Power outlets
#

class PowerOutletSerializer(serializers.ModelSerializer):
    device = DeviceNestedSerializer()

    class Meta:
        model = PowerOutlet
        fields = ['id', 'device', 'name', 'connected_port']


class PowerOutletNestedSerializer(PowerOutletSerializer):

    class Meta(PowerOutletSerializer.Meta):
        fields = ['id', 'device', 'name']


#
# Power ports
#

class PowerPortSerializer(serializers.ModelSerializer):
    device = DeviceNestedSerializer()
    power_outlet = PowerOutletNestedSerializer()

    class Meta:
        model = PowerPort
        fields = ['id', 'device', 'name', 'power_outlet', 'connection_status']


class PowerPortNestedSerializer(PowerPortSerializer):

    class Meta(PowerPortSerializer.Meta):
        fields = ['id', 'device', 'name']


#
# Interfaces
#

class InterfaceSerializer(serializers.ModelSerializer):
    device = DeviceNestedSerializer()
    form_factor = serializers.ReadOnlyField(source='get_form_factor_display')

    class Meta:
        model = Interface
        fields = ['id', 'device', 'name', 'form_factor', 'mgmt_only', 'description', 'is_connected']


class InterfaceNestedSerializer(InterfaceSerializer):
    form_factor = serializers.ReadOnlyField(source='get_form_factor_display')

    class Meta(InterfaceSerializer.Meta):
        fields = ['id', 'device', 'name']


class InterfaceDetailSerializer(InterfaceSerializer):
    connected_interface = InterfaceSerializer(source='get_connected_interface')

    class Meta(InterfaceSerializer.Meta):
        fields = ['id', 'device', 'name', 'form_factor', 'mgmt_only', 'description', 'is_connected',
                  'connected_interface']


#
# Interface connections
#

class InterfaceConnectionSerializer(serializers.ModelSerializer):

    class Meta:
        model = InterfaceConnection
        fields = ['id', 'interface_a', 'interface_b', 'connection_status']
