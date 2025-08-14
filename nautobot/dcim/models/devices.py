from collections import OrderedDict

from django.contrib.contenttypes.fields import GenericRelation
from django.contrib.contenttypes.models import ContentType
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.core.serializers.json import DjangoJSONEncoder
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models import F, ProtectedError, Q
from django.urls import reverse
from django.utils.functional import cached_property, classproperty
from django.utils.html import format_html, format_html_join
import yaml

from nautobot.core.constants import CHARFIELD_MAX_LENGTH
from nautobot.core.models import BaseManager, RestrictedQuerySet
from nautobot.core.models.fields import JSONArrayField, LaxURLField, NaturalOrderingField
from nautobot.core.models.generics import BaseModel, OrganizationalModel, PrimaryModel
from nautobot.core.models.tree_queries import TreeModel
from nautobot.core.utils.config import get_settings_or_config
from nautobot.dcim.choices import (
    ControllerCapabilitiesChoices,
    DeviceFaceChoices,
    DeviceRedundancyGroupFailoverStrategyChoices,
    SoftwareImageFileHashingAlgorithmChoices,
    SubdeviceRoleChoices,
)
from nautobot.dcim.constants import MODULE_RECURSION_DEPTH_LIMIT
from nautobot.dcim.utils import get_all_network_driver_mappings, get_network_driver_mapping_tool_names
from nautobot.extras.models import ChangeLoggedModel, ConfigContextModel, RoleField, StatusField
from nautobot.extras.querysets import ConfigContextModelQuerySet
from nautobot.extras.utils import extras_features
from nautobot.wireless.models import ControllerManagedDeviceGroupWirelessNetworkAssignment

from .device_components import (
    ConsolePort,
    ConsoleServerPort,
    DeviceBay,
    FrontPort,
    Interface,
    InventoryItem,
    ModuleBay,
    PowerOutlet,
    PowerPort,
    RearPort,
)

__all__ = (
    "Controller",
    "ControllerManagedDeviceGroup",
    "Device",
    "DeviceFamily",
    "DeviceRedundancyGroup",
    "DeviceType",
    "InterfaceVDCAssignment",
    "Manufacturer",
    "Platform",
    "VirtualChassis",
    "VirtualDeviceContext",
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

    name = models.CharField(max_length=CHARFIELD_MAX_LENGTH, unique=True)
    description = models.CharField(max_length=CHARFIELD_MAX_LENGTH, blank=True)

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
class DeviceFamily(PrimaryModel):
    """
    A Device Family is a model that represents a grouping of DeviceTypes.
    """

    name = models.CharField(max_length=CHARFIELD_MAX_LENGTH, unique=True)
    description = models.CharField(max_length=CHARFIELD_MAX_LENGTH, blank=True)

    class Meta:
        ordering = ["name"]
        verbose_name_plural = "device families"

    def __str__(self):
        return self.name


@extras_features("graphql")
class DeviceTypeToSoftwareImageFile(BaseModel, ChangeLoggedModel):
    device_type = models.ForeignKey(
        "dcim.DeviceType", on_delete=models.CASCADE, related_name="software_image_file_mappings"
    )
    software_image_file = models.ForeignKey(
        "dcim.SoftwareImageFile", on_delete=models.PROTECT, related_name="device_type_mappings"
    )
    is_metadata_associable_model = False

    class Meta:
        unique_together = [
            ["device_type", "software_image_file"],
        ]
        verbose_name = "device type to software image file mapping"
        verbose_name_plural = "device type to software image file mappings"

    def __str__(self):
        return f"{self.device_type!s} - {self.software_image_file!s}"


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
    device_family = models.ForeignKey(
        to="dcim.DeviceFamily",
        on_delete=models.PROTECT,
        related_name="device_types",
        blank=True,
        null=True,
    )
    model = models.CharField(max_length=CHARFIELD_MAX_LENGTH)
    part_number = models.CharField(
        max_length=CHARFIELD_MAX_LENGTH, blank=True, help_text="Discrete part number (optional)"
    )
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
    software_image_files = models.ManyToManyField(
        to="dcim.SoftwareImageFile",
        through=DeviceTypeToSoftwareImageFile,
        related_name="device_types",
        blank=True,
        verbose_name="Software Image Files",
    )
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
        if self.module_bay_templates.exists():
            data["module-bays"] = [
                {
                    "name": c.name,
                    "position": c.position,
                    "label": c.label,
                    "description": c.description,
                }
                for c in self.module_bay_templates.all()
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
                        "u_height": format_html(
                            "Unable to set 0U height: "
                            'Found <a href="{}">{} instances</a> already mounted within racks.',
                            url,
                            racked_instance_count,
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

    name = models.CharField(max_length=CHARFIELD_MAX_LENGTH, unique=True)
    manufacturer = models.ForeignKey(
        to="dcim.Manufacturer",
        on_delete=models.PROTECT,
        related_name="platforms",
        blank=True,
        null=True,
        help_text="Optionally limit this platform to devices of a certain manufacturer",
    )
    network_driver = models.CharField(
        max_length=CHARFIELD_MAX_LENGTH,
        blank=True,
        help_text=(
            "The normalized network driver to use when interacting with devices, e.g. cisco_ios, arista_eos, etc."
            " Library-specific driver names will be derived from this setting as appropriate"
        ),
    )
    napalm_driver = models.CharField(
        max_length=CHARFIELD_MAX_LENGTH,
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
    description = models.CharField(max_length=CHARFIELD_MAX_LENGTH, blank=True)

    @cached_property
    def network_driver_mappings(self):
        """Dictionary of library-specific network drivers derived from network_driver by netutils library mapping or NETWORK_DRIVERS setting."""

        network_driver_mappings = get_all_network_driver_mappings()
        return network_driver_mappings.get(self.network_driver, {})

    def fetch_network_driver_mappings(self):
        """
        Returns the network driver mappings for this Platform instance.
        If the platform is missing network driver mappings, returns an empty dictionary.
        """
        if not self.network_driver:
            return {}

        tool_names = get_network_driver_mapping_tool_names()
        return {tool_name: self.network_driver_mappings.get(tool_name) for tool_name in tool_names}

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


@extras_features(
    "custom_links",
    "custom_validators",
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
    name = models.CharField(  # noqa: DJ001  # django-nullable-model-string-field -- intentional, see below
        max_length=CHARFIELD_MAX_LENGTH,
        blank=True,
        null=True,  # because name is part of uniqueness constraint but is optional
        db_index=True,
    )
    _name = NaturalOrderingField(
        target_field="name", max_length=CHARFIELD_MAX_LENGTH, blank=True, null=True, db_index=True
    )
    serial = models.CharField(max_length=CHARFIELD_MAX_LENGTH, blank=True, verbose_name="Serial number", db_index=True)
    asset_tag = models.CharField(
        max_length=CHARFIELD_MAX_LENGTH,
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
    software_version = models.ForeignKey(
        to="dcim.SoftwareVersion",
        on_delete=models.PROTECT,
        related_name="devices",
        blank=True,
        null=True,
        help_text="The software version installed on this device",
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

    software_image_files = models.ManyToManyField(
        to="dcim.SoftwareImageFile",
        related_name="devices",
        blank=True,
        verbose_name="Software Image Files",
        help_text="Override the software image files associated with the software version for this device",
    )
    controller_managed_device_group = models.ForeignKey(
        to="dcim.ControllerManagedDeviceGroup",
        on_delete=models.SET_NULL,
        related_name="devices",
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
            if self.rack is not None:
                device_location = self.location
                # Rack's location must be a child location or the same location as that of the parent device.
                # Location is a required field on rack.
                rack_location = self.rack.location
                if device_location not in rack_location.ancestors(include_self=True):
                    raise ValidationError(
                        {
                            "rack": f'Rack "{self.rack}" does not belong to location "{self.location}" and its descendants.'
                        }
                    )

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
        all_interfaces = self.all_interfaces.all()
        for field in ["primary_ip4", "primary_ip6"]:
            ip = getattr(self, field)
            if ip is not None:
                if field == "primary_ip4":
                    if ip.ip_version != 4:
                        raise ValidationError({f"{field}": f"{ip} is not an IPv4 address."})
                else:
                    if ip.ip_version != 6:
                        raise ValidationError({f"{field}": f"{ip} is not an IPv6 address."})
                if ipam_models.IPAddressToInterface.objects.filter(
                    ip_address=ip, interface__in=all_interfaces
                ).exists():
                    pass
                elif (
                    ip.nat_inside is not None
                    and ipam_models.IPAddressToInterface.objects.filter(
                        ip_address=ip.nat_inside, interface__in=all_interfaces
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
                        "virtual_chassis": f"The master device for the virtual chassis ({existing_virtual_chassis}) may not be removed"
                    }
                )

        # Validate device is a member of a device redundancy group if it has a device redundancy group priority set
        if self.device_redundancy_group_priority is not None and self.device_redundancy_group is None:
            raise ValidationError(
                {
                    "device_redundancy_group_priority": "Must assign a redundancy group when defining a redundancy group priority."
                }
            )

        # If any software image file is specified, validate that
        # each of the software image files belongs to the device's device type or is a default image
        # TODO: this is incorrect as we cannot validate a ManyToMany during clean() - nautobot/nautobot#6344
        for image_file in self.software_image_files.all():
            if not image_file.default_image and self.device_type not in image_file.device_types.all():
                raise ValidationError(
                    {
                        "software_image_files": (
                            f"Software image file {image_file} for version '{image_file.software_version}' is not "
                            f"valid for device type {self.device_type}."
                        )
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
            save_child_device = False
            if device.location != self.location:
                device.location = self.location
                save_child_device = True
            if device.rack != self.rack:
                device.rack = self.rack
                save_child_device = True

            if save_child_device:
                device.save()

    def create_components(self):
        """Create device components from the device type definition."""
        # The order of these is significant as
        # - PowerOutlet depends on PowerPort
        # - FrontPort depends on RearPort
        component_models = [
            (ConsolePort, self.device_type.console_port_templates.all()),
            (ConsoleServerPort, self.device_type.console_server_port_templates.all()),
            (PowerPort, self.device_type.power_port_templates.all()),
            (PowerOutlet, self.device_type.power_outlet_templates.all()),
            (Interface, self.device_type.interface_templates.all()),
            (RearPort, self.device_type.rear_port_templates.all()),
            (FrontPort, self.device_type.front_port_templates.all()),
            (DeviceBay, self.device_type.device_bay_templates.all()),
            (ModuleBay, self.device_type.module_bay_templates.all()),
        ]
        instantiated_components = []
        for model, templates in component_models:
            model.objects.bulk_create([x.instantiate(device=self) for x in templates])
        cache_key = f"nautobot.dcim.device.{self.pk}.has_module_bays"
        cache.delete(cache_key)
        return instantiated_components

    create_components.alters_data = True

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
        qs = self.all_interfaces
        if self.virtual_chassis and self.virtual_chassis.master == self:
            for member in self.virtual_chassis.members.exclude(id=self.id):
                qs |= member.all_interfaces.filter(mgmt_only=False)
        return qs

    @property
    def common_vc_interfaces(self):
        """
        Return a QuerySet matching all Interfaces assigned to this Device or,
        if this Device belongs to a VirtualChassis, it returns all interfaces belonging Devices with same VirtualChassis
        """
        if self.virtual_chassis:
            return self.virtual_chassis.member_interfaces
        return self.all_interfaces

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

    @property
    def has_module_bays(self) -> bool:
        """
        Cacheable property for determining whether this Device has any ModuleBays, and therefore may contain Modules.
        """
        cache_key = f"nautobot.dcim.device.{self.pk}.has_module_bays"
        module_bays_exists = cache.get(cache_key)
        if module_bays_exists is None:
            module_bays_exists = self.module_bays.exists()
            cache.set(cache_key, module_bays_exists, timeout=5)
        return module_bays_exists

    @property
    def all_modules(self):
        """
        Return all child Modules installed in ModuleBays within this Device.
        """
        # Supports Device->ModuleBay->Module->ModuleBay->Module->ModuleBay->Module->ModuleBay->Module
        # This query looks for modules that are installed in a module_bay and attached to this device
        # We artificially limit the recursion to 4 levels or we would be stuck in an infinite loop.
        recursion_depth = MODULE_RECURSION_DEPTH_LIMIT
        qs = Module.objects.all()
        if not self.has_module_bays:
            # Short-circuit to avoid an expensive nested query
            return qs.none()
        query = Q()
        for level in range(recursion_depth):
            recursive_query = "parent_module_bay__parent_module__" * level
            query = query | Q(**{f"{recursive_query}parent_module_bay__parent_device": self})
        return qs.filter(query)

    @property
    def all_console_ports(self):
        """
        Return all Console Ports that are installed in the device or in modules that are installed in the device.
        """
        # TODO: These could probably be optimized to reduce the number of joins
        return ConsolePort.objects.filter(Q(device=self) | Q(module__in=self.all_modules))

    @property
    def all_console_server_ports(self):
        """
        Return all Console Server Ports that are installed in the device or in modules that are installed in the device.
        """
        return ConsoleServerPort.objects.filter(Q(device=self) | Q(module__in=self.all_modules))

    @property
    def all_front_ports(self):
        """
        Return all Front Ports that are installed in the device or in modules that are installed in the device.
        """
        return FrontPort.objects.filter(Q(device=self) | Q(module__in=self.all_modules))

    @property
    def all_interfaces(self):
        """
        Return all Interfaces that are installed in the device or in modules that are installed in the device.
        """
        return Interface.objects.filter(Q(device=self) | Q(module__in=self.all_modules))

    @property
    def all_module_bays(self):
        """
        Return all Module Bays that are installed in the device or in modules that are installed in the device.
        """
        return ModuleBay.objects.filter(Q(parent_device=self) | Q(parent_module__in=self.all_modules))

    @property
    def all_power_ports(self):
        """
        Return all Power Ports that are installed in the device or in modules that are installed in the device.
        """
        return PowerPort.objects.filter(Q(device=self) | Q(module__in=self.all_modules))

    @property
    def all_power_outlets(self):
        """
        Return all Power Outlets that are installed in the device or in modules that are installed in the device.
        """
        return PowerOutlet.objects.filter(Q(device=self) | Q(module__in=self.all_modules))

    @property
    def all_rear_ports(self):
        """
        Return all Rear Ports that are installed in the device or in modules that are installed in the device.
        """
        return RearPort.objects.filter(Q(device=self) | Q(module__in=self.all_modules))


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
    name = models.CharField(max_length=CHARFIELD_MAX_LENGTH, unique=True)
    domain = models.CharField(max_length=CHARFIELD_MAX_LENGTH, blank=True)

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
    "export_templates",
    "graphql",
    "statuses",
    "webhooks",
)
class DeviceRedundancyGroup(PrimaryModel):
    """
    A DeviceRedundancyGroup represents a logical grouping of physical hardware for the purposes of high-availability.
    """

    name = models.CharField(max_length=CHARFIELD_MAX_LENGTH, unique=True)
    status = StatusField(blank=False, null=False)
    description = models.CharField(max_length=CHARFIELD_MAX_LENGTH, blank=True)

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

    @property
    def controllers_sorted(self):
        return self.controllers.order_by("name")

    def __str__(self):
        return self.name


#
# Software image files
#


class SoftwareImageFileQuerySet(RestrictedQuerySet):
    """Queryset for SoftwareImageFile objects."""

    def get_for_object(self, obj):
        """Return all SoftwareImageFiles assigned to the given object."""
        from nautobot.virtualization.models import VirtualMachine

        if isinstance(obj, Device):
            if obj.software_image_files.exists():
                return obj.software_image_files.all()
            device_type_qs = self.filter(software_version__devices=obj, device_types=obj.device_type)
            if device_type_qs.exists():
                return device_type_qs
            return self.filter(software_version__devices=obj, default_image=True)
        elif isinstance(obj, InventoryItem):
            if obj.software_image_files.exists():
                return obj.software_image_files.all()
            else:
                return self.filter(software_version__inventory_items=obj)
        elif isinstance(obj, DeviceType):
            qs = self.filter(device_types=obj)
        elif isinstance(obj, VirtualMachine):
            if obj.software_image_files.exists():
                return obj.software_image_files.all()
            else:
                qs = self.filter(software_version__virtual_machines=obj)
        else:
            valid_types = "Device, DeviceType, InventoryItem and VirtualMachine"
            raise TypeError(f"{obj} is not a valid object type. Valid types are {valid_types}.")

        return qs


@extras_features(
    "custom_links",
    "custom_validators",
    "export_templates",
    "graphql",
    "statuses",
    "webhooks",
)
class SoftwareImageFile(PrimaryModel):
    """A software image file for a Device, Virtual Machine or Inventory Item."""

    software_version = models.ForeignKey(
        to="SoftwareVersion",
        on_delete=models.CASCADE,
        related_name="software_image_files",
        verbose_name="Software Version",
    )
    image_file_name = models.CharField(blank=False, max_length=CHARFIELD_MAX_LENGTH, verbose_name="Image File Name")
    image_file_checksum = models.CharField(blank=True, max_length=256, verbose_name="Image File Checksum")
    hashing_algorithm = models.CharField(
        choices=SoftwareImageFileHashingAlgorithmChoices,
        blank=True,
        max_length=255,
        verbose_name="Hashing Algorithm",
        help_text="Hashing algorithm for image file checksum",
    )
    image_file_size = models.PositiveBigIntegerField(
        blank=True,
        null=True,
        verbose_name="Image File Size",
        help_text="Image file size in bytes",
    )
    download_url = LaxURLField(blank=True, verbose_name="Download URL")
    external_integration = models.ForeignKey(
        to="extras.ExternalIntegration",
        on_delete=models.PROTECT,
        related_name="software_image_files",
        blank=True,
        null=True,
    )
    default_image = models.BooleanField(
        verbose_name="Default Image", help_text="Is the default image for this software version", default=False
    )
    status = StatusField(blank=False, null=False)

    objects = BaseManager.from_queryset(SoftwareImageFileQuerySet)()

    class Meta:
        ordering = ("software_version", "image_file_name")
        unique_together = ("image_file_name", "software_version")

    def __str__(self):
        return f"{self.software_version} - {self.image_file_name}"

    def delete(self, *args, **kwargs):
        """
        Intercept the ProtectedError for SoftwareImageFiles that are assigned to a DeviceType and provide a better
        error message. Instead of raising an exception on the DeviceTypeToSoftwareImageFile object, raise on the DeviceType.
        """

        try:
            return super().delete(*args, **kwargs)
        except models.ProtectedError as exc:
            protected_device_types = [
                instance.device_type
                for instance in exc.protected_objects
                if isinstance(instance, DeviceTypeToSoftwareImageFile)
            ]
            if protected_device_types:
                raise ProtectedError(
                    "Cannot delete some instances of model 'SoftwareImageFile' because they are "
                    "referenced through protected foreign keys: 'DeviceType.software_image_files'.",
                    protected_device_types,
                ) from exc
            raise exc


class SoftwareVersionQuerySet(RestrictedQuerySet):
    """Queryset for SoftwareVersion objects."""

    def get_for_object(self, obj):
        """Return all SoftwareVersions assigned to the given object."""
        from nautobot.virtualization.models import VirtualMachine

        if isinstance(obj, Device):
            qs = self.filter(devices=obj)
        elif isinstance(obj, InventoryItem):
            qs = self.filter(inventory_items=obj)
        elif isinstance(obj, DeviceType):
            qs = self.filter(software_image_files__device_types=obj)
        elif isinstance(obj, VirtualMachine):
            qs = self.filter(virtual_machines=obj)
        else:
            valid_types = "Device, DeviceType, InventoryItem and VirtualMachine"
            raise TypeError(f"{obj} is not a valid object type. Valid types are {valid_types}.")

        return qs


@extras_features(
    "custom_links",
    "custom_validators",
    "export_templates",
    "graphql",
    "statuses",
    "webhooks",
)
class SoftwareVersion(PrimaryModel):
    """A software version for a Device, Virtual Machine or Inventory Item."""

    platform = models.ForeignKey(to="dcim.Platform", on_delete=models.CASCADE)
    version = models.CharField(max_length=CHARFIELD_MAX_LENGTH)
    alias = models.CharField(
        max_length=CHARFIELD_MAX_LENGTH, blank=True, help_text="Optional alternative label for this version"
    )
    release_date = models.DateField(null=True, blank=True, verbose_name="Release Date")
    end_of_support_date = models.DateField(null=True, blank=True, verbose_name="End of Support Date")
    documentation_url = models.URLField(blank=True, verbose_name="Documentation URL")
    long_term_support = models.BooleanField(
        verbose_name="Long Term Support", default=False, help_text="Is a Long Term Support version"
    )
    pre_release = models.BooleanField(verbose_name="Pre-Release", default=False, help_text="Is a Pre-Release version")
    status = StatusField(blank=False, null=False)

    objects = BaseManager.from_queryset(SoftwareVersionQuerySet)()

    class Meta:
        ordering = ("platform", "version", "end_of_support_date", "release_date")
        unique_together = (
            "platform",
            "version",
        )

    def __str__(self):
        if self.alias:
            return self.alias
        return f"{self.platform} - {self.version}"


#
# Controller
#


@extras_features(
    "custom_links",
    "custom_validators",
    "export_templates",
    "graphql",
    "locations",
    "statuses",
    "webhooks",
)
class Controller(PrimaryModel):
    """Represents an entity that manages or controls one or more devices, acting as a central point of control.

    A Controller can be deployed to a single device or a group of devices represented by a DeviceRedundancyGroup.
    """

    name = models.CharField(max_length=CHARFIELD_MAX_LENGTH, unique=True)
    status = StatusField(blank=False, null=False)
    description = models.CharField(max_length=CHARFIELD_MAX_LENGTH, blank=True)
    location = models.ForeignKey(
        to="dcim.Location",
        on_delete=models.PROTECT,
        related_name="controllers",
    )
    platform = models.ForeignKey(
        to="dcim.Platform",
        on_delete=models.SET_NULL,
        related_name="controllers",
        blank=True,
        null=True,
    )
    role = RoleField(blank=True, null=True)
    capabilities = JSONArrayField(
        base_field=models.CharField(choices=ControllerCapabilitiesChoices),
        blank=True,
        null=True,
        help_text="List of capabilities supported by the controller, these capabilities are used to enhance views in Nautobot.",
    )
    tenant = models.ForeignKey(
        to="tenancy.Tenant",
        on_delete=models.PROTECT,
        related_name="controllers",
        blank=True,
        null=True,
    )
    external_integration = models.ForeignKey(
        to="extras.ExternalIntegration",
        on_delete=models.PROTECT,
        related_name="controllers",
        blank=True,
        null=True,
    )
    controller_device = models.ForeignKey(
        to="dcim.Device",
        on_delete=models.PROTECT,
        related_name="controllers",
        blank=True,
        null=True,
    )
    controller_device_redundancy_group = models.ForeignKey(
        to="dcim.DeviceRedundancyGroup",
        on_delete=models.PROTECT,
        related_name="controllers",
        blank=True,
        null=True,
    )

    class Meta:
        ordering = ("name",)

    def __str__(self):
        return self.name or super().__str__()

    def clean(self):
        super().clean()

        if self.controller_device and self.controller_device_redundancy_group:
            raise ValidationError(
                {
                    "controller_device": ("Cannot assign both a device and a device redundancy group to a controller."),
                },
            )
        if self.location:
            if ContentType.objects.get_for_model(self) not in self.location.location_type.content_types.all():
                raise ValidationError(
                    {"location": f'Controllers may not associate to locations of type "{self.location.location_type}".'}
                )

    def get_capabilities_display(self):
        if not self.capabilities:
            return format_html('<span class="text-muted">&mdash;</span>')
        return format_html_join(" ", '<span class="label label-default">{}</span>', ((v,) for v in self.capabilities))

    @property
    def wireless_network_assignments(self):
        """
        Returns all Controller Managed Device Group Wireless Network Assignment linked to this controller.
        """
        return ControllerManagedDeviceGroupWirelessNetworkAssignment.objects.filter(
            controller_managed_device_group__controller=self
        )


@extras_features(
    "custom_links",
    "custom_validators",
    "export_templates",
    "graphql",
    "webhooks",
)
class ControllerManagedDeviceGroup(TreeModel, PrimaryModel):
    """Represents a mapping of controlled devices to a specific controller.

    This model allows for the organization of controlled devices into hierarchical groups for structured representation.
    """

    name = models.CharField(
        max_length=CHARFIELD_MAX_LENGTH,
        unique=True,
        help_text="Name of the controller device group",
    )
    description = models.CharField(max_length=CHARFIELD_MAX_LENGTH, blank=True)
    weight = models.PositiveIntegerField(
        default=1000,
        help_text="Weight of the controller device group, used to sort the groups within its parent group",
    )
    controller = models.ForeignKey(
        to="dcim.Controller",
        on_delete=models.CASCADE,
        related_name="controller_managed_device_groups",
        blank=False,
        null=False,
        help_text="Controller that manages the devices in this group",
    )
    radio_profiles = models.ManyToManyField(
        to="wireless.RadioProfile",
        related_name="controller_managed_device_groups",
        through="wireless.ControllerManagedDeviceGroupRadioProfileAssignment",
        through_fields=("controller_managed_device_group", "radio_profile"),
        blank=True,
    )
    wireless_networks = models.ManyToManyField(
        to="wireless.WirelessNetwork",
        related_name="controller_managed_device_groups",
        through="wireless.ControllerManagedDeviceGroupWirelessNetworkAssignment",
        through_fields=("controller_managed_device_group", "wireless_network"),
        blank=True,
    )
    capabilities = JSONArrayField(
        base_field=models.CharField(choices=ControllerCapabilitiesChoices),
        blank=True,
        null=True,
        help_text="List of capabilities supported by the controller device group, these capabilities are used to enhance views in Nautobot.",
    )
    tenant = models.ForeignKey(
        to="tenancy.Tenant",
        on_delete=models.PROTECT,
        related_name="controller_managed_device_groups",
        blank=True,
        null=True,
    )

    class Meta:
        ordering = ("weight",)

    def __str__(self):
        return self.name or super().__str__()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._original_controller = self.controller if self.present_in_database else None
        self._original_parent = self.parent if self.present_in_database else None

    def clean(self):
        super().clean()

        if self.controller == self._original_controller and self.parent == self._original_parent:
            return

        if self.parent and self.controller and self.controller != self.parent.controller:  # pylint: disable=no-member
            raise ValidationError(
                {"controller": "Controller device group must have the same controller as the parent group."}
            )

    def get_capabilities_display(self):
        if not self.capabilities:
            return format_html('<span class="text-muted">&mdash;</span>')
        return format_html_join(" ", '<span class="label label-default">{}</span>', ((v,) for v in self.capabilities))


#
# Modules
#


@extras_features(
    "custom_links",
    "custom_validators",
    "export_templates",
    "graphql",
    "webhooks",
)
class ModuleFamily(PrimaryModel):
    """
    A ModuleFamily represents a classification of ModuleTypes.
    It is used to enforce compatibility between ModuleBays and Modules.
    """

    name = models.CharField(max_length=CHARFIELD_MAX_LENGTH, unique=True)
    description = models.CharField(max_length=CHARFIELD_MAX_LENGTH, blank=True)

    class Meta:
        ordering = ["name"]
        verbose_name_plural = "module families"

    def __str__(self):
        return self.name


# TODO: 5840 - Translate comments field from devicetype library, Nautobot doesn't use that field for ModuleType
@extras_features(
    "custom_links",
    "custom_validators",
    "export_templates",
    "graphql",
    "webhooks",
)
class ModuleType(PrimaryModel):
    """
    A ModuleType represents a particular make (Manufacturer) and model of Module. A Module can represent
    a line card, supervisor, or other interchangeable hardware component within a ModuleBay.

    ModuleType implements a subset of the features of DeviceType.

    Each ModuleType can have an arbitrary number of component templates assigned to it,
    which define console, power, and interface objects. For example, a Cisco WS-SUP720-3B
    ModuleType would have:

      * 1 ConsolePortTemplate
      * 2 InterfaceTemplates

    When a new Module of this type is created, the appropriate console, power, and interface
    objects (as defined by the ModuleType) are automatically created as well.
    """

    manufacturer = models.ForeignKey(to="dcim.Manufacturer", on_delete=models.PROTECT, related_name="module_types")
    module_family = models.ForeignKey(
        to="dcim.ModuleFamily",
        on_delete=models.PROTECT,
        related_name="module_types",
        blank=True,
        null=True,
    )
    model = models.CharField(max_length=CHARFIELD_MAX_LENGTH)
    part_number = models.CharField(
        max_length=CHARFIELD_MAX_LENGTH, blank=True, help_text="Discrete part number (optional)"
    )
    comments = models.TextField(blank=True)

    clone_fields = [
        "manufacturer",
        "module_family",
    ]

    class Meta:
        ordering = ("manufacturer", "model")
        unique_together = [
            ("manufacturer", "model"),
        ]

    def __str__(self):
        return self.model

    def to_yaml(self):
        data = OrderedDict(
            (
                ("manufacturer", self.manufacturer.name),
                ("model", self.model),
                ("part_number", self.part_number),
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
        if self.module_bay_templates.exists():
            data["module-bays"] = [
                {
                    "name": c.name,
                    "position": c.position,
                    "label": c.label,
                    "description": c.description,
                }
                for c in self.module_bay_templates.all()
            ]

        return yaml.dump(dict(data), sort_keys=False, allow_unicode=True)

    @property
    def display(self):
        return f"{self.manufacturer.name} {self.model}"


@extras_features(
    "custom_links",
    "custom_validators",
    "export_templates",
    "graphql",
    "locations",
    "statuses",
    "webhooks",
)
class Module(PrimaryModel):
    """
    A Module represents a line card, supervisor, or other interchangeable hardware component within a ModuleBay.
    Each Module is assigned a ModuleType and Status, and optionally a Role and/or Tenant.

    Each Module must be assigned to either a ModuleBay or a Location, but not both.

    When a new Module is created, console, power and interface components are created along with it as dictated
    by the component templates assigned to its ModuleType. Components can also be added, modified, or deleted after
    the creation of a Module.
    """

    module_type = models.ForeignKey(to="dcim.ModuleType", on_delete=models.PROTECT, related_name="modules")
    parent_module_bay = models.OneToOneField(
        to="dcim.ModuleBay",
        on_delete=models.CASCADE,
        related_name="installed_module",
        blank=True,
        null=True,
    )
    status = StatusField()
    role = RoleField(blank=True, null=True)
    tenant = models.ForeignKey(
        to="tenancy.Tenant",
        on_delete=models.PROTECT,
        related_name="modules",
        blank=True,
        null=True,
    )
    serial = models.CharField(  # noqa: DJ001  # django-nullable-model-string-field -- intentional
        max_length=CHARFIELD_MAX_LENGTH,
        blank=True,
        null=True,
        verbose_name="Serial number",
        db_index=True,
    )
    asset_tag = models.CharField(
        max_length=CHARFIELD_MAX_LENGTH,
        blank=True,
        null=True,
        unique=True,
        verbose_name="Asset tag",
        help_text="A unique tag used to identify this module",
    )
    location = models.ForeignKey(
        to="dcim.Location",
        on_delete=models.PROTECT,
        related_name="modules",
        blank=True,
        null=True,
    )
    # TODO: add software support for Modules

    clone_fields = [
        "module_type",
        "role",
        "tenant",
        "location",
        "status",
    ]

    # The recursive nature of this model combined with the fact that it can be a child of a
    # device or location makes our natural key implementation unusable, so just use the pk
    natural_key_field_names = ["pk"]

    class Meta:
        ordering = ("parent_module_bay", "location", "module_type", "asset_tag", "serial")
        constraints = [
            models.UniqueConstraint(
                fields=["module_type", "serial"],
                name="dcim_module_module_type_serial_unique",
            ),
        ]

    def __str__(self):
        serial = f" (Serial: {self.serial})" if self.serial else ""
        asset_tag = f" (Asset Tag: {self.asset_tag})" if self.asset_tag else ""
        return str(self.module_type) + serial + asset_tag

    @property
    def display(self):
        if self.location:
            return f"{self!s} at location {self.location}"
        elif self.parent_module_bay.parent_device is not None:
            return f"{self.module_type!s} installed in {self.parent_module_bay.parent_device.display}"
        else:
            return f"{self.module_type!s} installed in {self.parent_module_bay.parent_module.display}"

    @property
    def device(self):
        """Walk up parent chain to find the Device that this Module is installed in, if one exists."""
        if self.parent_module_bay is None:
            return None
        return self.parent_module_bay.parent

    def clean(self):
        super().clean()

        # Validate that the Module is associated with a Location or a ModuleBay
        if self.parent_module_bay is None and self.location is None:
            raise ValidationError("One of location or parent_module_bay must be set")

        # Validate location
        if self.location is not None:
            if self.parent_module_bay is not None:
                raise ValidationError("Only one of location or parent_module_bay must be set")

            if ContentType.objects.get_for_model(self) not in self.location.location_type.content_types.all():
                raise ValidationError(
                    {"location": f'Modules may not associate to locations of type "{self.location.location_type}".'}
                )

        # Validate module family compatibility
        if self.parent_module_bay and self.parent_module_bay.module_family:
            if self.module_type.module_family != self.parent_module_bay.module_family:
                module_family_name = self.parent_module_bay.module_family.name
                if self.module_type.module_family is None:
                    module_type_family = "not assigned to a family"
                else:
                    module_type_family = f"in the family {self.module_type.module_family.name}"
                raise ValidationError(
                    {
                        "module_type": f"The selected module bay requires a module type in the family {module_family_name}, "
                        f"but the selected module type is {module_type_family}."
                    }
                )

        # Validate module manufacturer constraint
        if self.parent_module_bay and self.parent_module_bay.requires_first_party_modules:
            if self.parent_module_bay.parent_device:
                parent_mfr = self.parent_module_bay.parent_device.device_type.manufacturer
            elif self.parent_module_bay.parent_module:
                parent_mfr = self.parent_module_bay.parent_module.module_type.manufacturer
            else:
                parent_mfr = None
            if parent_mfr and self.module_type.manufacturer != parent_mfr:
                raise ValidationError(
                    {
                        "module_type": "The selected module bay requires a module type from the same manufacturer as the parent device or module"
                    }
                )

    def save(self, *args, **kwargs):
        is_new = not self.present_in_database

        if self.serial == "":
            self.serial = None
        if self.asset_tag == "":
            self.asset_tag = None

        # Prevent creating a Module that is its own ancestor, creating an infinite loop
        parent_module = getattr(self.parent_module_bay, "parent_module", None)
        while parent_module is not None:
            if parent_module == self:
                raise ValidationError("Creating this instance would cause an infinite loop.")
            parent_module = getattr(parent_module.parent_module_bay, "parent_module", None)

        # Keep track of whether the parent module bay has changed so we can update the component names
        parent_module_changed = (
            not is_new and not Module.objects.filter(pk=self.pk, parent_module_bay=self.parent_module_bay).exists()
        )

        super().save(*args, **kwargs)

        # If this is a new Module, instantiate all related components per the ModuleType definition
        if is_new:
            self.create_components()

        # Render component names when this Module is first created or when the parent module bay has changed
        if is_new or parent_module_changed:
            self.render_component_names()

    def create_components(self):
        """Create module components from the module type definition."""
        # The order of these is significant as
        # - PowerOutlet depends on PowerPort
        # - FrontPort depends on RearPort
        component_models = [
            (ConsolePort, self.module_type.console_port_templates.all()),
            (ConsoleServerPort, self.module_type.console_server_port_templates.all()),
            (PowerPort, self.module_type.power_port_templates.all()),
            (PowerOutlet, self.module_type.power_outlet_templates.all()),
            (Interface, self.module_type.interface_templates.all()),
            (RearPort, self.module_type.rear_port_templates.all()),
            (FrontPort, self.module_type.front_port_templates.all()),
            (ModuleBay, self.module_type.module_bay_templates.all()),
        ]
        instantiated_components = []
        for model, templates in component_models:
            model.objects.bulk_create([x.instantiate(device=None, module=self) for x in templates])
        return instantiated_components

    create_components.alters_data = True

    def render_component_names(self):
        """
        Replace the {module}, {module.parent}, {module.parent.parent}, etc. template variables in descendant
        component names with the correct parent module bay positions.
        """

        # disable sorting to improve performance, sorting isn't necessary here
        component_models = [
            self.console_ports.all().order_by(),
            self.console_server_ports.all().order_by(),
            self.power_ports.all().order_by(),
            self.power_outlets.all().order_by(),
            self.interfaces.all().order_by(),
            self.rear_ports.all().order_by(),
            self.front_ports.all().order_by(),
        ]

        for component_qs in component_models:
            for component in component_qs.only("name", "module"):
                component.render_name_template(save=True)

        for child in self.get_children():
            child.render_component_names()

    render_component_names.alters_data = True

    def get_cables(self, pk_list=False):
        """
        Return a QuerySet or PK list matching all Cables connected to any component of this Module.
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
            cable_pks += component_model.objects.filter(module=self, cable__isnull=False).values_list(
                "cable", flat=True
            )
        if pk_list:
            return cable_pks
        return Cable.objects.filter(pk__in=cable_pks)

    def get_children(self):
        """
        Return the set of child Modules installed in ModuleBays within this Module.
        """
        return Module.objects.filter(parent_module_bay__parent_module=self)


#
# Virtual Device Contexts
#


@extras_features(
    "custom_links",
    "custom_validators",
    "export_templates",
    "graphql",
    "statuses",
    "webhooks",
)
class VirtualDeviceContext(PrimaryModel):
    name = models.CharField(max_length=CHARFIELD_MAX_LENGTH)
    device = models.ForeignKey("dcim.Device", on_delete=models.CASCADE, related_name="virtual_device_contexts")
    identifier = models.PositiveSmallIntegerField(
        help_text="Unique identifier provided by the platform being virtualized (Example: Nexus VDC Identifier)",
        blank=True,
        null=True,
    )
    status = StatusField(blank=False, null=False)
    role = RoleField(blank=True, null=True)
    primary_ip4 = models.ForeignKey(
        to="ipam.IPAddress",
        on_delete=models.SET_NULL,
        related_name="ip4_vdcs",
        blank=True,
        null=True,
        verbose_name="Primary IPv4",
    )
    primary_ip6 = models.ForeignKey(
        to="ipam.IPAddress",
        on_delete=models.SET_NULL,
        related_name="ip6_vdcs",
        blank=True,
        null=True,
        verbose_name="Primary IPv6",
    )
    tenant = models.ForeignKey(
        "tenancy.Tenant", on_delete=models.CASCADE, related_name="virtual_device_contexts", blank=True, null=True
    )
    interfaces = models.ManyToManyField(
        blank=True,
        related_name="virtual_device_contexts",
        to="dcim.Interface",
        through="dcim.InterfaceVDCAssignment",
    )
    description = models.CharField(max_length=CHARFIELD_MAX_LENGTH, blank=True)

    class Meta:
        ordering = ("name",)
        unique_together = (("device", "identifier"), ("device", "name"))

    def __str__(self):
        return self.name

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

    def validate_primary_ips(self):
        for field in ["primary_ip4", "primary_ip6"]:
            ip = getattr(self, field)
            if ip is not None:
                if field == "primary_ip4" and ip.ip_version != 4:
                    raise ValidationError({f"{field}": f"{ip} is not an IPv4 address."})
                if field == "primary_ip6" and ip.ip_version != 6:
                    raise ValidationError({f"{field}": f"{ip} is not an IPv6 address."})
                if not ip.interfaces.filter(device=self.device).exists():
                    raise ValidationError(
                        {f"{field}": f"{ip} is not part of an interface that belongs to this VDC's device."}
                    )
                # Note: The validation for primary IPs `validate_primary_ips` is commented out due to the order in which Django processes form validation with
                # Many-to-Many (M2M) fields. During form saving, Django creates the instance first before assigning the M2M fields (in this case, interfaces).
                # As a result, the primary_ips fields could fail validation at this point because the interfaces are not yet linked to the instance,
                # leading to validation errors.
                # interfaces = self.interfaces.all()
                # if IPAddressToInterface.objects.filter(ip_address=ip, interface__in=interfaces).exists():
                #     pass
                # elif (
                #     ip.nat_inside is None
                #     or not IPAddressToInterface.objects.filter(
                #         ip_address=ip.nat_inside, interface__in=interfaces
                #     ).exists()
                # ):
                #     raise ValidationError(
                #         {f"{field}": f"The specified IP address ({ip}) is not assigned to this Virtual Device Context."}
                #     )

    def clean(self):
        super().clean()
        self.validate_primary_ips()

        # Validate that device is not being modified
        if self.present_in_database:
            vdc = VirtualDeviceContext.objects.get(id=self.id)
            if vdc.device != self.device:
                raise ValidationError({"device": "Virtual Device Context's device cannot be changed once created"})


@extras_features(
    "custom_links",
    "custom_validators",
    "export_templates",
    "graphql",
)
class InterfaceVDCAssignment(BaseModel):
    virtual_device_context = models.ForeignKey(
        VirtualDeviceContext, on_delete=models.CASCADE, related_name="interface_assignments"
    )
    interface = models.ForeignKey(
        Interface, on_delete=models.CASCADE, related_name="virtual_device_context_assignments"
    )

    class Meta:
        unique_together = ["virtual_device_context", "interface"]
        ordering = ["virtual_device_context", "interface"]

    def __str__(self):
        return f"{self.virtual_device_context}: {self.interface}"
