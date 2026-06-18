"""Generate demo data showcasing breakout cables for manual testing of the cable trace renderer.

Each scenario creates DEMO-prefixed objects so the dataset is easy to flush and re-create. Pass
`--flush` to wipe demo objects before generating. New scenarios should be added as `_scenario_*`
methods invoked from `handle()`; the helpers below cover the common factory shapes.
"""

from django.contrib.contenttypes.models import ContentType
from django.core.management.base import BaseCommand
from django.db import transaction

from nautobot.circuits.models import Circuit, CircuitTermination, CircuitType, Provider
from nautobot.dcim.choices import (
    CableTypeChoices,
    CableTypePolarityMethodChoices,
    InterfaceTypeChoices,
    PortTypeChoices,
)
from nautobot.dcim.models import (
    Cable,
    CableType,
    Device,
    DeviceType,
    FrontPort,
    Interface,
    Location,
    LocationType,
    Manufacturer,
    RearPort,
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
        self.circuit_status = Status.objects.get_for_model(Circuit).get(name="Active")
        self.device_role = Role.objects.get_for_model(Device).first()

        loc_type, _ = LocationType.objects.get_or_create(name="DEMO Data Center")
        loc_type.content_types.add(ContentType.objects.get_for_model(Device))
        self.location, _ = Location.objects.get_or_create(
            name="DEMO-DC1",
            location_type=loc_type,
            defaults={"status": self.status_active},
        )
        mfg, _ = Manufacturer.objects.get_or_create(name="DEMO-Vendor")
        self.dt_spine, _ = DeviceType.objects.get_or_create(model="DEMO-Spine-Switch", manufacturer=mfg)
        self.dt_leaf, _ = DeviceType.objects.get_or_create(model="DEMO-Leaf-Switch", manufacturer=mfg)
        self.dt_server, _ = DeviceType.objects.get_or_create(model="DEMO-Server", manufacturer=mfg)
        self.dt_patch, _ = DeviceType.objects.get_or_create(model="DEMO-Patch-Panel", manufacturer=mfg)

        self.spine1 = self._device("DEMO-SPINE-01", self.dt_spine)
        self.leaves = [self._device(f"DEMO-LEAF-{i:02d}", self.dt_leaf) for i in range(1, 5)]
        self.servers = [self._device(f"DEMO-SRV-{i:02d}", self.dt_server) for i in range(1, 3)]
        self.patch1 = self._device("DEMO-PATCH-01", self.dt_patch)
        self.patch2 = self._device("DEMO-PATCH-02", self.dt_patch)

        self._create_cable_types()

        # Scenarios — each one is independent and idempotent (skips itself if its cable label exists).
        self._scenario_1_spine_400g_to_4x_leaf_100g()
        self._scenario_2_40g_to_4x10g_server()
        self._scenario_3_100g_to_2x50g_partial()
        self._scenario_4_planned_400g_breakout()
        self._scenario_5_mixed_type_showcase()
        self._scenario_6_2x4_trunk_to_8x1_fanout()
        self._scenario_7_aggregation_perspective()
        self._scenario_8_reverse_fanout_perspective()
        self._scenario_9_polarity_shuffle()
        self._scenario_10_complex_multi_hop_path()

        self.stdout.write(self.style.SUCCESS("Demo data created successfully."))
        self.stdout.write(f"  Location: {self.location}")
        self.stdout.write(f"  Devices: {Device.objects.filter(name__startswith='DEMO-').count()}")
        self.stdout.write(f"  Cable types: {CableType.objects.filter(name__startswith='DEMO').count()}")
        self.stdout.write(f"  Cables: {Cable.objects.filter(label__startswith='DEMO').count()}")

    def _flush(self):
        self.stdout.write(self.style.WARNING("Flushing existing demo data..."))
        # Delete in dependency order: cables (which reference terminations on devices) before
        # devices/device types/circuits, and CableType last since cables FK into it.
        Cable.objects.filter(label__startswith="DEMO").delete()
        CircuitTermination.objects.filter(circuit__cid__startswith="DEMO-").delete()
        Circuit.objects.filter(cid__startswith="DEMO-").delete()
        CircuitType.objects.filter(name__startswith="DEMO-").delete()
        Provider.objects.filter(name__startswith="DEMO-").delete()
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

    def _breakout_children(self, trunk, count):
        """Create `count` numbered virtual child interfaces under a breakout-trunk interface.

        Each child's `breakout_position` (1..count) maps it to a position on the trunk connector's
        breakout cable, demonstrating the child-interface position mapping in the UI.
        """
        children = []
        for position in range(1, count + 1):
            child, _ = Interface.objects.get_or_create(
                device=trunk.device,
                name=f"{trunk.name}.{position}",
                defaults={
                    "type": InterfaceTypeChoices.TYPE_VIRTUAL,
                    "status": self.intf_status,
                    "parent_interface": trunk,
                    "breakout_position": position,
                },
            )
            children.append(child)
        return children

    def _rear_port(self, device, name, positions=1, port_type=PortTypeChoices.TYPE_LC):
        rear, _ = RearPort.objects.get_or_create(
            device=device,
            name=name,
            defaults={"positions": positions, "type": port_type},
        )
        return rear

    def _front_port(self, device, name, rear_port, position=1, port_type=PortTypeChoices.TYPE_LC):
        front, _ = FrontPort.objects.get_or_create(
            device=device,
            name=name,
            defaults={"rear_port": rear_port, "rear_port_position": position, "type": port_type},
        )
        return front

    def _circuit_termination(self, cid, term_side="A"):
        ct_type, _ = CircuitType.objects.get_or_create(name="DEMO-Transit")
        provider, _ = Provider.objects.get_or_create(name="DEMO-ISP")
        circuit, _ = Circuit.objects.get_or_create(
            cid=cid,
            defaults={"circuit_type": ct_type, "provider": provider, "status": self.circuit_status},
        )
        termination, _ = CircuitTermination.objects.get_or_create(
            circuit=circuit,
            term_side=term_side,
            defaults={"location": self.location},
        )
        return termination

    def _cable(self, *, label, term_a, term_b, cable_type=None, type_choice="", status=None, extra_terminations=()):
        """Create a breakout-aware Cable, idempotent on `label`.

        `extra_terminations` is an iterable of `(termination, side, connector)` tuples that get
        attached via `cable.add_termination(...)` after the cable is saved — used to wire up
        additional connectors on breakout cables beyond the implicit A1/B1 pair created by the
        base cable.
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
        """Define the breakout CableTypes shared across scenarios. Mapping auto-generates unless overridden."""
        # 1x4 breakout — used by scenarios 1, 2, 4, 5, and 7. Mapping auto-generates straight-through.
        self.ct_1x4, _ = CableType.objects.get_or_create(
            name="DEMO-1x4 Breakout (400G → 4x100G)",
            defaults={
                "a_connectors": 1,
                "b_connectors": 4,
                "total_lanes": 4,
                "strands_per_lane": 1,
                "description": "1 A-side connector broken out to 4 B-side connectors.",
            },
        )
        # 1x2 breakout — scenario 3.
        self.ct_1x2, _ = CableType.objects.get_or_create(
            name="DEMO-1x2 Breakout (100G → 2x50G)",
            defaults={
                "a_connectors": 1,
                "b_connectors": 2,
                "total_lanes": 2,
                "strands_per_lane": 1,
                "description": "1 A-side connector broken out to 2 B-side connectors.",
            },
        )
        # 2x8 breakout — scenarios 6 and 8. Each A connector carries 4 lanes; 8 individual B legs.
        self.ct_2x8, _ = CableType.objects.get_or_create(
            name="DEMO-2x8 Trunk → 8 Legs",
            defaults={
                "a_connectors": 2,
                "b_connectors": 8,
                "total_lanes": 8,
                "strands_per_lane": 2,
                "polarity_method": CableTypePolarityMethodChoices.METHOD_STRAIGHT,
                "description": "2 A-side trunks (4 lanes each) fanning out to 8 individual B-side legs.",
            },
        )
        # MPO-12 duplex fanout — scenario 7's secondary CableType (wider fan-out, multi-strand lanes).
        # Mapping auto-generates straight-through.
        self.ct_mpo12, _ = CableType.objects.get_or_create(
            name="DEMO-MPO-12 Duplex Fanout",
            defaults={
                "a_connectors": 1,
                "b_connectors": 6,
                "total_lanes": 6,
                "strands_per_lane": 2,
                "polarity_method": CableTypePolarityMethodChoices.METHOD_STRAIGHT,
                "description": "MPO-12 trunk fanning out to 6 LC duplex connections.",
            },
        )
        # Polarity-shuffled even-shaped CableType — scenario 8's secondary use case. The mapping
        # crosses lanes between connectors to demonstrate non-straight-through wiring; the renderer
        # needs to draw these inner lane crossings correctly.
        shuffle_mapping = [
            {"label": "1", "a_connector": 1, "a_position": 1, "b_connector": 1, "b_position": 1},
            {"label": "2", "a_connector": 1, "a_position": 2, "b_connector": 1, "b_position": 2},
            {"label": "3", "a_connector": 1, "a_position": 3, "b_connector": 2, "b_position": 1},
            {"label": "4", "a_connector": 1, "a_position": 4, "b_connector": 2, "b_position": 2},
            {"label": "5", "a_connector": 2, "a_position": 1, "b_connector": 1, "b_position": 3},
            {"label": "6", "a_connector": 2, "a_position": 2, "b_connector": 1, "b_position": 4},
            {"label": "7", "a_connector": 2, "a_position": 3, "b_connector": 2, "b_position": 3},
            {"label": "8", "a_connector": 2, "a_position": 4, "b_connector": 2, "b_position": 4},
        ]
        self.ct_2x2_shuffle, _ = CableType.objects.get_or_create(
            name="DEMO-2x2 Polarity Shuffle",
            defaults={
                "a_connectors": 2,
                "b_connectors": 2,
                "total_lanes": 8,
                "strands_per_lane": 2,
                "is_shuffle": True,
                "polarity_method": CableTypePolarityMethodChoices.METHOD_PAIR_REVERSED,
                "mapping": shuffle_mapping,
                "description": "Two A-side and two B-side MPO connectors with polarity-shuffled lanes between them.",
            },
        )

    # ─────────────────────────────────────────────────────────────────
    # Scenarios
    # ─────────────────────────────────────────────────────────────────

    def _scenario_1_spine_400g_to_4x_leaf_100g(self):
        """1x400G spine port broken out to 4x 100G leaf uplinks — the canonical DC breakout."""
        spine = self._interface(self.spine1, "Ethernet1/1", InterfaceTypeChoices.TYPE_400GE_QSFP_DD)
        leaves = [self._interface(leaf, "Ethernet1/1", InterfaceTypeChoices.TYPE_100GE_QSFP28) for leaf in self.leaves]
        # Numbered sub-interfaces, one per breakout lane, mapping to the four B-side leaf uplinks.
        self._breakout_children(spine, 4)
        self._cable(
            label="DEMO-BKO-SPINE-LEAF-400G",
            term_a=spine,
            term_b=leaves[0],
            cable_type=self.ct_1x4,
            type_choice=CableTypeChoices.TYPE_DAC_PASSIVE,
            extra_terminations=[(leaves[i], "B", i + 1) for i in range(1, 4)],
        )

    def _scenario_2_40g_to_4x10g_server(self):
        """40G QSFP+ → 4x 10G SFP+ server NICs — same 1x4 shape as scenario 1, different speeds and devices."""
        spine = self._interface(self.spine1, "Ethernet2/1", InterfaceTypeChoices.TYPE_40GE_QSFP_PLUS)
        srv_nics = [
            self._interface(self.servers[0], f"eth{i}", InterfaceTypeChoices.TYPE_10GE_SFP_PLUS) for i in range(1, 5)
        ]
        self._cable(
            label="DEMO-BKO-40G-4x10G-SRV",
            term_a=spine,
            term_b=srv_nics[0],
            cable_type=self.ct_1x4,
            type_choice=CableTypeChoices.TYPE_DAC_PASSIVE,
            extra_terminations=[(srv_nics[i], "B", i + 1) for i in range(1, 4)],
        )

    def _scenario_3_100g_to_2x50g_partial(self):
        """100G → 2x50G with B-connector-2 intentionally uncabled — exercises the unconnected-lane path."""
        spine = self._interface(self.spine1, "Ethernet3/1", InterfaceTypeChoices.TYPE_100GE_QSFP28)
        leaf_50g = self._interface(self.leaves[0], "Ethernet2/1", InterfaceTypeChoices.TYPE_50GE_QSFP28)
        self._cable(
            label="DEMO-BKO-1x2-PARTIAL",
            term_a=spine,
            term_b=leaf_50g,
            cable_type=self.ct_1x2,
            type_choice=CableTypeChoices.TYPE_DAC_PASSIVE,
        )

    def _scenario_4_planned_400g_breakout(self):
        """A 1x4 breakout marked Planned — the cable exists but isn't physically installed yet."""
        spine = self._interface(self.spine1, "Ethernet4/1", InterfaceTypeChoices.TYPE_400GE_QSFP_DD)
        leaves = [self._interface(leaf, "Ethernet4/1", InterfaceTypeChoices.TYPE_100GE_QSFP28) for leaf in self.leaves]
        self._breakout_children(spine, 4)
        self._cable(
            label="DEMO-BKO-PLANNED-400G",
            term_a=spine,
            term_b=leaves[0],
            cable_type=self.ct_1x4,
            type_choice=CableTypeChoices.TYPE_DAC_ACTIVE,
            status=self.status_planned,
            extra_terminations=[(leaves[i], "B", i + 1) for i in range(1, 4)],
        )

    def _scenario_5_mixed_type_showcase(self):
        """1x4 breakout where each B-side lane uses a different termination type.

        Lane 1: Interface on a leaf
        Lane 2: FrontPort on a patch panel
        Lane 3: RearPort on a patch panel (bare — no front-port pair)
        Lane 4: CircuitTermination
        """
        spine = self._interface(self.spine1, "Ethernet5/1", InterfaceTypeChoices.TYPE_400GE_QSFP_DD)
        leaf_iface = self._interface(self.leaves[2], "Ethernet5/1", InterfaceTypeChoices.TYPE_100GE_QSFP28)
        patch_rear_paired = self._rear_port(self.patch1, "Rear-Mixed-1")
        patch_front = self._front_port(self.patch1, "Front-Mixed-1", patch_rear_paired)
        patch_rear_bare = self._rear_port(self.patch1, "Rear-Mixed-2")
        circuit_term = self._circuit_termination(cid="DEMO-CID-MIXED")
        self._breakout_children(spine, 4)
        self._cable(
            label="DEMO-BKO-MIXED-TYPES",
            term_a=spine,
            term_b=leaf_iface,
            cable_type=self.ct_1x4,
            type_choice=CableTypeChoices.TYPE_SMF,
            extra_terminations=[
                (patch_front, "B", 2),
                (patch_rear_bare, "B", 3),
                (circuit_term, "B", 4),
            ],
        )

    def _scenario_6_2x4_trunk_to_8x1_fanout(self):
        """2x4 trunk (2 MPO connectors, 4 lanes each) fanning out to 8 individual LC legs."""
        trunks = [
            self._interface(self.spine1, "Ethernet6/1", InterfaceTypeChoices.TYPE_100GE_QSFP28),
            self._interface(self.spine1, "Ethernet6/2", InterfaceTypeChoices.TYPE_100GE_QSFP28),
        ]
        # Each trunk connector carries 4 lanes, so each gets four numbered sub-interfaces. This
        # exercises the multi-connector trunk case (position is relative to each trunk connector).
        for trunk in trunks:
            self._breakout_children(trunk, 4)
        # 8 legs distributed across the four leaves (two ports each).
        legs = [
            self._interface(self.leaves[i // 2], f"Ethernet6/{(i % 2) + 1}", InterfaceTypeChoices.TYPE_10GE_SFP_PLUS)
            for i in range(8)
        ]
        self._cable(
            label="DEMO-BKO-2x4-FANOUT",
            term_a=trunks[0],
            term_b=legs[0],
            cable_type=self.ct_2x8,
            type_choice=CableTypeChoices.TYPE_SMF,
            extra_terminations=[
                (trunks[1], "A", 2),
                *[(legs[i], "B", i + 1) for i in range(1, 8)],
            ],
        )

    def _scenario_7_aggregation_perspective(self):
        """Four single-lane legs aggregating into one 4-lane trunk.

        Same cable shape as scenario 1 (1x4), but viewed from the "many legs → one trunk"
        perspective: the *trunk* still has to live on the A side per model constraint
        (`a_connectors <= b_connectors`), so we connect to leg interfaces on the B side and
        attach an additional CableType — `ct_mpo12` — for variety: an MPO-12 trunk fanning out
        to 6 LC duplex legs in this scenario, demonstrating wider fan-out and multi-strand lanes.
        """
        trunk = self._interface(self.spine1, "Ethernet7/1", InterfaceTypeChoices.TYPE_100GE_QSFP28)
        leg_rears = [
            self._rear_port(self.patch1, f"Rear-Agg-{i}", positions=1, port_type=PortTypeChoices.TYPE_LC)
            for i in range(1, 7)
        ]
        self._cable(
            label="DEMO-BKO-MPO12-AGGREGATION",
            term_a=trunk,
            term_b=leg_rears[0],
            cable_type=self.ct_mpo12,
            type_choice=CableTypeChoices.TYPE_SMF,
            extra_terminations=[(leg_rears[i], "B", i + 1) for i in range(1, 6)],
        )

    def _scenario_8_reverse_fanout_perspective(self):
        """8 individual server NICs feeding into 2 spine trunks via a 2x8 cable.

        Same structural CableType as scenario 6 but the wiring is server-to-spine instead of
        spine-to-leaf — exercises a different trace start point (kicking off from one of the
        servers) and the renderer's handling of a wider, server-focused trace.
        """
        trunks = [
            self._interface(self.spine1, "Ethernet10/1", InterfaceTypeChoices.TYPE_40GE_QSFP_PLUS),
            self._interface(self.spine1, "Ethernet10/2", InterfaceTypeChoices.TYPE_40GE_QSFP_PLUS),
        ]
        # 8 server NICs spread across the two server devices, 4 per server.
        legs = [
            self._interface(self.servers[i // 4], f"eth{(i % 4) + 10}", InterfaceTypeChoices.TYPE_10GE_SFP_PLUS)
            for i in range(8)
        ]
        self._cable(
            label="DEMO-BKO-2x8-REVERSE-FANOUT",
            term_a=trunks[0],
            term_b=legs[0],
            cable_type=self.ct_2x8,
            type_choice=CableTypeChoices.TYPE_SMF,
            extra_terminations=[
                (trunks[1], "A", 2),
                *[(legs[i], "B", i + 1) for i in range(1, 8)],
            ],
        )

    def _scenario_9_polarity_shuffle(self):
        """2-to-2 cable with polarity-shuffled lane mapping — A and B both have 2 MPO connectors.

        The CableType's mapping crosses lanes between connectors (A-conn-1 lanes 3-4 → B-conn-2,
        A-conn-2 lanes 1-2 → B-conn-1), so the renderer needs to draw non-straight-through inner
        lane crossings as an X-pattern between the two A connectors and two B connectors.
        """
        a_trunks = [
            self._interface(self.spine1, "Ethernet9/1", InterfaceTypeChoices.TYPE_400GE_QSFP_DD),
            self._interface(self.spine1, "Ethernet9/2", InterfaceTypeChoices.TYPE_400GE_QSFP_DD),
        ]
        b_trunks = [
            self._interface(self.leaves[3], "Ethernet9/1", InterfaceTypeChoices.TYPE_400GE_QSFP_DD),
            self._interface(self.leaves[3], "Ethernet9/2", InterfaceTypeChoices.TYPE_400GE_QSFP_DD),
        ]
        self._cable(
            label="DEMO-BKO-2x2-SHUFFLE",
            term_a=a_trunks[0],
            term_b=b_trunks[0],
            cable_type=self.ct_2x2_shuffle,
            type_choice=CableTypeChoices.TYPE_SMF,
            extra_terminations=[
                (a_trunks[1], "A", 2),
                (b_trunks[1], "B", 2),
            ],
        )

    def _scenario_10_complex_multi_hop_path(self):
        """Complex multi-hop trace exercising pass-throughs, grouped nodes, and multi-segment cables.

        Topology:
            SPINE-01 Ethernet11/1 (400G QSFP-DD)
                │   1x4 breakout cable
            ┌───┴───┬───┬───┐
            B1      B2  B3  B4
            │       │   │   │
            ├───────┤  PATCH-01 Front-LC-1  PATCH-01 Front-LC-2
            │       │   ╲     │  pass-through to Rear-MPO-1 (positions 1, 2)
        LEAF-01  LEAF-01  Rear-MPO-1
        Eth7/1   Eth7/2       │
                              │  MPO cable
                              ▼
                         PATCH-02 Rear-MPO-1
                          ╱     ╲  pass-through to Front-LC-1/Front-LC-2
                  Front-LC-1   Front-LC-2
                          │           │  LC cables
                  LEAF-02 Eth7/1   LEAF-03 Eth7/1

        Lanes B1/B2 land directly on the same leaf (exercises `grouped_node` colspan).
        Lanes B3/B4 traverse two patch panels with FrontPort↔RearPort pass-throughs.
        """  # noqa: RUF002
        spine = self._interface(self.spine1, "Ethernet11/1", InterfaceTypeChoices.TYPE_400GE_QSFP_DD)

        # B1, B2 — direct to LEAF-01 (same device → grouped node on the renderer).
        leaf1_eth1 = self._interface(self.leaves[0], "Ethernet7/1", InterfaceTypeChoices.TYPE_100GE_QSFP28)
        leaf1_eth2 = self._interface(self.leaves[0], "Ethernet7/2", InterfaceTypeChoices.TYPE_100GE_QSFP28)

        # B3, B4 — to PATCH-01 Front-LC ports paired with a single MPO rear port.
        patch1_rear_mpo = self._rear_port(self.patch1, "Rear-MPO-1", positions=2, port_type=PortTypeChoices.TYPE_MPO)
        patch1_front_lc1 = self._front_port(
            self.patch1, "Front-LC-1", patch1_rear_mpo, position=1, port_type=PortTypeChoices.TYPE_LC
        )
        patch1_front_lc2 = self._front_port(
            self.patch1, "Front-LC-2", patch1_rear_mpo, position=2, port_type=PortTypeChoices.TYPE_LC
        )

        self._cable(
            label="DEMO-BKO-COMPLEX-PATH",
            term_a=spine,
            term_b=leaf1_eth1,
            cable_type=self.ct_1x4,
            type_choice=CableTypeChoices.TYPE_DAC_PASSIVE,
            extra_terminations=[
                (leaf1_eth2, "B", 2),
                (patch1_front_lc1, "B", 3),
                (patch1_front_lc2, "B", 4),
            ],
        )

        # PATCH-02 mirrors PATCH-01: one MPO rear port with two LC front ports.
        patch2_rear_mpo = self._rear_port(self.patch2, "Rear-MPO-1", positions=2, port_type=PortTypeChoices.TYPE_MPO)
        patch2_front_lc1 = self._front_port(
            self.patch2, "Front-LC-1", patch2_rear_mpo, position=1, port_type=PortTypeChoices.TYPE_LC
        )
        patch2_front_lc2 = self._front_port(
            self.patch2, "Front-LC-2", patch2_rear_mpo, position=2, port_type=PortTypeChoices.TYPE_LC
        )

        # MPO trunk between the two patch panels' rear ports.
        self._cable(
            label="DEMO-MPO-PATCH1-PATCH2",
            term_a=patch1_rear_mpo,
            term_b=patch2_rear_mpo,
            type_choice=CableTypeChoices.TYPE_MMF,
        )

        # LC cables from PATCH-02's front ports to the destination leaves.
        leaf2_eth1 = self._interface(self.leaves[1], "Ethernet7/1", InterfaceTypeChoices.TYPE_10GE_SFP_PLUS)
        leaf3_eth1 = self._interface(self.leaves[2], "Ethernet7/1", InterfaceTypeChoices.TYPE_10GE_SFP_PLUS)
        self._cable(
            label="DEMO-PATCH2-LC1-LEAF2",
            term_a=patch2_front_lc1,
            term_b=leaf2_eth1,
            type_choice=CableTypeChoices.TYPE_SMF,
        )
        self._cable(
            label="DEMO-PATCH2-LC2-LEAF3",
            term_a=patch2_front_lc2,
            term_b=leaf3_eth1,
            type_choice=CableTypeChoices.TYPE_SMF,
        )
