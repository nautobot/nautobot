from collections import OrderedDict

import yaml
from django.contrib.contenttypes.fields import GenericRelation
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.core.serializers.json import DjangoJSONEncoder
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models import F, ProtectedError, Q
from django.urls import reverse
from django.utils.safestring import mark_safe

from nautobot.dcim.choices import DeviceFaceChoices, DeviceRedundancyGroupFailoverStrategyChoices, SubdeviceRoleChoices

from nautobot.extras.models import ConfigContextModel, StatusModel
from nautobot.extras.querysets import ConfigContextModelQuerySet
from nautobot.extras.utils import extras_features
from nautobot.core.fields import AutoSlugField
from nautobot.core.models.generics import OrganizationalModel, PrimaryModel
from nautobot.utilities.choices import ColorChoices
from nautobot.utilities.config import get_settings_or_config
from nautobot.utilities.fields import ColorField, NaturalOrderingField
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


__all__ = (
    "Device",
    "DeviceRedundancyGroup",
    "DeviceRole",
    "DeviceType",
    "Manufacturer",
    "Platform",
    "VirtualChassis",
)


#
# Device Types
#


@extras_features(
    "custom_fields",
    "custom_validators",
    "export_templates",
    "graphql",
    "relationships",
    "webhooks",
)
class Manufacturer(OrganizationalModel):
    """
    A Manufacturer represents a company which produces hardware devices; for example, Juniper or Dell.
    """

    name = models.CharField(max_length=100, unique=True)
    slug = AutoSlugField(populate_from="name")
    description = models.CharField(max_length=200, blank=True)

    csv_headers = ["name", "slug", "description"]

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse("dcim:manufacturer", args=[self.slug])

    def to_csv(self):
        return (self.name, self.slug, self.description)


@extras_features(
    "custom_fields",
    "custom_links",
    "custom_validators",
    "export_templates",
    "graphql",
    "relationships",
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
    # 2.0 TODO: Remove unique=None to make slug globally unique. This would be a breaking change.
    slug = AutoSlugField(populate_from="model", unique=None, db_index=True)
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
            # 2.0 TODO: Remove unique_together to make slug globally unique. This would be a breaking change.
            ["manufacturer", "slug"],
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

    def get_absolute_url(self):
        return reverse("dcim:devicetype", args=[self.pk])

    def to_yaml(self):
        data = OrderedDict(
            (
                ("manufacturer", self.manufacturer.name),
                ("model", self.model),
                ("slug", self.slug),
                ("part_number", self.part_number),
                ("u_height", self.u_height),
                ("is_full_depth", self.is_full_depth),
                ("subdevice_role", self.subdevice_role),
                ("comments", self.comments),
            )
        )

        # Component templates
        if self.consoleporttemplates.exists():
            data["console-ports"] = [
                {
                    "name": c.name,
                    "type": c.type,
                }
                for c in self.consoleporttemplates.all()
            ]
        if self.consoleserverporttemplates.exists():
            data["console-server-ports"] = [
                {
                    "name": c.name,
                    "type": c.type,
                }
                for c in self.consoleserverporttemplates.all()
            ]
        if self.powerporttemplates.exists():
            data["power-ports"] = [
                {
                    "name": c.name,
                    "type": c.type,
                    "maximum_draw": c.maximum_draw,
                    "allocated_draw": c.allocated_draw,
                }
                for c in self.powerporttemplates.all()
            ]
        if self.poweroutlettemplates.exists():
            data["power-outlets"] = [
                {
                    "name": c.name,
                    "type": c.type,
                    "power_port": c.power_port.name if c.power_port else None,
                    "feed_leg": c.feed_leg,
                }
                for c in self.poweroutlettemplates.all()
            ]
        if self.interfacetemplates.exists():
            data["interfaces"] = [
                {
                    "name": c.name,
                    "type": c.type,
                    "mgmt_only": c.mgmt_only,
                }
                for c in self.interfacetemplates.all()
            ]
        if self.frontporttemplates.exists():
            data["front-ports"] = [
                {
                    "name": c.name,
                    "type": c.type,
                    "rear_port": c.rear_port.name,
                    "rear_port_position": c.rear_port_position,
                }
                for c in self.frontporttemplates.all()
            ]
        if self.rearporttemplates.exists():
            data["rear-ports"] = [
                {
                    "name": c.name,
                    "type": c.type,
                    "positions": c.positions,
                }
                for c in self.rearporttemplates.all()
            ]
        if self.devicebaytemplates.exists():
            data["device-bays"] = [
                {
                    "name": c.name,
                }
                for c in self.devicebaytemplates.all()
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
                url = f"{reverse('dcim:device_list')}?manufacturer_id={self.manufacturer_id}&device_type_id={self.pk}"
                raise ValidationError(
                    {
                        "u_height": mark_safe(
                            f'Unable to set 0U height: Found <a href="{url}">{racked_instance_count} instances</a> already '
                            f"mounted within racks."
                        )
                    }
                )

        if (self.subdevice_role != SubdeviceRoleChoices.ROLE_PARENT) and self.devicebaytemplates.count():
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


@extras_features("custom_fields", "custom_validators", "relationships", "graphql")
class DeviceRole(OrganizationalModel):
    """
    Devices are organized by functional role; for example, "Core Switch" or "File Server". Each DeviceRole is assigned a
    color to be used when displaying rack elevations. The vm_role field determines whether the role is applicable to
    virtual machines as well.
    """

    name = models.CharField(max_length=100, unique=True)
    slug = AutoSlugField(populate_from="name")
    color = ColorField(default=ColorChoices.COLOR_GREY)
    # todoindex:
    vm_role = models.BooleanField(
        default=True,
        verbose_name="VM Role",
        help_text="Virtual machines may be assigned to this role",
    )
    description = models.CharField(
        max_length=200,
        blank=True,
    )

    csv_headers = ["name", "slug", "color", "vm_role", "description"]

    class Meta:
        ordering = ["name"]

    def get_absolute_url(self):
        return reverse("dcim:devicerole", args=[self.slug])

    def __str__(self):
        return self.name

    def to_csv(self):
        return (
            self.name,
            self.slug,
            self.color,
            self.vm_role,
            self.description,
        )


@extras_features("custom_fields", "custom_validators", "relationships", "graphql")
class Platform(OrganizationalModel):
    """
    Platform refers to the software or firmware running on a Device. For example, "Cisco IOS-XR" or "Juniper Junos".
    Nautobot uses Platforms to determine how to interact with devices when pulling inventory data or other information by
    specifying a NAPALM driver.
    """

    name = models.CharField(max_length=100, unique=True)
    slug = AutoSlugField(populate_from="name")
    manufacturer = models.ForeignKey(
        to="dcim.Manufacturer",
        on_delete=models.PROTECT,
        related_name="platforms",
        blank=True,
        null=True,
        help_text="Optionally limit this platform to devices of a certain manufacturer",
    )
    napalm_driver = models.CharField(
        max_length=50,
        blank=True,
        verbose_name="NAPALM driver",
        help_text="The name of the NAPALM driver to use when interacting with devices",
    )
    napalm_args = models.JSONField(
        encoder=DjangoJSONEncoder,
        blank=True,
        null=True,
        verbose_name="NAPALM arguments",
        help_text="Additional arguments to pass when initiating the NAPALM driver (JSON format)",
    )
    description = models.CharField(max_length=200, blank=True)

    csv_headers = [
        "name",
        "slug",
        "manufacturer",
        "napalm_driver",
        "napalm_args",
        "description",
    ]

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse("dcim:platform", args=[self.slug])

    def to_csv(self):
        return (
            self.name,
            self.slug,
            self.manufacturer.name if self.manufacturer else None,
            self.napalm_driver,
            self.napalm_args,
            self.description,
        )


@extras_features(
    "custom_fields",
    "custom_links",
    "custom_validators",
    "dynamic_groups",
    "export_templates",
    "graphql",
    "locations",
    "relationships",
    "statuses",
    "webhooks",
)
class Device(PrimaryModel, ConfigContextModel, StatusModel):
    """
    A Device represents a piece of physical hardware. Each Device is assigned a DeviceType,
    DeviceRole, and (optionally) a Platform. Device names are not required, however if one is set it must be unique.

    Each Device must be assigned to a Site and/or Location, and optionally to a Rack within that.
    Associating a device with a particular rack face or unit is optional (for example, vertically mounted PDUs
    do not consume rack units).

    When a new Device is created, console/power/interface/device bay components are created along with it as dictated
    by the component templates assigned to its DeviceType. Components can also be added, modified, or deleted after the
    creation of a Device.
    """

    device_type = models.ForeignKey(to="dcim.DeviceType", on_delete=models.PROTECT, related_name="instances")
    device_role = models.ForeignKey(to="dcim.DeviceRole", on_delete=models.PROTECT, related_name="devices")
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
        max_length=50,
        blank=True,
        null=True,
        unique=True,
        verbose_name="Asset tag",
        help_text="A unique tag used to identify this device",
    )
    site = models.ForeignKey(to="dcim.Site", on_delete=models.PROTECT, related_name="devices")
    location = models.ForeignKey(
        to="dcim.Location",
        on_delete=models.PROTECT,
        related_name="devices",
        blank=True,
        null=True,
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
    primary_ip4 = models.OneToOneField(
        to="ipam.IPAddress",
        on_delete=models.SET_NULL,
        related_name="primary_ip4_for",
        blank=True,
        null=True,
        verbose_name="Primary IPv4",
    )
    primary_ip6 = models.OneToOneField(
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
        related_name="members",
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
        default=None,
        blank=True,
        null=True,
    )

    objects = ConfigContextModelQuerySet.as_manager()

    csv_headers = [
        "name",
        "device_role",
        "tenant",
        "manufacturer",
        "device_type",
        "platform",
        "serial",
        "asset_tag",
        "status",
        "site",
        "location",
        "rack_group",
        "rack_name",
        "position",
        "face",
        "device_redundancy_group",
        "device_redundancy_group_priority",
        "secrets_group",
        "primary_ip",
        "comments",
    ]
    clone_fields = [
        "device_type",
        "device_role",
        "tenant",
        "platform",
        "site",
        "location",
        "rack",
        "status",
        "cluster",
        "secrets_group",
    ]

    class Meta:
        ordering = ("_name",)  # Name may be null
        unique_together = (
            ("site", "tenant", "name"),  # See validate_unique below
            ("rack", "position", "face"),
            ("virtual_chassis", "vc_position"),
        )

    def __str__(self):
        return self.display or super().__str__()

    def get_absolute_url(self):
        return reverse("dcim:device", args=[self.pk])

    def validate_unique(self, exclude=None):

        # Check for a duplicate name on a device assigned to the same Site and no Tenant. This is necessary
        # because Django does not consider two NULL fields to be equal, and thus will not trigger a violation
        # of the uniqueness constraint without manual intervention.
        if self.name and hasattr(self, "site") and self.tenant is None:
            if Device.objects.exclude(pk=self.pk).filter(name=self.name, site=self.site, tenant__isnull=True):
                raise ValidationError({"name": "A device with this name already exists."})

        super().validate_unique(exclude)

    def clean(self):
        super().clean()

        # Validate site/rack combination
        if self.rack and self.site != self.rack.site:
            raise ValidationError(
                {
                    "rack": f"Rack {self.rack} does not belong to site {self.site}.",
                }
            )

        # Validate location
        if self.location is not None:
            if self.location.base_site != self.site:
                raise ValidationError(
                    {"location": f'Location "{self.location}" does not belong to site "{self.site}".'}
                )

            if self.rack is not None and self.rack.location is not None and self.rack.location != self.location:
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
        if self.primary_ip4:
            if self.primary_ip4.family != 4:
                raise ValidationError({"primary_ip4": f"{self.primary_ip4} is not an IPv4 address."})
            if self.primary_ip4.assigned_object in vc_interfaces:
                pass
            elif (
                self.primary_ip4.nat_inside is not None and self.primary_ip4.nat_inside.assigned_object in vc_interfaces
            ):
                pass
            else:
                raise ValidationError(
                    {"primary_ip4": f"The specified IP address ({self.primary_ip4}) is not assigned to this device."}
                )
        if self.primary_ip6:
            if self.primary_ip6.family != 6:
                raise ValidationError({"primary_ip6": f"{self.primary_ip6} is not an IPv6 address."})
            if self.primary_ip6.assigned_object in vc_interfaces:
                pass
            elif (
                self.primary_ip6.nat_inside is not None and self.primary_ip6.nat_inside.assigned_object in vc_interfaces
            ):
                pass
            else:
                raise ValidationError(
                    {"primary_ip6": f"The specified IP address ({self.primary_ip6}) is not assigned to this device."}
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

        # A Device can only be assigned to a Cluster in the same Site (or no Site)
        if self.cluster and self.cluster.site is not None and self.cluster.site != self.site:
            raise ValidationError(
                {"cluster": f"The assigned cluster belongs to a different site ({self.cluster.site})"}
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

        # If this is a new Device, instantiate all of the related components per the DeviceType definition
        if is_new:
            ConsolePort.objects.bulk_create([x.instantiate(self) for x in self.device_type.consoleporttemplates.all()])
            ConsoleServerPort.objects.bulk_create(
                [x.instantiate(self) for x in self.device_type.consoleserverporttemplates.all()]
            )
            PowerPort.objects.bulk_create([x.instantiate(self) for x in self.device_type.powerporttemplates.all()])
            PowerOutlet.objects.bulk_create([x.instantiate(self) for x in self.device_type.poweroutlettemplates.all()])
            Interface.objects.bulk_create([x.instantiate(self) for x in self.device_type.interfacetemplates.all()])
            RearPort.objects.bulk_create([x.instantiate(self) for x in self.device_type.rearporttemplates.all()])
            FrontPort.objects.bulk_create([x.instantiate(self) for x in self.device_type.frontporttemplates.all()])
            DeviceBay.objects.bulk_create([x.instantiate(self) for x in self.device_type.devicebaytemplates.all()])

        # Update Site and Rack assignment for any child Devices
        devices = Device.objects.filter(parent_bay__device=self)
        for device in devices:
            device.site = self.site
            device.rack = self.rack
            device.save()

    def to_csv(self):
        return (
            self.name or "",
            self.device_role.name,
            self.tenant.name if self.tenant else None,
            self.device_type.manufacturer.name,
            self.device_type.model,
            self.platform.name if self.platform else None,
            self.serial,
            self.asset_tag,
            self.get_status_display(),
            self.site.name,
            self.location.name if self.location else None,
            self.rack.group.name if self.rack and self.rack.group else None,
            self.rack.name if self.rack else None,
            self.position,
            self.get_face_display(),
            self.device_redundancy_group.slug if self.device_redundancy_group else None,
            self.device_redundancy_group_priority,
            self.secrets_group.name if self.secrets_group else None,
            self.primary_ip if self.primary_ip else None,
            self.comments,
        )

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
    "custom_fields",
    "custom_links",
    "custom_validators",
    "export_templates",
    "graphql",
    "relationships",
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
    name = models.CharField(max_length=64, db_index=True)
    domain = models.CharField(max_length=30, blank=True)

    csv_headers = ["name", "domain", "master"]

    class Meta:
        ordering = ["name"]
        verbose_name_plural = "virtual chassis"

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse("dcim:virtualchassis", kwargs={"pk": self.pk})

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

    def to_csv(self):
        return (
            self.name,
            self.domain,
            self.master.name if self.master else None,
        )


@extras_features(
    "custom_fields",
    "custom_links",
    "custom_validators",
    "dynamic_groups",
    "export_templates",
    "graphql",
    "relationships",
    "statuses",
    "webhooks",
)
class DeviceRedundancyGroup(PrimaryModel, StatusModel):
    """
    A DeviceRedundancyGroup represents a logical grouping of physical hardware for the purposes of high-availability.
    """

    name = models.CharField(max_length=100, unique=True)
    slug = AutoSlugField(populate_from="name")
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
        default=None,
        blank=True,
        null=True,
    )

    clone_fields = [
        "failover_strategy",
        "status",
        "secrets_group",
    ]

    csv_headers = ["name", "failover_strategy", "status", "secrets_group", "comments"]

    class Meta:
        ordering = ("name",)

    @property
    def members_sorted(self):
        return self.members.order_by("device_redundancy_group_priority")

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse("dcim:deviceredundancygroup", args=[self.slug])

    def to_csv(self):
        return (
            self.name,
            self.failover_strategy,
            self.get_status_display(),
            self.secrets_group.name if self.secrets_group else None,
            self.comments,
        )
