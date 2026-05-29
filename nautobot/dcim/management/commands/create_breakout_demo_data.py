"""Generate demo data showcasing breakout cables for manual testing of the cable trace renderer.

Each scenario creates DEMO-prefixed objects so the dataset is easy to flush and re-create. Pass
`--flush` to wipe demo objects before generating. New scenarios should be added as `_scenario_*`
methods invoked from `handle()`; the helpers below cover the common factory shapes.
"""

from django.core.management.base import BaseCommand
from django.db import transaction

from nautobot.dcim.choices import (
    CableTypeChoices,
    InterfaceTypeChoices,
)
from nautobot.dcim.models import (
    Cable,
    CableType,
    Device,
    DeviceType,
    Interface,
    Location,
    LocationType,
    Manufacturer,
)
from nautobot.extras.models import Role, Status


class Command(BaseCommand):
    help = "Generate demo data showcasing breakout cables for manual testing of the cable trace SVG renderer."

    def add_arguments(self, parser):
        parser.add_argument(
            "--flush",
            action="store_true",
            help="Delete existing demo data (DEMO- prefix) before creating fresh objects.",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        if options["flush"]:
            self._flush()

        self.stdout.write(self.style.NOTICE("Creating breakout cable demo data..."))

        self.status_active = Status.objects.get_for_model(Device).get(name="Active")
        self.status_connected = Status.objects.get_for_model(Cable).get(name="Connected")
        self.status_planned = Status.objects.get_for_model(Cable).get(name="Planned")
        self.intf_status = Status.objects.get_for_model(Interface).first()
        self.device_role = Role.objects.get_for_model(Device).first()

        loc_type, _ = LocationType.objects.get_or_create(name="DEMO Data Center")
        self.location, _ = Location.objects.get_or_create(
            name="DEMO-DC1",
            location_type=loc_type,
            defaults={"status": self.status_active},
        )
        mfg, _ = Manufacturer.objects.get_or_create(name="DEMO-Vendor")
        self.dt_spine, _ = DeviceType.objects.get_or_create(model="DEMO-Spine-Switch", manufacturer=mfg)
        self.dt_leaf, _ = DeviceType.objects.get_or_create(model="DEMO-Leaf-Switch", manufacturer=mfg)

        self.spine1 = self._device("DEMO-SPINE-01", self.dt_spine)
        self.leaves = [self._device(f"DEMO-LEAF-{i:02d}", self.dt_leaf) for i in range(1, 5)]

        self._create_cable_types()

        # Scenarios — each one is independent and idempotent (skips itself if its cable label exists).
        self._scenario_spine_400g_to_4x_leaf_100g()
        self._scenario_100g_to_2x_50g_partial()

        self.stdout.write(self.style.SUCCESS("Demo data created successfully."))
        self.stdout.write(f"  Location: {self.location}")
        self.stdout.write(f"  Devices: {Device.objects.filter(name__startswith='DEMO-').count()}")
        self.stdout.write(f"  Cable types: {CableType.objects.filter(name__startswith='DEMO').count()}")
        self.stdout.write(f"  Cables: {Cable.objects.filter(label__startswith='DEMO').count()}")

    def _flush(self):
        self.stdout.write(self.style.WARNING("Flushing existing demo data..."))
        # Delete in dependency order: cables (which reference terminations on devices) before
        # devices/device types, and CableType last since cables FK into it.
        Cable.objects.filter(label__startswith="DEMO").delete()
        Device.objects.filter(name__startswith="DEMO-").delete()
        DeviceType.objects.filter(model__startswith="DEMO-").delete()
        Manufacturer.objects.filter(name="DEMO-Vendor").delete()
        Location.objects.filter(name="DEMO-DC1").delete()
        LocationType.objects.filter(name="DEMO Data Center").delete()
        CableType.objects.filter(name__startswith="DEMO").delete()

    # ─────────────────────────────────────────────────────────────────
    # Factory helpers
    # ─────────────────────────────────────────────────────────────────

    def _device(self, name, device_type):
        device, _ = Device.objects.get_or_create(
            name=name,
            defaults={
                "device_type": device_type,
                "role": self.device_role,
                "status": self.status_active,
                "location": self.location,
            },
        )
        return device

    def _interface(self, device, name, intf_type=InterfaceTypeChoices.TYPE_100GE_QSFP28):
        interface, _ = Interface.objects.get_or_create(
            device=device,
            name=name,
            defaults={"type": intf_type, "status": self.intf_status},
        )
        return interface

    def _cable(self, *, label, term_a, term_b, cable_type=None, type_choice="", status=None, extra_terminations=()):
        """Create a breakout-aware Cable, idempotent on `label`.

        `extra_terminations` is an iterable of `(termination, side, connector)` tuples that get
        attached via `cable.add_termination(...)` after the cable is saved — used to wire up
        additional B-side connectors on breakout cables beyond the implicit A1/B1 pair.
        """
        existing = Cable.objects.filter(label=label).first()
        if existing is not None:
            return existing
        cable = Cable(
            label=label,
            termination_a=term_a,
            termination_b=term_b,
            status=status or self.status_connected,
            cable_type=cable_type,
            type=type_choice,
        )
        cable.validated_save()
        for termination, side, connector in extra_terminations:
            cable.add_termination(termination, side, connector=connector)
        return cable

    def _create_cable_types(self):
        """Define the breakout CableTypes shared across scenarios. Mapping auto-generates."""
        self.ct_1x4, _ = CableType.objects.get_or_create(
            name="DEMO-1x4 Breakout (400G → 4x100G)",
            defaults={
                "a_connectors": 1,
                "b_connectors": 4,
                "total_lanes": 4,
                "strands_per_lane": 1,
                "description": "400G QSFP-DD broken out to 4x 100G SFP28 lanes (DAC/AOC).",
            },
        )
        self.ct_1x2, _ = CableType.objects.get_or_create(
            name="DEMO-1x2 Breakout (100G → 2x50G)",
            defaults={
                "a_connectors": 1,
                "b_connectors": 2,
                "total_lanes": 2,
                "strands_per_lane": 1,
                "description": "100G broken out to 2x 50G lanes.",
            },
        )

    # ─────────────────────────────────────────────────────────────────
    # Scenarios
    # ─────────────────────────────────────────────────────────────────

    def _scenario_spine_400g_to_4x_leaf_100g(self):
        """1x400G spine port broken out to 4x 100G leaf uplinks — the canonical DC breakout."""
        spine = self._interface(self.spine1, "Ethernet1/1", InterfaceTypeChoices.TYPE_400GE_QSFP_DD)
        leaves = [self._interface(leaf, "Ethernet1/1", InterfaceTypeChoices.TYPE_100GE_QSFP28) for leaf in self.leaves]
        self._cable(
            label="DEMO-BKO-SPINE-LEAF-400G",
            term_a=spine,
            term_b=leaves[0],
            cable_type=self.ct_1x4,
            type_choice=CableTypeChoices.TYPE_DAC_PASSIVE,
            extra_terminations=[(leaves[i], "B", i + 1) for i in range(1, 4)],
        )

    def _scenario_100g_to_2x_50g_partial(self):
        """100G → 2x50G with B-connector-2 intentionally uncabled — exercises the unconnected-lane path."""
        spine = self._interface(self.spine1, "Ethernet1/2", InterfaceTypeChoices.TYPE_100GE_QSFP28)
        leaf_50g_a = self._interface(self.leaves[0], "Ethernet1/2", InterfaceTypeChoices.TYPE_50GE_QSFP28)
        # Only B-connector-1 is wired; the 1x2 breakout's B-connector-2 stays uncabled.
        self._cable(
            label="DEMO-BKO-1x2-PARTIAL",
            term_a=spine,
            term_b=leaf_50g_a,
            cable_type=self.ct_1x2,
            type_choice=CableTypeChoices.TYPE_DAC_PASSIVE,
        )
