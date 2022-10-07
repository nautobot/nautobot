from django.contrib.contenttypes.fields import GenericForeignKey, GenericRelation
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models import Sum
from django.urls import reverse
from mptt.models import MPTTModel, TreeForeignKey

from nautobot.dcim.choices import (
    ConsolePortTypeChoices,
    InterfaceModeChoices,
    InterfaceStatusChoices,
    InterfaceTypeChoices,
    PortTypeChoices,
    PowerFeedPhaseChoices,
    PowerOutletFeedLegChoices,
    PowerOutletTypeChoices,
    PowerPortTypeChoices,
)
from nautobot.dcim.constants import (
    NONCONNECTABLE_IFACE_TYPES,
    REARPORT_POSITIONS_MAX,
    REARPORT_POSITIONS_MIN,
    VIRTUAL_IFACE_TYPES,
    WIRELESS_IFACE_TYPES,
)

from nautobot.dcim.fields import MACAddressCharField
from nautobot.extras.models import (
    RelationshipModel,
    Status,
    StatusModel,
)
from nautobot.extras.utils import extras_features
from nautobot.core.models.generics import PrimaryModel
from nautobot.utilities.fields import NaturalOrderingField
from nautobot.utilities.mptt import TreeManager
from nautobot.utilities.ordering import naturalize_interface
from nautobot.utilities.query_functions import CollateAsChar
from nautobot.utilities.utils import UtilizationData

__all__ = (
    "BaseInterface",
    "CableTermination",
    "ConsolePort",
    "ConsoleServerPort",
    "DeviceBay",
    "FrontPort",
    "Interface",
    "InventoryItem",
    "PathEndpoint",
    "PowerOutlet",
    "PowerPort",
    "RearPort",
)


class ComponentModel(PrimaryModel):
    """
    An abstract model inherited by any model which has a parent Device.
    """

    device = models.ForeignKey(to="dcim.Device", on_delete=models.CASCADE, related_name="%(class)ss")
    name = models.CharField(max_length=64, db_index=True)
    _name = NaturalOrderingField(target_field="name", max_length=100, blank=True, db_index=True)
    label = models.CharField(max_length=64, blank=True, help_text="Physical label")
    description = models.CharField(max_length=200, blank=True)

    class Meta:
        abstract = True

    def __str__(self):
        if self.label:
            return f"{self.name} ({self.label})"
        return self.name

    def to_objectchange(self, action, **kwargs):
        """
        Return a new ObjectChange with the `related_object` pinned to the `device` by default.
        """
        # Annotate the parent Device
        try:
            device = self.device
        except ObjectDoesNotExist:
            # The parent Device has already been deleted
            device = None

        return super().to_objectchange(action, related_object=device, **kwargs)

    @property
    def parent(self):
        return getattr(self, "device", None)


class CableTermination(models.Model):
    """
    An abstract model inherited by all models to which a Cable can terminate (certain device components, PowerFeed, and
    CircuitTermination instances). The `cable` field indicates the Cable instance which is terminated to this instance.

    `_cable_peer` is a GenericForeignKey used to cache the far-end CableTermination on the local instance; this is a
    shortcut to referencing `cable.termination_b`, for example. `_cable_peer` is set or cleared by the receivers in
    dcim.signals when a Cable instance is created or deleted, respectively.
    """

    cable = models.ForeignKey(
        to="dcim.Cable",
        on_delete=models.SET_NULL,
        related_name="+",
        blank=True,
        null=True,
    )
    _cable_peer_type = models.ForeignKey(
        to=ContentType,
        on_delete=models.SET_NULL,
        related_name="+",
        blank=True,
        null=True,
    )
    _cable_peer_id = models.UUIDField(blank=True, null=True)
    _cable_peer = GenericForeignKey(ct_field="_cable_peer_type", fk_field="_cable_peer_id")

    # Generic relations to Cable. These ensure that an attached Cable is deleted if the terminated object is deleted.
    _cabled_as_a = GenericRelation(
        to="dcim.Cable",
        content_type_field="termination_a_type",
        object_id_field="termination_a_id",
    )
    _cabled_as_b = GenericRelation(
        to="dcim.Cable",
        content_type_field="termination_b_type",
        object_id_field="termination_b_id",
    )

    class Meta:
        abstract = True

    def get_cable_peer(self):
        return self._cable_peer


class PathEndpoint(models.Model):
    """
    An abstract model inherited by any CableTermination subclass which represents the end of a CablePath; specifically,
    these include ConsolePort, ConsoleServerPort, PowerPort, PowerOutlet, Interface, PowerFeed, and CircuitTermination.

    `_path` references the CablePath originating from this instance, if any. It is set or cleared by the receivers in
    dcim.signals in response to changes in the cable path, and complements the `origin` GenericForeignKey field on the
    CablePath model. `_path` should not be accessed directly; rather, use the `path` property.

    `connected_endpoint()` is a convenience method for returning the destination of the associated CablePath, if any.
    """

    _path = models.ForeignKey(to="dcim.CablePath", on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        abstract = True

    def trace(self):
        if self._path is None:
            return []

        # Construct the complete path
        path = [self, *self._path.get_path()]
        while (len(path) + 1) % 3:
            # Pad to ensure we have complete three-tuples (e.g. for paths that end at a RearPort)
            path.append(None)
        path.append(self._path.destination)

        # Return the path as a list of three-tuples (A termination, cable, B termination)
        return list(zip(*[iter(path)] * 3))

    @property
    def path(self):
        return self._path

    @property
    def connected_endpoint(self):
        """
        Caching accessor for the attached CablePath's destination (if any)
        """
        if not hasattr(self, "_connected_endpoint"):
            self._connected_endpoint = self._path.destination if self._path else None
        return self._connected_endpoint


#
# Console ports
#


@extras_features(
    "cable_terminations",
    "custom_fields",
    "custom_validators",
    "export_templates",
    "graphql",
    "relationships",
    "webhooks",
)
class ConsolePort(CableTermination, PathEndpoint, ComponentModel):
    """
    A physical console port within a Device. ConsolePorts connect to ConsoleServerPorts.
    """

    type = models.CharField(
        max_length=50,
        choices=ConsolePortTypeChoices,
        blank=True,
        help_text="Physical port type",
    )

    csv_headers = ["device", "name", "label", "type", "description"]

    class Meta:
        ordering = ("device", "_name")
        unique_together = ("device", "name")

    def get_absolute_url(self):
        return reverse("dcim:consoleport", kwargs={"pk": self.pk})

    def to_csv(self):
        return (
            self.device.identifier,
            self.name,
            self.label,
            self.type,
            self.description,
        )


#
# Console server ports
#


@extras_features("cable_terminations", "custom_fields", "custom_validators", "graphql", "relationships", "webhooks")
class ConsoleServerPort(CableTermination, PathEndpoint, ComponentModel):
    """
    A physical port within a Device (typically a designated console server) which provides access to ConsolePorts.
    """

    type = models.CharField(
        max_length=50,
        choices=ConsolePortTypeChoices,
        blank=True,
        help_text="Physical port type",
    )

    csv_headers = ["device", "name", "label", "type", "description"]

    class Meta:
        ordering = ("device", "_name")
        unique_together = ("device", "name")

    def get_absolute_url(self):
        return reverse("dcim:consoleserverport", kwargs={"pk": self.pk})

    def to_csv(self):
        return (
            self.device.identifier,
            self.name,
            self.label,
            self.type,
            self.description,
        )


#
# Power ports
#


@extras_features(
    "cable_terminations",
    "custom_fields",
    "custom_validators",
    "export_templates",
    "graphql",
    "relationships",
    "webhooks",
)
class PowerPort(CableTermination, PathEndpoint, ComponentModel):
    """
    A physical power supply (intake) port within a Device. PowerPorts connect to PowerOutlets.
    """

    type = models.CharField(
        max_length=50,
        choices=PowerPortTypeChoices,
        blank=True,
        help_text="Physical port type",
    )
    maximum_draw = models.PositiveSmallIntegerField(
        blank=True,
        null=True,
        validators=[MinValueValidator(1)],
        help_text="Maximum power draw (watts)",
    )
    allocated_draw = models.PositiveSmallIntegerField(
        blank=True,
        null=True,
        validators=[MinValueValidator(1)],
        help_text="Allocated power draw (watts)",
    )

    csv_headers = [
        "device",
        "name",
        "label",
        "type",
        "maximum_draw",
        "allocated_draw",
        "description",
    ]

    class Meta:
        ordering = ("device", "_name")
        unique_together = ("device", "name")

    def get_absolute_url(self):
        return reverse("dcim:powerport", kwargs={"pk": self.pk})

    def to_csv(self):
        return (
            self.device.identifier,
            self.name,
            self.label,
            self.get_type_display(),
            self.maximum_draw,
            self.allocated_draw,
            self.description,
        )

    def clean(self):
        super().clean()

        if self.maximum_draw is not None and self.allocated_draw is not None:
            if self.allocated_draw > self.maximum_draw:
                raise ValidationError(
                    {"allocated_draw": f"Allocated draw cannot exceed the maximum draw ({self.maximum_draw}W)."}
                )

    def get_power_draw(self):
        """
        Return the allocated and maximum power draw (in VA) and child PowerOutlet count for this PowerPort.
        """
        # Calculate aggregate draw of all child power outlets if no numbers have been defined manually
        if self.allocated_draw is None and self.maximum_draw is None:
            poweroutlet_ct = ContentType.objects.get_for_model(PowerOutlet)
            outlet_ids = PowerOutlet.objects.filter(power_port=self).values_list("pk", flat=True)
            utilization = PowerPort.objects.filter(
                _cable_peer_type=poweroutlet_ct, _cable_peer_id__in=outlet_ids
            ).aggregate(
                maximum_draw_total=Sum("maximum_draw"),
                allocated_draw_total=Sum("allocated_draw"),
            )
            numerator = utilization["allocated_draw_total"] or 0
            denominator = utilization["maximum_draw_total"] or 0
            ret = {
                "allocated": utilization["allocated_draw_total"] or 0,
                "maximum": utilization["maximum_draw_total"] or 0,
                "outlet_count": len(outlet_ids),
                "legs": [],
                "utilization_data": UtilizationData(
                    numerator=numerator,
                    denominator=denominator,
                ),
            }

            # Calculate per-leg aggregates for three-phase feeds
            if getattr(self._cable_peer, "phase", None) == PowerFeedPhaseChoices.PHASE_3PHASE:
                # Setup numerator and denominator for later display.
                for leg, leg_name in PowerOutletFeedLegChoices:
                    outlet_ids = PowerOutlet.objects.filter(power_port=self, feed_leg=leg).values_list("pk", flat=True)
                    utilization = PowerPort.objects.filter(
                        _cable_peer_type=poweroutlet_ct, _cable_peer_id__in=outlet_ids
                    ).aggregate(
                        maximum_draw_total=Sum("maximum_draw"),
                        allocated_draw_total=Sum("allocated_draw"),
                    )
                    ret["legs"].append(
                        {
                            "name": leg_name,
                            "allocated": utilization["allocated_draw_total"] or 0,
                            "maximum": utilization["maximum_draw_total"] or 0,
                            "outlet_count": len(outlet_ids),
                        }
                    )

            return ret

        if self.connected_endpoint and hasattr(self.connected_endpoint, "available_power"):
            denominator = self.connected_endpoint.available_power or 0
        else:
            denominator = 0

        # Default to administratively defined values
        return {
            "allocated": self.allocated_draw or 0,
            "maximum": self.maximum_draw or 0,
            "outlet_count": PowerOutlet.objects.filter(power_port=self).count(),
            "legs": [],
            "utilization_data": UtilizationData(numerator=self.allocated_draw or 0, denominator=denominator),
        }


#
# Power outlets
#


@extras_features("cable_terminations", "custom_fields", "custom_validators", "graphql", "relationships", "webhooks")
class PowerOutlet(CableTermination, PathEndpoint, ComponentModel):
    """
    A physical power outlet (output) within a Device which provides power to a PowerPort.
    """

    type = models.CharField(
        max_length=50,
        choices=PowerOutletTypeChoices,
        blank=True,
        help_text="Physical port type",
    )
    power_port = models.ForeignKey(
        to="dcim.PowerPort",
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="poweroutlets",
    )
    # todoindex:
    feed_leg = models.CharField(
        max_length=50,
        choices=PowerOutletFeedLegChoices,
        blank=True,
        help_text="Phase (for three-phase feeds)",
    )

    csv_headers = [
        "device",
        "name",
        "label",
        "type",
        "power_port",
        "feed_leg",
        "description",
    ]

    class Meta:
        ordering = ("device", "_name")
        unique_together = ("device", "name")

    def get_absolute_url(self):
        return reverse("dcim:poweroutlet", kwargs={"pk": self.pk})

    def to_csv(self):
        return (
            self.device.identifier,
            self.name,
            self.label,
            self.get_type_display(),
            self.power_port.name if self.power_port else None,
            self.get_feed_leg_display(),
            self.description,
        )

    def clean(self):
        super().clean()

        # Validate power port assignment
        if self.power_port and self.power_port.device != self.device:
            raise ValidationError(f"Parent power port ({self.power_port}) must belong to the same device")


#
# Interfaces
#


class BaseInterface(RelationshipModel, StatusModel):
    """
    Abstract base class for fields shared by dcim.Interface and virtualization.VMInterface.
    """

    enabled = models.BooleanField(default=True)
    mac_address = MACAddressCharField(null=True, blank=True, verbose_name="MAC Address")
    mtu = models.PositiveIntegerField(
        blank=True,
        null=True,
        validators=[MinValueValidator(1), MaxValueValidator(65536)],
        verbose_name="MTU",
    )
    mode = models.CharField(max_length=50, choices=InterfaceModeChoices, blank=True)
    parent_interface = models.ForeignKey(
        to="self",
        on_delete=models.CASCADE,
        related_name="child_interfaces",
        null=True,
        blank=True,
        verbose_name="Parent interface",
        help_text="Assigned parent interface",
    )
    bridge = models.ForeignKey(
        to="self",
        on_delete=models.SET_NULL,
        related_name="bridged_interfaces",
        null=True,
        blank=True,
        verbose_name="Bridge interface",
        help_text="Assigned bridge interface",
    )

    class Meta:
        abstract = True

    def clean(self):
        # Remove untagged VLAN assignment for non-802.1Q interfaces
        if not self.mode and self.untagged_vlan is not None:
            raise ValidationError({"untagged_vlan": "Mode must be set when specifying untagged_vlan"})

    def save(self, *args, **kwargs):

        if not self.status:
            query = Status.objects.get_for_model(self)
            try:
                status = query.get(slug=InterfaceStatusChoices.STATUS_ACTIVE)
            except Status.DoesNotExist:
                raise ValidationError({"status": "Default status 'active' does not exist"})
            self.status = status

        # Only "tagged" interfaces may have tagged VLANs assigned. ("tagged all" implies all VLANs are assigned.)
        if self.present_in_database and self.mode != InterfaceModeChoices.MODE_TAGGED:
            self.tagged_vlans.clear()

        return super().save(*args, **kwargs)


@extras_features(
    "cable_terminations",
    "custom_fields",
    "custom_validators",
    "export_templates",
    "graphql",
    "relationships",
    "statuses",
    "webhooks",
)
class Interface(CableTermination, PathEndpoint, ComponentModel, BaseInterface):
    """
    A network interface within a Device. A physical Interface can connect to exactly one other Interface.
    """

    # Override ComponentModel._name to specify naturalize_interface function
    _name = NaturalOrderingField(
        target_field="name", naturalize_function=naturalize_interface, max_length=100, blank=True, db_index=True
    )
    lag = models.ForeignKey(
        to="self",
        on_delete=models.SET_NULL,
        related_name="member_interfaces",
        null=True,
        blank=True,
        verbose_name="Parent LAG",
        help_text="Assigned LAG interface",
    )
    # todoindex:
    type = models.CharField(max_length=50, choices=InterfaceTypeChoices)
    # todoindex:
    mgmt_only = models.BooleanField(
        default=False,
        verbose_name="Management only",
        help_text="This interface is used only for out-of-band management",
    )
    untagged_vlan = models.ForeignKey(
        to="ipam.VLAN",
        on_delete=models.SET_NULL,
        related_name="interfaces_as_untagged",
        null=True,
        blank=True,
        verbose_name="Untagged VLAN",
    )
    tagged_vlans = models.ManyToManyField(
        to="ipam.VLAN",
        related_name="interfaces_as_tagged",
        blank=True,
        verbose_name="Tagged VLANs",
    )
    ip_addresses = GenericRelation(
        to="ipam.IPAddress",
        content_type_field="assigned_object_type",
        object_id_field="assigned_object_id",
        related_query_name="interface",
    )

    csv_headers = [
        "device",
        "name",
        "label",
        "lag",
        "type",
        "enabled",
        "mac_address",
        "mtu",
        "mgmt_only",
        "description",
        "mode",
        "status",
        "parent_interface",
        "bridge",
    ]

    class Meta:
        ordering = ("device", CollateAsChar("_name"))
        unique_together = ("device", "name")

    def get_absolute_url(self):
        return reverse("dcim:interface", kwargs={"pk": self.pk})

    def to_csv(self):
        return (
            self.device.identifier if self.device else None,
            self.name,
            self.label,
            self.lag.name if self.lag else None,
            self.get_type_display(),
            self.enabled,
            self.mac_address,
            self.mtu,
            self.mgmt_only,
            self.description,
            self.get_mode_display(),
            self.get_status_display(),
            self.parent_interface.name if self.parent_interface else None,
            self.bridge.name if self.bridge else None,
        )

    def clean(self):
        super().clean()

        # LAG validation
        if self.lag is not None:

            # A LAG interface cannot be its own parent
            if self.lag_id == self.pk:
                raise ValidationError({"lag": "A LAG interface cannot be its own parent."})

            # An interface's LAG must belong to the same device or virtual chassis
            if self.lag.device_id != self.device_id:
                if self.device.virtual_chassis is None:
                    raise ValidationError(
                        {
                            "lag": f"The selected LAG interface ({self.lag}) belongs to a different device ({self.lag.device})."
                        }
                    )
                elif self.lag.device.virtual_chassis_id != self.device.virtual_chassis_id:
                    raise ValidationError(
                        {
                            "lag": (
                                f"The selected LAG interface ({self.lag}) belongs to {self.lag.device}, which is not part "
                                f"of virtual chassis {self.device.virtual_chassis}."
                            )
                        }
                    )

            # A virtual interface cannot have a parent LAG
            if self.type == InterfaceTypeChoices.TYPE_VIRTUAL:
                raise ValidationError({"lag": "Virtual interfaces cannot have a parent LAG interface."})

        # Virtual interfaces cannot be connected
        if getattr(self, "type", None) in NONCONNECTABLE_IFACE_TYPES and (
            self.cable or getattr(self, "circuit_termination", False)
        ):
            raise ValidationError(
                {
                    "type": "Virtual and wireless interfaces cannot be connected to another interface or circuit. "
                    "Disconnect the interface or choose a suitable type."
                }
            )

        # Parent validation
        if self.parent_interface is not None:

            # An interface cannot be its own parent
            if self.parent_interface_id == self.pk:
                raise ValidationError({"parent_interface": "An interface cannot be its own parent."})
            # A physical interface cannot have a parent interface
            if hasattr(self, "type") and self.type != InterfaceTypeChoices.TYPE_VIRTUAL:
                raise ValidationError(
                    {"parent_interface": "Only virtual interfaces may be assigned to a parent interface."}
                )

            # A virtual interface cannot be a parent interface
            if getattr(self.parent_interface, "type", None) == InterfaceTypeChoices.TYPE_VIRTUAL:
                raise ValidationError(
                    {"parent_interface": "Virtual interfaces may not be parents of other interfaces."}
                )

            # An interface's parent must belong to the same device or virtual chassis
            if self.parent_interface.parent != self.parent:
                if getattr(self.parent, "virtual_chassis", None) is None:
                    raise ValidationError(
                        {
                            "parent_interface": f"The selected parent interface ({self.parent_interface}) belongs to a different device "
                            f"({self.parent_interface.parent})."
                        }
                    )
                elif self.parent_interface.parent.virtual_chassis != self.parent.virtual_chassis:
                    raise ValidationError(
                        {
                            "parent_interface": f"The selected parent interface ({self.parent_interface}) belongs to {self.parent_interface.parent}, which "
                            f"is not part of virtual chassis {self.parent.virtual_chassis}."
                        }
                    )

        # Validate untagged VLAN
        if self.untagged_vlan and self.untagged_vlan.site_id not in [self.parent.site_id, None]:
            raise ValidationError(
                {
                    "untagged_vlan": (
                        f"The untagged VLAN ({self.untagged_vlan}) must belong to the same site as the interface's parent "
                        f"device, or it must be global."
                    )
                }
            )

        # Bridge validation
        if self.bridge is not None:

            # An interface cannot be bridged to itself
            if self.bridge_id == self.pk:
                raise ValidationError({"bridge": "An interface cannot be bridged to itself."})

            # A bridged interface belong to the same device or virtual chassis
            if self.bridge.parent.id != self.parent.id:
                if getattr(self.parent, "virtual_chassis", None) is None:
                    raise ValidationError(
                        {
                            "bridge": (
                                f"The selected bridge interface ({self.bridge}) belongs to a different device "
                                f"({self.bridge.parent})."
                            )
                        }
                    )
                elif self.bridge.parent.virtual_chassis_id != self.parent.virtual_chassis_id:
                    raise ValidationError(
                        {
                            "bridge": (
                                f"The selected bridge interface ({self.bridge}) belongs to {self.bridge.parent}, which "
                                f"is not part of virtual chassis {self.parent.virtual_chassis}."
                            )
                        }
                    )

    @property
    def is_connectable(self):
        return self.type not in NONCONNECTABLE_IFACE_TYPES

    @property
    def is_virtual(self):
        return self.type in VIRTUAL_IFACE_TYPES

    @property
    def is_wireless(self):
        return self.type in WIRELESS_IFACE_TYPES

    @property
    def is_lag(self):
        return self.type == InterfaceTypeChoices.TYPE_LAG

    @property
    def count_ipaddresses(self):
        return self.ip_addresses.count()

    @property
    def parent(self):
        return self.device


#
# Pass-through ports
#


@extras_features("cable_terminations", "custom_fields", "custom_validators", "graphql", "relationships", "webhooks")
class FrontPort(CableTermination, ComponentModel):
    """
    A pass-through port on the front of a Device.
    """

    type = models.CharField(max_length=50, choices=PortTypeChoices)
    rear_port = models.ForeignKey(to="dcim.RearPort", on_delete=models.CASCADE, related_name="frontports")
    rear_port_position = models.PositiveSmallIntegerField(
        default=1,
        validators=[
            MinValueValidator(REARPORT_POSITIONS_MIN),
            MaxValueValidator(REARPORT_POSITIONS_MAX),
        ],
    )

    csv_headers = [
        "device",
        "name",
        "label",
        "type",
        "rear_port",
        "rear_port_position",
        "description",
    ]

    class Meta:
        ordering = ("device", "_name")
        unique_together = (
            ("device", "name"),
            ("rear_port", "rear_port_position"),
        )

    def get_absolute_url(self):
        return reverse("dcim:frontport", kwargs={"pk": self.pk})

    def to_csv(self):
        return (
            self.device.identifier,
            self.name,
            self.label,
            self.get_type_display(),
            self.rear_port.name,
            self.rear_port_position,
            self.description,
        )

    def clean(self):
        super().clean()

        # Validate rear port assignment
        if self.rear_port.device != self.device:
            raise ValidationError({"rear_port": f"Rear port ({self.rear_port}) must belong to the same device"})

        # Validate rear port position assignment
        if self.rear_port_position > self.rear_port.positions:
            raise ValidationError(
                {
                    "rear_port_position": f"Invalid rear port position ({self.rear_port_position}): Rear port "
                    f"{self.rear_port.name} has only {self.rear_port.positions} positions"
                }
            )


@extras_features("cable_terminations", "custom_fields", "custom_validators", "graphql", "relationships", "webhooks")
class RearPort(CableTermination, ComponentModel):
    """
    A pass-through port on the rear of a Device.
    """

    type = models.CharField(max_length=50, choices=PortTypeChoices)
    positions = models.PositiveSmallIntegerField(
        default=1,
        validators=[
            MinValueValidator(REARPORT_POSITIONS_MIN),
            MaxValueValidator(REARPORT_POSITIONS_MAX),
        ],
    )

    csv_headers = ["device", "name", "label", "type", "positions", "description"]

    class Meta:
        ordering = ("device", "_name")
        unique_together = ("device", "name")

    def get_absolute_url(self):
        return reverse("dcim:rearport", kwargs={"pk": self.pk})

    def clean(self):
        super().clean()

        # Check that positions count is greater than or equal to the number of associated FrontPorts
        frontport_count = self.frontports.count()
        if self.positions < frontport_count:
            raise ValidationError(
                {
                    "positions": f"The number of positions cannot be less than the number of mapped front ports "
                    f"({frontport_count})"
                }
            )

    def to_csv(self):
        return (
            self.device.identifier,
            self.name,
            self.label,
            self.get_type_display(),
            self.positions,
            self.description,
        )


#
# Device bays
#


@extras_features("custom_fields", "custom_validators", "graphql", "relationships", "webhooks")
class DeviceBay(ComponentModel):
    """
    An empty space within a Device which can house a child device
    """

    installed_device = models.OneToOneField(
        to="dcim.Device",
        on_delete=models.SET_NULL,
        related_name="parent_bay",
        blank=True,
        null=True,
    )

    csv_headers = ["device", "name", "label", "installed_device", "description"]

    class Meta:
        ordering = ("device", "_name")
        unique_together = ("device", "name")

    def get_absolute_url(self):
        return reverse("dcim:devicebay", kwargs={"pk": self.pk})

    def to_csv(self):
        return (
            self.device.identifier,
            self.name,
            self.label,
            self.installed_device.identifier if self.installed_device else None,
            self.description,
        )

    def clean(self):
        super().clean()

        # Validate that the parent Device can have DeviceBays
        if not self.device.device_type.is_parent_device:
            raise ValidationError(f"This type of device ({self.device.device_type}) does not support device bays.")

        # Cannot install a device into itself, obviously
        if self.device == self.installed_device:
            raise ValidationError("Cannot install a device into itself.")

        # Check that the installed device is not already installed elsewhere
        if self.installed_device:
            current_bay = DeviceBay.objects.filter(installed_device=self.installed_device).first()
            if current_bay and current_bay != self:
                raise ValidationError(
                    {
                        "installed_device": f"Cannot install the specified device; device is already installed in {current_bay}"
                    }
                )


#
# Inventory items
#


@extras_features(
    "custom_fields",
    "custom_validators",
    "export_templates",
    "graphql",
    "relationships",
    "webhooks",
)
class InventoryItem(MPTTModel, ComponentModel):
    """
    An InventoryItem represents a serialized piece of hardware within a Device, such as a line card or power supply.
    InventoryItems are used only for inventory purposes.
    """

    parent = TreeForeignKey(
        to="self",
        on_delete=models.CASCADE,
        related_name="child_items",
        blank=True,
        null=True,
        db_index=True,
    )
    manufacturer = models.ForeignKey(
        to="dcim.Manufacturer",
        on_delete=models.PROTECT,
        related_name="inventory_items",
        blank=True,
        null=True,
    )
    part_id = models.CharField(
        max_length=50,
        verbose_name="Part ID",
        blank=True,
        help_text="Manufacturer-assigned part identifier",
    )
    serial = models.CharField(max_length=255, verbose_name="Serial number", blank=True, db_index=True)
    asset_tag = models.CharField(
        max_length=50,
        unique=True,
        blank=True,
        null=True,
        verbose_name="Asset tag",
        help_text="A unique tag used to identify this item",
    )
    discovered = models.BooleanField(default=False, help_text="This item was automatically discovered")

    objects = TreeManager()

    csv_headers = [
        "device",
        "name",
        "label",
        "manufacturer",
        "part_id",
        "serial",
        "asset_tag",
        "discovered",
        "description",
    ]

    class Meta:
        ordering = ("device__id", "parent__id", "_name")
        unique_together = ("device", "parent", "name")

    def get_absolute_url(self):
        return reverse("dcim:inventoryitem", kwargs={"pk": self.pk})

    def to_csv(self):
        return (
            self.device.name or f"{{{self.device.pk}}}",
            self.name,
            self.label,
            self.manufacturer.name if self.manufacturer else None,
            self.part_id,
            self.serial,
            self.asset_tag,
            self.discovered,
            self.description,
        )
