from decimal import Decimal
import re

from django.contrib.contenttypes.fields import GenericForeignKey, GenericRelation
from django.contrib.contenttypes.models import ContentType
from django.core.cache import cache
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models, transaction
from django.db.models import Sum
from django.utils.functional import classproperty

from nautobot.core.constants import CHARFIELD_MAX_LENGTH
from nautobot.core.models.fields import ForeignKeyWithAutoRelatedName, MACAddressCharField, NaturalOrderingField
from nautobot.core.models.generics import BaseModel, PrimaryModel
from nautobot.core.models.ordering import naturalize_interface
from nautobot.core.models.query_functions import CollateAsChar
from nautobot.core.models.tree_queries import TreeModel
from nautobot.core.utils.data import UtilizationData
from nautobot.dcim.choices import (
    ConsolePortTypeChoices,
    InterfaceModeChoices,
    InterfaceRedundancyGroupProtocolChoices,
    InterfaceStatusChoices,
    InterfaceTypeChoices,
    PortTypeChoices,
    PowerFeedPhaseChoices,
    PowerOutletFeedLegChoices,
    PowerOutletTypeChoices,
    PowerPortTypeChoices,
    SubdeviceRoleChoices,
)
from nautobot.dcim.constants import (
    NONCONNECTABLE_IFACE_TYPES,
    REARPORT_POSITIONS_MAX,
    REARPORT_POSITIONS_MIN,
    VIRTUAL_IFACE_TYPES,
    WIRELESS_IFACE_TYPES,
)
from nautobot.dcim.utils import convert_watts_to_va
from nautobot.extras.models import (
    ChangeLoggedModel,
    RelationshipModel,
    RoleField,
    Status,
    StatusField,
)
from nautobot.extras.utils import extras_features

__all__ = (
    "BaseInterface",
    "CableTermination",
    "ConsolePort",
    "ConsoleServerPort",
    "DeviceBay",
    "FrontPort",
    "Interface",
    "InterfaceRedundancyGroup",
    "InterfaceRedundancyGroupAssociation",
    "InventoryItem",
    "ModuleBay",
    "PathEndpoint",
    "PowerOutlet",
    "PowerPort",
    "RearPort",
)


class ComponentModel(PrimaryModel):
    """
    An abstract model inherited by any model which has a parent Device.
    """

    device = ForeignKeyWithAutoRelatedName(to="dcim.Device", on_delete=models.CASCADE)
    name = models.CharField(max_length=CHARFIELD_MAX_LENGTH, db_index=True)
    _name = NaturalOrderingField(target_field="name", max_length=CHARFIELD_MAX_LENGTH, blank=True, db_index=True)
    label = models.CharField(max_length=CHARFIELD_MAX_LENGTH, blank=True, help_text="Physical label")
    description = models.CharField(max_length=CHARFIELD_MAX_LENGTH, blank=True)

    natural_key_field_names = ["device", "name"]

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
        if "related_object" in kwargs:
            return super().to_objectchange(action, **kwargs)

        # Annotate the parent Device
        try:
            device = self.device
        except ObjectDoesNotExist:
            # The parent Device has already been deleted
            device = None

        return super().to_objectchange(action, related_object=device, **kwargs)

    @property
    def parent(self):
        return self.device


class ModularComponentModel(ComponentModel):
    device = ForeignKeyWithAutoRelatedName(
        to="dcim.Device",
        on_delete=models.CASCADE,
        blank=True,
        null=True,
    )
    module = ForeignKeyWithAutoRelatedName(
        to="dcim.Module",
        on_delete=models.CASCADE,
        blank=True,
        null=True,
    )

    natural_key_field_names = ["device", "module", "name"]

    class Meta:
        abstract = True
        ordering = ("device", "module__id", "_name")  # Module.ordering is complex/expensive so don't order by module
        constraints = [
            models.UniqueConstraint(
                fields=("device", "name"),
                name="%(app_label)s_%(class)s_device_name_unique",
            ),
            models.UniqueConstraint(
                fields=("module", "name"),
                name="%(app_label)s_%(class)s_module_name_unique",
            ),
        ]

    @property
    def parent(self):
        """Device that this component belongs to, walking up module inheritance if necessary."""
        return self.module.device if self.module else self.device  # pylint: disable=no-member

    def render_name_template(self, save=False):
        """
        Replace the {module}, {module.parent}, {module.parent.parent}, etc. variables in the name
        field with the actual module bay positions.

        Args:
            save (bool, optional): If True, save the object after updating the name field. Defaults to False.

        If a module bay position is blank, it will be skipped and the parents will be checked until a non-blank
        position is found. If all parent module bays are exhausted, the variable is left as-is.

        Example:
            - Device (name="Device 1")
              - ModuleBay (position="A")
                - Module
                  - ModuleBay (position="")
                    - Module
                      - Interface (name="{module}{module.parent}")

            The deeply nested interface would be named "A{module.parent}" after calling this method.
        """
        if self.module and self.module.parent_module_bay and "{module" in self.name:  # pylint: disable=no-member
            name = ""
            module_bay = self.module.parent_module_bay  # pylint: disable=no-member
            positions = []
            while module_bay is not None:
                position = getattr(module_bay, "position", None)
                if position:
                    positions.append(position)
                module_bay = getattr(getattr(module_bay, "parent_module", None), "parent_module_bay", None)
            for part in re.split(r"({module(?:\.parent)*})", self.name):
                if re.fullmatch(r"{module(\.parent)*}", part):
                    depth = part.count(".parent")
                    if depth < len(positions):
                        name += positions[depth]
                        continue
                name += part
            if self.name != name:
                self.name = name
                if save:
                    self.save(update_fields=["_name", "name"])

    render_name_template.alters_data = True

    def to_objectchange(self, action, **kwargs):
        """
        Return a new ObjectChange with the `related_object` pinned to the parent `device` or `module`.
        """
        if "related_object" in kwargs:
            return super().to_objectchange(action, **kwargs)

        # Annotate the parent
        try:
            parent = self.device if self.device else self.module
        except ObjectDoesNotExist:
            # The parent may have already been deleted
            parent = None

        return super().to_objectchange(action, related_object=parent, **kwargs)

    def clean(self):
        super().clean()

        # Validate that a Device or Module is set, but not both
        if self.device and self.module:
            raise ValidationError("Only one of device or module must be set")

        if not (self.device or self.module):
            raise ValidationError("Either device or module must be set")


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

    @property
    def parent(self):
        """
        Convenience property - used in template rendering among other cases.

        Could be a Device, a Circuit, a PowerPanel, etc.
        """
        raise NotImplementedError("Class didn't implement 'parent' property")


class PathEndpoint(models.Model):
    """
    An abstract model inherited by any CableTermination subclass which represents the end of a CablePath; specifically,
    these include ConsolePort, ConsoleServerPort, PowerPort, PowerOutlet, Interface, PowerFeed, and CircuitTermination.

    `_path` references the CablePath originating from this instance, if any. It is set or cleared by the receivers in
    dcim.signals in response to changes in the cable path, and complements the `origin` GenericForeignKey field on the
    CablePath model. `_path` should not be accessed directly; rather, use the `path` property.

    `connected_endpoint()` is a convenience method for returning the destination of the associated CablePath, if any.
    """

    _path = ForeignKeyWithAutoRelatedName(
        to="dcim.CablePath",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )

    class Meta:
        abstract = True

    def trace(self):
        if self._path is None:
            return []

        # Construct the complete path
        path = [self, *self._path.get_path()]  # pylint: disable=no-member
        while (len(path) + 1) % 3:
            # Pad to ensure we have complete three-tuples (e.g. for paths that end at a RearPort)
            path.append(None)
        path.append(self._path.destination)  # pylint: disable=no-member

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
    "custom_links",
    "custom_validators",
    "export_templates",
    "graphql",
    "webhooks",
)
class ConsolePort(ModularComponentModel, CableTermination, PathEndpoint):
    """
    A physical console port within a Device or Module. ConsolePorts connect to ConsoleServerPorts.
    """

    type = models.CharField(
        max_length=50,
        choices=ConsolePortTypeChoices,
        blank=True,
        help_text="Physical port type",
    )


#
# Console server ports
#


@extras_features("custom_links", "cable_terminations", "custom_validators", "graphql", "webhooks")
class ConsoleServerPort(ModularComponentModel, CableTermination, PathEndpoint):
    """
    A physical port within a Device or Module (typically a designated console server) which provides access to ConsolePorts.
    """

    type = models.CharField(
        max_length=50,
        choices=ConsolePortTypeChoices,
        blank=True,
        help_text="Physical port type",
    )


#
# Power ports
#


@extras_features(
    "cable_terminations",
    "custom_links",
    "custom_validators",
    "export_templates",
    "graphql",
    "webhooks",
)
class PowerPort(ModularComponentModel, CableTermination, PathEndpoint):
    """
    A physical power supply (intake) port within a Device or Module. PowerPorts connect to PowerOutlets.
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
    power_factor = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        default=Decimal("0.95"),
        validators=[MinValueValidator(Decimal("0.01")), MaxValueValidator(Decimal("1.00"))],
        help_text="Power factor (0.01-1.00) for converting between watts (W) and volt-amps (VA). Defaults to 0.95.",
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

            # Convert watts to VA for aggregated values
            allocated_va = convert_watts_to_va(utilization["allocated_draw_total"], self.power_factor)
            maximum_va = convert_watts_to_va(utilization["maximum_draw_total"], self.power_factor)

            ret = {
                "allocated": allocated_va,
                "maximum": maximum_va,
                "outlet_count": len(outlet_ids),
                "legs": [],
                "utilization_data": UtilizationData(
                    numerator=allocated_va,
                    denominator=maximum_va,
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

                    # Convert watts to VA for leg values
                    leg_allocated_va = convert_watts_to_va(utilization["allocated_draw_total"], self.power_factor)
                    leg_maximum_va = convert_watts_to_va(utilization["maximum_draw_total"], self.power_factor)

                    ret["legs"].append(
                        {
                            "name": leg_name,
                            "allocated": leg_allocated_va,
                            "maximum": leg_maximum_va,
                            "outlet_count": len(outlet_ids),
                        }
                    )

            return ret

        if self.connected_endpoint and hasattr(self.connected_endpoint, "available_power"):
            denominator = self.connected_endpoint.available_power or 0
        else:
            denominator = 0

        # Convert administratively defined values from watts to VA
        allocated_va = convert_watts_to_va(self.allocated_draw, self.power_factor)
        maximum_va = convert_watts_to_va(self.maximum_draw, self.power_factor)

        return {
            "allocated": allocated_va,
            "maximum": maximum_va,
            "outlet_count": PowerOutlet.objects.filter(power_port=self).count(),
            "legs": [],
            "utilization_data": UtilizationData(numerator=allocated_va, denominator=denominator),
        }


#
# Power outlets
#


@extras_features("cable_terminations", "custom_links", "custom_validators", "graphql", "webhooks")
class PowerOutlet(ModularComponentModel, CableTermination, PathEndpoint):
    """
    A physical power outlet (output) within a Device or Module which provides power to a PowerPort.
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
        related_name="power_outlets",
    )
    # todoindex:
    feed_leg = models.CharField(
        max_length=50,
        choices=PowerOutletFeedLegChoices,
        blank=True,
        help_text="Phase (for three-phase feeds)",
    )

    def clean(self):
        super().clean()

        # Validate power port assignment
        if self.power_port and self.parent and self.power_port.parent != self.parent:
            raise ValidationError(f"Parent power port ({self.power_port}) must belong to the same device")


#
# Interfaces
#


class BaseInterface(RelationshipModel):
    """
    Abstract base class for fields shared by dcim.Interface and virtualization.VMInterface.
    """

    status = StatusField(blank=False, null=False)
    enabled = models.BooleanField(default=True)
    mac_address = MACAddressCharField(blank=True, default="", verbose_name="MAC Address")
    mtu = models.PositiveIntegerField(
        blank=True,
        null=True,
        # 3.0 TODO: 65536 != constants.INTERFACE_MTU_MAX... need to reconcile this
        validators=[MinValueValidator(1), MaxValueValidator(65536)],
        verbose_name="MTU",
    )
    role = RoleField(blank=True, null=True)
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
        if not self.mode and self.untagged_vlan is not None:  # pylint: disable=no-member  # Intf/VMIntf both have untagged_vlan
            raise ValidationError({"untagged_vlan": "Mode must be set when specifying untagged_vlan"})

    def save(self, *args, **kwargs):
        if not self.status:
            query = Status.objects.get_for_model(self)
            try:
                status_as_dict = InterfaceStatusChoices.as_dict()
                status = query.get(name=status_as_dict.get(InterfaceStatusChoices.STATUS_ACTIVE))
            except Status.DoesNotExist:
                raise ValidationError({"status": "Default status 'active' does not exist"})
            self.status = status

        # Only "tagged" interfaces may have tagged VLANs assigned. ("tagged all" implies all VLANs are assigned.)
        if self.present_in_database and self.mode != InterfaceModeChoices.MODE_TAGGED:  # pylint: disable=no-member
            self.tagged_vlans.clear()  # pylint: disable=no-member  # Intf/VMIntf both have tagged_vlans

        return super().save(*args, **kwargs)


@extras_features(
    "cable_terminations",
    "custom_links",
    "custom_validators",
    "export_templates",
    "graphql",
    "statuses",
    "webhooks",
)
class Interface(ModularComponentModel, CableTermination, PathEndpoint, BaseInterface):
    """
    A network interface within a Device or Module. A physical Interface can connect to exactly one other Interface.
    """

    # Override ComponentModel._name to specify naturalize_interface function
    _name = NaturalOrderingField(
        target_field="name",
        naturalize_function=naturalize_interface,
        max_length=CHARFIELD_MAX_LENGTH,
        blank=True,
        db_index=True,
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
    vrf = models.ForeignKey(
        to="ipam.VRF",
        related_name="interfaces",
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
    )
    ip_addresses = models.ManyToManyField(
        to="ipam.IPAddress",
        through="ipam.IPAddressToInterface",
        related_name="interfaces",
        blank=True,
        verbose_name="IP Addresses",
    )

    class Meta(ModularComponentModel.Meta):
        ordering = ("device", "module__id", CollateAsChar("_name"))  # Module.ordering is complex; don't order by module

    def clean(self):
        super().clean()

        # VRF validation
        if self.vrf and self.parent and self.vrf not in self.parent.vrfs.all():
            # TODO(jathan): Or maybe we automatically add the VRF to the device?
            raise ValidationError({"vrf": "VRF must be assigned to same Device."})

        # LAG validation
        if self.lag is not None:
            # A LAG interface cannot be its own parent
            if self.lag_id == self.pk:
                raise ValidationError({"lag": "A LAG interface cannot be its own parent."})

            # An interface's LAG must belong to the same device or virtual chassis
            if self.parent and self.lag.parent != self.parent:
                if self.lag.parent is None:
                    raise ValidationError(
                        {"lag": f"The selected LAG interface ({self.lag}) does not belong to a device."}
                    )
                elif self.parent.virtual_chassis is None:
                    raise ValidationError(
                        {
                            "lag": f"The selected LAG interface ({self.lag}) belongs to a different device ({self.lag.parent})."
                        }
                    )
                elif self.lag.parent.virtual_chassis_id != self.parent.virtual_chassis_id:
                    raise ValidationError(
                        {
                            "lag": (
                                f"The selected LAG interface ({self.lag}) belongs to {self.lag.parent}, which is not part "
                                f"of virtual chassis {self.parent.virtual_chassis}."
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

            # An interface's parent must belong to the same device or virtual chassis
            if self.parent and self.parent_interface.parent != self.parent:  # pylint: disable=no-member
                if getattr(self.parent, "virtual_chassis", None) is None:
                    raise ValidationError(
                        {  # pylint: disable=no-member  # false positive on parent_interface.parent
                            "parent_interface": f"The selected parent interface ({self.parent_interface}) belongs "
                            f"to a different device ({self.parent_interface.parent})."
                        }
                    )
                elif self.parent_interface.parent.virtual_chassis != self.parent.virtual_chassis:  # pylint: disable=no-member
                    raise ValidationError(
                        {  # pylint: disable=no-member  # false positive on parent_interface.parent
                            "parent_interface": f"The selected parent interface ({self.parent_interface}) belongs "
                            f"to {self.parent_interface.parent}, which "
                            f"is not part of virtual chassis {self.parent.virtual_chassis}."
                        }
                    )

        # Validate untagged VLAN
        location = self.parent.location if self.parent is not None else None
        if location:
            location_ids = location.ancestors(include_self=True).values_list("id", flat=True)
        else:
            location_ids = []
        if (
            self.untagged_vlan
            and self.untagged_vlan.locations.exists()
            and self.parent
            and not self.untagged_vlan.locations.filter(pk__in=location_ids).exists()
        ):
            raise ValidationError(
                {
                    "untagged_vlan": (
                        f"The untagged VLAN ({self.untagged_vlan}) must have a common location as the interface's parent "
                        f"device, or is in one of the parents of the interface's parent device's location, or it must be global."
                    )
                }
            )

        # Bridge validation
        if self.bridge is not None:
            # An interface cannot be bridged to itself
            if self.bridge_id == self.pk:
                raise ValidationError({"bridge": "An interface cannot be bridged to itself."})

            # A bridged interface belong to the same device or virtual chassis
            if self.parent and self.bridge.parent != self.parent:  # pylint: disable=no-member
                if getattr(self.parent, "virtual_chassis", None) is None:
                    raise ValidationError(
                        {
                            "bridge": (
                                # pylint: disable=no-member  # false positive on bridge.parent
                                f"The selected bridge interface ({self.bridge}) belongs to a different device "
                                f"({self.bridge.parent})."
                            )
                        }
                    )
                elif self.bridge.parent.virtual_chassis_id != self.parent.virtual_chassis_id:  # pylint: disable=no-member
                    raise ValidationError(
                        {
                            "bridge": (
                                f"The selected bridge interface ({self.bridge}) belongs to {self.bridge.parent}, which "  # pylint: disable=no-member
                                f"is not part of virtual chassis {self.parent.virtual_chassis}."
                            )
                        }
                    )

    def add_ip_addresses(
        self,
        ip_addresses,
        is_source=False,
        is_destination=False,
        is_default=False,
        is_preferred=False,
        is_primary=False,
        is_secondary=False,
        is_standby=False,
    ):
        """Add one or more IPAddress instances to this interface's `ip_addresses` many-to-many relationship.

        Args:
            ip_addresses (:obj:`list` or `IPAddress`): Instance of `nautobot.ipam.models.IPAddress` or list of `IPAddress` instances.
            is_source (bool, optional): Is source address. Defaults to False.
            is_destination (bool, optional): Is destination address. Defaults to False.
            is_default (bool, optional): Is default address. Defaults to False.
            is_preferred (bool, optional): Is preferred address. Defaults to False.
            is_primary (bool, optional): Is primary address. Defaults to False.
            is_secondary (bool, optional): Is secondary address. Defaults to False.
            is_standby (bool, optional): Is standby address. Defaults to False.

        Returns:
            Number of instances added.
        """
        if not isinstance(ip_addresses, (tuple, list)):
            ip_addresses = [ip_addresses]
        with transaction.atomic():
            for ip in ip_addresses:
                instance = self.ip_addresses.through(
                    ip_address=ip,
                    interface=self,
                    is_source=is_source,
                    is_destination=is_destination,
                    is_default=is_default,
                    is_preferred=is_preferred,
                    is_primary=is_primary,
                    is_secondary=is_secondary,
                    is_standby=is_standby,
                )
                instance.validated_save()
        return len(ip_addresses)

    add_ip_addresses.alters_data = True

    def remove_ip_addresses(self, ip_addresses):
        """Remove one or more IPAddress instances from this interface's `ip_addresses` many-to-many relationship.

        Args:
            ip_addresses (:obj:`list` or `IPAddress`): Instance of `nautobot.ipam.models.IPAddress` or list of `IPAddress` instances.

        Returns:
            Number of instances removed.
        """
        count = 0
        if not isinstance(ip_addresses, (tuple, list)):
            ip_addresses = [ip_addresses]
        with transaction.atomic():
            for ip in ip_addresses:
                qs = self.ip_addresses.through.objects.filter(ip_address=ip, interface=self)
                deleted_count, _ = qs.delete()
                count += deleted_count
        return count

    remove_ip_addresses.alters_data = True

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
    def ip_address_count(self):
        return self.ip_addresses.count()


@extras_features(
    "custom_fields",
    "custom_links",
    "custom_validators",
    "export_templates",
    "graphql",
    "relationships",
    "statuses",
    "webhooks",
)
class InterfaceRedundancyGroup(PrimaryModel):  # pylint: disable=too-many-ancestors
    """
    A collection of Interfaces that supply a redundancy group for protocols like HSRP/VRRP.
    """

    name = models.CharField(max_length=CHARFIELD_MAX_LENGTH, unique=True)
    status = StatusField(blank=False, null=False)
    # Preemptively model 2.0 behavior by making `created` a DateTimeField rather than a DateField.
    created = models.DateTimeField(auto_now_add=True)
    description = models.CharField(
        max_length=CHARFIELD_MAX_LENGTH,
        blank=True,
    )
    interfaces = models.ManyToManyField(
        to="dcim.Interface",
        through="dcim.InterfaceRedundancyGroupAssociation",
        related_name="interface_redundancy_groups",
        blank=True,
    )
    protocol = models.CharField(
        max_length=50,
        blank=True,
        choices=InterfaceRedundancyGroupProtocolChoices,
        verbose_name="Redundancy Protocol",
    )
    protocol_group_id = models.CharField(
        max_length=CHARFIELD_MAX_LENGTH,
        blank=True,
    )
    secrets_group = models.ForeignKey(
        to="extras.SecretsGroup",
        on_delete=models.SET_NULL,
        default=None,
        blank=True,
        null=True,
    )
    virtual_ip = models.ForeignKey(
        to="ipam.IPAddress",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="interface_redundancy_groups",
    )

    class Meta:
        """Meta class."""

        ordering = ["name"]

    def __str__(self):
        """Return a string representation of the instance."""
        return self.name

    def add_interface(self, interface, priority):
        """
        Add an interface including `priority`.

        :param interface:
            Interface instance
        :param priority:
            Integer priority used by redundancy protocol
        """
        instance = self.interfaces.through(
            interface_redundancy_group=self,
            interface=interface,
            priority=priority,
        )
        return instance.validated_save()

    add_interface.alters_data = True

    def remove_interface(self, interface):
        """
        Remove an interface.

        :param interface:
            Interface instance
        """
        instance = self.interfaces.through.objects.get(
            interface_redundancy_group=self,
            interface=interface,
        )
        return instance.delete()

    remove_interface.alters_data = True


@extras_features("graphql")
class InterfaceRedundancyGroupAssociation(BaseModel, ChangeLoggedModel):
    """Intermediary model for associating Interface(s) to InterfaceRedundancyGroup(s)."""

    interface_redundancy_group = models.ForeignKey(
        to="dcim.InterfaceRedundancyGroup",
        on_delete=models.CASCADE,
        related_name="interface_redundancy_group_associations",
    )
    interface = models.ForeignKey(
        to="dcim.Interface",
        on_delete=models.CASCADE,
        related_name="interface_redundancy_group_associations",
    )
    priority = models.PositiveSmallIntegerField()
    is_metadata_associable_model = False

    class Meta:
        """Meta class."""

        unique_together = (("interface_redundancy_group", "interface"),)
        ordering = ("interface_redundancy_group", "-priority")

    def __str__(self):
        """Return a string representation of the instance."""
        return f"{self.interface_redundancy_group}: {self.interface.device or self.interface.module} {self.interface}: {self.priority}"


#
# Pass-through ports
#


@extras_features("cable_terminations", "custom_links", "custom_validators", "graphql", "webhooks")
class FrontPort(ModularComponentModel, CableTermination):
    """
    A pass-through port on the front of a Device or Module.
    """

    type = models.CharField(max_length=50, choices=PortTypeChoices)
    rear_port = models.ForeignKey(to="dcim.RearPort", on_delete=models.CASCADE, related_name="front_ports")
    rear_port_position = models.PositiveSmallIntegerField(
        default=1,
        validators=[
            MinValueValidator(REARPORT_POSITIONS_MIN),
            MaxValueValidator(REARPORT_POSITIONS_MAX),
        ],
    )

    natural_key_field_names = ["device", "module", "name", "rear_port", "rear_port_position"]

    class Meta(ModularComponentModel.Meta):
        constraints = [
            *ModularComponentModel.Meta.constraints,
            models.UniqueConstraint(
                fields=("rear_port", "rear_port_position"),
                name="dcim_frontport_rear_port_position_unique",
            ),
        ]

    def clean(self):
        super().clean()

        # Validate rear port assignment
        if self.parent and self.rear_port.parent != self.parent:
            raise ValidationError({"rear_port": f"Rear port ({self.rear_port}) must belong to the same device"})

        # Validate rear port position assignment
        if self.rear_port_position > self.rear_port.positions:
            raise ValidationError(
                {
                    "rear_port_position": f"Invalid rear port position ({self.rear_port_position}): Rear port "
                    f"{self.rear_port.name} has only {self.rear_port.positions} positions"
                }
            )


@extras_features("cable_terminations", "custom_links", "custom_validators", "graphql", "webhooks")
class RearPort(ModularComponentModel, CableTermination):
    """
    A pass-through port on the rear of a Device or Module.
    """

    type = models.CharField(max_length=50, choices=PortTypeChoices)
    positions = models.PositiveSmallIntegerField(
        default=1,
        validators=[
            MinValueValidator(REARPORT_POSITIONS_MIN),
            MaxValueValidator(REARPORT_POSITIONS_MAX),
        ],
    )

    def clean(self):
        super().clean()

        # Check that positions count is greater than or equal to the number of associated FrontPorts
        front_port_count = self.front_ports.count()
        if self.positions < front_port_count:
            raise ValidationError(
                {
                    "positions": f"The number of positions cannot be less than the number of mapped front ports "
                    f"({front_port_count})"
                }
            )


#
# Device bays
#


@extras_features("custom_links", "custom_validators", "graphql", "webhooks")
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

    class Meta:
        ordering = ("device", "_name")
        unique_together = ("device", "name")

    def clean(self):
        super().clean()

        # Validate that the parent Device can have DeviceBays
        if not self.device.device_type.is_parent_device:  # pylint: disable=no-member
            raise ValidationError(f"This type of device ({self.device.device_type}) does not support device bays.")  # pylint: disable=no-member

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
            if self.installed_device.device_type.subdevice_role != SubdeviceRoleChoices.ROLE_CHILD:
                raise ValidationError(
                    {
                        "installed_device": f'Cannot install device "{self.installed_device}"; device-type "{self.installed_device.device_type}" subdevice_role is not "child".'
                    }
                )


#
# Inventory items
#


@extras_features(
    "custom_links",
    "custom_validators",
    "export_templates",
    "graphql",
    "webhooks",
)
class InventoryItem(TreeModel, ComponentModel):
    """
    An InventoryItem represents a serialized piece of hardware within a Device, such as a line card or power supply.
    InventoryItems are used only for inventory purposes.
    """

    manufacturer = models.ForeignKey(
        to="dcim.Manufacturer",
        on_delete=models.PROTECT,
        related_name="inventory_items",
        blank=True,
        null=True,
    )
    part_id = models.CharField(
        max_length=CHARFIELD_MAX_LENGTH,
        verbose_name="Part ID",
        blank=True,
        help_text="Manufacturer-assigned part identifier",
    )
    serial = models.CharField(max_length=CHARFIELD_MAX_LENGTH, verbose_name="Serial number", blank=True, db_index=True)
    asset_tag = models.CharField(
        max_length=CHARFIELD_MAX_LENGTH,
        unique=True,
        blank=True,
        null=True,
        verbose_name="Asset tag",
        help_text="A unique tag used to identify this item",
    )
    discovered = models.BooleanField(default=False, help_text="This item was automatically discovered")
    software_version = models.ForeignKey(
        to="dcim.SoftwareVersion",
        on_delete=models.PROTECT,
        related_name="inventory_items",
        blank=True,
        null=True,
        verbose_name="Software Version",
        help_text="The software version installed on this inventory item",
    )
    software_image_files = models.ManyToManyField(
        to="dcim.SoftwareImageFile",
        related_name="inventory_items",
        blank=True,
        verbose_name="Software Image Files",
        help_text="Override the software image files associated with the software version for this inventory item",
    )

    class Meta:
        ordering = ("_name",)
        unique_together = ("device", "parent", "name")

    @classproperty  # https://github.com/PyCQA/pylint-django/issues/240
    def natural_key_field_lookups(cls):  # pylint: disable=no-self-argument
        """
        Due to the recursive nature of InventoryItem.unique_together, we need a custom implementation of this property.

        For the time being we just use the PK as a natural key.
        """
        return ["pk"]


@extras_features(
    "custom_links",
    "custom_validators",
    "export_templates",
    "graphql",
    "webhooks",
)
class ModuleBay(PrimaryModel):
    """
    A slot in a Device or Module which can contain Modules.
    """

    parent_device = models.ForeignKey(
        to="dcim.Device",
        on_delete=models.CASCADE,
        related_name="module_bays",
        blank=True,
        null=True,
    )
    parent_module = models.ForeignKey(
        to="dcim.Module",
        on_delete=models.CASCADE,
        related_name="module_bays",
        blank=True,
        null=True,
    )
    module_family = models.ForeignKey(
        to="dcim.ModuleFamily",
        on_delete=models.PROTECT,
        related_name="module_bays",
        blank=True,
        null=True,
        help_text="Module family that can be installed in this bay",
    )
    requires_first_party_modules = models.BooleanField(
        default=False,
        help_text="This bay will only accept modules from the same manufacturer as the parent device or module",
    )
    name = models.CharField(max_length=CHARFIELD_MAX_LENGTH, db_index=True)
    _name = NaturalOrderingField(target_field="name", max_length=CHARFIELD_MAX_LENGTH, blank=True, db_index=True)
    position = models.CharField(
        blank=True,
        max_length=CHARFIELD_MAX_LENGTH,
        help_text="The position of the module bay within the parent device/module",
    )
    label = models.CharField(max_length=CHARFIELD_MAX_LENGTH, blank=True, help_text="Physical label")
    description = models.CharField(max_length=CHARFIELD_MAX_LENGTH, blank=True)

    clone_fields = ["parent_device", "parent_module", "module_family", "requires_first_party_modules"]

    # The recursive nature of this model combined with the fact that it can be a child of a
    # device or location makes our natural key implementation unusable, so just use the pk
    natural_key_field_names = ["pk"]

    class Meta:
        # TODO: Ordering by parent_module.id is not correct but prevents an infinite loop
        ordering = (
            "parent_device",
            "parent_module__id",
            "_name",
        )
        constraints = [
            models.UniqueConstraint(
                fields=["parent_device", "name"],
                name="dcim_modulebay_parent_device_name_unique",
            ),
            models.UniqueConstraint(
                fields=["parent_module", "name"],
                name="dcim_modulebay_parent_module_name_unique",
            ),
        ]

    @property
    def parent(self):
        """Walk up parent chain to find the Device that this ModuleBay is installed in, if one exists."""
        return self.parent_module.device if self.parent_module else self.parent_device

    def __str__(self):
        if self.parent_device is not None:
            return f"{self.parent_device} ({self.name})"
        else:
            return f"{self.parent_module} ({self.name})"

    @property
    def display(self):
        if self.parent_device is not None:
            return f"{self.parent_device.display} ({self.name})"
        else:
            return f"{self.parent_module.display} ({self.name})"

    def to_objectchange(self, action, **kwargs):
        """
        Return a new ObjectChange with the `related_object` pinned to the parent `device` or `module`.
        """
        # Annotate the parent
        try:
            parent = self.parent
        except ObjectDoesNotExist:
            # The parent has already been deleted
            parent = None

        return super().to_objectchange(action, related_object=parent, **kwargs)

    def clean(self):
        super().clean()

        # Validate that a Device or Module is set, but not both
        if self.parent_device and self.parent_module:
            raise ValidationError("Only one of parent_device or parent_module must be set")

        if not (self.parent_device or self.parent_module):
            raise ValidationError("Either parent_device or parent_module must be set")

        # Populate the position field with the name of the module bay if it is not supplied by the user.

        if not self.position:
            self.position = self.name

    clean.alters_data = True

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)

        if self.parent_device is not None:
            # Set the has_module_bays cache key on the parent device - see Device.has_module_bays()
            cache.set(f"nautobot.dcim.device.{self.parent_device.pk}.has_module_bays", True, timeout=5)
