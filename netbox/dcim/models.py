from collections import OrderedDict

from django.core.exceptions import ValidationError
from django.core.urlresolvers import reverse
from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import Q, ObjectDoesNotExist

from extras.rpc import RPC_CLIENTS
from utilities.fields import NullableCharField


RACK_FACE_FRONT = 0
RACK_FACE_REAR = 1
RACK_FACE_CHOICES = [
    [RACK_FACE_FRONT, 'Front'],
    [RACK_FACE_REAR, 'Rear'],
]

COLOR_TEAL = 'teal'
COLOR_GREEN = 'green'
COLOR_BLUE = 'blue'
COLOR_PURPLE = 'purple'
COLOR_YELLOW = 'yellow'
COLOR_ORANGE = 'orange'
COLOR_RED = 'red'
COLOR_GRAY1 = 'light_gray'
COLOR_GRAY2 = 'medium_gray'
COLOR_GRAY3 = 'dark_gray'
DEVICE_ROLE_COLOR_CHOICES = [
    [COLOR_TEAL, 'Teal'],
    [COLOR_GREEN, 'Green'],
    [COLOR_BLUE, 'Blue'],
    [COLOR_PURPLE, 'Purple'],
    [COLOR_YELLOW, 'Yellow'],
    [COLOR_ORANGE, 'Orange'],
    [COLOR_RED, 'Red'],
    [COLOR_GRAY1, 'Light Gray'],
    [COLOR_GRAY2, 'Medium Gray'],
    [COLOR_GRAY3, 'Dark Gray'],
]

IFACE_FF_VIRTUAL = 0
IFACE_FF_100M_COPPER = 800
IFACE_FF_1GE_COPPER = 1000
IFACE_FF_SFP = 1100
IFACE_FF_SFP_PLUS = 1200
IFACE_FF_XFP = 1300
IFACE_FF_QSFP_PLUS = 1400
IFACE_FF_CHOICES = [
    [IFACE_FF_VIRTUAL, 'Virtual'],
    [IFACE_FF_100M_COPPER, '10/100M (Copper)'],
    [IFACE_FF_1GE_COPPER, '1GE (Copper)'],
    [IFACE_FF_SFP, '1GE (SFP)'],
    [IFACE_FF_SFP_PLUS, '10GE (SFP+)'],
    [IFACE_FF_XFP, '10GE (XFP)'],
    [IFACE_FF_QSFP_PLUS, '40GE (QSFP+)'],
]

STATUS_ACTIVE = True
STATUS_OFFLINE = False
STATUS_CHOICES = [
    [STATUS_ACTIVE, 'Active'],
    [STATUS_OFFLINE, 'Offline'],
]

CONNECTION_STATUS_PLANNED = False
CONNECTION_STATUS_CONNECTED = True
CONNECTION_STATUS_CHOICES = [
    [CONNECTION_STATUS_PLANNED, 'Planned'],
    [CONNECTION_STATUS_CONNECTED, 'Connected'],
]

# For mapping platform -> NC client
RPC_CLIENT_JUNIPER_JUNOS = 'juniper-junos'
RPC_CLIENT_CISCO_IOS = 'cisco-ios'
RPC_CLIENT_OPENGEAR = 'opengear'
RPC_CLIENT_CHOICES = [
    [RPC_CLIENT_JUNIPER_JUNOS, 'Juniper Junos (NETCONF)'],
    [RPC_CLIENT_CISCO_IOS, 'Cisco IOS (SSH)'],
    [RPC_CLIENT_OPENGEAR, 'Opengear (SSH)'],
]


class Site(models.Model):
    """
    A physical site
    """
    name = models.CharField(max_length=50, unique=True)
    slug = models.SlugField(unique=True)
    facility = models.CharField(max_length=50, blank=True)
    asn = models.PositiveIntegerField(blank=True, null=True, verbose_name='ASN')
    physical_address = models.CharField(max_length=200, blank=True)
    shipping_address = models.CharField(max_length=200, blank=True)
    comments = models.TextField(blank=True)

    class Meta:
        ordering = ['name']

    def __unicode__(self):
        return self.name

    def get_absolute_url(self):
        return reverse('dcim:site', args=[self.slug])

    @property
    def count_prefixes(self):
        return self.prefixes.count()

    @property
    def count_vlans(self):
        return self.vlans.count()

    @property
    def count_racks(self):
        return Rack.objects.filter(site=self).count()

    @property
    def count_devices(self):
        return Device.objects.filter(rack__site=self).count()

    @property
    def count_circuits(self):
        return self.circuits.count()


class RackGroup(models.Model):
    """
    An arbitrary grouping of Racks; e.g. a building or room.
    """
    name = models.CharField(max_length=50)
    slug = models.SlugField()
    site = models.ForeignKey('Site', related_name='rack_groups')

    class Meta:
        ordering = ['site', 'name']
        unique_together = [
            ['site', 'name'],
            ['site', 'slug'],
        ]

    def __unicode__(self):
        return self.name

    def get_absolute_url(self):
        return "{}?group={}".format(reverse('dcim:rack_list'), self.slug)


class Rack(models.Model):
    """
    An equipment rack within a site (e.g. a 48U rack)
    """
    name = models.CharField(max_length=50)
    facility_id = NullableCharField(max_length=30, blank=True, null=True, verbose_name='Facility ID')
    site = models.ForeignKey('Site', related_name='racks', on_delete=models.PROTECT)
    group = models.ForeignKey('RackGroup', related_name='racks', blank=True, null=True, on_delete=models.SET_NULL)
    u_height = models.PositiveSmallIntegerField(default=42, verbose_name='Height (U)')
    comments = models.TextField(blank=True)

    class Meta:
        ordering = ['site', 'name']
        unique_together = [
            ['site', 'name'],
            ['site', 'facility_id'],
        ]

    def __unicode__(self):
        if self.facility_id:
            return "{} ({})".format(self.name, self.facility_id)
        return self.name

    def get_absolute_url(self):
        return reverse('dcim:rack', args=[self.pk])

    @property
    def units(self):
        return reversed(range(1, self.u_height + 1))

    def get_rack_units(self, face=RACK_FACE_FRONT, remove_redundant=False):
        """
        Return a list of rack units as dictionaries. Example: {'device': None, 'face': 0, 'id': 48, 'name': 'U48'}
        Each key 'device' is either a Device or None. By default, multi-U devices are repeated for each U they occupy.

        :param face: Rack face (front or rear)
        :param remove_redundant: If True, rack units occupied by a device already listed will be omitted
        """

        elevation = OrderedDict()
        for u in reversed(range(1, self.u_height + 1)):
            elevation[u] = {'id': u, 'name': 'U{}'.format(u), 'face': face, 'device': None}

        # Add devices to rack units list
        if self.pk:
            for device in Device.objects.select_related('device_type__manufacturer', 'device_role')\
                    .filter(rack=self, position__gt=0).filter(Q(face=face) | Q(device_type__is_full_depth=True)):
                if remove_redundant:
                    elevation[device.position]['device'] = device
                    for u in range(device.position + 1, device.position + device.device_type.u_height):
                        elevation.pop(u, None)
                else:
                    for u in range(device.position, device.position + device.device_type.u_height):
                        elevation[u]['device'] = device

        return [u for u in elevation.values()]

    def get_front_elevation(self):
        return self.get_rack_units(face=RACK_FACE_FRONT, remove_redundant=True)

    def get_rear_elevation(self):
        return self.get_rack_units(face=RACK_FACE_REAR, remove_redundant=True)

    def get_available_units(self, u_height=1, rack_face=None, exclude=list()):
        """
        Return a list of units within the rack available to accommodate a device of a given U height (default 1).
        Optionally exclude one or more devices when calculating empty units (needed when moving a device from one
        position to another within a rack).

        :param u_height: Minimum number of contiguous free units required
        :param rack_face: The face of the rack (front or rear) required; 'None' if device is full depth
        :param exclude: List of devices IDs to exclude (useful when moving a device within a rack)
        """

        # Gather all devices which consume U space within the rack
        devices = self.devices.select_related().filter(position__gte=1).exclude(pk__in=exclude)

        # Initialize the rack unit skeleton
        units = range(1, self.u_height + 1)

        # Remove units consumed by installed devices
        for d in devices:
            if rack_face is None or d.face == rack_face or d.device_type.is_full_depth:
                for u in range(d.position, d.position + d.device_type.u_height):
                    try:
                        units.remove(u)
                    except ValueError:
                        # Found overlapping devices in the rack!
                        pass

        # Remove units without enough space above them to accommodate a device of the specified height
        available_units = []
        for u in units:
            if set(range(u, u + u_height)).issubset(units):
                available_units.append(u)

        return list(reversed(available_units))

    def get_0u_devices(self):
        return self.devices.filter(position=0)


#
# Device Types
#

class Manufacturer(models.Model):
    """
    A hardware manufacturer
    """
    name = models.CharField(max_length=50, unique=True)
    slug = models.SlugField(unique=True)

    class Meta:
        ordering = ['name']

    def __unicode__(self):
        return self.name


class DeviceType(models.Model):
    """
    A unique hardware type; manufacturer and model number (e.g. Juniper EX4300-48T)
    """
    manufacturer = models.ForeignKey('Manufacturer', related_name='device_types', on_delete=models.PROTECT)
    model = models.CharField(max_length=50)
    slug = models.SlugField()
    u_height = models.PositiveSmallIntegerField(verbose_name='Height (U)', default=1)
    is_full_depth = models.BooleanField(default=True, verbose_name="Is full depth",
                                        help_text="Device consumes both front and rear rack faces")
    is_console_server = models.BooleanField(default=False, verbose_name='Is a console server',
                                            help_text="This type of device has console server ports")
    is_pdu = models.BooleanField(default=False, verbose_name='Is a PDU',
                                 help_text="This type of device has power outlets")
    is_network_device = models.BooleanField(default=True, verbose_name='Is a network device',
                                            help_text="This type of device has network interfaces")

    class Meta:
        ordering = ['manufacturer', 'model']
        unique_together = [
            ['manufacturer', 'model'],
            ['manufacturer', 'slug'],
        ]

    def __unicode__(self):
        return "{0} {1}".format(self.manufacturer, self.model)

    def get_absolute_url(self):
        return reverse('dcim:devicetype', args=[self.pk])


class ConsolePortTemplate(models.Model):
    """
    A template for a ConsolePort to be created for a new device
    """
    device_type = models.ForeignKey('DeviceType', related_name='console_port_templates', on_delete=models.CASCADE)
    name = models.CharField(max_length=30)

    class Meta:
        ordering = ['device_type', 'name']
        unique_together = ['device_type', 'name']

    def __unicode__(self):
        return self.name


class ConsoleServerPortTemplate(models.Model):
    """
    A template for a ConsoleServerPort to be created for a new device
    """
    device_type = models.ForeignKey('DeviceType', related_name='cs_port_templates', on_delete=models.CASCADE)
    name = models.CharField(max_length=30)

    class Meta:
        ordering = ['device_type', 'name']
        unique_together = ['device_type', 'name']

    def __unicode__(self):
        return self.name


class PowerPortTemplate(models.Model):
    """
    A template for a PowerPort to be created for a new device
    """
    device_type = models.ForeignKey('DeviceType', related_name='power_port_templates', on_delete=models.CASCADE)
    name = models.CharField(max_length=30)

    class Meta:
        ordering = ['device_type', 'name']
        unique_together = ['device_type', 'name']

    def __unicode__(self):
        return self.name


class PowerOutletTemplate(models.Model):
    """
    A template for a PowerOutlet to be created for a new device
    """
    device_type = models.ForeignKey('DeviceType', related_name='power_outlet_templates', on_delete=models.CASCADE)
    name = models.CharField(max_length=30)

    class Meta:
        ordering = ['device_type', 'name']
        unique_together = ['device_type', 'name']

    def __unicode__(self):
        return self.name


class InterfaceTemplate(models.Model):
    """
    A template for a physical data interface on a new device
    """
    device_type = models.ForeignKey('DeviceType', related_name='interface_templates', on_delete=models.CASCADE)
    name = models.CharField(max_length=30)
    form_factor = models.PositiveSmallIntegerField(choices=IFACE_FF_CHOICES, default=IFACE_FF_SFP_PLUS)
    mgmt_only = models.BooleanField(default=False, verbose_name='Management only')

    class Meta:
        ordering = ['device_type', 'name']
        unique_together = ['device_type', 'name']

    def __unicode__(self):
        return self.name


#
# Devices
#

class DeviceRole(models.Model):
    """
    The functional role of a device (e.g. router, switch, console server, etc.)
    """
    name = models.CharField(max_length=50, unique=True)
    slug = models.SlugField(unique=True)
    color = models.CharField(max_length=30, choices=DEVICE_ROLE_COLOR_CHOICES)

    class Meta:
        ordering = ['name']

    def __unicode__(self):
        return self.name


class Platform(models.Model):
    """
    A class of software running on a hardware device (e.g. Juniper Junos or Cisco IOS)
    """
    name = models.CharField(max_length=50, unique=True)
    slug = models.SlugField(unique=True)
    rpc_client = models.CharField(max_length=30, choices=RPC_CLIENT_CHOICES, blank=True, verbose_name='RPC client')

    class Meta:
        ordering = ['name']

    def __unicode__(self):
        return self.name


class Device(models.Model):
    """
    A physical piece of equipment mounted within a rack
    """
    device_type = models.ForeignKey('DeviceType', related_name='instances', on_delete=models.PROTECT)
    device_role = models.ForeignKey('DeviceRole', related_name='devices', on_delete=models.PROTECT)
    platform = models.ForeignKey('Platform', related_name='devices', blank=True, null=True, on_delete=models.SET_NULL)
    name = NullableCharField(max_length=50, blank=True, null=True, unique=True)
    serial = models.CharField(max_length=50, blank=True, verbose_name='Serial number')
    rack = models.ForeignKey('Rack', related_name='devices', on_delete=models.PROTECT)
    position = models.PositiveSmallIntegerField(blank=True, null=True, validators=[MinValueValidator(1)], verbose_name='Position (U)', help_text='Number of the lowest U position occupied by the device')
    face = models.PositiveSmallIntegerField(blank=True, null=True, choices=RACK_FACE_CHOICES, verbose_name='Rack face')
    status = models.BooleanField(choices=STATUS_CHOICES, default=STATUS_ACTIVE, verbose_name='Status')
    primary_ip = models.OneToOneField('ipam.IPAddress', related_name='primary_for', on_delete=models.SET_NULL, blank=True, null=True, verbose_name='Primary IP')
    ro_snmp = models.CharField(max_length=50, blank=True, verbose_name='SNMP (RO)')
    comments = models.TextField(blank=True)

    class Meta:
        ordering = ['name']
        unique_together = ['rack', 'position', 'face']

    def __unicode__(self):
        return self.display_name

    def get_absolute_url(self):
        return reverse('dcim:device', args=[self.pk])

    @property
    def display_name(self):
        if self.name:
            return self.name
        elif self.position:
            return "{} ({} U{})".format(self.device_type, self.rack, self.position)
        else:
            return "{} ({})".format(self.device_type, self.rack)

    def clean(self):

        # Validate position/face combination
        if self.position and self.face is None:
            raise ValidationError("Must specify rack face with rack position.")

        # Validate rack space
        rack_face = self.face if not self.device_type.is_full_depth else None
        exclude_list = [self.pk] if self.pk else []
        try:
            available_units = self.rack.get_available_units(u_height=self.device_type.u_height, rack_face=rack_face,
                                                            exclude=exclude_list)
            if self.position and self.position not in available_units:
                raise ValidationError("U{} is already occupied or does not have sufficient space to accommodate a(n) "
                                      "{} ({}U).".format(self.position, self.device_type, self.device_type.u_height))
        except Rack.DoesNotExist:
            pass

    def save(self, *args, **kwargs):

        is_new = not bool(self.pk)

        super(Device, self).save(*args, **kwargs)

        # If this is a new Device, instantiate all of the related components per the DeviceType definition
        if is_new:
            ConsolePort.objects.bulk_create(
                [ConsolePort(device=self, name=template.name) for template in self.device_type.console_port_templates.all()]
            )
            ConsoleServerPort.objects.bulk_create(
                [ConsoleServerPort(device=self, name=template.name) for template in self.device_type.cs_port_templates.all()]
            )
            PowerPort.objects.bulk_create(
                [PowerPort(device=self, name=template.name) for template in self.device_type.power_port_templates.all()]
            )
            PowerOutlet.objects.bulk_create(
                [PowerOutlet(device=self, name=template.name) for template in self.device_type.power_outlet_templates.all()]
            )
            Interface.objects.bulk_create(
                [Interface(device=self, name=template.name, form_factor=template.form_factor, mgmt_only=template.mgmt_only) for template in self.device_type.interface_templates.all()]
            )

    def get_rpc_client(self):
        """
        Return the appropriate RPC (e.g. NETCONF, ssh, etc.) client for this device's platform, if one is defined.
        """
        if not self.platform:
            return None
        return RPC_CLIENTS.get(self.platform.rpc_client)


class ConsolePort(models.Model):
    """
    A physical console port on a device
    """
    device = models.ForeignKey('Device', related_name='console_ports', on_delete=models.CASCADE)
    name = models.CharField(max_length=30)
    cs_port = models.OneToOneField('ConsoleServerPort', related_name='connected_console', on_delete=models.SET_NULL, verbose_name='Console server port', blank=True, null=True)
    connection_status = models.NullBooleanField(choices=CONNECTION_STATUS_CHOICES, default=CONNECTION_STATUS_CONNECTED)

    class Meta:
        ordering = ['device', 'name']
        unique_together = ['device', 'name']

    def __unicode__(self):
        return self.name


class ConsoleServerPortManager(models.Manager):

    def get_queryset(self):
        """
        Include the trailing numeric portion of each port name to allow for proper ordering.
        For example:
            Port 1, Port 2, Port 3 ... Port 9, Port 10, Port 11 ...
        Instead of:
            Port 1, Port 10, Port 11 ... Port 19, Port 2, Port 20 ...
        """
        return super(ConsoleServerPortManager, self).get_queryset().extra(select={
            'name_as_integer': "CAST(substring(dcim_consoleserverport.name FROM '[0-9]+$') AS INTEGER)",
        }).order_by('device', 'name_as_integer')


class ConsoleServerPort(models.Model):
    """
    A physical port on a console server
    """
    device = models.ForeignKey('Device', related_name='cs_ports', on_delete=models.CASCADE)
    name = models.CharField(max_length=30)

    objects = ConsoleServerPortManager()

    class Meta:
        unique_together = ['device', 'name']

    def __unicode__(self):
        return self.name


class PowerPort(models.Model):
    """
    A physical power supply (intake) port on a device
    """
    device = models.ForeignKey('Device', related_name='power_ports', on_delete=models.CASCADE)
    name = models.CharField(max_length=30)
    power_outlet = models.OneToOneField('PowerOutlet', related_name='connected_port', on_delete=models.SET_NULL, blank=True, null=True)
    connection_status = models.NullBooleanField(choices=CONNECTION_STATUS_CHOICES, default=CONNECTION_STATUS_CONNECTED)

    class Meta:
        ordering = ['device', 'name']
        unique_together = ['device', 'name']

    def __unicode__(self):
        return self.name


class PowerOutletManager(models.Manager):

    def get_queryset(self):
        return super(PowerOutletManager, self).get_queryset().extra(select={
            'name_padded': "CONCAT(SUBSTRING(dcim_poweroutlet.name FROM '^[^0-9]+'), LPAD(SUBSTRING(dcim_poweroutlet.name FROM '[0-9\/]+$'), 8, '0'))",
        }).order_by('device', 'name_padded')


class PowerOutlet(models.Model):
    """
    A physical power outlet (output) port on a device
    """
    device = models.ForeignKey('Device', related_name='power_outlets', on_delete=models.CASCADE)
    name = models.CharField(max_length=30)

    objects = PowerOutletManager()

    class Meta:
        unique_together = ['device', 'name']

    def __unicode__(self):
        return self.name


class InterfaceManager(models.Manager):

    def get_queryset(self):
        """
        Cast up to three interface slot/position IDs as independent integers and order appropriately. This ensures that
        interfaces are ordered numerically without regard to type. For example:
            xe-0/0/0, xe-0/0/1, xe-0/0/2 ... et-0/0/47, et-0/0/48, et-0/0/49 ...
        instead of:
            et-0/0/48, et-0/0/49, et-0/0/50 ... et-0/0/53, xe-0/0/0, xe-0/0/1 ...
        """
        return super(InterfaceManager, self).get_queryset().extra(select={
            '_id1': "CAST(SUBSTRING(dcim_interface.name FROM '([0-9]+)\/([0-9]+)\/([0-9]+)$') AS integer)",
            '_id2': "CAST(SUBSTRING(dcim_interface.name FROM '([0-9]+)\/([0-9]+)$') AS integer)",
            '_id3': "CAST(SUBSTRING(dcim_interface.name FROM '([0-9]+)$') AS integer)",
        }).order_by('device', '_id1', '_id2', '_id3')

    def virtual(self):
        return self.get_queryset().filter(form_factor=IFACE_FF_VIRTUAL)

    def physical(self):
        return self.get_queryset().exclude(form_factor=IFACE_FF_VIRTUAL)


class Interface(models.Model):
    """
    A physical data interface on a device
    """
    device = models.ForeignKey('Device', related_name='interfaces', on_delete=models.CASCADE)
    name = models.CharField(max_length=30)
    form_factor = models.PositiveSmallIntegerField(choices=IFACE_FF_CHOICES, default=IFACE_FF_SFP_PLUS)
    mgmt_only = models.BooleanField(default=False, verbose_name='OOB Management')
    description = models.CharField(max_length=100, blank=True)

    objects = InterfaceManager()

    class Meta:
        ordering = ['device', 'name']
        unique_together = ['device', 'name']

    def __unicode__(self):
        return self.name

    @property
    def is_physical(self):
        return self.form_factor != IFACE_FF_VIRTUAL

    @property
    def is_connected(self):
        try:
            return bool(self.circuit)
        except ObjectDoesNotExist:
            pass
        return bool(self.connection)

    @property
    def connection(self):
        try:
            return self.connected_as_a
        except ObjectDoesNotExist:
            pass
        try:
            return self.connected_as_b
        except ObjectDoesNotExist:
            pass
        return None

    def get_connected_interface(self):
        try:
            connection = InterfaceConnection.objects.select_related().get(Q(interface_a=self) | Q(interface_b=self))
            if connection.interface_a == self:
                return connection.interface_b
            else:
                return connection.interface_a
        except InterfaceConnection.DoesNotExist:
            return None
        except InterfaceConnection.MultipleObjectsReturned as e:
            raise e("Multiple connections found for {0} interface {1}!".format(self.device, self))


class InterfaceConnection(models.Model):
    """
    A symmetrical, one-to-one connection between two device interfaces
    """
    interface_a = models.OneToOneField('Interface', related_name='connected_as_a', on_delete=models.CASCADE)
    interface_b = models.OneToOneField('Interface', related_name='connected_as_b', on_delete=models.CASCADE)
    connection_status = models.BooleanField(choices=CONNECTION_STATUS_CHOICES, default=CONNECTION_STATUS_CONNECTED, verbose_name='Status')

    def clean(self):

        if self.interface_a == self.interface_b:
            raise ValidationError("Cannot connect an interface to itself")


class Module(models.Model):
    """
    A hardware module belonging to a device. Used for inventory purposes only.
    """
    device = models.ForeignKey('Device', related_name='modules', on_delete=models.CASCADE)
    parent = models.ForeignKey('self', related_name='submodules', blank=True, null=True, on_delete=models.CASCADE)
    name = models.CharField(max_length=50, verbose_name='Name')
    part_id = models.CharField(max_length=50, verbose_name='Part ID', blank=True)
    serial = models.CharField(max_length=50, verbose_name='Serial number', blank=True)

    class Meta:
        ordering = ['device__id', 'parent__id', 'name']
        unique_together = ['device', 'parent', 'name']

    def __unicode__(self):
        return self.name
