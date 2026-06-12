"""Bulk Connect — create many cables at once from one "template" cable plus a count.

The user fills in a single cable on the connection form and sets a **Count**. We then create that
many cables: each side starts from the ports the user picked and walks the device's (or circuit's)
natural port order to fill in the rest. The chosen ``CableType`` decides the shape — a normal type
makes N two-ended cables, a breakout type makes N breakout cables.

This module is the single place that logic lives, so the form (and any future API) just hands it a
spec. It has no models of its own; model imports happen inside functions to avoid an import cycle.

Examples:

* Normal 1x1, Count=4: pick ``A.RP1`` + ``B.RP1`` -> RP1<->RP1, RP2<->RP2, RP3<->RP3, RP4<->RP4.
* Breakout 1x4, pick only ``A.Xcvr1`` + ``B.SFP1``, Count=3 -> Xcvr1<->SFP1, Xcvr2<->SFP2, Xcvr3<->SFP3.
* Breakout 1x4, pick ``A.Xcvr1`` + all four B ports, Count=3 -> Xcvr1<->SFP1-4, Xcvr2<->SFP5-8, Xcvr3<->SFP9-12.
"""

from dataclasses import dataclass, field
from typing import Optional

from django.core.exceptions import ValidationError
from django.db import transaction

CABLE_END_A = "A"
CABLE_END_B = "B"


# ─── Input / output structures (not database models) ───


@dataclass
class ConnectorSelection:
    """One termination the user picked, and where it sits (side + connector)."""

    side: str  # "A" or "B"
    connector: int
    termination: object  # an Interface / RearPort / CircuitTermination / ... instance


@dataclass
class BulkConnectSpec:
    """Everything needed to run a bulk connect: the template picks, the count, and the shared
    cable attributes. Built by the form (or a serializer) and handed to the service."""

    cable_type: Optional[object]  # dcim.CableType, or None for a plain 1x1 cable
    selections: list  # the template — list[ConnectorSelection]
    count: int  # how many cables to create
    status: object  # extras.Status
    label: str = ""
    color: str = ""
    length: Optional[int] = None
    length_unit: str = ""
    type: str = ""
    tags: list = field(default_factory=list)


@dataclass
class ResolvedSide:
    """One cable end after auto-fill: the connectors in play and the full ordered list of
    terminations (the user's picks plus the ports we walked to)."""

    side: str
    connectors: list  # connector numbers, in order (e.g. [1] or [1, 2, 3, 4])
    terminations: list
    sel: int  # terminations per cable on this side (== len(connectors))

    @property
    def filled_cables(self):
        """How many whole cables this side has enough terminations for."""
        if not self.sel:
            return 0
        return len(self.terminations) // self.sel

    def block(self, cable_index):
        """The terminations belonging to one cable (0-based), lined up with ``connectors``."""
        start = cable_index * self.sel
        return self.terminations[start : start + self.sel]


@dataclass
class BulkConnectResult:
    """The outcome of a run: the cables created, and a bit of context about them."""

    cables: list
    is_breakout: bool
    count: int


# ─── Natural-ordering walk ───


def _open_siblings(start):
    """Open (uncabled) ports of the same kind on the same device/circuit as ``start``, in the order
    the UI lists them — the list the walk steps through, so already-cabled ports are skipped.

    Finds the foreign key on the termination model that points back to the parent's model, so it
    works for every type (Interface/RearPort/... on a Device, CircuitTermination on a Circuit, etc.)
    and honors that model's natural ``Meta.ordering``.
    """
    model = type(start)
    parent = start.parent
    for fk_field in model._meta.get_fields():
        if getattr(fk_field, "many_to_one", False) and fk_field.related_model is type(parent):
            return list(model.objects.filter(**{fk_field.name: parent}, cable_termination__isnull=True))
    # No link to the parent's model (e.g. a module-attached component) — return just the start so
    # auto-fill quietly does nothing rather than walking the wrong set.
    return [start]


def walk_terminations(start, count):
    """Return up to ``count`` open ports starting at ``start``, in natural order.

    Skips already-cabled ports and stops early if it runs out. Also used by the form's per-connector
    "Fill" button.
    """
    if count < 1:
        return []
    siblings = _open_siblings(start)
    for idx, term in enumerate(siblings):
        if term.pk == start.pk:
            return siblings[idx : idx + count]
    return [start]


# ─── Service ───


class BulkCableConnectService:
    """Turns a :class:`BulkConnectSpec` into cables.

    Three steps: ``resolve()`` works out the terminations, ``validate()`` checks the whole plan, and
    ``run()`` does both and then creates the cables. ``resolve`` and ``validate`` don't touch the
    database, so callers (the view, tests) can use them to preview or pre-validate.
    """

    def __init__(self, spec, user):
        # `user` is required (not defaulted) so the permission check can never be silently skipped:
        # this service writes cables, and a missing user must fail closed, not open.
        self.spec = spec
        self.user = user

    # -- public --

    def run(self):
        """Validate the plan, then create the cables in one transaction."""
        resolved = self.resolve()
        self.validate(resolved)
        return self._create_cables(resolved)

    def resolve(self):
        """Work out each side's terminations (the picks plus the walked-in ports). No DB writes."""
        return {
            CABLE_END_A: self._resolve_side(CABLE_END_A),
            CABLE_END_B: self._resolve_side(CABLE_END_B),
        }

    def validate(self, resolved):
        """Check what only the bulk operation can know before anything is created.

        Deliberately narrow: per-cable field rules (status validity, length/unit, already-connected
        terminations, pair compatibility) are enforced by ``Cable.clean()`` and
        ``CableToCableTermination.clean()`` when the rows are saved, and the whole create runs in one
        transaction that rolls back on any failure — so re-checking them here would just duplicate the
        model. What stays is the bulk math (each side must fill ``count`` whole cables) and object-level
        permissions, which the model has no way to know about.
        """
        errors = []
        count = self.spec.count

        if count < 1:
            errors.append("Count (number of cables) must be at least 1.")

        for side in (CABLE_END_A, CABLE_END_B):
            errors.extend(self._validate_side(resolved[side], count))

        if not resolved[CABLE_END_A].sel and not resolved[CABLE_END_B].sel:
            errors.append("Select at least one termination to connect.")

        errors.extend(self._validate_permissions(resolved, count))

        if errors:
            raise ValidationError(errors)

    # -- resolve helpers --

    def _resolve_side(self, side):
        """Build one side's termination list: the user's picks, then the next open ports needed to
        reach ``count`` cables (walking from the last pick)."""
        selections = sorted(
            (s for s in self.spec.selections if s.side == side and s.termination is not None),
            key=lambda s: s.connector,
        )
        connectors = [s.connector for s in selections]
        template = [s.termination for s in selections]
        sel = len(template)
        if sel == 0:
            return ResolvedSide(side=side, connectors=[], terminations=[], sel=0)

        count = self.spec.count
        if count <= 1:
            return ResolvedSide(side=side, connectors=connectors, terminations=list(template), sel=sel)

        # Walk forward from the furthest selected port for the remaining (count - 1) blocks; drop the
        # anchor itself (it's already in the template) with the [1:].
        anchor = self._anchor_termination(template)
        extra = walk_terminations(anchor, (count - 1) * sel + 1)[1:] if anchor is not None else []
        return ResolvedSide(side=side, connectors=connectors, terminations=list(template) + extra, sel=sel)

    @staticmethod
    def _anchor_termination(template):
        """Of the picks on a side, the one furthest down the natural order — where the walk continues."""
        if not template:
            return None
        try:
            order = {term.pk: i for i, term in enumerate(_open_siblings(template[0]))}
        except (AttributeError, NotImplementedError):
            return template[-1]
        return max(template, key=lambda t: order.get(t.pk, -1))

    # -- validate helpers --

    def _validate_side(self, resolved, count):
        """A side must use one port type/parent (the walk is a single stream) and have enough open
        ports to fill every requested cable."""
        errors = []
        if resolved.sel == 0:
            return errors
        models = {
            (type(s.termination), getattr(s.termination, "parent", None))
            for s in self.spec.selections
            if s.side == resolved.side and s.termination is not None
        }
        if len(models) > 1:
            errors.append(
                f"All {resolved.side}-side connectors must use the same termination type and parent "
                f"to auto-fill by count."
            )
            return errors
        if resolved.filled_cables < count:
            errors.append(
                f"{resolved.side} side can only fill {resolved.filled_cables} cable(s) from the "
                f"selected start (requested {count}); not enough terminations remain."
            )
        return errors

    def _validate_permissions(self, resolved, count):
        """The user must be allowed to add cables and to view every device/circuit involved."""
        errors = []
        if not self.user.has_perm("dcim.add_cable"):
            return ["You do not have permission to add cables."]
        parents_by_model = {}
        for side in (CABLE_END_A, CABLE_END_B):
            rside = resolved[side]
            for term in rside.terminations[: count * rside.sel] if rside.sel else []:
                parent = getattr(term, "parent", None)
                if parent is not None:
                    parents_by_model.setdefault(type(parent), set()).add(parent.pk)
        for model, pks in parents_by_model.items():
            allowed = set(model.objects.restrict(self.user, "view").filter(pk__in=pks).values_list("pk", flat=True))
            missing = pks - allowed
            if missing:
                errors.append(f"You do not have permission to view {len(missing)} of the selected {model._meta.verbose_name_plural}.")
        return errors

    def _is_breakout(self):
        """Whether the chosen cable type is a breakout (its A and B connector counts differ)."""
        return bool(self.spec.cable_type and self.spec.cable_type.is_breakout)

    # -- create --

    def _create_cables(self, resolved):
        """Create all the cables and their terminations in one transaction (rolled back on any error)."""
        from nautobot.dcim.models import Cable
        from nautobot.dcim.signals import defer_cable_path_rebuilds

        count = self.spec.count
        cables = []
        # `defer_cable_path_rebuilds` batches the cable-path recalculation into one pass at the end.
        with transaction.atomic():
            with defer_cable_path_rebuilds():
                for i in range(count):
                    cable = Cable(
                        cable_type=self.spec.cable_type,
                        status=self.spec.status,
                        type=self.spec.type,
                        label=self._per_cable_label(i),
                        color=self.spec.color,
                        length=self.spec.length,
                        length_unit=self.spec.length_unit,
                    )
                    cable.validated_save()
                    if self.spec.tags:
                        cable.tags.set(self.spec.tags)
                    for side in (CABLE_END_A, CABLE_END_B):
                        rside = resolved[side]
                        for connector, term in zip(rside.connectors, rside.block(i)):
                            cable.add_termination(term, cable_end=side, connector=connector)
                    cables.append(cable)
        return BulkConnectResult(cables=cables, is_breakout=self._is_breakout(), count=count)

    def _per_cable_label(self, index):
        """When labeling more than one cable, add a ``(1)``, ``(2)``... suffix to keep them distinct."""
        label = self.spec.label
        if label and self.spec.count > 1:
            return f"{label} ({index + 1})"
        return label
