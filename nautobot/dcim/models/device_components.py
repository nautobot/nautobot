from decimal import Decimal
import re
import warnings

from django.contrib.contenttypes.fields import GenericRelation
from django.contrib.contenttypes.prefetch import GenericPrefetch
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models import Prefetch, Sum
from django.utils.functional import classproperty

from nautobot.core.constants import CHARFIELD_MAX_LENGTH
from nautobot.core.models.fields import ForeignKeyWithAutoRelatedName, MACAddressCharField, NaturalOrderingField
from nautobot.core.models.generics import BaseModel, PrimaryModel
from nautobot.core.models.managers import BaseManager
from nautobot.core.models.ordering import naturalize_interface
from nautobot.core.models.query_functions import CollateAsChar
from nautobot.core.models.querysets import RestrictedQuerySet
from nautobot.core.models.tree_queries import TreeModel
from nautobot.core.utils.data import UtilizationData
from nautobot.dcim.choices import (
    ConsolePortTypeChoices,
    InterfaceDuplexChoices,
    InterfaceModeChoices,
    InterfaceRedundancyGroupProtocolChoices,
    InterfaceStatusChoices,
    InterfaceTypeChoices,
    PortTypeChoices,
    PowerFeedPhaseChoices,
    PowerOutletFeedLegChoices,
    PowerOutletTypeChoices,
    PowerPortTypeChoices,
)
from nautobot.dcim.constants import (
    CABLE_BREAKOUT_MAX_LANES,
    COPPER_TWISTED_PAIR_IFACE_TYPES,
    NONCONNECTABLE_IFACE_TYPES,
    REARPORT_POSITIONS_MAX,
    REARPORT_POSITIONS_MIN,
    TERMINATION_FK_FIELDS,
    VIRTUAL_IFACE_TYPES,
    WIRELESS_IFACE_TYPES,
)
from nautobot.dcim.utils import convert_watts_to_va, power_ports_connected_to
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
                fields=("module", "name"),
                name="%(app_label)s_%(class)s_module_name_unique",
            )
        ]

    @property
    def parent(self):
        """Device that this component belongs to, walking up module inheritance if necessary."""
        return self.device

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
            direct_ancestor = self.module if self.module else self.device
        except ObjectDoesNotExist:
            # The parent may have already been deleted
            direct_ancestor = None

        return super().to_objectchange(action, related_object=direct_ancestor, **kwargs)

    def clean(self):
        super().clean()
        if self.device and self.module:
            if self.device != (nested_device := getattr(self.module.parent_module_bay, "parent_device", None)):  # pylint: disable=no-member
                raise ValidationError(
                    f"Module's assigned device differs ({nested_device._meta.verbose_name}) from the root device: {self.device._meta.verbose_name}"
                )
        if (
            self.module is None
            and self.__class__.objects.filter(device=self.device, module__isnull=True, name=self.name)
            .exclude(pk=self.pk)
            .exists()
        ):
            raise ValidationError(f"A {self._meta.verbose_name} by this name already exists on {self.device}")

        if not (self.device or self.module):
            raise ValidationError("Either device or module must be set")

    def save(self, *args, **kwargs):
        if self.device is None and self.module is not None:
            self.device = getattr(self.module.parent_module_bay, "parent_device", None)

        super().save(*args, **kwargs)


class CableTerminationQuerySet(RestrictedQuerySet):
    """RestrictedQuerySet with backward-compat translation for `cable=`-style lookups.

    The `cable` FK is no longer a real field on CableTermination subclasses; cable membership lives
    on the `CableToCableTermination` join model and is exposed via the `cable_termination` reverse
    OneToOneField. To preserve common existing query patterns, this queryset translates
    `cable`/`cable_id`/`cable__*`/`cable_id__*` lookup kwargs (and `select_related("cable")`) into
    the equivalent `cable_termination__cable[...]` paths, with a `DeprecationWarning` for each
    translated lookup.

    Patterns NOT translated (use the explicit form on these instead):
      * Q expressions referencing `cable` (use `Q(cable_termination__cable=...)`)
      * `order_by("cable")` (use `order_by("cable_termination__cable")`)
      * `values("cable")` / `values_list("cable")` (use `cable_termination__cable`)
    """

    @staticmethod
    def _warn(old, new):
        warnings.warn(
            f"Querying CableTermination subclasses by `{old}` is deprecated; use `{new}` instead. "
            "The `cable` field has been replaced with the `cable_termination` reverse OneToOneField.",
            DeprecationWarning,
            stacklevel=4,
        )

    @classmethod
    def _translate_cable_kwargs(cls, kwargs):
        out = {}
        for key, value in kwargs.items():
            if key == "cable":
                if value is None:
                    cls._warn("cable=None", "cable_termination__isnull=True")
                    out["cable_termination__isnull"] = True
                else:
                    cls._warn("cable=...", "cable_termination__cable=...")
                    out["cable_termination__cable"] = value
            elif key == "cable_id":
                if value is None:
                    cls._warn("cable_id=None", "cable_termination__isnull=True")
                    out["cable_termination__isnull"] = True
                else:
                    cls._warn("cable_id=...", "cable_termination__cable_id=...")
                    out["cable_termination__cable_id"] = value
            elif key == "cable__isnull":
                cls._warn("cable__isnull=...", "cable_termination__isnull=...")
                out["cable_termination__isnull"] = bool(value)
            elif key.startswith("cable__"):
                cls._warn(f"{key}=...", f"cable_termination__{key}=...")
                out[f"cable_termination__cable__{key[len('cable__') :]}"] = value
            elif key.startswith("cable_id__"):
                cls._warn(f"{key}=...", f"cable_termination__{key}=...")
                out[f"cable_termination__cable_id__{key[len('cable_id__') :]}"] = value
            else:
                out[key] = value
        return out

    @classmethod
    def _translate_select_related_fields(cls, fields):
        translated = []
        for field in fields:
            if field == "cable":
                cls._warn('select_related("cable")', 'select_related("cable_termination__cable")')
                translated.append("cable_termination__cable")
            elif field.startswith("cable__"):
                cls._warn(f'select_related("{field}")', f'select_related("cable_termination__{field}")')
                translated.append(f"cable_termination__cable__{field[len('cable__') :]}")
            else:
                translated.append(field)
        return translated

    def filter(self, *args, **kwargs):
        return super().filter(*args, **self._translate_cable_kwargs(kwargs))

    def exclude(self, *args, **kwargs):
        return super().exclude(*args, **self._translate_cable_kwargs(kwargs))

    def get(self, *args, **kwargs):
        return super().get(*args, **self._translate_cable_kwargs(kwargs))

    def select_related(self, *fields):
        return super().select_related(*self._translate_select_related_fields(fields))


# Manager class wired to the translation queryset; concrete CableTermination subclasses set this
# as their default `objects` manager.
CableTerminationManager = BaseManager.from_queryset(CableTerminationQuerySet)


class CableTermination(models.Model):
    """
    An abstract model inherited by all models to which a Cable can terminate (certain device components, PowerFeed, and
    CircuitTermination instances).

    Cable membership is recorded in the `CableToCableTermination` join model. Each concrete subclass gets a reverse
    `cable_termination` accessor (a single related row, or `None`/`DoesNotExist` if not connected). The `cable`
    property below is a backward-compat shorthand for `self.cable_termination.cable`.

    Use `get_cable_peer()` (singular) or `get_cable_peers()` (plural; required for breakout cables) to look up the
    far-end termination(s) via the CableToCableTermination join table.

    Each concrete subclass overrides `objects = CableTerminationManager()` to enable backward-compat
    `cable=...`/`select_related("cable")` query translation. (We don't put it here because Django's
    MRO-based manager resolution would be overridden by `BaseModel.objects` for any subclass that
    inherits from a non-abstract base earlier in the parent list.)
    """

    class Meta:
        abstract = True

    # Whether this termination type can have a cable attached. Subclasses (notably Interface) may override
    # this with a property to make it dependent on per-instance state.
    is_connectable = True

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if getattr(self, "_pending_cable_disconnect", False):
            # Clear the flag first to prevent re-entry from disconnect_termination's internal save calls.
            self._pending_cable_disconnect = False
            from nautobot.dcim.utils import disconnect_termination

            if getattr(self, "cable_termination", None) is not None:
                disconnect_termination(self)

    @property
    def cable(self):
        """The Cable this termination is connected to, or None.

        Backward-compat shorthand for `self.cable_termination.cable`. Issues up to two queries on first
        access (one for the join-table row, one for the cable). Use
        `select_related("cable_termination__cable")` on the parent queryset to avoid the queries.
        """
        if getattr(self, "_pending_cable_disconnect", False):
            return None
        ct = getattr(self, "cable_termination", None)
        return ct.cable if ct is not None else None

    @cable.setter
    def cable(self, value):
        """Backward-compat setter for `termination.cable = None` (disconnect).

        Setting to None marks this termination for disconnect on the next ``save()``: the
        CableToCableTermination row will be removed and dependent paths cleaned up at that point.
        Setting to a Cable instance is not supported in the new model: use
        ``Cable.objects.create(termination_a=..., termination_b=..., ...)`` to connect a termination,
        or write the appropriate ``CableToCableTermination`` row directly.
        """
        if value is None:
            self._pending_cable_disconnect = True
        else:
            raise NotImplementedError(
                f"Connecting {self} to a Cable via `termination.cable = ...` is not supported. "
                "Use Cable.objects.create(termination_a=..., termination_b=...) instead, or write a "
                "CableToCableTermination row directly."
            )

    @property
    def cable_id(self):
        """The PK of the Cable this termination is connected to, or None.

        Backward-compat shorthand for `self.cable_termination.cable_id`. Issues a single query on
        first access (only the join-table row, no second query for the Cable itself). Use
        `select_related("cable_termination")` on the parent queryset to avoid that query.
        """
        if getattr(self, "_pending_cable_disconnect", False):
            return None
        ct = getattr(self, "cable_termination", None)
        return ct.cable_id if ct is not None else None

    def get_cable_peer(self, peer_connector=None):
        """Return the far-end termination of this cable.

        For non-breakout cables, returns the single peer (or the first peer if multiple exist).

        For breakout cables, pass `peer_connector` to select the termination on a specific
        opposite-side connector. The connector number refers to the *peer's* side of the cable
        — i.e. the side opposite to this termination. Returns None if no termination occupies
        that connector (disconnected lane) or if `peer_connector` isn't a connector this
        termination's connector maps to via the cable type's lane mapping.
        """
        rows = self._get_cable_peer_rows()
        if peer_connector is None:
            return rows[0].termination if rows and rows[0].termination is not None else None
        for row in rows:
            if row.connector == peer_connector:
                return row.termination
        return None

    @property
    def cable_peer(self):
        """First far-end termination on the connected cable, or None.

        For breakout/multi-termination cables, use `get_cable_peers()` to retrieve all peers.
        """
        return self.get_cable_peer()

    def get_cable_peers(self):
        """Return the opposite-side termination objects mapped to this termination's lane(s).

        For standard cables, returns a list with one peer.
        For breakout cables, returns peers mapped to this termination's connector via the template.

        Reads `cable.terminations.all()` and filters / sorts in Python so callers can prefetch
        the cable's terminations (with per-type FKs `select_related`'d) to avoid N+1 queries
        when this is called for many rows in a table render. See
        `CableTermination.optimize_queryset_for_cable_columns`.
        """
        return [row.termination for row in self._get_cable_peer_rows() if row.termination is not None]

    def _get_cable_peer_rows(self):
        """Return the opposite-side `CableToCableTermination` rows mapped to this termination's
        lane(s), sorted by connector. Internal helper shared by `get_cable_peer` (which picks
        one row by `peer_connector`) and `get_cable_peers` (which extracts terminations).

        For breakout cables, only peer-side rows whose connector is reachable from this
        termination's connector via the cable type's lane mapping are returned. For non-breakout
        cables, all opposite-side rows are returned.
        """
        my_endpoint = getattr(self, "cable_termination", None)
        if my_endpoint is None:
            return []

        cable = my_endpoint.cable
        opposite_side = "B" if my_endpoint.cable_end == "A" else "A"

        all_rows = cable.terminations.all()

        if cable.cable_type_id and cable.cable_type.is_breakout:
            mapped_far_connectors = self._mapped_far_connectors()
            opposite_endpoints = [
                ep for ep in all_rows if ep.cable_end == opposite_side and ep.connector in mapped_far_connectors
            ]
        else:
            opposite_endpoints = [ep for ep in all_rows if ep.cable_end == opposite_side]

        opposite_endpoints.sort(key=lambda ep: ep.connector or 0)
        return opposite_endpoints

    def _mapped_far_connectors(self):
        """Opposite-side connector numbers this termination's connector maps to via the cable type's
        lane mapping. Only meaningful for breakout cables; returns an empty set otherwise.
        """
        my_endpoint = getattr(self, "cable_termination", None)
        if my_endpoint is None or my_endpoint.cable is None:
            return set()
        cable = my_endpoint.cable
        if not (cable.cable_type_id and cable.cable_type.is_breakout):
            return set()
        origin_side_key = "a_connector" if my_endpoint.cable_end == "A" else "b_connector"
        far_side_key = "b_connector" if my_endpoint.cable_end == "A" else "a_connector"
        return {
            entry[far_side_key] for entry in cable.cable_type.mapping if entry[origin_side_key] == my_endpoint.connector
        }

    def breakout_fans_out(self):
        """True if this termination sits on the fan-out side of a breakout cable.

        That is, its connector maps to more than one opposite-side connector — the signal fans out
        to multiple lanes, which is a genuine path split, regardless of how many of those lanes are
        currently connected. A connector mapping to a single far connector (the aggregating side of
        a breakout, or any non-breakout cable) is deterministic and not a split.
        """
        return len(self._mapped_far_connectors()) > 1

    def get_breakout_trunk_child_interfaces(self):
        """Trunk-side child interfaces this fan-out-side termination maps to.

        For a termination on the fan-out (more-connectors) side of a breakout cable, resolve the
        trunk-side peer and — *only* when that peer is an `Interface` — return the child
        interface(s) whose name suffix matches each trunk-connector position this termination's
        connector carries. This is the reverse of `Interface.get_breakout_lane`.

        Returns a list of dicts, empty when not applicable (non-breakout cable, this termination on
        the trunk side rather than the fan-out side, or a non-`Interface` trunk peer). Each dict:

        - `trunk_interface`: the trunk-side peer `Interface`
        - `position`: the trunk-connector position this termination's lane maps to
        - `label`: the lane's mapping label, if any
        - `child_interface`: the trunk's child interface whose `breakout_position` matches, or
          `None` if no child interface claims that position
        """
        my_row = getattr(self, "cable_termination", None)
        if my_row is None:
            return []
        cable = my_row.cable
        if cable is None or not cable.cable_type_id or not cable.cable_type.is_breakout:
            return []
        trunk_end = cable.cable_type.trunk_end
        # Only applies when *this* termination is on the fan-out side, opposite the trunk.
        if my_row.cable_end == trunk_end:
            return []
        fanout_side, trunk_side = my_row.cable_end.lower(), trunk_end.lower()
        results = []
        for lane in cable.get_lanes():
            if lane[f"{fanout_side}_connector"] != my_row.connector:
                continue
            trunk_termination = lane[f"{trunk_side}_termination"]
            # Child interfaces are an Interface-only concept; ignore any other trunk peer type.
            if not isinstance(trunk_termination, Interface):
                continue
            position = lane[f"{trunk_side}_position"]
            child_interface = next(
                (child for child in trunk_termination.child_interfaces.all() if child.breakout_position == position),
                None,
            )
            results.append(
                {
                    "trunk_interface": trunk_termination,
                    "position": position,
                    "label": lane["label"],
                    "child_interface": child_interface,
                }
            )
        return results

    def get_breakout_trunk_child_interface_for_endpoint(self, endpoint):
        """The breakout-trunk child (sub)interface whose lane connects to `self` via `endpoint`.

        When a connection traced from `self` terminates on a breakout-trunk `Interface` `endpoint` —
        possibly several hops away, through intervening patch-panel front/rear ports — return the
        trunk's child interface whose breakout lane resolves back to `self`, or `None`.

        This complements `get_breakout_trunk_child_interfaces`, which only inspects the cable
        directly attached to `self`; here the breakout cable may be mid-path. Resolution roots
        entirely on `endpoint` (its per-lane `cable_paths`, breakout cable lanes, and
        `child_interfaces`) so a single prefetch on the connection destination keeps table renders
        query-free per row. See `cable_columns_prefetch_related_fields`.
        """
        if not isinstance(endpoint, Interface):
            return None
        trunk_row = getattr(endpoint, "cable_termination", None)
        if trunk_row is None:
            return None
        cable = trunk_row.cable
        if cable is None or not cable.cable_type_id or not cable.cable_type.is_breakout:
            return None
        trunk_end = cable.cable_type.trunk_end
        # `endpoint` must terminate the trunk (fewer-connectors) side of the breakout.
        if trunk_row.cable_end != trunk_end:
            return None
        # Which fan-out connector's lane leads back to `self`? The trunk has one CablePath per
        # fan-out lane, keyed by `peer_connector` (the breakout-side connector).
        far_connector = next(
            (path.peer_connector for path in endpoint.cable_paths.all() if path.destination == self),
            None,
        )
        if far_connector is None:
            return None
        trunk_side = trunk_end.lower()
        far_side = "b" if trunk_end == "A" else "a"
        position = next(
            (
                lane[f"{trunk_side}_position"]
                for lane in cable.get_lanes()
                if lane[f"{trunk_side}_connector"] == trunk_row.connector
                and lane[f"{far_side}_connector"] == far_connector
            ),
            None,
        )
        if position is None:
            return None
        return next(
            (child for child in endpoint.child_interfaces.all() if child.breakout_position == position),
            None,
        )

    @classmethod
    def cable_columns_select_related_fields(cls):
        """
        Return the list of `select_related` field paths needed for table renders of the `cable`
        and `cable_peer` columns to avoid per-row queries against the join table / cable type.
        """
        return ["cable_termination__cable__cable_type"]

    @classmethod
    def cable_columns_prefetch_related_fields(cls):
        """
        Return the list of `prefetch_related` arguments (strings and/or `Prefetch` objects)
        needed for table renders of the `cable_peer` column (and, for `PathEndpoint` subclasses,
        the `connection` column) to avoid per-row queries.
        """
        from nautobot.dcim.models.cables import CableToCableTermination

        prefetches = [
            Prefetch(
                "cable_termination__cable__terminations",
                queryset=CableToCableTermination.objects.select_related(*TERMINATION_FK_FIELDS),
            ),
            # The breakout child-interface annotation resolves the trunk peer's child interfaces.
            "cable_termination__cable__terminations__interface__child_interfaces",
        ]
        if issubclass(cls, PathEndpoint):
            # `cable_paths__destination` powers the `connection` column. When a destination is a
            # breakout-trunk Interface, the connection's trunk child-interface annotation
            # (`get_breakout_trunk_child_interface_for_endpoint`) reads that destination's own
            # per-lane `cable_paths`, breakout cable lanes, and `child_interfaces`. Prefetch those on
            # the Interface destinations so the annotation stays query-free per row, even when the
            # breakout cable is several hops away behind patch-panel front/rear ports.
            prefetches.append(
                GenericPrefetch(
                    "cable_paths__destination",
                    [
                        Interface.objects.select_related("cable_termination__cable__cable_type").prefetch_related(
                            Prefetch(
                                "cable_termination__cable__terminations",
                                queryset=CableToCableTermination.objects.select_related(*TERMINATION_FK_FIELDS),
                            ),
                            "cable_paths__destination",
                            "child_interfaces",
                        )
                    ],
                )
            )
        return prefetches

    @classmethod
    def optimize_queryset_for_cable_columns(cls, queryset):
        """
        Apply `select_related` / `prefetch_related` to `queryset` so that table renders of the
        `cable`, `cable_peer`, and (for PathEndpoint subclasses) `connection` columns avoid the
        per-row N+1 queries that those accessors otherwise trigger.

        Usage on a list view's `queryset`:

            queryset = Interface.optimize_queryset_for_cable_columns(Interface.objects.all())

        For panel-based detail views that take `select_related_fields` / `prefetch_related_fields`
        directly, use the underlying `cable_columns_select_related_fields()` /
        `cable_columns_prefetch_related_fields()` classmethods instead.
        """
        queryset = queryset.select_related(*cls.cable_columns_select_related_fields())
        queryset = queryset.prefetch_related(*cls.cable_columns_prefetch_related_fields())
        return queryset

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

    `cable_paths` is a GenericRelation to CablePath rows that have this instance as their origin. For non-breakout
    cables there is at most one such row; for breakout cables there is one per fan-out lane.
    """

    cable_paths = GenericRelation(
        "dcim.CablePath",
        content_type_field="origin_type",
        object_id_field="origin_id",
        related_query_name="origin_endpoint",
    )

    class Meta:
        abstract = True

    def trace(self):
        # Trace the endpoint's first path (a non-breakout endpoint has at most one).
        path_obj = self.cable_paths.first()  # pylint: disable=no-member
        return path_obj.trace() if path_obj is not None else []

    @property
    def path(self):
        return self.cable_paths.first()  # pylint: disable=no-member

    @property
    def connected_endpoint(self):
        """
        Return the attached CablePath's destination (if any)
        """
        path_obj = self.cable_paths.first()  # pylint: disable=no-member
        return path_obj.destination if path_obj else None

    def get_connected_endpoints(self):
        """
        Return destinations of all CablePaths originating from this endpoint.

        For standard cables there is at most one destination. For breakout cables there is one
        destination per fan-out lane. Unresolved or split paths contribute no destinations.
        """
        return [path.destination for path in self.cable_paths.all() if path.destination is not None]


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

    objects = CableTerminationManager()


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

    objects = CableTerminationManager()


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

    objects = CableTerminationManager()

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
            outlet_qs = PowerOutlet.objects.filter(power_port=self)
            outlet_count = outlet_qs.count()
            utilization = power_ports_connected_to(outlet_qs).aggregate(
                maximum_draw_total=Sum("maximum_draw"),
                allocated_draw_total=Sum("allocated_draw"),
            )

            # Convert watts to VA for aggregated values
            allocated_va = convert_watts_to_va(utilization["allocated_draw_total"], self.power_factor)
            maximum_va = convert_watts_to_va(utilization["maximum_draw_total"], self.power_factor)

            ret = {
                "allocated": allocated_va,
                "maximum": maximum_va,
                "outlet_count": outlet_count,
                "legs": [],
                "utilization_data": UtilizationData(
                    numerator=allocated_va,
                    denominator=maximum_va,
                ),
            }

            # Calculate per-leg aggregates for three-phase feeds
            if getattr(self.get_cable_peer(), "phase", None) == PowerFeedPhaseChoices.PHASE_3PHASE:
                # Setup numerator and denominator for later display.
                for leg, leg_name in PowerOutletFeedLegChoices:
                    leg_outlet_qs = PowerOutlet.objects.filter(power_port=self, feed_leg=leg)
                    leg_outlet_count = leg_outlet_qs.count()
                    utilization = power_ports_connected_to(leg_outlet_qs).aggregate(
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
                            "outlet_count": leg_outlet_count,
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

    objects = CableTerminationManager()

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
        through_defaults = {
            "is_source": is_source,
            "is_destination": is_destination,
            "is_default": is_default,
            "is_preferred": is_preferred,
            "is_primary": is_primary,
            "is_secondary": is_secondary,
            "is_standby": is_standby,
        }

        if not isinstance(ip_addresses, (tuple, list)):
            ip_addresses = [ip_addresses]

        # This ensures that ips_to_add only contains IPs which need to be added to the interface. This ensures
        # that len(ips_to_add) accurately represents the results of the action.
        ips_to_add = set(ip_addresses) - set(self.ip_addresses.all())

        if ips_to_add:
            self.ip_addresses.add(*ips_to_add, through_defaults=through_defaults)  # pylint: disable=no-member  # Intf/VMIntf both have ip_addresses

        return len(ips_to_add)

    add_ip_addresses.alters_data = True

    def remove_ip_addresses(self, ip_addresses):
        """Remove one or more IPAddress instances from this interface's `ip_addresses` many-to-many relationship.

        Args:
            ip_addresses (:obj:`list` or `IPAddress`): Instance of `nautobot.ipam.models.IPAddress` or list of `IPAddress` instances.

        Returns:
            Number of instances removed.
        """
        if not isinstance(ip_addresses, (tuple, list)):
            ip_addresses = [ip_addresses]

        # The delete() call used previously (ref: https://github.com/nautobot/nautobot/issues/3236)
        # meant that if None was passed in, it was silently ignored. Rather that raise an exception,
        # this comprehension maintains backwards compatibility.
        ip_addresses = {ip for ip in ip_addresses if ip is not None}

        # This checks that the IPs passed in are actually on the interface. By populating
        # ips_to_remove correctly, we ensure that the only IPs passed to remove() are IPs known
        # to be on the interface. This ensures that len(ips_to_remove) accurately represents
        # the results of the action.
        ips_to_remove = ip_addresses & set(self.ip_addresses.all())

        if ips_to_remove:
            self.ip_addresses.remove(*ips_to_remove)  # pylint: disable=no-member  # Intf/VMIntf both have ip_addresses

        return len(ips_to_remove)

    remove_ip_addresses.alters_data = True


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
    port_type = models.CharField(
        max_length=50,
        choices=PortTypeChoices,
        blank=True,
        help_text="Physical connector type",
    )
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
    # Operational attributes (distinct from interface type capabilities)
    speed = models.PositiveIntegerField(null=True, blank=True)
    duplex = models.CharField(max_length=10, choices=InterfaceDuplexChoices, blank=True, default="")
    breakout_position = models.PositiveSmallIntegerField(
        blank=True,
        null=True,
        validators=[MinValueValidator(1), MaxValueValidator(CABLE_BREAKOUT_MAX_LANES)],
        help_text=(
            "For a child interface of a breakout-cable trunk, the position on the parent interface's "
            "trunk connector that this child interface maps to."
        ),
    )

    objects = CableTerminationManager()

    class Meta(ModularComponentModel.Meta):
        ordering = ("device", "module__id", CollateAsChar("_name"))  # Module.ordering is complex; don't order by module
        constraints = [
            *ModularComponentModel.Meta.constraints,
            # A given trunk position can be claimed by at most one child interface. Rows without a
            # breakout_position are exempt automatically: NULL != NULL, so they never collide.
            models.UniqueConstraint(
                fields=("parent_interface", "breakout_position"),
                name="dcim_interface_unique_parent_breakout_position",
            ),
        ]

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
        if self.type in NONCONNECTABLE_IFACE_TYPES and (self.cable or getattr(self, "circuit_termination", False)):
            raise ValidationError(
                {
                    "type": "Virtual and wireless interfaces cannot be connected to another interface or circuit. "
                    "Disconnect the interface or choose a suitable type."
                }
            )

        # Virtual interfaces cannot have a port type
        if self.type in NONCONNECTABLE_IFACE_TYPES and self.port_type:
            raise ValidationError({"port_type": "Virtual and wireless interfaces cannot have a port type."})

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

        # A breakout position only makes sense relative to a parent (trunk) interface.
        if self.breakout_position is not None and self.parent_interface_id is None:
            raise ValidationError(
                {
                    "breakout_position": "A breakout position can only be set on an interface that has a parent interface."
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

        # Speed/Duplex validation
        self._validate_speed_and_duplex()

    def _validate_speed_and_duplex(self):
        """Validate speed (Kbps) and duplex based on interface type."""

        # Check settings by interface type
        if self.speed and any([self.is_lag, self.is_virtual, self.is_wireless]):
            raise ValidationError({"speed": "Speed is not applicable to this interface type."})

        if self.duplex and any([self.is_lag, self.is_virtual, self.is_wireless]):
            raise ValidationError({"duplex": "Duplex is not applicable to this interface type."})

        if self.duplex and self.type not in COPPER_TWISTED_PAIR_IFACE_TYPES:
            raise ValidationError({"duplex": "Duplex is only applicable to copper twisted-pair interfaces."})

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

    @classmethod
    def cable_columns_select_related_fields(cls):
        """Extend the base cable-column hints with the parent trunk interface's cable/cable-type.

        Breakout child-interface rows resolve their `connection` / `cable_peer` columns through the
        parent trunk (`get_breakout_lane` / `get_breakout_connected_endpoint`), so the parent's
        cable and cable type must be joined to avoid a per-row query.
        """
        return [
            *super().cable_columns_select_related_fields(),
            "parent_interface__cable_termination__cable__cable_type",
        ]

    @classmethod
    def cable_columns_prefetch_related_fields(cls):
        """Extend the base cable-column prefetches for breakout child-interface rows.

        `get_breakout_lane` reads the parent trunk cable's terminations (via `Cable.get_lanes`), and
        `get_breakout_connected_endpoint` scans the parent trunk's `CablePath` rows and their
        destinations. Prefetching both off `parent_interface` keeps those accessors query-free per
        row.
        """
        from nautobot.dcim.models.cables import CableToCableTermination

        return [
            *super().cable_columns_prefetch_related_fields(),
            Prefetch(
                "parent_interface__cable_termination__cable__terminations",
                queryset=CableToCableTermination.objects.select_related(*TERMINATION_FK_FIELDS),
            ),
            "parent_interface__cable_paths__destination",
        ]

    def get_breakout_lane(self):
        """The breakout-cable trunk lane this child interface maps to, or `None` if not applicable.

        Applies only when this is a child interface (`parent_interface` set) with an explicit
        `breakout_position`, whose parent terminates the trunk (fewer-connectors) side of a breakout
        cable that carries that position. This is the forward direction;
        `CableTermination.get_breakout_trunk_child_interfaces` resolves the reverse.

        Returns a dict describing the mapped lane, or `None` if any condition isn't met (no parent,
        no `breakout_position`, parent not cabled to a breakout trunk, or the position isn't carried
        by the parent's trunk connector):

        - `position`: this interface's `breakout_position`
        - `label`: the lane's mapping label, if any
        - `far_connector`: the breakout-side connector this lane maps to (used to select the parent
          trunk's matching `CablePath`; see `get_breakout_connected_endpoint`)
        - `far_termination`: the termination cabled on the far (breakout-side) connector for this
          lane, or `None` if that connector is currently unoccupied
        """
        position = self.breakout_position
        if position is None:
            return None
        parent = self.parent_interface
        if parent is None:
            return None
        parent_row = getattr(parent, "cable_termination", None)
        if parent_row is None:
            return None
        cable = parent_row.cable
        if cable is None or not cable.cable_type_id or not cable.cable_type.is_breakout:
            return None
        # The parent must terminate the trunk (fewer-connectors) side of the breakout.
        trunk_end = cable.cable_type.trunk_end
        if parent_row.cable_end != trunk_end:
            return None
        trunk_side = trunk_end.lower()
        far_side = "b" if trunk_end == "A" else "a"
        for lane in cable.get_lanes():
            if lane[f"{trunk_side}_connector"] == parent_row.connector and lane[f"{trunk_side}_position"] == position:
                return {
                    "position": position,
                    "label": lane["label"],
                    "far_connector": lane[f"{far_side}_connector"],
                    "far_termination": lane[f"{far_side}_termination"],
                }
        return None

    def get_breakout_lane_cable_path(self):
        """The parent trunk's `CablePath` for this breakout child interface's lane, or None.

        A breakout child (sub)interface has no `CablePath` of its own; its physical path is its
        parent trunk's breakout lane at this child's `breakout_position`, identified among the
        trunk's per-lane paths by the lane's far (breakout-side) connector. Returns None when this
        isn't a mapped breakout child, or that lane currently has no resolved path (e.g. its far
        connector is unoccupied). Used to originate a cable trace from the subinterface — the path's
        `cablepath_id` plus the parent trunk's PK identify the single lane to render.
        """
        lane = self.get_breakout_lane()
        if lane is None:
            return None
        # Iterate the prefetched `cable_paths` in Python and match `peer_connector` here rather than
        # with a `.filter()` — a prefetch cache only serves `.all()`, so filtering in SQL would
        # re-query once per row and reintroduce the N+1 this prefetch exists to avoid. See
        # `Interface.cable_columns_prefetch_related_fields`.
        for path in self.parent_interface.cable_paths.all():
            if path.peer_connector == lane["far_connector"]:
                return path
        return None

    def get_breakout_connected_endpoint(self):
        """The ultimate connected endpoint reached through this breakout child interface's lane.

        Where `get_breakout_lane().far_termination` is the *one-hop* cable peer on the parent's
        breakout cable, this is the *n-hop* endpoint: it follows the parent trunk interface's
        already-traced `CablePath` for this lane — past any intermediate front/rear pass-through
        ports — and returns its `destination` `PathEndpoint`. Returns `None` if this isn't a mapped
        breakout child, or if that lane's path is unresolved, split, or otherwise has no destination.
        """
        path = self.get_breakout_lane_cable_path()
        return path.destination if path is not None else None

    def get_breakout_child_interface_for_connector(self, peer_connector):
        """The child (sub)interface whose breakout lane emerges through `peer_connector`, or None.

        For a breakout-trunk interface, each child interface maps to a trunk-connector position
        whose lane surfaces on a specific breakout-side connector (`get_breakout_lane().far_connector`).
        Given that far connector — e.g. one of the trunk's per-lane `CablePath.peer_connector`
        values — return the child interface whose lane matches, so a lane/path can be labeled with
        its subinterface. This is the reverse of `get_breakout_lane_cable_path`.
        """
        for child in self.child_interfaces.all():
            lane = child.get_breakout_lane()
            if lane is not None and lane["far_connector"] == peer_connector:
                return child
        return None


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
    priority = models.PositiveIntegerField()
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

    objects = CableTerminationManager()

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

    objects = CableTerminationManager()

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

        if self.installed_device:
            self._validate_installed_device_parent_chain()

    def _validate_installed_device_parent_chain(self):
        """Validate this bay assignment against the parent chain.

        Ensures:
        - installed_device is not already an ancestor of this bay's device
        - no existing loop in the parent chain
        - device not already in another bay
        - device type is child or parent-child
        """
        seen_device_ids = set()
        parent_bay = DeviceBay.objects.filter(installed_device=self.device).first()
        while parent_bay is not None:
            parent_device = parent_bay.device
            if parent_device == self.installed_device:
                raise ValidationError(
                    "Installing this device would create a loop; it is already an ancestor of this bay's device."
                )
            if parent_device.pk in seen_device_ids:
                raise ValidationError(
                    "The device parent chain already contains a loop; fix existing data before making this assignment."
                )
            seen_device_ids.add(parent_device.pk)
            parent_bay = DeviceBay.objects.filter(installed_device=parent_device).first()

        current_bay = DeviceBay.objects.filter(installed_device=self.installed_device).first()
        if current_bay and current_bay != self:
            raise ValidationError(
                {
                    "installed_device": (
                        f"Cannot install the specified device; device is already installed in {current_bay}"
                    )
                }
            )
        if not self.installed_device.device_type.is_child_device:
            raise ValidationError(
                {
                    "installed_device": (
                        f'Cannot install device "{self.installed_device}"; device-type '
                        f'"{self.installed_device.device_type}" subdevice_role is not "child" or "parent-child".'
                    )
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
                fields=["parent_module", "name"],
                name="dcim_modulebay_parent_module_name_unique",
            )
        ]

    @property
    def parent(self):
        """Walk up parent chain to find the Device that this ModuleBay is installed in, if one exists."""
        return self.parent_device

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

        if self.parent_device and self.parent_module:
            if self.parent_device != (
                nested_device := getattr(self.parent_module.parent_module_bay, "parent_device", None)
            ):
                raise ValidationError(
                    f"{self._meta.verbose_name}.parent_device differs from the parent_module's nested device: {nested_device._meta.verbose_name}"
                )
        elif self.parent_device and not self.parent_module:
            if (
                ModuleBay.objects.filter(parent_device=self.parent_device, parent_module__isnull=True, name=self.name)
                .exclude(pk=self.pk)
                .exists()
            ):
                raise ValidationError(f"A module bay by this name already exists on {self.parent_device}")
        elif not (self.parent_device or self.parent_module):
            raise ValidationError("Either parent_device or parent_module must be set")

        if not self.position:
            self.position = self.name

    clean.alters_data = True

    def save(self, *args, **kwargs):
        if not self.present_in_database:
            if self.parent_device is None and self.parent_module is not None:
                self.parent_device = getattr(self.parent_module.parent_module_bay, "parent_device", None)
        super().save(*args, **kwargs)
