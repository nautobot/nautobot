import django_tables2 as tables
from django_tables2.utils import Accessor

from .models import Site, RackGroup, Rack, Manufacturer, DeviceType, ConsolePortTemplate, ConsoleServerPortTemplate,\
    PowerPortTemplate, PowerOutletTemplate, InterfaceTemplate, DeviceRole, Device, ConsolePort, PowerPort

DEVICE_LINK = """
<a href="{% url 'dcim:device' pk=record.pk %}">{{ record.name|default:'<span class="label label-info">Unnamed device</span>' }}</a>
"""

RACKGROUP_EDIT_LINK = """
{% if perms.dcim.change_rackgroup %}<a href="{% url 'dcim:rackgroup_edit' pk=record.pk %}">Edit</a>{% endif %}
"""

DEVICEROLE_EDIT_LINK = """
{% if perms.dcim.change_devicerole %}<a href="{% url 'dcim:devicerole_edit' slug=record.slug %}">Edit</a>{% endif %}
"""

MANUFACTURER_EDIT_LINK = """
{% if perms.dcim.change_manufacturer %}<a href="{% url 'dcim:manufacturer_edit' slug=record.slug %}">Edit</a>{% endif %}
"""

STATUS_ICON = """
<span class="glyphicon glyphicon-{% if record.status %}ok-sign text-success" title="Active{% else %}minus-sign text-danger" title="Offline{% endif %}" aria-hidden="true"></span>
"""


#
# Sites
#

class SiteTable(tables.Table):
    name = tables.LinkColumn('dcim:site', args=[Accessor('slug')], verbose_name='Name')
    facility = tables.Column(verbose_name='Facility')
    asn = tables.Column(verbose_name='ASN')
    rack_count = tables.Column(accessor=Accessor('count_racks'), orderable=False, verbose_name='Racks')
    device_count = tables.Column(accessor=Accessor('count_devices'), orderable=False, verbose_name='Devices')
    prefix_count = tables.Column(accessor=Accessor('count_prefixes'), orderable=False, verbose_name='Prefixes')
    vlan_count = tables.Column(accessor=Accessor('count_vlans'), orderable=False, verbose_name='VLANs')
    circuit_count = tables.Column(accessor=Accessor('count_circuits'), orderable=False, verbose_name='Circuits')

    class Meta:
        model = Site
        fields = ('name', 'facility', 'asn', 'rack_count', 'device_count', 'prefix_count', 'vlan_count', 'circuit_count')
        empty_text = "No sites have been defined."
        attrs = {
            'class': 'table table-hover',
        }


#
# Rack groups
#

class RackGroupTable(tables.Table):
    pk = tables.CheckBoxColumn(visible=False, default='')
    name = tables.LinkColumn(verbose_name='Name')
    site = tables.LinkColumn('dcim:site', args=[Accessor('site.slug')], verbose_name='Site')
    rack_count = tables.Column(verbose_name='Racks')
    slug = tables.Column(verbose_name='Slug')
    edit = tables.TemplateColumn(template_code=RACKGROUP_EDIT_LINK, verbose_name='')

    class Meta:
        model = RackGroup
        fields = ('pk', 'name', 'site', 'rack_count', 'slug', 'edit')
        empty_text = "No rack groups were found."
        attrs = {
            'class': 'table table-hover',
        }


#
# Racks
#

class RackTable(tables.Table):
    pk = tables.CheckBoxColumn(visible=False, default='')
    name = tables.LinkColumn('dcim:rack', args=[Accessor('pk')], verbose_name='Name')
    site = tables.LinkColumn('dcim:site', args=[Accessor('site.slug')], verbose_name='Site')
    group = tables.Column(accessor=Accessor('group.name'), verbose_name='Group')
    facility_id = tables.Column(verbose_name='Facility ID')
    u_height = tables.Column(verbose_name='Height (U)')
    devices = tables.Column(accessor=Accessor('device_count'), orderable=False, verbose_name='Devices')

    class Meta:
        model = Rack
        fields = ('pk', 'name', 'site', 'group', 'facility_id', 'u_height')
        empty_text = "No racks were found."
        attrs = {
            'class': 'table table-hover',
        }


#
# Manufacturers
#

class ManufacturerTable(tables.Table):
    pk = tables.CheckBoxColumn(visible=False, default='')
    name = tables.LinkColumn(verbose_name='Name')
    devicetype_count = tables.Column(verbose_name='Device Types')
    slug = tables.Column(verbose_name='Slug')
    edit = tables.TemplateColumn(template_code=MANUFACTURER_EDIT_LINK, verbose_name='')

    class Meta:
        model = Manufacturer
        fields = ('pk', 'name', 'devicetype_count', 'slug', 'edit')
        empty_text = "No device types were found."
        attrs = {
            'class': 'table table-hover',
        }


#
# Device types
#

class DeviceTypeTable(tables.Table):
    pk = tables.CheckBoxColumn(visible=False, default='')
    model = tables.LinkColumn('dcim:devicetype', args=[Accessor('pk')], verbose_name='Device Type')

    class Meta:
        model = DeviceType
        fields = ('pk', 'model', 'manufacturer', 'u_height')
        empty_text = "No device types were found."
        attrs = {
            'class': 'table table-hover',
        }


#
# Device type components
#

class ConsolePortTemplateTable(tables.Table):
    pk = tables.CheckBoxColumn(visible=False, default='')

    class Meta:
        model = ConsolePortTemplate
        fields = ('pk', 'name')
        empty_text = "None"
        show_header = False
        attrs = {
            'class': 'table table-hover panel-body',
        }


class ConsoleServerPortTemplateTable(tables.Table):
    pk = tables.CheckBoxColumn(visible=False, default='')

    class Meta:
        model = ConsoleServerPortTemplate
        fields = ('pk', 'name')
        empty_text = "None"
        show_header = False
        attrs = {
            'class': 'table table-hover panel-body',
        }


class PowerPortTemplateTable(tables.Table):
    pk = tables.CheckBoxColumn(visible=False, default='')

    class Meta:
        model = PowerPortTemplate
        fields = ('pk', 'name')
        empty_text = "None"
        show_header = False
        attrs = {
            'class': 'table table-hover panel-body',
        }


class PowerOutletTemplateTable(tables.Table):
    pk = tables.CheckBoxColumn(visible=False, default='')

    class Meta:
        model = PowerOutletTemplate
        fields = ('pk', 'name')
        empty_text = "None"
        show_header = False
        attrs = {
            'class': 'table table-hover panel-body',
        }


class InterfaceTemplateTable(tables.Table):
    pk = tables.CheckBoxColumn(visible=False, default='')

    class Meta:
        model = InterfaceTemplate
        fields = ('pk', 'name')
        empty_text = "None"
        show_header = False
        attrs = {
            'class': 'table table-hover panel-body',
        }


#
# Device roles
#

class DeviceRoleTable(tables.Table):
    pk = tables.CheckBoxColumn(visible=False, default='')
    name = tables.LinkColumn(verbose_name='Name')
    device_count = tables.Column(verbose_name='Devices')
    slug = tables.Column(verbose_name='Slug')
    color = tables.Column(verbose_name='Color')
    edit = tables.TemplateColumn(template_code=DEVICEROLE_EDIT_LINK, verbose_name='')

    class Meta:
        model = DeviceRole
        fields = ('pk', 'name', 'device_count', 'slug', 'color')
        empty_text = "No device roles were found."
        attrs = {
            'class': 'table table-hover',
        }


#
# Devices
#

class DeviceTable(tables.Table):
    pk = tables.CheckBoxColumn(visible=False, default='')
    status = tables.TemplateColumn(template_code=STATUS_ICON, verbose_name='')
    name = tables.TemplateColumn(template_code=DEVICE_LINK, verbose_name='Name')
    site = tables.Column(accessor=Accessor('rack.site'), verbose_name='Site')
    rack = tables.LinkColumn('dcim:rack', args=[Accessor('rack.pk')], verbose_name='Rack')
    device_role = tables.Column(verbose_name='Role')
    device_type = tables.Column(verbose_name='Type')
    primary_ip = tables.TemplateColumn(orderable=False, verbose_name='IP Address', template_code="{{ record.primary_ip.address.ip }}")

    class Meta:
        model = Device
        fields = ('pk', 'name', 'status', 'site', 'rack', 'device_role', 'device_type', 'primary_ip')
        empty_text = "No devices were found."
        attrs = {
            'class': 'table table-hover',
        }


class DeviceImportTable(tables.Table):
    name = tables.TemplateColumn(template_code=DEVICE_LINK, verbose_name='Name')
    site = tables.Column(accessor=Accessor('rack.site'), verbose_name='Site')
    rack = tables.LinkColumn('dcim:rack', args=[Accessor('rack.pk')], verbose_name='Rack')
    position = tables.Column(verbose_name='Position')
    device_role = tables.Column(verbose_name='Role')
    device_type = tables.Column(verbose_name='Type')

    class Meta:
        model = Device
        fields = ('name', 'site', 'rack', 'position', 'device_role', 'device_type')
        attrs = {
            'class': 'table table-hover',
        }


#
# Device connections
#

class ConsoleConnectionTable(tables.Table):
    console_server = tables.LinkColumn('dcim:device', accessor=Accessor('cs_port.device'), args=[Accessor('cs_port.device.pk')], verbose_name='Console server')
    cs_port = tables.Column(verbose_name='Port')
    device = tables.LinkColumn('dcim:device', args=[Accessor('device.pk')], verbose_name='Device')
    name = tables.Column(verbose_name='Console port')

    class Meta:
        model = ConsolePort
        fields = ('console_server', 'cs_port', 'device', 'name')
        attrs = {
            'class': 'table table-hover',
        }


class PowerConnectionTable(tables.Table):
    pdu = tables.LinkColumn('dcim:device', accessor=Accessor('power_outlet.device'), args=[Accessor('power_outlet.device.pk')], verbose_name='PDU')
    power_outlet = tables.Column(verbose_name='Outlet')
    device = tables.LinkColumn('dcim:device', args=[Accessor('device.pk')], verbose_name='Device')
    name = tables.Column(verbose_name='Console port')

    class Meta:
        model = PowerPort
        fields = ('pdu', 'power_outlet', 'device', 'name')
        attrs = {
            'class': 'table table-hover',
        }


class InterfaceConnectionTable(tables.Table):
    device_a = tables.LinkColumn('dcim:device', accessor=Accessor('interface_a.device'), args=[Accessor('interface_a.device.pk')], verbose_name='Device A')
    interface_a = tables.Column(verbose_name='Interface A')
    device_b = tables.LinkColumn('dcim:device', accessor=Accessor('interface_b.device'), args=[Accessor('interface_b.device.pk')], verbose_name='Device B')
    interface_b = tables.Column(verbose_name='Interface B')

    class Meta:
        model = PowerPort
        fields = ('device_a', 'interface_a', 'device_b', 'interface_b')
        attrs = {
            'class': 'table table-hover',
        }
