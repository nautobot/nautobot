from collections import defaultdict
import logging

from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models, transaction
from django.db.models import Sum
from django.utils.functional import classproperty

from nautobot.core.constants import CHARFIELD_MAX_LENGTH
from nautobot.core.models.fields import ColorField
from nautobot.core.utils.data import to_meters
from nautobot.dcim.choices import CableLengthUnitChoices, CableTypeChoices, CableTypePolarityMethodChoices
from nautobot.dcim.constants import (
    BREAKOUT_COMPATIBLE_TERMINATION_TYPES,
    CABLE_BREAKOUT_MAX_CONNECTORS,
    CABLE_BREAKOUT_MAX_LANES,
    COMPATIBLE_TERMINATION_TYPES,
)
from nautobot.dcim.fields import JSONPathField
from nautobot.dcim.svg.cable_breakout import BreakoutDiagramSVG
from nautobot.dcim.utils import (
    decompile_path_node,
    generate_cable_breakout_mapping,
    object_to_path_node,
    path_node_to_object,
    validate_cable_breakout_mapping,
    validate_cable_termination,
)
from nautobot.extras.models import Status, StatusField
from nautobot.extras.utils import extras_features

# TODO: There's an ugly circular-import pattern where if we move this import "up" to above, we get into an import loop
# from dcim.models.cables to core.models.generics to extras.models.datasources to core.models.generics.
# Deferring the update to here works for now; fixing so that core.models.generics doesn't depend on extras.models
# would be the much more invasive but much more "correct" fix.
from nautobot.core.models.generics import BaseModel, PrimaryModel  # isort: skip

from .device_components import FrontPort, RearPort

__all__ = (
    "Cable",
    "CablePath",
    "CableToCableTermination",
    "CableType",
)

logger = logging.getLogger(__name__)


#
# Cable Types
#


@extras_features(
    "custom_links",
    "custom_validators",
    "export_templates",
    "graphql",
    "webhooks",
)
class CableType(PrimaryModel):
    """
    A reusable definition of a kind of cable.

    Includes (for breakout cables) internal lane structure, connectors on each side,
    the total number of logical lanes, and the A-to-B lane mapping for the breakout.

    By convention and by model enforcement, any breakout is A-to-B, not B-to-A; that is, `a_connectors` may never be
    greater than `b_connectors`, though they may be equal. `total_lanes` must be evenly divisible by both
    `a_connectors` and `b_connectors`; the implied per-side positions per connector are derived from that division.
    """

    name = models.CharField(max_length=CHARFIELD_MAX_LENGTH, unique=True)
    description = models.CharField(max_length=CHARFIELD_MAX_LENGTH, blank=True)
    manufacturer = models.ForeignKey(
        to="dcim.Manufacturer",
        on_delete=models.PROTECT,
        related_name="cable_types",
        blank=True,
        null=True,
    )
    part_number = models.CharField(
        max_length=CHARFIELD_MAX_LENGTH, blank=True, help_text="Discrete part number (optional)"
    )
    has_embedded_transceivers = models.BooleanField(
        default=False,
        help_text="Indicates that this cable type has transceivers (e.g. SFP) built in.",
    )
    a_connectors = models.PositiveSmallIntegerField(
        default=1,
        help_text="Number of physical connectors on the A side.",
        validators=[MinValueValidator(1), MaxValueValidator(CABLE_BREAKOUT_MAX_CONNECTORS)],
    )
    b_connectors = models.PositiveSmallIntegerField(
        default=1,
        help_text="Number of physical connectors on the B side.",
        validators=[MinValueValidator(1), MaxValueValidator(CABLE_BREAKOUT_MAX_CONNECTORS)],
    )
    total_lanes = models.PositiveSmallIntegerField(
        default=1,
        help_text="Total number of logical lanes in the breakout, distributed evenly across connectors on each side.",
        validators=[MinValueValidator(1), MaxValueValidator(CABLE_BREAKOUT_MAX_LANES)],
    )
    mapping = models.JSONField(
        default=list,
        blank=True,
        help_text="A→B lane mapping as a JSON array of objects with keys: "
        "label, a_connector, a_position, b_connector, b_position. If empty, populated by clean().",
    )
    is_shuffle = models.BooleanField(
        default=False,
        help_text="Indicates non-linear (polarity-shuffled) position mapping. Informational only.",
    )
    strands_per_lane = models.PositiveSmallIntegerField(
        default=1,
        help_text="Number of physical strands per logical lane (e.g. 1 for copper, 2 for duplex fiber).",
        validators=[MinValueValidator(1)],
    )
    polarity_method = models.CharField(
        blank=True,
        choices=CableTypePolarityMethodChoices,
        default="",
        help_text="Fiber polarity method. Informational only.",
        max_length=50,
    )

    natural_key_field_names = ["name"]

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name

    @property
    def a_positions(self):
        """Number of positions per A-side connector, derived as total_lanes // a_connectors."""
        if not self.a_connectors:
            return 0
        return self.total_lanes // self.a_connectors

    @property
    def b_positions(self):
        """Number of positions per B-side connector, derived as total_lanes // b_connectors."""
        if not self.b_connectors:
            return 0
        return self.total_lanes // self.b_connectors

    @property
    def total_strands(self):
        """Total physical strand count: total_lanes x strands_per_lane."""
        return self.total_lanes * self.strands_per_lane

    @property
    def is_breakout(self):
        """True if A-side and B-side connector counts differ."""
        return self.a_connectors != self.b_connectors

    def get_diagram_svg(self):
        """Return SVG string for the lane mapping diagram (no connection status, all gray)."""
        diagram = BreakoutDiagramSVG(self.mapping, show_status=False)
        return diagram.render()

    def _autogenerate_mapping(self):
        """Populate `self.mapping` from the connector/lane dimensions if unset and the dimensions are usable."""
        if self.mapping or not (self.a_connectors and self.b_connectors and self.total_lanes):
            return
        if self.total_lanes % self.a_connectors or self.total_lanes % self.b_connectors:
            return
        self.mapping = generate_cable_breakout_mapping(self.a_connectors, self.b_connectors, self.total_lanes)

    def save(self, *args, **kwargs):
        # Auto-generate the mapping here (not only in `clean()`) so callers using `objects.create()`
        # or bare `.save()` get a working breakout cable type, not just `validated_save()` callers.
        self._autogenerate_mapping()
        super().save(*args, **kwargs)

    def clean(self):
        super().clean()

        if self.a_connectors > self.b_connectors:
            raise ValidationError(
                {"b_connectors": "Wrong breakout direction, a_connectors must not exceed b_connectors"}
            )

        if self.total_lanes % self.a_connectors != 0:
            raise ValidationError(
                {"total_lanes": f"total_lanes must be evenly divisible by a_connectors ({self.a_connectors})."}
            )
        if self.total_lanes % self.b_connectors != 0:
            raise ValidationError(
                {"total_lanes": f"total_lanes must be evenly divisible by b_connectors ({self.b_connectors})."}
            )

        self._autogenerate_mapping()
        validate_cable_breakout_mapping(self.mapping, self.a_connectors, self.b_connectors, self.total_lanes)


#
# Cables
#


@extras_features(
    "custom_links",
    "custom_validators",
    "export_templates",
    "graphql",
    "statuses",
    "webhooks",
)
class Cable(PrimaryModel):
    """
    A physical connection between two endpoints.

    Terminations are stored in the CableTermination join table. The `termination_a` and `termination_b`
    properties retrieve the first A-side and B-side terminations respectively for backward compatibility.
    """

    cable_type = models.ForeignKey(
        to=CableType,
        on_delete=models.PROTECT,
        related_name="cables",
        blank=True,
        null=True,
        help_text="The cable type defining this cable's lane structure and other properties."
        "May be null for standard point-to-point cables.",
    )
    type = models.CharField(max_length=50, choices=CableTypeChoices, blank=True)
    status = StatusField(blank=False, null=False)
    label = models.CharField(max_length=CHARFIELD_MAX_LENGTH, blank=True)
    color = ColorField(blank=True)
    length = models.PositiveSmallIntegerField(blank=True, null=True)
    length_unit = models.CharField(
        max_length=50,
        choices=CableLengthUnitChoices,
        blank=True,
    )
    # Stores the normalized length (in meters) for database ordering
    _abs_length = models.DecimalField(max_digits=10, decimal_places=4, blank=True, null=True)

    # Typed many-to-many accessors for each terminating model. The through model is
    # CableToCableTermination, which carries the cable_end / connector lane attributes.
    # Reverse access (`<termination>.cable_termination`) is provided by the OneToOneFields on the
    # through model itself; reverse here is suppressed via `related_name="+"` to avoid a misleading
    # plural "cables" on each terminating model (each termination is on at most one cable).
    circuit_terminations = models.ManyToManyField(
        to="circuits.CircuitTermination",
        through="dcim.CableToCableTermination",
        through_fields=("cable", "circuit_termination"),
        related_name="+",
    )
    console_ports = models.ManyToManyField(
        to="dcim.ConsolePort",
        through="dcim.CableToCableTermination",
        through_fields=("cable", "console_port"),
        related_name="+",
    )
    console_server_ports = models.ManyToManyField(
        to="dcim.ConsoleServerPort",
        through="dcim.CableToCableTermination",
        through_fields=("cable", "console_server_port"),
        related_name="+",
    )
    front_ports = models.ManyToManyField(
        to="dcim.FrontPort",
        through="dcim.CableToCableTermination",
        through_fields=("cable", "front_port"),
        related_name="+",
    )
    interfaces = models.ManyToManyField(
        to="dcim.Interface",
        through="dcim.CableToCableTermination",
        through_fields=("cable", "interface"),
        related_name="+",
    )
    power_feeds = models.ManyToManyField(
        to="dcim.PowerFeed",
        through="dcim.CableToCableTermination",
        through_fields=("cable", "power_feed"),
        related_name="+",
    )
    power_outlets = models.ManyToManyField(
        to="dcim.PowerOutlet",
        through="dcim.CableToCableTermination",
        through_fields=("cable", "power_outlet"),
        related_name="+",
    )
    power_ports = models.ManyToManyField(
        to="dcim.PowerPort",
        through="dcim.CableToCableTermination",
        through_fields=("cable", "power_port"),
        related_name="+",
    )
    rear_ports = models.ManyToManyField(
        to="dcim.RearPort",
        through="dcim.CableToCableTermination",
        through_fields=("cable", "rear_port"),
        related_name="+",
    )

    natural_key_field_names = ["pk"]

    class Meta:
        ordering = ["label", "pk"]

    def __init__(self, *args, **kwargs):
        # Handle legacy kwargs from code that still passes termination_a/b GFK-style arguments.
        # Store them for post-save processing by signal handlers or forms.
        self._initial_termination_a = kwargs.pop("termination_a", None)
        self._initial_termination_b = kwargs.pop("termination_b", None)
        # Also handle the type/id kwargs used by serializers and forms
        self._initial_termination_a_type = kwargs.pop("termination_a_type", None)
        self._initial_termination_a_id = kwargs.pop("termination_a_id", None)
        self._initial_termination_b_type = kwargs.pop("termination_b_type", None)
        self._initial_termination_b_id = kwargs.pop("termination_b_id", None)

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

    @classproperty  # https://github.com/PyCQA/pylint-django/issues/240
    def STATUS_CONNECTED(cls):  # pylint: disable=no-self-argument
        """Return a cached "connected" `Status` object for later reference."""
        if getattr(cls, "__status_connected", None) is None:
            try:
                cls.__status_connected = Status.objects.get_for_model(Cable).get(name="Connected")
            except Status.DoesNotExist:
                logger.warning("Status 'connected' not found for dcim.cable")
                return None

        return cls.__status_connected

    # ─── Termination properties (read from CableToCableTermination join table) ───

    def _first_endpoint(self, side):
        """Return the first CableToCableTermination row for the given side, or None."""
        return self.terminations.filter(cable_end=side).order_by("connector").first()

    def _get_termination_attr(self, side, endpoint_attr, fallback_attr):
        """Get an attribute from the first endpoint on the given side, or fall back to an _initial_* attr."""
        endpoint = self._first_endpoint(side)
        if endpoint:
            return getattr(endpoint, endpoint_attr)
        return getattr(self, fallback_attr, None)

    @property
    def termination_a(self):
        """First A-side termination object (backward compat)."""
        return self._get_termination_attr("A", "termination", "_initial_termination_a")

    @termination_a.setter
    def termination_a(self, value):
        # Backward-compatibility setter: store on `_initial_termination_a` for the post_save signal
        # (on create) or for explicit consumers to materialize into a CableToCableTermination row.
        self._initial_termination_a = value

    @property
    def termination_b(self):
        """First B-side termination object (backward compat)."""
        return self._get_termination_attr("B", "termination", "_initial_termination_b")

    @termination_b.setter
    def termination_b(self, value):
        self._initial_termination_b = value

    @property
    def termination_a_type(self):
        """ContentType of first A-side termination (backward compat)."""
        return self._get_termination_attr("A", "termination_type", "_initial_termination_a_type")

    @termination_a_type.setter
    def termination_a_type(self, value):
        self._initial_termination_a_type = value

    @property
    def termination_a_id(self):
        """UUID of first A-side termination (backward compat)."""
        return self._get_termination_attr("A", "termination_id", "_initial_termination_a_id")

    @termination_a_id.setter
    def termination_a_id(self, value):
        self._initial_termination_a_id = value

    @property
    def termination_b_type(self):
        """ContentType of first B-side termination (backward compat)."""
        return self._get_termination_attr("B", "termination_type", "_initial_termination_b_type")

    @termination_b_type.setter
    def termination_b_type(self, value):
        self._initial_termination_b_type = value

    @property
    def termination_b_id(self):
        """UUID of first B-side termination (backward compat)."""
        return self._get_termination_attr("B", "termination_id", "_initial_termination_b_id")

    @termination_b_id.setter
    def termination_b_id(self, value):
        self._initial_termination_b_id = value

    @property
    def terminations_a(self):
        """All A-side CableTermination rows."""
        return self.terminations.filter(cable_end="A").order_by("connector")

    @property
    def terminations_b(self):
        """All B-side CableTermination rows."""
        return self.terminations.filter(cable_end="B").order_by("connector")

    # ─── Breakout lane properties ───

    @property
    def breakout_eligible(self):
        """Whether this cable's termination types support breakout lane modeling."""

        if not self.present_in_database:
            return True  # New cable, no terminations yet
        for endpoint in self.terminations.all():
            term = endpoint.termination
            if term is not None and term._meta.model_name not in BREAKOUT_COMPATIBLE_TERMINATION_TYPES:
                return False
        return True

    @property
    def total_lanes(self):
        """Total number of lanes defined by the CableType; 1 for standard (non-breakout) cables."""
        if self.cable_type_id:
            return self.cable_type.total_lanes
        return 1

    def _get_connector_status(self):
        """Collect connected connector sets and termination labels from this cable's endpoints.

        Returns (connected_a, connected_b, a_labels, b_labels).
        """
        connected_a = set()
        connected_b = set()
        a_labels = {}
        b_labels = {}
        for endpoint in self.terminations.all():
            termination = endpoint.termination
            if termination:
                parent = getattr(termination, "parent", None)
                label = f"{parent} / {termination}" if parent else str(termination)
                if endpoint.cable_end == "A":
                    connected_a.add(endpoint.connector)
                    a_labels[endpoint.connector] = label
                else:
                    connected_b.add(endpoint.connector)
                    b_labels[endpoint.connector] = label
        return connected_a, connected_b, a_labels, b_labels

    def get_mapping_diagram_svg(self):
        """Return SVG string for the breakout lane mapping diagram with connection status and tooltips."""
        if not self.cable_type_id:
            return ""

        _, _, a_labels, b_labels = self._get_connector_status()
        diagram = BreakoutDiagramSVG(
            self.cable_type.mapping,
            show_status=True,
            a_termination_labels=a_labels,
            b_termination_labels=b_labels,
        )
        return diagram.render()

    @property
    def _effective_mapping(self):
        """The breakout mapping for this cable, or a synthetic single-lane mapping for standard
        (non-breakout) cables — lets `connected_lanes` and `get_lanes` use the same code path
        regardless of cable type."""
        if self.cable_type_id:
            return self.cable_type.mapping
        return [{"a_connector": 1, "a_position": 1, "b_connector": 1, "b_position": 1}]

    @property
    def connected_lanes(self):
        """Number of lanes where both the A-side and B-side connectors have terminations.

        For standard (non-breakout) cables this is 0 (no terminations or only one side) or 1
        (both sides terminated).
        """
        connected_a_connectors = set()
        connected_b_connectors = set()
        for endpoint in self.terminations.all():
            if endpoint.cable_end == "A":
                connected_a_connectors.add(endpoint.connector)
            else:
                connected_b_connectors.add(endpoint.connector)
        return sum(
            1
            for entry in self._effective_mapping
            if entry["a_connector"] in connected_a_connectors and entry["b_connector"] in connected_b_connectors
        )

    def get_lanes(self):
        """
        Return a list of lane dicts, each containing lane number, connector/position info, and
        actual termination objects (or None for unconnected). Standard (non-breakout) cables
        return a single-element list representing the implicit one-lane connection.

        Note that multiple lanes which share a far-/near-side connector resolve to the same
        termination object — the cable's mapping is what makes them distinct logical lanes,
        not the termination row.
        """
        # Build lookup: (cable_end, connector) → CableToCableTermination
        endpoint_lookup = {(endpoint.cable_end, endpoint.connector): endpoint for endpoint in self.terminations.all()}

        lanes = []
        for lane_number, entry in enumerate(self._effective_mapping, start=1):
            a_endpoint = endpoint_lookup.get(("A", entry["a_connector"]))
            b_endpoint = endpoint_lookup.get(("B", entry["b_connector"]))
            lanes.append(
                {
                    "lane": lane_number,
                    "a_connector": entry["a_connector"],
                    "a_position": entry["a_position"],
                    "b_connector": entry["b_connector"],
                    "b_position": entry["b_position"],
                    "a_termination": a_endpoint.termination if a_endpoint else None,
                    "b_termination": b_endpoint.termination if b_endpoint else None,
                }
            )
        return lanes

    def get_connections(self):
        """
        Return a flat row list for displaying cable connections.
        A is always left, B is always right.

        Each row: {a, b, a_rowspan, b_rowspan}
        a_rowspan/b_rowspan indicate how many rows this cell spans (0 = skip, already covered by previous rowspan).

        For 1x4→4x1: 4 rows. A1 has rowspan=4, B1-B4 each rowspan=1.
        For 4x1→1x4: 4 rows. A1-A4 each rowspan=1, B1 has rowspan=4.
        """
        endpoint_by_connector = {
            (endpoint.cable_end, endpoint.connector): endpoint for endpoint in self.terminations.all()
        }

        cable_type = self.cable_type if self.cable_type_id else None

        def _build_connector_info(side, connector_number, position_count):
            endpoint = endpoint_by_connector.get((side, connector_number))
            return {
                "connector": connector_number,
                "side": side,
                "lanes": position_count,
                "cable_termination": endpoint,
                "termination": endpoint.termination if endpoint else None,
            }

        if not cable_type:
            a_info = _build_connector_info("A", 1, 1)
            b_info = _build_connector_info("B", 1, 1)
            return {
                "rows": [{"a": a_info, "b": b_info, "a_rowspan": 1, "b_rowspan": 1}],
                "is_breakout": False,
                "a_connector_count": 1,
                "b_connector_count": 1,
            }

        # Build the mapping: which A connectors map to which B connectors
        a_to_b_connectors = {}
        b_to_a_connectors = {}
        for entry in cable_type.mapping:
            a_to_b_connectors.setdefault(entry["a_connector"], set()).add(entry["b_connector"])
            b_to_a_connectors.setdefault(entry["b_connector"], set()).add(entry["a_connector"])

        # Build a flat row list from the mapping, assigning rowspans.
        # Each unique (a_connector, b_connector) pair gets one row.
        rows = []
        seen_a_connectors = {}  # a_connector → first row index
        seen_b_connectors = {}  # b_connector → first row index
        seen_pairs = set()

        for entry in cable_type.mapping:
            a_connector = entry["a_connector"]
            b_connector = entry["b_connector"]
            pair = (a_connector, b_connector)
            if pair in seen_pairs:
                continue
            seen_pairs.add(pair)

            a_info = _build_connector_info("A", a_connector, cable_type.a_positions)
            b_info = _build_connector_info("B", b_connector, cable_type.b_positions)

            a_rowspan = 0  # 0 = skip (covered by previous rowspan)
            b_rowspan = 0

            if a_connector not in seen_a_connectors:
                a_rowspan = len(a_to_b_connectors.get(a_connector, []))
                seen_a_connectors[a_connector] = len(rows)

            if b_connector not in seen_b_connectors:
                b_rowspan = len(b_to_a_connectors.get(b_connector, []))
                seen_b_connectors[b_connector] = len(rows)

            rows.append(
                {
                    "a": a_info,
                    "b": b_info,
                    "a_rowspan": a_rowspan,
                    "b_rowspan": b_rowspan,
                    "_a_connector": a_connector,
                    "_b_connector": b_connector,
                }
            )

        return {
            "rows": rows,
            "is_breakout": True,
            "a_connector_count": cable_type.a_connectors,
            "b_connector_count": cable_type.b_connectors,
        }

    # ─── Validation ───

    def clean(self):
        super().clean()

        # Per-termination validations on the first A/B terminations (sufficient for standard cables;
        # breakout-cable iteration across all lanes is a future enhancement).
        # Form-driven flows set `_form_cleaned_terminations` on the instance to tell us to use
        # the cleaned form data (`_initial_termination_a/_b`) directly — including the case where
        # the user has *cleared* a side (None) and wants us to validate the new partial pair, not
        # the previously-saved invalid pair. For direct model usage we fall back to the saved-rows
        # property as before.
        if getattr(self, "_form_cleaned_terminations", False):
            term_a = getattr(self, "_initial_termination_a", None)
            term_b = getattr(self, "_initial_termination_b", None)
        else:
            term_a = self.termination_a
            term_b = self.termination_b
        validate_cable_termination(term_a, cable_id=self.pk)
        validate_cable_termination(term_b, cable_id=self.pk)

        # Pair-wise validation on the first A/B pair.
        self._validate_termination_pair(term_a, term_b)

        # Validate length and length_unit
        if self.length is not None and not self.length_unit:
            raise ValidationError("Must specify a unit when setting a cable length")
        elif self.length is None:
            self.length_unit = ""

    @staticmethod
    def _validate_termination_pair(term_a, term_b):
        """Validate compatibility of one A-side / B-side termination pair.

        Raises ValidationError if the pair is incompatible (mismatched types, same termination on both
        sides, FrontPort connected to its corresponding RearPort, or RearPorts with mismatched position
        counts).
        """
        if term_a is None or term_b is None:
            return

        type_a = term_a._meta.model_name
        type_b = term_b._meta.model_name

        if term_a == term_b:
            raise ValidationError(f"Cannot connect {term_a._meta.verbose_name} to itself")

        if type_b not in COMPATIBLE_TERMINATION_TYPES.get(type_a, ()):
            raise ValidationError(f"Incompatible termination types: {type_a} and {type_b}")

        if (
            type_a in ("frontport", "rearport")
            and type_b in ("frontport", "rearport")
            and (
                getattr(term_a, "rear_port_id", None) == term_b.pk or getattr(term_b, "rear_port_id", None) == term_a.pk
            )
        ):
            raise ValidationError("A front port cannot be connected to its corresponding rear port")

        if isinstance(term_a, RearPort) and isinstance(term_b, RearPort):
            if term_a.positions > 1 and term_b.positions > 1 and term_a.positions != term_b.positions:
                raise ValidationError(
                    f"{term_a} has {term_a.positions} position(s) but {term_b} has {term_b.positions}. "
                    f"Both terminations must have the same number of positions (if greater than one)."
                )

    def save(self, *args, **kwargs):
        # Store the given length (if any) in meters for use in database ordering
        if self.length and self.length_unit:
            self._abs_length = to_meters(self.length, self.length_unit)
        else:
            self._abs_length = None

        is_creation = self._state.adding
        status_changed = (not is_creation) and self.status != self._orig_status

        # Wrap the Cable row save and its post-save side effects (join-row materialization +
        # CablePath rebuild) in a single transaction so any failure during termination
        # materialization or the signal-driven path rebuild rolls the Cable row back too.
        # Otherwise we'd be left with an orphaned Cable row that has no join rows and can't be
        # cleaned up through the cable form.
        with transaction.atomic():
            super().save(*args, **kwargs)

            # Update the private pk used in __str__ in case this is a new object (i.e. just got its pk)
            self._pk = self.pk

            # Side effects previously handled by the `update_connected_endpoints` post_save signal.
            # Loaddata bypasses `save()` entirely (it calls `save_base()`), so we no longer need a
            # `raw=True` guard here. Path rebuilds are now driven by the post_save/post_delete signal
            # handlers on `CableToCableTermination` — wrap the row-population in
            # `defer_cable_path_rebuilds()` so the per-row signals coalesce into one rebuild for this
            # cable on context exit.
            if is_creation:
                from nautobot.dcim.signals import defer_cable_path_rebuilds

                with defer_cable_path_rebuilds():
                    self._materialize_initial_terminations()
            elif status_changed:
                self._sync_cable_path_active_flags()

        # Reset the cached "previous status" so subsequent saves compare against the value just
        # persisted, not against the initial value captured in __init__.
        self._orig_status = self.status

    def _materialize_initial_terminations(self):
        """
        Create `CableToCableTermination` rows from any `_initial_termination_*` attrs supplied via
        __init__ / property setter / direct attribute assignment. Used for newly-created cables;
        edits to existing cables go through forms / serializers that manage the join rows directly.
        """
        term_a = getattr(self, "_initial_termination_a", None)
        term_b = getattr(self, "_initial_termination_b", None)

        # Also handle type/id kwargs for the case where termination objects aren't resolved yet.
        if term_a is None and getattr(self, "_initial_termination_a_type", None):
            ct = self._initial_termination_a_type
            term_a = ct.model_class().objects.get(pk=self._initial_termination_a_id)
        if term_b is None and getattr(self, "_initial_termination_b_type", None):
            ct = self._initial_termination_b_type
            term_b = ct.model_class().objects.get(pk=self._initial_termination_b_id)

        # Determine lane 1 connector. Defaults to 1 (the only valid connector on each side for a
        # standard cable); breakout cables read the lane-1 connectors from mapping[0].
        a_connector = b_connector = 1
        if self.cable_type_id and self.cable_type.mapping:
            entry = self.cable_type.mapping[0]
            a_connector = entry["a_connector"]
            b_connector = entry["b_connector"]

        for term, end, conn in (
            (term_a, "A", a_connector),
            (term_b, "B", b_connector),
        ):
            if not term:
                continue
            fk_field = termination_fk_field(term)
            CableToCableTermination.objects.get_or_create(
                cable=self,
                cable_end=end,
                **{fk_field: term},
                defaults={"connector": conn},
            )
            logger.debug(f"Created CableToCableTermination {end}-side for {term} on cable {self}")

    def _sync_cable_path_active_flags(self):
        """Reflect a Cable status change onto any CablePath that traverses this cable."""
        from nautobot.dcim.signals import rebuild_paths

        if self.status != Cable.STATUS_CONNECTED:
            CablePath.objects.filter(path__contains=self).update(is_active=False)
        else:
            rebuild_paths(self)

    def add_termination(self, termination, cable_end, connector=1):
        """
        Attach `termination` to this cable, creating the `CableToCableTermination` join row and
        rebuilding any affected `CablePath`s.

        Use this in preference to creating `CableToCableTermination` rows directly when adding
        terminations after a cable has been saved (e.g. for additional breakout connectors that
        the single A/B kwargs on `Cable.__init__` can't express). The single-step Cable creation
        flow (`Cable(termination_a=..., termination_b=..., ...).save()`) is unchanged.

        Each call triggers a full `rebuild_paths(self)` after the row is inserted (via the
        `CableToCableTermination` post_save signal handler), so adding many terminations one-by-one
        (e.g. populating all connectors of a wide breakout cable) is O(N) path rebuilds. For bulk
        additions, wrap the loop in `defer_cable_path_rebuilds()` so the signal coalesces into a
        single rebuild on context exit.

        Args:
            termination: A `CableTermination` subclass instance (Interface, FrontPort, RearPort,
                CircuitTermination, PowerFeed, etc.).
            cable_end: "A" or "B" — which side of the cable to attach to.
            connector: Connector number on this cable end. Defaults to 1 (the only valid value for
                a standard cable). Breakout cables pass 1..a_connectors / 1..b_connectors here.

        Returns:
            The newly-created `CableToCableTermination` row.
        """
        fk_field = termination_fk_field(termination)
        row = CableToCableTermination(
            cable=self,
            cable_end=cable_end,
            connector=connector,
            **{fk_field: termination},
        )
        # Wrap row insert + signal-driven path rebuild in a transaction so a rebuild failure
        # rolls the row back too. `validated_save` runs `full_clean` so the connector-range
        # check in `clean()` and the field-level MinValueValidator/MaxValueValidator on
        # `connector` are enforced.
        with transaction.atomic():
            row.validated_save()
        return row

    def get_compatible_types(self):
        """
        Return all termination types compatible with termination A.
        """
        if self.termination_a is None:
            return None
        return COMPATIBLE_TERMINATION_TYPES[self.termination_a._meta.model_name]


#
# Cable Terminations (concrete join table)
#

CABLE_END_CHOICES = (
    ("A", "A"),
    ("B", "B"),
)


# Per-type one-to-one FK field name → (app_label, model) natural key for its target model.
# The dict is the source of truth; `TERMINATION_FK_FIELDS` is derived for ordered iteration.
# At most one of these FKs may be non-null on each CableToCableTermination row; enforced by a
# CheckConstraint below. The stricter "exactly one" requirement is enforced in `clean()` — at the
# DB level we allow the all-null state because Django's cascade-delete machinery temporarily nulls
# the nullable FK before deleting the row, and a CHECK constraint would block that intermediate
# step on MySQL.
_TERMINATION_FK_TO_NATURAL_KEY = {
    "circuit_termination": ("circuits", "circuittermination"),
    "console_port": ("dcim", "consoleport"),
    "console_server_port": ("dcim", "consoleserverport"),
    "front_port": ("dcim", "frontport"),
    "interface": ("dcim", "interface"),
    "power_feed": ("dcim", "powerfeed"),
    "power_outlet": ("dcim", "poweroutlet"),
    "power_port": ("dcim", "powerport"),
    "rear_port": ("dcim", "rearport"),
}
TERMINATION_FK_FIELDS = tuple(_TERMINATION_FK_TO_NATURAL_KEY)

# Reverse map: (app_label, model_name) → FK field name. Used by signal/form/serializer code that
# needs to write to the right per-type FK on CableToCableTermination given a termination instance.
_NATURAL_KEY_TO_TERMINATION_FK = {nk: fk for fk, nk in _TERMINATION_FK_TO_NATURAL_KEY.items()}


def termination_fk_field(model_or_instance):
    """Return the CableToCableTermination FK field name corresponding to the given model class or instance.

    Raises TypeError if the given model isn't a known CableTermination subclass.
    """
    opts = model_or_instance._meta
    try:
        return _NATURAL_KEY_TO_TERMINATION_FK[(opts.app_label, opts.model_name)]
    except KeyError:
        raise TypeError(
            f"{opts.label} is not a known CableTermination subclass; expected one of "
            f"{sorted(_NATURAL_KEY_TO_TERMINATION_FK)}"
        ) from None


def _resolve_termination_device(termination):
    """Return the effective parent Device of a termination, walking through any chain of nested modules."""
    if termination is None:
        return None
    direct_device = getattr(termination, "device", None)
    if direct_device is not None:
        return direct_device
    module = getattr(termination, "module", None)
    while module is not None:
        if module.device is not None:
            return module.device
        parent_bay = getattr(module, "parent_module_bay", None)
        if parent_bay is None:
            return None
        if getattr(parent_bay, "parent_device", None) is not None:
            return parent_bay.parent_device
        module = getattr(parent_bay, "parent_module", None)
    return None


def _at_most_one_termination_q():
    """Build a Q expression that's true iff at most one of the TERMINATION_FK_FIELDS is non-null.

    The all-null state is permitted at the DB level so that Django's cascade-delete machinery can
    null out the relevant FK on MySQL before deleting the row. The stricter "exactly one" rule is
    enforced in `CableToCableTermination.clean()`.
    """
    # All-null is permitted (cascade-delete intermediate state).
    expr = models.Q(**{f"{field}__isnull": True for field in TERMINATION_FK_FIELDS})
    # Plus the nine "this one is set, all others are null" disjuncts.
    for field in TERMINATION_FK_FIELDS:
        clause = models.Q(**{f"{field}__isnull": False})
        for other in TERMINATION_FK_FIELDS:
            if other != field:
                clause &= models.Q(**{f"{other}__isnull": True})
        expr |= clause
    return expr


@extras_features("graphql")
class CableToCableTermination(BaseModel):
    """
    Join model between a Cable and a terminating object (Interface, FrontPort, RearPort, etc.).
    Each cable has at least two such rows (one A-side, one B-side); breakout cables have multiple
    rows per side, each with a connector identifying the physical port on that cable end. Lane-
    level (position-within-connector) routing lives in the cable's `CableType.mapping`, not here:
    a single termination occupies a connector, and the mapping describes which logical lanes that
    connector carries.

    Exactly one of the per-type foreign key fields (`interface`, `console_port`, etc.) is set on each
    row, enforced via a CheckConstraint.
    """

    cable = models.ForeignKey(
        to="dcim.Cable",
        on_delete=models.CASCADE,
        related_name="terminations",
    )
    cable_end = models.CharField(
        max_length=1,
        choices=CABLE_END_CHOICES,
    )

    # Per-type one-to-one foreign keys to each concrete CableTermination subclass.
    circuit_termination = models.OneToOneField(
        to="circuits.CircuitTermination",
        on_delete=models.CASCADE,
        related_name="cable_termination",
        blank=True,
        null=True,
    )
    console_port = models.OneToOneField(
        to="dcim.ConsolePort",
        on_delete=models.CASCADE,
        related_name="cable_termination",
        blank=True,
        null=True,
    )
    console_server_port = models.OneToOneField(
        to="dcim.ConsoleServerPort",
        on_delete=models.CASCADE,
        related_name="cable_termination",
        blank=True,
        null=True,
    )
    front_port = models.OneToOneField(
        to="dcim.FrontPort",
        on_delete=models.CASCADE,
        related_name="cable_termination",
        blank=True,
        null=True,
    )
    interface = models.OneToOneField(
        to="dcim.Interface",
        on_delete=models.CASCADE,
        related_name="cable_termination",
        blank=True,
        null=True,
    )
    power_feed = models.OneToOneField(
        to="dcim.PowerFeed",
        on_delete=models.CASCADE,
        related_name="cable_termination",
        blank=True,
        null=True,
    )
    power_outlet = models.OneToOneField(
        to="dcim.PowerOutlet",
        on_delete=models.CASCADE,
        related_name="cable_termination",
        blank=True,
        null=True,
    )
    power_port = models.OneToOneField(
        to="dcim.PowerPort",
        on_delete=models.CASCADE,
        related_name="cable_termination",
        blank=True,
        null=True,
    )
    rear_port = models.OneToOneField(
        to="dcim.RearPort",
        on_delete=models.CASCADE,
        related_name="cable_termination",
        blank=True,
        null=True,
    )

    # Connector number on this cable end. Defaults to 1 for standard (non-breakout) cables; for
    # breakout cables, 1..a_connectors on the A side and 1..b_connectors on the B side.
    connector = models.PositiveSmallIntegerField(
        default=1,
        validators=[MinValueValidator(1), MaxValueValidator(CABLE_BREAKOUT_MAX_CONNECTORS)],
        help_text="The connector number on this cable end. Always 1 for standard cables.",
    )

    # Cached parent Device for filtering (resolved through any chain of nested modules at save time).
    # Necessary denormalization: the effective device of a modular component is reached through a
    # recursive parent_module_bay/parent_module chain, which can't be expressed as a single ORM JOIN.
    _termination_device = models.ForeignKey(
        to="dcim.Device",
        on_delete=models.CASCADE,
        related_name="+",
        blank=True,
        null=True,
    )

    natural_key_field_names = ["pk"]

    class Meta:
        ordering = ["cable", "cable_end", "connector"]
        constraints = [
            # At most one row per (cable, cable_end, connector). For standard cables `connector` is
            # always 1, so this enforces exactly one A and one B per cable; for breakout cables it
            # enforces a single termination per physical connector on each side.
            models.UniqueConstraint(
                fields=["cable", "cable_end", "connector"],
                name="dcim_cabletocabletermination_unique_connector",
            ),
            # At most one of the per-type termination foreign keys may be set; `clean()` further
            # requires that exactly one be set on save. See `_at_most_one_termination_q` for why
            # the DB constraint is the looser of the two.
            models.CheckConstraint(
                name="dcim_cabletocabletermination_at_most_one_termination",
                condition=_at_most_one_termination_q(),
            ),
        ]

    @property
    def termination(self):
        """The single non-null termination FK on this row."""
        for field in TERMINATION_FK_FIELDS:
            obj = getattr(self, field, None)
            if obj is not None:
                return obj
        return None

    @property
    def termination_type(self):
        """The ContentType of this row's termination, or None if unset.

        Inspects the FK `*_id` columns rather than fetching the related object.
        """
        for field in TERMINATION_FK_FIELDS:
            if getattr(self, f"{field}_id", None) is not None:
                app_label, model = _TERMINATION_FK_TO_NATURAL_KEY[field]
                return ContentType.objects.get_by_natural_key(app_label, model)
        return None

    @property
    def termination_id(self):
        """The PK of this row's termination, or None if unset.

        Inspects the FK `*_id` columns rather than fetching the related object.
        """
        for field in TERMINATION_FK_FIELDS:
            pk = getattr(self, f"{field}_id", None)
            if pk is not None:
                return pk
        return None

    def __str__(self):
        return f"{self.cable} {self.cable_end}-side: {self.termination}"

    def clean(self):
        super().clean()
        # Exactly one termination FK must be set. The DB-level CheckConstraint only enforces
        # "at most one" so that cascade deletion (which transiently nulls the FK) doesn't trip it.
        set_fields = [field for field in TERMINATION_FK_FIELDS if getattr(self, f"{field}_id", None) is not None]
        if len(set_fields) == 0:
            raise ValidationError("Exactly one termination foreign key must be set; none are.")
        if len(set_fields) > 1:
            raise ValidationError(
                f"Exactly one termination foreign key must be set; {len(set_fields)} are: {', '.join(set_fields)}."
            )

        term = self.termination
        if term is not None:
            validate_cable_termination(term, cable_id=self.cable_id)

        # `connector` must be in the range defined by the parent cable's CableType. Standard cables
        # (no CableType) have a single connector on each end, so `connector` must be 1; breakout
        # cables have `a_connectors`/`b_connectors` valid positions per side.
        if self.cable is not None:
            if self.cable.cable_type_id is None:
                max_connector = 1
            elif self.cable_end == "A":
                max_connector = self.cable.cable_type.a_connectors
            else:
                max_connector = self.cable.cable_type.b_connectors
            if not 1 <= self.connector <= max_connector:
                raise ValidationError(
                    {
                        "connector": (
                            f"Connector {self.connector} is outside the valid range "
                            f"(1..{max_connector}) for the {self.cable_end}-side of this cable."
                        )
                    }
                )

    def save(self, *args, **kwargs):
        # Cache the effective parent device for filtering. See `_termination_device` field comment.
        self._termination_device = _resolve_termination_device(self.termination)
        super().save(*args, **kwargs)


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
    # Cable-peer-side connector that this path emerges through on its first hop — allows
    # multiple CablePaths per origin (one per peer-side connector on a breakout fan-out).
    # Always 1 for non-breakout paths.
    peer_connector = models.PositiveSmallIntegerField(
        default=1,
        validators=[MinValueValidator(1), MaxValueValidator(CABLE_BREAKOUT_MAX_CONNECTORS)],
    )
    # `CablePathSerializer` currently does not inherit from `BaseModelSerializer`
    # thus it does not have `object_type` field needed for the `assigned_object` field using `PolymorphicProxySerializer`.
    is_metadata_associable_model = False

    natural_key_field_names = ["pk"]

    class Meta:
        unique_together = ("origin_type", "origin_id", "peer_connector")
        ordering = ["peer_connector"]

    def __str__(self):
        status = " (active)" if self.is_active else " (split)" if self.is_split else ""
        return f"Path #{self.pk}: {self.origin} to {self.destination} via {len(self.path)} nodes{status}"

    @property
    def segment_count(self):
        total_length = 1 + len(self.path) + (1 if self.destination else 0)
        return int(total_length / 3)

    @classmethod
    def from_origin(cls, origin, peer_connector=1):
        """
        Create a new CablePath instance as traced from the given path origin.

        Args:
            origin: The PathEndpoint to trace from.
            peer_connector: For breakout-origin paths, the cable-peer-side connector to follow on
                the first hop. Defaults to 1, which is the only valid value for non-breakout
                cables. Stamped onto the returned CablePath so its identity matches the lane it
                represents.
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
        first_hop = True
        while node.cable is not None:
            if node.id in visited_nodes:
                raise ValidationError("a loop is detected in the path")
            visited_nodes.add(node.id)
            if node.cable.status != Cable.STATUS_CONNECTED:
                is_active = False

            # Mid-path breakout bail-out: don't even enter the cable. Lane-aware routing
            # *through* a mid-path breakout cable (e.g. an MPO trunk between pass-through ports
            # in a cross-connect cabinet) isn't supported, so we mark the path as split and stop
            # at the previous pass-through rather than picking an arbitrary peer.
            if not first_hop and node.cable.cable_type_id and node.cable.cable_type.is_breakout:
                is_split = True
                break

            # Follow the cable to its far-end termination
            path.append(object_to_path_node(node.cable))
            if first_hop and node.cable.cable_type_id and node.cable.cable_type.is_breakout:
                # Origin sits on a breakout cable. Look up the peer at the requested connector —
                # may be None for disconnected lanes (path is split).
                peer_termination = node.get_cable_peer(peer_connector=peer_connector)
                if peer_termination is None:
                    is_split = True
            else:
                peer_termination = node.get_cable_peer()
            first_hop = False

            # Unconnected lane on a breakout cable, or broken path
            if peer_termination is None:
                break

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
            peer_connector=peer_connector,
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
