"""Bulk Connect — create many cables at once from one "template" cable plus a count.

A user selects a cable or breakout cable plus a count, and the form auto-fills the
next open ports from each side's furthest pick to make a full plan for all the cables.
The user reviews that plan on a confirmation screen before committing.
"""

from dataclasses import dataclass, field
from typing import Optional

from django.core.exceptions import ValidationError
from django.db import transaction

CABLE_END_A = "A"
CABLE_END_B = "B"
WALKABLE_MODEL_NAMES = frozenset({"interface", "frontport", "rearport"})


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
        """The terminations belonging to one cable (0-based), lined up with `connectors`."""
        start = cable_index * self.sel
        return self.terminations[start : start + self.sel]


def walk_terminations(start, limit):
    """Return up to `limit` open ports starting at `start`, in natural (`_name`) order."""
    if limit < 1:
        return []
    if start._meta.model_name not in WALKABLE_MODEL_NAMES:
        return [start]
    # All open ports on the same device, in name order. Per PR #9060 every interface/port carries a
    # populated `device` FK (including module-attached ones), so scoping by device covers both cases.
    return list(
        type(start)
        .objects.filter(cable_termination__isnull=True, _name__gte=start._name, device_id=start.device_id)
        .order_by("_name")[:limit]
    )


class BulkCableConnectService:
    """Turns a :class:`BulkConnectSpec` into cables.

    Three steps: `resolve()` works out the terminations, `validate()` checks the whole plan, and
    `run()` does both and then creates the cables. `resolve` and `validate` don't touch the
    database, so callers (the view, tests) can use them to preview or pre-validate.
    """

    def __init__(self, spec):
        self.spec = spec

    # -- public --

    def run(self):
        """Validate the plan, then create the cables in one transaction"""
        if self.spec.count < 2:
            raise ValidationError("Count (number of cables) must be at least 2.")
        resolved = self.resolve()
        self.validate(resolved)
        return self._create_cables(resolved)

    def resolve(self):
        """Work out each side's terminations: the user's picks (cable 0), plus — only when making more
        than one cable — the next open ports walked from each side's furthest pick to reach `count`
        cables.

        Each side becomes one flat termination list that splits into `count` cables of `sel` ports
        each (`sel` = how many connectors that side has); `block(i)` returns cable `i`'s ports.
        Example: a side whose two connectors were set to interfaces `eth1` and `eth2` (`sel` = 2),
        making `count` = 3 cables::

            user's picks (cable 0):  eth1, eth2
            walked in (cables 1-2):  eth3, eth4, eth5, eth6
            terminations:            [eth1, eth2]  [eth3, eth4]  [eth5, eth6]
                                     cable 0     cable 1     cable 2
        """
        sides = {end: self._side_picks(end) for end in (CABLE_END_A, CABLE_END_B)}
        for rside in sides.values():
            if rside.sel:
                # Natural order is by `_name`, so the furthest pick is just the largest `_name`.
                # Walk from it for the remaining (count - 1) blocks; the walk includes `furthest`
                # itself (already in the picks), so request one extra and drop it with [1:].
                furthest = max(rside.terminations, key=lambda t: getattr(t, "_name", ""))
                rside.terminations += walk_terminations(furthest, (self.spec.count - 1) * rside.sel + 1)[1:]
        return sides

    def validate(self, resolved):
        """Two documented validation rules in the comments."""
        errors = []
        count = self.spec.count

        # Auto-fill only knows how to walk device port types; a count on anything else can't fill.
        unsupported = sorted(
            {
                s.termination._meta.verbose_name
                for s in self.spec.selections
                if s.termination is not None and s.termination._meta.model_name not in WALKABLE_MODEL_NAMES
            }
        )
        if unsupported:
            errors.append(
                "Bulk add auto-fills Interface, Front Port, and Rear Port terminations only; "
                f"connect {', '.join(unsupported)} terminations individually."
            )

        # Each side must reach count whole cables; if the walk hit the end of the device's open ports
        # first, abort rather than create cables with missing terminations.
        for side in (CABLE_END_A, CABLE_END_B):
            rside = resolved[side]
            if rside.sel and rside.filled_cables < count:
                errors.append(
                    f"{side} side can only fill {rside.filled_cables} cable(s) from the selected "
                    f"start (requested {count}); not enough terminations remain."
                )

        if not resolved[CABLE_END_A].sel and not resolved[CABLE_END_B].sel:
            errors.append("Select at least one termination to connect.")

        if errors:
            raise ValidationError(errors)

    def _side_picks(self, side):
        """One side's picks (cable 0) as a `ResolvedSide` — connectors + terminations, before any
        auto-fill. `resolve()` applies the count > 1 walk."""
        picks = sorted(
            (s for s in self.spec.selections if s.side == side and s.termination is not None),
            key=lambda s: s.connector,
        )
        terminations = [s.termination for s in picks]
        return ResolvedSide(
            side=side,
            connectors=[s.connector for s in picks],
            terminations=terminations,
            sel=len(terminations),
        )

    def _create_cables(self, resolved):
        """Create all the cables and their terminations in one transaction (rolled back on any error).

        Returns the list of created `Cable` instances.
        """
        from nautobot.dcim.models import Cable
        from nautobot.dcim.signals import defer_cable_path_rebuilds

        count = self.spec.count
        cables = []
        # `defer_cable_path_rebuilds` batches the cable-path recalculation into one pass at the end.
        with transaction.atomic():
            with defer_cable_path_rebuilds():
                for index in range(count):
                    label = self.spec.label
                    per_cable_label = f"{label} ({index + 1})" if label else label
                    cable = Cable(
                        cable_type=self.spec.cable_type,
                        status=self.spec.status,
                        type=self.spec.type,
                        label=per_cable_label,
                        color=self.spec.color,
                        length=self.spec.length,
                        length_unit=self.spec.length_unit,
                    )
                    cable.validated_save()
                    if self.spec.tags:
                        cable.tags.set(self.spec.tags)
                    for side in (CABLE_END_A, CABLE_END_B):
                        rside = resolved[side]
                        for connector, term in zip(rside.connectors, rside.block(index)):
                            cable.add_termination(term, cable_end=side, connector=connector)
                    cables.append(cable)
        return cables
