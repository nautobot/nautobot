from collections import OrderedDict

import yaml
from django.contrib.contenttypes.fields import GenericRelation
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.core.serializers.json import DjangoJSONEncoder
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models import F, ProtectedError, Q
from django.utils.functional import cached_property
from django.urls import reverse
from django.utils.functional import classproperty
from django.utils.safestring import mark_safe

from nautobot.core.models import BaseManager
from nautobot.core.models.fields import NaturalOrderingField
from nautobot.core.models.generics import OrganizationalModel, PrimaryModel
from nautobot.core.utils.config import get_settings_or_config
from nautobot.dcim.choices import DeviceFaceChoices, DeviceRedundancyGroupFailoverStrategyChoices, SubdeviceRoleChoices
from nautobot.extras.models import ConfigContextModel, RoleField, StatusField
from nautobot.extras.querysets import ConfigContextModelQuerySet
from nautobot.extras.utils import extras_features
from .device_components import (
    ConsolePort,
    ConsoleServerPort,
    DeviceBay,
    FrontPort,
    Interface,
    PowerOutlet,
    PowerPort,
    RearPort,
)
from nautobot.dcim.utils import get_all_network_driver_mappings


__all__ = (
    "Device",
    "DeviceRedundancyGroup",
    "DeviceType",
    "Manufacturer",
    "Platform",
    "VirtualChassis",
)


#
# Device Types
#


@extras_features(
    "custom_validators",
    "export_templates",
    "graphql",
    "webhooks",
)
class Manufacturer(OrganizationalModel):
    """
    A Manufacturer represents a company which produces hardware devices; for example, Juniper or Dell.
    """

    name = models.CharField(max_length=100, unique=True)
    description = models.CharField(max_length=200, blank=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


@extras_features(
    "custom_links",
    "custom_validators",
    "export_templates",
    "graphql",
    "webhooks",
)
class DeviceType(PrimaryModel):
    """
    A DeviceType represents a particular make (Manufacturer) and model of device. It specifies rack height and depth, as
    well as high-level functional role(s).

    Each DeviceType can have an arbitrary number of component templates assigned to it, which define console, power, and
    interface objects. For example, a Juniper EX4300-48T DeviceType would have:

      * 1 ConsolePortTemplate
      * 2 PowerPortTemplates
      * 48 InterfaceTemplates

    When a new Device of this type is created, the appropriate console, power, and interface objects (as defined by the
    DeviceType) are automatically created as well.
    """

    manufacturer = models.ForeignKey(to="dcim.Manufacturer", on_delete=models.PROTECT, related_name="device_types")
    model = models.CharField(max_length=100)
    part_number = models.CharField(max_length=50, blank=True, help_text="Discrete part number (optional)")
    # 2.0 TODO: Profile filtering on this field if it could benefit from an index
    u_height = models.PositiveSmallIntegerField(default=1, verbose_name="Height (U)")
    # todoindex:
    is_full_depth = models.BooleanField(
        default=True,
        verbose_name="Is full depth",
        help_text="Device consumes both front and rear rack faces",
    )
    # todoindex:
    subdevice_role = models.CharField(
        max_length=50,
        choices=SubdeviceRoleChoices,
        blank=True,
        verbose_name="Parent/child status",
        help_text="Parent devices house child devices in device bays. Leave blank "
        "if this device type is neither a parent nor a child.",
    )
    front_image = models.ImageField(upload_to="devicetype-images", blank=True)
    rear_image = models.ImageField(upload_to="devicetype-images", blank=True)
    comments = models.TextField(blank=True)

    clone_fields = [
        "manufacturer",
        "u_height",
        "is_full_depth",
        "subdevice_role",
    ]

    class Meta:
        ordering = ["manufacturer", "model"]
        unique_together = [
            ["manufacturer", "model"],
        ]

    def __str__(self):
        return self.model

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Save a copy of u_height for validation in clean()
        self._original_u_height = self.u_height if self.present_in_database else 1

        # Save references to the original front/rear images
        self._original_front_image = self.front_image if self.present_in_database else None
        self._original_rear_image = self.rear_image if self.present_in_database else None

    def to_yaml(self):
        data = OrderedDict(
            (
                ("manufacturer", self.manufacturer.name),
                ("model", self.model),
                ("part_number", self.part_number),
                ("u_height", self.u_height),
                ("is_full_depth", self.is_full_depth),
                ("subdevice_role", self.subdevice_role),
                ("comments", self.comments),
            )
        )

        # Component templates
        if self.console_port_templates.exists():
            data["console-ports"] = [
                {
                    "name": c.name,
                    "type": c.type,
                }
                for c in self.console_port_templates.all()
            ]
        if self.console_server_port_templates.exists():
            data["console-server-ports"] = [
                {
                    "name": c.name,
                    "type": c.type,
                }
                for c in self.console_server_port_templates.all()
            ]
        if self.power_port_templates.exists():
            data["power-ports"] = [
                {
                    "name": c.name,
                    "type": c.type,
                    "maximum_draw": c.maximum_draw,
                    "allocated_draw": c.allocated_draw,
                }
                for c in self.power_port_templates.all()
            ]
        if self.power_outlet_templates.exists():
            data["power-outlets"] = [
                {
                    "name": c.name,
                    "type": c.type,
                    "power_port": c.power_port_template.name if c.power_port_template else None,
                    "feed_leg": c.feed_leg,
                }
                for c in self.power_outlet_templates.all()
            ]
        if self.interface_templates.exists():
            data["interfaces"] = [
                {
                    "name": c.name,
                    "type": c.type,
                    "mgmt_only": c.mgmt_only,
                }
                for c in self.interface_templates.all()
            ]
        if self.front_port_templates.exists():
            data["front-ports"] = [
                {
                    "name": c.name,
                    "type": c.type,
                    "rear_port": c.rear_port_template.name,
                    "rear_port_position": c.rear_port_position,
                }
                for c in self.front_port_templates.all()
            ]
        if self.rear_port_templates.exists():
            data["rear-ports"] = [
                {
                    "name": c.name,
                    "type": c.type,
                    "positions": c.positions,
                }
                for c in self.rear_port_templates.all()
            ]
        if self.device_bay_templates.exists():
            data["device-bays"] = [
                {
                    "name": c.name,
                }
                for c in self.device_bay_templates.all()
            ]

        return yaml.dump(dict(data), sort_keys=False, allow_unicode=True)

    def clean(self):
        super().clean()

        # If editing an existing DeviceType to have a larger u_height, first validate that *all* instances of it have
        # room to expand within their racks. This validation will impose a very high performance penalty when there are
        # many instances to check, but increasing the u_height of a DeviceType should be a very rare occurrence.
        if self.present_in_database and self.u_height > self._original_u_height:
            for d in Device.objects.filter(device_type=self, position__isnull=False):
                face_required = None if self.is_full_depth else d.face
                u_available = d.rack.get_available_units(
                    u_height=self.u_height, rack_face=face_required, exclude=[d.pk]
                )
                if d.position not in u_available:
                    raise ValidationError(
                        {
                            "u_height": f"Device {d} in rack {d.rack} does not have sufficient space to accommodate a height of {self.u_height}U"
                        }
                    )

        # If modifying the height of an existing DeviceType to 0U, check for any instances assigned to a rack position.
        elif self.present_in_database and self._original_u_height > 0 and self.u_height == 0:
            racked_instance_count = Device.objects.filter(device_type=self, position__isnull=False).count()
            if racked_instance_count:
                url = f"{reverse('dcim:device_list')}?manufacturer={self.manufacturer_id}&device_type={self.pk}"
                raise ValidationError(
                    {
                        "u_height": mark_safe(
                            f'Unable to set 0U height: Found <a href="{url}">{racked_instance_count} instances</a> already '
                            f"mounted within racks."
                        )
                    }
                )

        if (self.subdevice_role != SubdeviceRoleChoices.ROLE_PARENT) and self.device_bay_templates.count():
            raise ValidationError(
                {
                    "subdevice_role": "Must delete all device bay templates associated with this device before "
                    "declassifying it as a parent device."
                }
            )

        if self.u_height and self.subdevice_role == SubdeviceRoleChoices.ROLE_CHILD:
            raise ValidationError({"u_height": "Child device types must be 0U."})

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)

        # Delete any previously uploaded image files that are no longer in use
        if self._original_front_image and self.front_image != self._original_front_image:
            self._original_front_image.delete(save=False)
        if self._original_rear_image and self.rear_image != self._original_rear_image:
            self._original_rear_image.delete(save=False)

    def delete(self, *args, **kwargs):
        super().delete(*args, **kwargs)

        # Delete any uploaded image files
        if self.front_image:
            self.front_image.delete(save=False)
        if self.rear_image:
            self.rear_image.delete(save=False)

    @property
    def display(self):
        return f"{self.manufacturer.name} {self.model}"

    @property
    def is_parent_device(self):
        return self.subdevice_role == SubdeviceRoleChoices.ROLE_PARENT

    @property
    def is_child_device(self):
        return self.subdevice_role == SubdeviceRoleChoices.ROLE_CHILD


#
# Devices
#


@extras_features("custom_validators", "graphql")
class Platform(OrganizationalModel):
    """
    Platform refers to the software or firmware running on a Device. For example, "Cisco IOS-XR" or "Juniper Junos".

    Nautobot uses Platforms to determine how to interact with devices when pulling inventory data or other information
    by specifying a network driver; `netutils` is then used to derive library-specific driver information from this.
    """

    name = models.CharField(max_length=100, unique=True)
    manufacturer = models.ForeignKey(
        to="dcim.Manufacturer",
        on_delete=models.PROTECT,
        related_name="platforms",
        blank=True,
        null=True,
        help_text="Optionally limit this platform to devices of a certain manufacturer",
    )
    network_driver = models.CharField(
        max_length=100,
        blank=True,
        help_text=(
            "The normalized network driver to use when interacting with devices, e.g. cisco_ios, arista_eos, etc."
            " Library-specific driver names will be derived from this setting as appropriate"
        ),
    )
    napalm_driver = models.CharField(
        max_length=50,
        blank=True,
        verbose_name="NAPALM driver",
        help_text="The name of the NAPALM driver to use when Nautobot internals interact with devices",
    )
    napalm_args = models.JSONField(
        encoder=DjangoJSONEncoder,
        blank=True,
        null=True,
        verbose_name="NAPALM arguments",
        help_text="Additional arguments to pass when initiating the NAPALM driver (JSON format)",
    )
    description = models.CharField(max_length=200, blank=True)

    @cached_property
    def network_driver_mappings(self):
        """Dictionary of library-specific network drivers derived from network_driver by netutils library mapping or NETWORK_DRIVERS setting."""

        network_driver_mappings = get_all_network_driver_mappings()
        return network_driver_mappings.get(self.network_driver, {})

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


@extras_features(
    "custom_links",
    "custom_validators",
    "dynamic_groups",
    "export_templates",
    "graphql",
    "locations",
    "statuses",
    "webhooks",
)
class Device(PrimaryModel, ConfigContextModel):
    """
    A Device represents a piece of physical hardware. Each Device is assigned a DeviceType,
    Role, and (optionally) a Platform. Device names are not required, however if one is set it must be unique.

    Each Device must be assigned to a Location, and optionally to a Rack within that.
    Associating a device with a particular rack face or unit is optional (for example, vertically mounted PDUs
    do not consume rack units).

    When a new Device is created, console/power/interface/device bay components are created along with it as dictated
    by the component templates assigned to its DeviceType. Components can also be added, modified, or deleted after the
    creation of a Device.
    """

    device_type = models.ForeignKey(to="dcim.DeviceType", on_delete=models.PROTECT, related_name="devices")
    status = StatusField(blank=False, null=False)
    role = RoleField(blank=False, null=False)
    tenant = models.ForeignKey(
        to="tenancy.Tenant",
        on_delete=models.PROTECT,
        related_name="devices",
        blank=True,
        null=True,
    )
    platform = models.ForeignKey(
        to="dcim.Platform",
        on_delete=models.SET_NULL,
        related_name="devices",
        blank=True,
        null=True,
    )
    name = models.CharField(max_length=64, blank=True, null=True, db_index=True)
    _name = NaturalOrderingField(target_field="name", max_length=100, blank=True, null=True, db_index=True)
    serial = models.CharField(max_length=255, blank=True, verbose_name="Serial number", db_index=True)
    asset_tag = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        unique=True,
        verbose_name="Asset tag",
        help_text="A unique tag used to identify this device",
    )
    location = models.ForeignKey(
        to="dcim.Location",
        on_delete=models.PROTECT,
        related_name="devices",
    )
    rack = models.ForeignKey(
        to="dcim.Rack",
        on_delete=models.PROTECT,
        related_name="devices",
        blank=True,
        null=True,
    )
    # 2.0 TODO: Profile filtering on this field if it could benefit from an index
    position = models.PositiveSmallIntegerField(
        blank=True,
        null=True,
        validators=[MinValueValidator(1)],
        verbose_name="Position (U)",
        help_text="The lowest-numbered unit occupied by the device",
    )
    # todoindex:
    face = models.CharField(max_length=50, blank=True, choices=DeviceFaceChoices, verbose_name="Rack face")
    primary_ip4 = models.ForeignKey(
        to="ipam.IPAddress",
        on_delete=models.SET_NULL,
        related_name="primary_ip4_for",
        blank=True,
        null=True,
        verbose_name="Primary IPv4",
    )
    primary_ip6 = models.ForeignKey(
        to="ipam.IPAddress",
        on_delete=models.SET_NULL,
        related_name="primary_ip6_for",
        blank=True,
        null=True,
        verbose_name="Primary IPv6",
    )
    cluster = models.ForeignKey(
        to="virtualization.Cluster",
        on_delete=models.SET_NULL,
        related_name="devices",
        blank=True,
        null=True,
    )
    virtual_chassis = models.ForeignKey(
        to="VirtualChassis",
        on_delete=models.SET_NULL,
        related_name="members",
        blank=True,
        null=True,
    )
    device_redundancy_group = models.ForeignKey(
        to="dcim.DeviceRedundancyGroup",
        on_delete=models.SET_NULL,
        related_name="devices",
        blank=True,
        null=True,
        verbose_name="Device Redundancy Group",
    )
    device_redundancy_group_priority = models.PositiveSmallIntegerField(
        blank=True,
        null=True,
        validators=[MinValueValidator(1)],
        verbose_name="Device Redundancy Group Priority",
        help_text="The priority the device has in the device redundancy group.",
    )
    # 2.0 TODO: Profile filtering on this field if it could benefit from an index
    vc_position = models.PositiveSmallIntegerField(blank=True, null=True, validators=[MaxValueValidator(255)])
    vc_priority = models.PositiveSmallIntegerField(blank=True, null=True, validators=[MaxValueValidator(255)])
    comments = models.TextField(blank=True)
    images = GenericRelation(to="extras.ImageAttachment")

    secrets_group = models.ForeignKey(
        to="extras.SecretsGroup",
        on_delete=models.SET_NULL,
        related_name="devices",
        default=None,
        blank=True,
        null=True,
    )

    objects = BaseManager.from_queryset(ConfigContextModelQuerySet)()

    clone_fields = [
        "device_type",
        "role",
        "tenant",
        "platform",
        "location",
        "rack",
        "status",
        "cluster",
        "secrets_group",
    ]

    @classproperty  # https://github.com/PyCQA/pylint-django/issues/240
    def natural_key_field_names(cls):  # pylint: disable=no-self-argument
        """
        When DEVICE_NAME_AS_NATURAL_KEY is set in settings or Constance, we use just the `name` for simplicity.
        """
        if get_settings_or_config("DEVICE_NAME_AS_NATURAL_KEY"):
            # opt-in simplified "pseudo-natural-key"
            return ["name"]
        else:
            # true natural-key given current uniqueness constraints
            return ["name", "tenant", "location"]  # location should be last since it's potentially variadic

    class Meta:
        ordering = ("_name",)  # Name may be null
        unique_together = (
            ("location", "tenant", "name"),  # See validate_unique below
            ("rack", "position", "face"),
            ("virtual_chassis", "vc_position"),
        )

    def __str__(self):
        return self.display or super().__str__()

    def validate_unique(self, exclude=None):
        # Check for a duplicate name on a device assigned to the same Location and no Tenant. This is necessary
        # because Django does not consider two NULL fields to be equal, and thus will not trigger a violation
        # of the uniqueness constraint without manual intervention.
        if self.name and hasattr(self, "location") and self.tenant is None:
            if Device.objects.exclude(pk=self.pk).filter(name=self.name, location=self.location, tenant__isnull=True):
                raise ValidationError({"name": "A device with this name already exists."})

        super().validate_unique(exclude)

    def clean(self):
        from nautobot.ipam import models as ipam_models  # circular import workaround

        super().clean()

        # Validate location
        if self.location is not None:
            # TODO: after Location model replaced Site, which was not a hierarchical model, should we allow users to assign a Rack belongs to
            # the parent Location or the child location of `self.location`?

            if self.rack is not None and self.rack.location != self.location:
                raise ValidationError({"rack": f'Rack "{self.rack}" does not belong to location "{self.location}".'})

            # self.cluster is validated somewhat later, see below

            if ContentType.objects.get_for_model(self) not in self.location.location_type.content_types.all():
                raise ValidationError(
                    {"location": f'Devices may not associate to locations of type "{self.location.location_type}".'}
                )

        if self.rack is None:
            if self.face:
                raise ValidationError(
                    {
                        "face": "Cannot select a rack face without assigning a rack.",
                    }
                )
            if self.position:
                raise ValidationError(
                    {
                        "position": "Cannot select a rack position without assigning a rack.",
                    }
                )

        # Validate position/face combination
        if self.position and not self.face:
            raise ValidationError(
                {
                    "face": "Must specify rack face when defining rack position.",
                }
            )

        # Prevent 0U devices from being assigned to a specific position
        if self.position and self.device_type.u_height == 0:
            raise ValidationError(
                {"position": f"A U0 device type ({self.device_type}) cannot be assigned to a rack position."}
            )

        if self.rack:
            try:
                # Child devices cannot be assigned to a rack face/unit
                if self.device_type.is_child_device and self.face:
                    raise ValidationError(
                        {
                            "face": "Child device types cannot be assigned to a rack face. This is an attribute of the "
                            "parent device."
                        }
                    )
                if self.device_type.is_child_device and self.position:
                    raise ValidationError(
                        {
                            "position": "Child device types cannot be assigned to a rack position. This is an attribute of "
                            "the parent device."
                        }
                    )

                # Validate rack space
                rack_face = self.face if not self.device_type.is_full_depth else None
                exclude_list = [self.pk] if self.present_in_database else []
                available_units = self.rack.get_available_units(
                    u_height=self.device_type.u_height,
                    rack_face=rack_face,
                    exclude=exclude_list,
                )
                if self.position and self.position not in available_units:
                    raise ValidationError(
                        {
                            "position": f"U{self.position} is already occupied or does not have sufficient space to "
                            f"accommodate this device type: {self.device_type} ({self.device_type.u_height}U)"
                        }
                    )

            except DeviceType.DoesNotExist:
                pass

        # Validate primary IP addresses
        vc_interfaces = self.vc_interfaces.all()
        for field in ["primary_ip4", "primary_ip6"]:
            ip = getattr(self, field)
            if ip is not None:
                if field == "primary_ip4":
                    if ip.ip_version != 4:
                        raise ValidationError({f"{field}": f"{ip} is not an IPv4 address."})
                else:
                    if ip.ip_version != 6:
                        raise ValidationError({f"{field}": f"{ip} is not an IPv6 address."})
                if ipam_models.IPAddressToInterface.objects.filter(ip_address=ip, interface__in=vc_interfaces).exists():
                    pass
                elif (
                    ip.nat_inside is not None
                    and ipam_models.IPAddressToInterface.objects.filter(
                        ip_address=ip.nat_inside, interface__in=vc_interfaces
                    ).exists()
                ):
                    pass
                else:
                    raise ValidationError(
                        {f"{field}": f"The specified IP address ({ip}) is not assigned to this device."}
                    )

        # Validate manufacturer/platform
        if hasattr(self, "device_type") and self.platform:
            if self.platform.manufacturer and self.platform.manufacturer != self.device_type.manufacturer:
                raise ValidationError(
                    {
                        "platform": (
                            f"The assigned platform is limited to {self.platform.manufacturer} device types, "
                            f"but this device's type belongs to {self.device_type.manufacturer}."
                        )
                    }
                )

        # A Device can only be assigned to a Cluster in the same location or parent location, if any
        if (
            self.cluster is not None
            and self.location is not None
            and self.cluster.location is not None
            and self.cluster.location not in self.location.ancestors(include_self=True)
        ):
            raise ValidationError(
                {"cluster": f"The assigned cluster belongs to a location that does not include {self.location}."}
            )

        # Validate virtual chassis assignment
        if self.virtual_chassis and self.vc_position is None:
            raise ValidationError(
                {"vc_position": "A device assigned to a virtual chassis must have its position defined."}
            )

        # Validate device isn't being removed from a virtual chassis when it is the master
        if not self.virtual_chassis and self.present_in_database:
            existing_virtual_chassis = Device.objects.get(id=self.id).virtual_chassis
            if existing_virtual_chassis and existing_virtual_chassis.master == self:
                raise ValidationError(
                    {
                        "virtual_chassis": f"The master device for the virtual chassis ({ existing_virtual_chassis}) may not be removed"
                    }
                )

        if self.device_redundancy_group_priority is not None and self.device_redundancy_group is None:
            raise ValidationError(
                {
                    "device_redundancy_group_priority": "Must assign a redundancy group when defining a redundancy group priority."
                }
            )

    def save(self, *args, **kwargs):
        is_new = not self.present_in_database

        super().save(*args, **kwargs)

        # If this is a new Device, instantiate all related components per the DeviceType definition
        if is_new:
            self.create_components()

        # Update Location and Rack assignment for any child Devices
        devices = Device.objects.filter(parent_bay__device=self)
        for device in devices:
            device.location = self.location
            device.rack = self.rack
            device.save()

    def create_components(self):
        """Create device components from the device type definition."""
        # The order of these is significant as
        # - PowerOutlet depends on PowerPort
        # - FrontPort depends on FrontPort
        component_models = [
            (ConsolePort, self.device_type.console_port_templates.all()),
            (ConsoleServerPort, self.device_type.console_server_port_templates.all()),
            (PowerPort, self.device_type.power_port_templates.all()),
            (PowerOutlet, self.device_type.power_outlet_templates.all()),
            (Interface, self.device_type.interface_templates.all()),
            (RearPort, self.device_type.rear_port_templates.all()),
            (FrontPort, self.device_type.front_port_templates.all()),
            (DeviceBay, self.device_type.device_bay_templates.all()),
        ]
        instantiated_components = []
        for model, templates in component_models:
            model.objects.bulk_create([x.instantiate(self) for x in templates])
        return instantiated_components

    @property
    def display(self):
        if self.name:
            return self.name
        elif self.virtual_chassis:
            return f"{self.virtual_chassis.name}:{self.vc_position} ({self.pk})"
        elif self.device_type:
            return f"{self.device_type.manufacturer} {self.device_type.model} ({self.pk})"
        else:
            return ""  # Device has not yet been created

    @property
    def identifier(self):
        """
        Return the device name if set; otherwise return the Device's primary key as {pk}
        """
        if self.name is not None:
            return self.name
        return f"{{{self.pk}}}"

    @property
    def primary_ip(self):
        if get_settings_or_config("PREFER_IPV4") and self.primary_ip4:
            return self.primary_ip4
        elif self.primary_ip6:
            return self.primary_ip6
        elif self.primary_ip4:
            return self.primary_ip4
        else:
            return None

    def get_vc_master(self):
        """
        If this Device is a VirtualChassis member, return the VC master. Otherwise, return None.
        """
        return self.virtual_chassis.master if self.virtual_chassis else None

    @property
    def vc_interfaces(self):
        """
        Return a QuerySet matching all Interfaces assigned to this Device or, if this Device is a VC master, to another
        Device belonging to the same VirtualChassis.
        """
        filter_q = Q(device=self)
        if self.virtual_chassis and self.virtual_chassis.master == self:
            filter_q |= Q(device__virtual_chassis=self.virtual_chassis, mgmt_only=False)
        return Interface.objects.filter(filter_q)

    @property
    def common_vc_interfaces(self):
        """
        Return a QuerySet matching all Interfaces assigned to this Device or,
        if this Device belongs to a VirtualChassis, it returns all interfaces belonging Devices with same VirtualChassis
        """
        if self.virtual_chassis:
            return self.virtual_chassis.member_interfaces
        return self.interfaces

    def get_cables(self, pk_list=False):
        """
        Return a QuerySet or PK list matching all Cables connected to a component of this Device.
        """
        from .cables import Cable

        cable_pks = []
        for component_model in [
            ConsolePort,
            ConsoleServerPort,
            PowerPort,
            PowerOutlet,
            Interface,
            FrontPort,
            RearPort,
        ]:
            cable_pks += component_model.objects.filter(device=self, cable__isnull=False).values_list(
                "cable", flat=True
            )
        if pk_list:
            return cable_pks
        return Cable.objects.filter(pk__in=cable_pks)

    def get_children(self):
        """
        Return the set of child Devices installed in DeviceBays within this Device.
        """
        return Device.objects.filter(parent_bay__device=self.pk)


#
# Virtual chassis
#


@extras_features(
    "custom_links",
    "custom_validators",
    "export_templates",
    "graphql",
    "webhooks",
)
class VirtualChassis(PrimaryModel):
    """
    A collection of Devices which operate with a shared control plane (e.g. a switch stack).
    """

    master = models.OneToOneField(
        to="Device",
        on_delete=models.PROTECT,
        related_name="vc_master_for",
        blank=True,
        null=True,
    )
    name = models.CharField(max_length=64, unique=True)
    domain = models.CharField(max_length=30, blank=True)

    natural_key_field_names = ["name"]

    class Meta:
        ordering = ["name"]
        verbose_name_plural = "virtual chassis"

    def __str__(self):
        return self.name

    @property
    def member_interfaces(self):
        """Return a list of Interfaces common to all member devices."""
        return Interface.objects.filter(pk__in=self.members.values_list("interfaces", flat=True))

    def clean(self):
        super().clean()

        # Verify that the selected master device has been assigned to this VirtualChassis. (Skip when creating a new
        # VirtualChassis.)
        if self.present_in_database and self.master and self.master not in self.members.all():
            raise ValidationError(
                {"master": f"The selected master ({self.master}) is not assigned to this virtual chassis."}
            )

    def delete(self, *args, **kwargs):
        # Check for LAG interfaces split across member chassis
        interfaces = Interface.objects.filter(device__in=self.members.all(), lag__isnull=False).exclude(
            lag__device=F("device")
        )
        if interfaces:
            raise ProtectedError(
                f"Unable to delete virtual chassis {self}. There are member interfaces which form a cross-chassis LAG",
                interfaces,
            )

        return super().delete(*args, **kwargs)


@extras_features(
    "custom_links",
    "custom_validators",
    "dynamic_groups",
    "export_templates",
    "graphql",
    "statuses",
    "webhooks",
)
class DeviceRedundancyGroup(PrimaryModel):
    """
    A DeviceRedundancyGroup represents a logical grouping of physical hardware for the purposes of high-availability.
    """

    name = models.CharField(max_length=100, unique=True)
    status = StatusField(blank=False, null=False)
    description = models.CharField(max_length=200, blank=True)

    failover_strategy = models.CharField(
        max_length=50,
        blank=True,
        choices=DeviceRedundancyGroupFailoverStrategyChoices,
        verbose_name="Failover strategy",
    )

    comments = models.TextField(blank=True)

    secrets_group = models.ForeignKey(
        to="extras.SecretsGroup",
        on_delete=models.SET_NULL,
        related_name="device_redundancy_groups",
        default=None,
        blank=True,
        null=True,
    )

    clone_fields = [
        "failover_strategy",
        "status",
        "secrets_group",
    ]

    class Meta:
        ordering = ("name",)

    @property
    def devices_sorted(self):
        return self.devices.order_by("device_redundancy_group_priority")

    def __str__(self):
        return self.name
