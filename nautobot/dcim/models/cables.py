import logging
from collections import defaultdict

from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.db import models
from django.db.models import Sum
from django.urls import reverse
from django.utils.functional import classproperty

from nautobot.dcim.choices import CableLengthUnitChoices, CableTypeChoices
from nautobot.dcim.constants import CABLE_TERMINATION_MODELS, COMPATIBLE_TERMINATION_TYPES, NONCONNECTABLE_IFACE_TYPES

from nautobot.dcim.fields import JSONPathField
from nautobot.dcim.utils import (
    decompile_path_node,
    object_to_path_node,
    path_node_to_object,
)
from nautobot.extras.models import Status, StatusModel
from nautobot.extras.utils import extras_features
from nautobot.core.models.generics import BaseModel, PrimaryModel
from nautobot.utilities.fields import ColorField
from nautobot.utilities.utils import to_meters
from .devices import Device
from .device_components import FrontPort, RearPort

__all__ = (
    "Cable",
    "CablePath",
)

logger = logging.getLogger(__name__)


#
# Cables
#


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
class Cable(PrimaryModel, StatusModel):
    """
    A physical connection between two endpoints.
    """

    termination_a_type = models.ForeignKey(
        to=ContentType,
        limit_choices_to=CABLE_TERMINATION_MODELS,
        on_delete=models.PROTECT,
        related_name="+",
    )
    termination_a_id = models.UUIDField()
    termination_a = GenericForeignKey(ct_field="termination_a_type", fk_field="termination_a_id")
    termination_b_type = models.ForeignKey(
        to=ContentType,
        limit_choices_to=CABLE_TERMINATION_MODELS,
        on_delete=models.PROTECT,
        related_name="+",
    )
    termination_b_id = models.UUIDField()
    termination_b = GenericForeignKey(ct_field="termination_b_type", fk_field="termination_b_id")
    type = models.CharField(max_length=50, choices=CableTypeChoices, blank=True)
    label = models.CharField(max_length=100, blank=True)
    color = ColorField(blank=True)
    length = models.PositiveSmallIntegerField(blank=True, null=True)
    length_unit = models.CharField(
        max_length=50,
        choices=CableLengthUnitChoices,
        blank=True,
    )
    # Stores the normalized length (in meters) for database ordering
    _abs_length = models.DecimalField(max_digits=10, decimal_places=4, blank=True, null=True)
    # Cache the associated device (where applicable) for the A and B terminations. This enables filtering of Cables by
    # their associated Devices.
    _termination_a_device = models.ForeignKey(
        to=Device, on_delete=models.CASCADE, related_name="+", blank=True, null=True
    )
    _termination_b_device = models.ForeignKey(
        to=Device, on_delete=models.CASCADE, related_name="+", blank=True, null=True
    )

    csv_headers = [
        "termination_a_type",
        "termination_a_id",
        "termination_b_type",
        "termination_b_id",
        "type",
        "status",
        "label",
        "color",
        "length",
        "length_unit",
    ]

    class Meta:
        ordering = [
            "termination_a_type",
            "termination_a_id",
            "termination_b_type",
            "termination_b_id",
        ]
        unique_together = (
            ("termination_a_type", "termination_a_id"),
            ("termination_b_type", "termination_b_id"),
        )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # A copy of the PK to be used by __str__ in case the object is deleted
        self._pk = self.pk

        if self.present_in_database:
            # Cache the original status so we can check later if it's been changed
            self._orig_status = self.status
        else:
            self._orig_status = None

    def __str__(self):
        pk = self.pk or self._pk
        return self.label or f"#{pk}"

    def get_absolute_url(self):
        return reverse("dcim:cable", args=[self.pk])

    @classproperty  # https://github.com/PyCQA/pylint-django/issues/240
    def STATUS_CONNECTED(cls):  # pylint: disable=no-self-argument
        """Return a cached "connected" `Status` object for later reference."""
        if getattr(cls, "__status_connected", None) is None:
            try:
                cls.__status_connected = Status.objects.get_for_model(Cable).get(slug="connected")
            except Status.DoesNotExist:
                logger.warning("Status 'connected' not found for dcim.cable")
                return None

        return cls.__status_connected

    def clean(self):
        super().clean()

        # We import this in this method due to circular importing issues.
        from nautobot.circuits.models import CircuitTermination

        # Validate that termination A exists
        if not hasattr(self, "termination_a_type"):
            raise ValidationError("Termination A type has not been specified")
        try:
            self.termination_a_type.model_class().objects.get(pk=self.termination_a_id)
        except ObjectDoesNotExist:
            raise ValidationError({"termination_a": f"Invalid ID for type {self.termination_a_type}"})

        # Validate that termination B exists
        if not hasattr(self, "termination_b_type"):
            raise ValidationError("Termination B type has not been specified")
        try:
            self.termination_b_type.model_class().objects.get(pk=self.termination_b_id)
        except ObjectDoesNotExist:
            raise ValidationError({"termination_b": f"Invalid ID for type {self.termination_b_type}"})

        # If editing an existing Cable instance, check that neither termination has been modified.
        if self.present_in_database:
            err_msg = "Cable termination points may not be modified. Delete and recreate the cable instead."

            existing_obj = Cable.objects.get(pk=self.pk)

            if (
                self.termination_a_type_id != existing_obj.termination_a_type_id
                or self.termination_a_id != existing_obj.termination_a_id
            ):
                raise ValidationError({"termination_a": err_msg})
            if (
                self.termination_b_type_id != existing_obj.termination_b_type_id
                or self.termination_b_id != existing_obj.termination_b_id
            ):
                raise ValidationError({"termination_b": err_msg})

        type_a = self.termination_a_type.model
        type_b = self.termination_b_type.model

        # Validate interface types
        if type_a == "interface" and self.termination_a.type in NONCONNECTABLE_IFACE_TYPES:
            raise ValidationError(
                {
                    "termination_a_id": f"Cables cannot be terminated to {self.termination_a.get_type_display()} interfaces"
                }
            )
        if type_b == "interface" and self.termination_b.type in NONCONNECTABLE_IFACE_TYPES:
            raise ValidationError(
                {
                    "termination_b_id": f"Cables cannot be terminated to {self.termination_b.get_type_display()} interfaces"
                }
            )

        # Check that termination types are compatible
        if type_b not in COMPATIBLE_TERMINATION_TYPES.get(type_a):
            raise ValidationError(
                f"Incompatible termination types: {self.termination_a_type} and {self.termination_b_type}"
            )

        # Check that two connected RearPorts have the same number of positions (if both are >1)
        if isinstance(self.termination_a, RearPort) and isinstance(self.termination_b, RearPort):
            if self.termination_a.positions > 1 and self.termination_b.positions > 1:
                if self.termination_a.positions != self.termination_b.positions:
                    raise ValidationError(
                        f"{self.termination_a} has {self.termination_a.positions} position(s) but "
                        f"{self.termination_b} has {self.termination_b.positions}. "
                        f"Both terminations must have the same number of positions (if greater than one)."
                    )

        # A termination point cannot be connected to itself
        if self.termination_a == self.termination_b:
            raise ValidationError(f"Cannot connect {self.termination_a_type} to itself")

        # A front port cannot be connected to its corresponding rear port
        if (
            type_a in ["frontport", "rearport"]
            and type_b in ["frontport", "rearport"]
            and (
                getattr(self.termination_a, "rear_port", None) == self.termination_b
                or getattr(self.termination_b, "rear_port", None) == self.termination_a
            )
        ):
            raise ValidationError("A front port cannot be connected to it corresponding rear port")

        # A CircuitTermination attached to a Provider Network cannot have a Cable
        if isinstance(self.termination_a, CircuitTermination) and self.termination_a.provider_network is not None:
            raise ValidationError(
                {"termination_a_id": "Circuit terminations attached to a provider network may not be cabled."}
            )
        if isinstance(self.termination_b, CircuitTermination) and self.termination_b.provider_network is not None:
            raise ValidationError(
                {"termination_b_id": "Circuit terminations attached to a provider network may not be cabled."}
            )

        # Check for an existing Cable connected to either termination object
        if self.termination_a.cable not in (None, self):
            raise ValidationError(f"{self.termination_a} already has a cable attached (#{self.termination_a.cable_id})")
        if self.termination_b.cable not in (None, self):
            raise ValidationError(f"{self.termination_b} already has a cable attached (#{self.termination_b.cable_id})")

        # Validate length and length_unit
        if self.length is not None and not self.length_unit:
            raise ValidationError("Must specify a unit when setting a cable length")
        elif self.length is None:
            self.length_unit = ""

    def save(self, *args, **kwargs):

        # Store the given length (if any) in meters for use in database ordering
        if self.length and self.length_unit:
            self._abs_length = to_meters(self.length, self.length_unit)
        else:
            self._abs_length = None

        # Store the parent Device for the A and B terminations (if applicable) to enable filtering
        if hasattr(self.termination_a, "device"):
            self._termination_a_device = self.termination_a.device
        if hasattr(self.termination_b, "device"):
            self._termination_b_device = self.termination_b.device

        super().save(*args, **kwargs)

        # Update the private pk used in __str__ in case this is a new object (i.e. just got its pk)
        self._pk = self.pk

    def to_csv(self):
        return (
            f"{self.termination_a_type.app_label}.{self.termination_a_type.model}",
            self.termination_a_id,
            f"{self.termination_b_type.app_label}.{self.termination_b_type.model}",
            self.termination_b_id,
            self.get_type_display(),
            self.get_status_display(),
            self.label,
            self.color,
            self.length,
            self.length_unit,
        )

    def get_compatible_types(self):
        """
        Return all termination types compatible with termination A.
        """
        if self.termination_a is None:
            return None
        return COMPATIBLE_TERMINATION_TYPES[self.termination_a._meta.model_name]


@extras_features("graphql")
class CablePath(BaseModel):
    """
    A CablePath instance represents the physical path from an origin to a destination, including all intermediate
    elements in the path. Every instance must specify an `origin`, whereas `destination` may be null (for paths which do
    not terminate on a PathEndpoint).

    `path` contains a list of nodes within the path, each represented by a tuple of (type, ID). The first element in the
    path must be a Cable instance, followed by a pair of pass-through ports. For example, consider the following
    topology:

                     1                              2                              3
        Interface A --- Front Port A | Rear Port A --- Rear Port B | Front Port B --- Interface B

    This path would be expressed as:

    CablePath(
        origin = Interface A
        destination = Interface B
        path = [Cable 1, Front Port A, Rear Port A, Cable 2, Rear Port B, Front Port B, Cable 3]
    )

    `is_active` is set to True only if 1) `destination` is not null, and 2) every Cable within the path has a status of
    "connected".
    """

    origin_type = models.ForeignKey(to=ContentType, on_delete=models.CASCADE, related_name="+")
    origin_id = models.UUIDField()
    origin = GenericForeignKey(ct_field="origin_type", fk_field="origin_id")
    destination_type = models.ForeignKey(
        to=ContentType,
        on_delete=models.CASCADE,
        related_name="+",
        blank=True,
        null=True,
    )
    destination_id = models.UUIDField(blank=True, null=True)
    destination = GenericForeignKey(ct_field="destination_type", fk_field="destination_id")
    # TODO: Profile filtering on this field if it could benefit from an index
    path = JSONPathField()
    is_active = models.BooleanField(default=False)
    is_split = models.BooleanField(default=False)

    class Meta:
        unique_together = ("origin_type", "origin_id")

    def __str__(self):
        status = " (active)" if self.is_active else " (split)" if self.is_split else ""
        return f"Path #{self.pk}: {self.origin} to {self.destination} via {len(self.path)} nodes{status}"

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)

        # Record a direct reference to this CablePath on its originating object
        model = self.origin._meta.model
        model.objects.filter(pk=self.origin.pk).update(_path=self.pk)

    @property
    def segment_count(self):
        total_length = 1 + len(self.path) + (1 if self.destination else 0)
        return int(total_length / 3)

    @classmethod
    def from_origin(cls, origin):
        """
        Create a new CablePath instance as traced from the given path origin.
        """
        if origin is None or origin.cable is None:
            return None

        # Import added here to avoid circular imports with Cable.
        from nautobot.circuits.models import CircuitTermination

        destination = None
        path = []
        position_stack = []
        is_active = True
        is_split = False

        node = origin
        visited_nodes = set()
        while node.cable is not None:
            if node.id in visited_nodes:
                raise ValidationError("a loop is detected in the path")
            visited_nodes.add(node.id)
            if node.cable.status != Cable.STATUS_CONNECTED:
                is_active = False

            # Follow the cable to its far-end termination
            path.append(object_to_path_node(node.cable))
            peer_termination = node.get_cable_peer()

            # Follow a FrontPort to its corresponding RearPort
            if isinstance(peer_termination, FrontPort):
                path.append(object_to_path_node(peer_termination))
                node = peer_termination.rear_port
                if node.positions > 1:
                    position_stack.append(peer_termination.rear_port_position)
                path.append(object_to_path_node(node))

            # Follow a RearPort to its corresponding FrontPort (if any)
            elif isinstance(peer_termination, RearPort):
                path.append(object_to_path_node(peer_termination))

                # Determine the peer FrontPort's position
                if peer_termination.positions == 1:
                    position = 1
                elif position_stack:
                    position = position_stack.pop()
                else:
                    # No position indicated: path has split, so we stop at the RearPort
                    is_split = True
                    break

                try:
                    node = FrontPort.objects.get(rear_port=peer_termination, rear_port_position=position)
                    path.append(object_to_path_node(node))
                except ObjectDoesNotExist:
                    # No corresponding FrontPort found for the RearPort
                    break

            # Follow a Circuit Termination if there is a corresponding Circuit Termination
            # Side A and Side Z exist
            elif isinstance(peer_termination, CircuitTermination):
                node = peer_termination.get_peer_termination()
                # A Circuit Termination does not require a peer.
                if node is None:
                    destination = peer_termination
                    break
                path.append(object_to_path_node(peer_termination))
                path.append(object_to_path_node(node))

            # Anything else marks the end of the path
            else:
                destination = peer_termination
                break

        if destination is None:
            is_active = False

        return cls(
            origin=origin,
            destination=destination,
            path=path,
            is_active=is_active,
            is_split=is_split,
        )

    def get_path(self):
        """
        Return the path as a list of prefetched objects.
        """
        # Compile a list of IDs to prefetch for each type of model in the path
        to_prefetch = defaultdict(list)
        for node in self.path:
            ct_id, object_id = decompile_path_node(node)
            to_prefetch[ct_id].append(object_id)

        # Prefetch path objects using one query per model type. Prefetch related devices where appropriate.
        prefetched = {}
        for ct_id, object_ids in to_prefetch.items():
            model_class = ContentType.objects.get_for_id(ct_id).model_class()
            queryset = model_class.objects.filter(pk__in=object_ids)
            if hasattr(model_class, "device"):
                queryset = queryset.prefetch_related("device")
            prefetched[ct_id] = {obj.id: obj for obj in queryset}

        # Replicate the path using the prefetched objects.
        path = []
        for node in self.path:
            ct_id, object_id = decompile_path_node(node)
            path.append(prefetched[ct_id][object_id])

        return path

    def get_total_length(self):
        """
        Return the sum of the length of each cable in the path.
        """
        cable_ids = [
            # Starting from the first element, every third element in the path should be a Cable
            decompile_path_node(self.path[i])[1]
            for i in range(0, len(self.path), 3)
        ]
        return Cable.objects.filter(id__in=cable_ids).aggregate(total=Sum("_abs_length"))["total"]

    def get_split_nodes(self):
        """
        Return all available next segments in a split cable path.
        """
        rearport = path_node_to_object(self.path[-1])
        return FrontPort.objects.filter(rear_port=rearport)
