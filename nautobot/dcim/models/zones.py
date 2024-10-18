from django.core.exceptions import ValidationError
from django.db import models

from nautobot.core.constants import CHARFIELD_MAX_LENGTH
from nautobot.core.models import BaseModel
from nautobot.core.models.generics import PrimaryModel
from nautobot.extras.models import RoleField, StatusField
from nautobot.extras.utils import extras_features


@extras_features(
    "custom_links",
    "custom_validators",
    "export_templates",
    "graphql",
    "locations",
    "webhooks",
)
class ZoneType(PrimaryModel):
    """
    A Zone Type is a organization specific way to catagorize a specific Zone implementation.
    E.g. "Secure DMZ" or "External Presentation"
    """

    name = models.CharField(max_length=CHARFIELD_MAX_LENGTH, unique=True)
    description = models.CharField(max_length=CHARFIELD_MAX_LENGTH, blank=True)

    natural_key_field_names = ["name"]

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
    "webhooks",
)
class Zone(PrimaryModel):
    """
    A Zone represents a logical area of a network topology that contains device connectivity,
    address space, VLAN domains, etc.

    Zones typically relate to larger portions that one can point out on a network design diagram,
    as being distinct areas of concern.
    """

    name = models.CharField(max_length=CHARFIELD_MAX_LENGTH, unique=True)
    description = models.CharField(max_length=CHARFIELD_MAX_LENGTH, blank=True)
    type = models.ForeignKey(to="ZoneType", on_delete=models.PROTECT, related_name="zones")
    role = RoleField(blank=True, null=True)
    status = StatusField(blank=False, null=False)
    location = models.ForeignKey(to="dcim.Location", on_delete=models.PROTECT, related_name="zones")
    tenant = models.ForeignKey(
        to="tenancy.Tenant",
        on_delete=models.PROTECT,
        related_name="zones",
        blank=True,
        null=True,
    )
    prefixes = models.ManyToManyField(
        blank=True,
        related_name="zones",
        to="ipam.Prefix",
        through="dcim.ZonePrefixAssignment",
    )
    devices = models.ManyToManyField(
        blank=True,
        related_name="zones",
        to="dcim.Device",
        through="dcim.ZoneDeviceAssignment",
    )
    interfaces = models.ManyToManyField(
        blank=True,
        related_name="zones",
        to="dcim.Interface",
        through="dcim.ZoneInterfaceAssignment",
    )
    vlans = models.ManyToManyField(
        blank=True,
        related_name="zones",
        to="ipam.VLAN",
        through="dcim.ZoneVLANAssignment",
    )
    vrfs = models.ManyToManyField(
        blank=True,
        related_name="zones",
        to="ipam.VRF",
        through="dcim.ZoneVRFAssignment",
    )

    natural_key_field_names = ["name"]

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name

    def clean(self):
        super().clean()


#
# M2M Through Tables
#

@extras_features(
    "custom_links",
    "custom_validators",
    "export_templates",
    "graphql",
)
class ZonePrefixAssignment(BaseModel):
    zone = models.ForeignKey(to="Zone", on_delete=models.CASCADE, related_name="prefix_assignments")
    prefix = models.ForeignKey("ipam.Prefix", on_delete=models.CASCADE, related_name="zone_assignments")

    class Meta:
        unique_together = ["zone", "prefix"]
        ordering = ["zone", "prefix"]

    def __str__(self):
        return f"{self.zone}: {self.prefix}"


@extras_features(
    "custom_links",
    "custom_validators",
    "export_templates",
    "graphql",
)
class ZoneDeviceAssignment(BaseModel):
    zone = models.ForeignKey(to="Zone", on_delete=models.CASCADE, related_name="device_assignments")
    device = models.ForeignKey("dcim.Device", on_delete=models.CASCADE, related_name="zone_assignments")

    class Meta:
        unique_together = ["zone", "device"]
        ordering = ["zone", "device"]

    def __str__(self):
        return f"{self.zone}: {self.device}"


@extras_features(
    "custom_links",
    "custom_validators",
    "export_templates",
    "graphql",
)
class ZoneInterfaceAssignment(BaseModel):
    zone = models.ForeignKey(to="Zone", on_delete=models.CASCADE, related_name="interface_assignments")
    interface = models.ForeignKey("dcim.Interface", on_delete=models.CASCADE, related_name="zone_assignments")

    class Meta:
        unique_together = ["zone", "interface"]
        ordering = ["zone", "interface"]

    def __str__(self):
        return f"{self.zone}: {self.interface}"
    
    def clean(self):
        super().clean()

        # The interface's device must be a member of the zone
        if not self.interface.device.zone_assignments.filter(zone=self.zone).exists():
            raise ValidationError({
                "interface": f"The device ({self.interface.device}) must be a member of the zone."
            })


@extras_features(
    "custom_links",
    "custom_validators",
    "export_templates",
    "graphql",
)
class ZoneVLANAssignment(BaseModel):
    zone = models.ForeignKey(to="Zone", on_delete=models.CASCADE, related_name="vlan_assignments")
    vlan = models.ForeignKey("ipam.VLAN", on_delete=models.CASCADE, related_name="zone_assignments")

    class Meta:
        unique_together = ["zone", "vlan"]
        ordering = ["zone", "vlan"]

    def __str__(self):
        return f"{self.zone}: {self.vlan}"


@extras_features(
    "custom_links",
    "custom_validators",
    "export_templates",
    "graphql",
)
class ZoneVRFAssignment(BaseModel):
    zone = models.ForeignKey(to="Zone", on_delete=models.CASCADE, related_name="vrf_assignments")
    vrf = models.ForeignKey("ipam.VRF", on_delete=models.CASCADE, related_name="zone_assignments")

    class Meta:
        unique_together = ["zone", "vrf"]
        ordering = ["zone", "vrf"]

    def __str__(self):
        return f"{self.zone}: {self.vrf}"
