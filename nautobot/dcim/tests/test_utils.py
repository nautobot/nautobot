from django.core.exceptions import ValidationError

from nautobot.circuits.models import Circuit, CircuitTermination, CircuitType, Provider
from nautobot.core.testing import TestCase
from nautobot.dcim.choices import InterfaceTypeChoices
from nautobot.dcim.constants import BREAKOUT_COMPATIBLE_TERMINATION_TYPES
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
from nautobot.dcim.tests.test_views import create_test_device
from nautobot.dcim.utils import (
    build_connector_row_layout,
    cable_status_color_css,
    create_breakout_subinterfaces,
    disconnect_termination,
    generate_cable_breakout_mapping,
    validate_cable_breakout_mapping,
)
from nautobot.extras.models import Role, Status


class DisconnectTerminationTestCase(TestCase):
    """Additional coverage of `disconnect_termination()` — also covered in test_cablepaths.py for common flows."""

    @classmethod
    def setUpTestData(cls):
        location = Location.objects.filter(location_type=LocationType.objects.get(name="Campus")).first()
        manufacturer = Manufacturer.objects.first()
        device_type = DeviceType.objects.create(manufacturer=manufacturer, model="Disconnect Test DT")
        device_role = Role.objects.get_for_model(Device).first()
        device_status = Status.objects.get_for_model(Device).first()
        cls.device = Device.objects.create(
            name="DisconnectTestDevice",
            device_type=device_type,
            role=device_role,
            location=location,
            status=device_status,
        )
        cls.uncabled_interface = Interface.objects.create(
            device=cls.device, name="eth0", status=Status.objects.get_for_model(Interface).first()
        )

    def test_disconnect_termination_with_none_returns_none(self):
        """Passing `None` (e.g. from a caller that already cleared its reference) is a no-op."""
        self.assertIsNone(disconnect_termination(None))

    def test_disconnect_termination_on_uncabled_termination_returns_none(self):
        """A termination that has no `CableToCableTermination` row is also a no-op."""
        self.assertIsNone(disconnect_termination(self.uncabled_interface))


class GenerateCableBreakoutMappingTestCase(TestCase):
    """Test the generate_cable_breakout_mapping utility function."""

    def test_generate_cable_breakout_mapping_minimal(self):
        mapping = generate_cable_breakout_mapping(a_connectors=1, b_connectors=1, total_lanes=4)
        self.assertEqual(len(mapping), 4)
        for lane_index, entry in enumerate(mapping, start=1):
            self.assertEqual(entry["label"], str(lane_index))
            self.assertEqual(entry["a_connector"], 1)
            self.assertEqual(entry["a_position"], lane_index)
            self.assertEqual(entry["b_connector"], 1)
            self.assertEqual(entry["b_position"], lane_index)

    def test_generate_cable_breakout_mapping_breakout(self):
        mapping = generate_cable_breakout_mapping(a_connectors=1, b_connectors=4, total_lanes=8)
        self.assertEqual(len(mapping), 8)
        # All entries are on a_connector 1, positions 1..8
        self.assertEqual([e["a_connector"] for e in mapping], [1] * 8)
        self.assertEqual([e["a_position"] for e in mapping], list(range(1, 9)))
        # B side fills 4 connectors, 2 positions each, in order
        self.assertEqual([e["b_connector"] for e in mapping], [1, 1, 2, 2, 3, 3, 4, 4])
        self.assertEqual([e["b_position"] for e in mapping], [1, 2, 1, 2, 1, 2, 1, 2])

    def test_generate_cable_breakout_mapping_with_labels(self):
        """Custom labels keyed by lane assignment are applied where the key matches, defaults elsewhere."""
        labels = {
            (1, 1, 1, 1): "Tx1",
            (1, 4, 1, 4): "Rx1",
            (9, 9, 9, 9): "ignored — no such lane",
        }
        mapping = generate_cable_breakout_mapping(a_connectors=1, b_connectors=1, total_lanes=4, labels=labels)
        self.assertEqual(mapping[0]["label"], "Tx1")
        self.assertEqual(mapping[1]["label"], "2")  # default
        self.assertEqual(mapping[2]["label"], "3")  # default
        self.assertEqual(mapping[3]["label"], "Rx1")

    def test_generate_cable_breakout_mapping_none_labels(self):
        """`labels=None` behaves the same as not providing the arg at all."""
        default_mapping = generate_cable_breakout_mapping(a_connectors=1, b_connectors=2, total_lanes=2)
        with_none = generate_cable_breakout_mapping(a_connectors=1, b_connectors=2, total_lanes=2, labels=None)
        self.assertEqual(default_mapping, with_none)


class ValidateCableBreakoutMappingTestCase(TestCase):
    """Test the validate_cable_breakout_mapping utility function."""

    def test_validate_cable_breakout_mapping_not_a_list(self):
        with self.assertRaisesRegex(ValidationError, "Mapping must be a JSON array"):
            validate_cable_breakout_mapping({"not": "a list"})

    def test_validate_cable_breakout_mapping_wrong_length(self):
        with self.assertRaisesRegex(ValidationError, "Expected 2 lane definitions, but got 1"):
            validate_cable_breakout_mapping(
                [{"a_connector": 1, "a_position": 1, "b_connector": 1, "b_position": 1}], total_lanes=2
            )

    def test_validate_cable_breakout_mapping_entry_not_dict(self):
        with self.assertRaisesRegex(ValidationError, "Entry 0 must be a JSON object"):
            validate_cable_breakout_mapping(["not a dict"])

    def test_validate_cable_breakout_mapping_missing_keys(self):
        with self.assertRaisesRegex(ValidationError, "missing required keys.*b_connector, b_position"):
            validate_cable_breakout_mapping([{"a_connector": 1, "a_position": 1}])

    def test_validate_cable_breakout_mapping_unknown_keys(self):
        with self.assertRaisesRegex(ValidationError, "unknown keys: bogus"):
            validate_cable_breakout_mapping(
                [{"a_connector": 1, "a_position": 1, "b_connector": 1, "b_position": 1, "bogus": "value"}]
            )

    def test_validate_cable_breakout_mapping_non_integer_value(self):
        with self.assertRaisesRegex(ValidationError, "key 'a_connector' must be a positive integer"):
            validate_cable_breakout_mapping([{"a_connector": "a", "a_position": 1, "b_connector": 1, "b_position": 1}])

    def test_validate_cable_breakout_mapping_out_of_range(self):
        cases = [
            ({"a_connector": 2, "a_position": 1, "b_connector": 1, "b_position": 1}, "a_connector 2 out of range"),
            ({"a_connector": 1, "a_position": 3, "b_connector": 1, "b_position": 1}, "a_position 3 out of range"),
            ({"a_connector": 1, "a_position": 1, "b_connector": 2, "b_position": 1}, "b_connector 2 out of range"),
            ({"a_connector": 1, "a_position": 1, "b_connector": 1, "b_position": 3}, "b_position 3 out of range"),
        ]
        for entry, expected_message in cases:
            with self.subTest(expected_message=expected_message):
                # Pad mapping to the expected size so validate_cable_breakout_mapping reaches the range checks.
                mapping = [
                    entry,
                    {"a_connector": 1, "a_position": 2, "b_connector": 1, "b_position": 2},
                ]
                with self.assertRaisesRegex(ValidationError, expected_message):
                    validate_cable_breakout_mapping(mapping, a_connectors=1, b_connectors=1, total_lanes=2)

    def test_validate_cable_breakout_mapping_duplicate_a_pair(self):
        with self.assertRaisesRegex(ValidationError, r"Duplicate A-side .*: \(1, 1\)"):
            validate_cable_breakout_mapping(
                [
                    {"a_connector": 1, "a_position": 1, "b_connector": 1, "b_position": 1},
                    {"a_connector": 1, "a_position": 1, "b_connector": 1, "b_position": 2},
                ]
            )

    def test_validate_cable_breakout_mapping_duplicate_b_pair(self):
        with self.assertRaisesRegex(ValidationError, r"Duplicate B-side .*: \(1, 1\)"):
            validate_cable_breakout_mapping(
                [
                    {"a_connector": 1, "a_position": 1, "b_connector": 1, "b_position": 1},
                    {"a_connector": 1, "a_position": 2, "b_connector": 1, "b_position": 1},
                ]
            )

    def test_validate_cable_breakout_mapping_non_string_label(self):
        with self.assertRaisesRegex(ValidationError, "Label 1 must be a string"):
            validate_cable_breakout_mapping(
                [{"label": 1, "a_connector": 1, "a_position": 1, "b_connector": 1, "b_position": 1}]
            )

    def test_validate_cable_breakout_mapping_duplicate_label(self):
        with self.assertRaisesRegex(ValidationError, "Duplicate label: same"):
            validate_cable_breakout_mapping(
                [
                    {"label": "same", "a_connector": 1, "a_position": 1, "b_connector": 1, "b_position": 1},
                    {"label": "same", "a_connector": 1, "a_position": 2, "b_connector": 1, "b_position": 2},
                ]
            )

    def test_validate_cable_breakout_mapping_assigns_default_label(self):
        mapping = [
            {"a_connector": 1, "a_position": 1, "b_connector": 1, "b_position": 1},
            {"a_connector": 1, "a_position": 2, "b_connector": 1, "b_position": 2},
        ]
        new_mapping, a_connectors, b_connectors, total_lanes = validate_cable_breakout_mapping(mapping)
        # validate_cable_breakout_mapping fills in missing labels (using the entry index as string).
        self.assertEqual(new_mapping, mapping)
        self.assertEqual(mapping[0]["label"], "0")
        self.assertEqual(mapping[1]["label"], "1")
        self.assertEqual(a_connectors, 1)
        self.assertEqual(b_connectors, 1)
        self.assertEqual(total_lanes, 2)


class BuildConnectorRowLayoutTestCase(TestCase):
    """Test the build_connector_row_layout utility function."""

    @staticmethod
    def _mapping(pairs):
        return [{"a_connector": a, "b_connector": b} for a, b in pairs]

    @staticmethod
    def _spans(rows):
        """Reduce rows to (a_connector, a_rowspan, b_connector, b_rowspan) tuples for assertions."""
        return [(r["a_connector"], r["a_rowspan"], r["b_connector"], r["b_rowspan"]) for r in rows]

    def test_1xn_breakout(self):
        # A single A connector fans out to four B connectors: A1 spans all four rows.
        rows = build_connector_row_layout(self._mapping([(1, 1), (1, 2), (1, 3), (1, 4)]))
        self.assertEqual(
            self._spans(rows),
            [(1, 4, 1, 1), (None, 0, 2, 1), (None, 0, 3, 1), (None, 0, 4, 1)],
        )

    def test_nx1_reverse(self):
        rows = build_connector_row_layout(self._mapping([(1, 1), (2, 1), (3, 1), (4, 1)]))
        self.assertEqual(
            self._spans(rows),
            [(1, 1, 1, 4), (2, 1, None, 0), (3, 1, None, 0), (4, 1, None, 0)],
        )

    def test_straight_2x2(self):
        rows = build_connector_row_layout(self._mapping([(1, 1), (2, 2)]))
        self.assertEqual(self._spans(rows), [(1, 1, 1, 1), (2, 1, 2, 1)])

    def test_shuffled_2x2_mesh(self):
        # Polarity-shuffled 2x2: each A connector wires to BOTH B connectors (a mesh). The layout
        # must stay a structurally valid 2-row table — never overlapping rowspans — even though no
        # rowspan grouping can represent the crossings.
        rows = build_connector_row_layout(
            self._mapping([(1, 1), (1, 1), (1, 2), (1, 2), (2, 1), (2, 1), (2, 2), (2, 2)])
        )
        self.assertEqual(self._spans(rows), [(1, 1, 1, 1), (2, 1, 2, 1)])
        # Every column is fully tiled: rowspans on each side sum to the row count, with no overlap.
        self.assertEqual(sum(r["a_rowspan"] for r in rows), len(rows))
        self.assertEqual(sum(r["b_rowspan"] for r in rows), len(rows))


class CableStatusColorCssTestCase(TestCase):
    def test_cable_status_color_css_virtual_subinterface_no_breakout_lane(self):
        """A virtual sub-interface sets `parent_interface_id` but is not a breakout child, so
        `get_breakout_lane()` returns None. Coloring must not treat it as a breakout lane and blow
        up on `.far_termination`; it should fall through to "".
        Regression test for AttributeError: 'NoneType' object has no attribute 'far_termination'.
        """
        status_active = Status.objects.get_for_model(Interface).first()
        local = create_test_device("Virtual Subiface Local")

        parent = Interface.objects.create(device=local, name="Eth-parent", status=status_active)
        subiface = Interface.objects.create(
            device=local,
            name="Eth-parent.100",
            type=InterfaceTypeChoices.TYPE_VIRTUAL,
            parent_interface=parent,
            status=status_active,
        )

        # Exactly the shape that used to crash.
        self.assertIsNone(subiface.cable)
        self.assertIsNotNone(subiface.parent_interface_id)
        self.assertIsNone(subiface.get_breakout_lane())

        self.assertEqual(cable_status_color_css(subiface), "")


class CreateBreakoutSubinterfacesTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.location = Location.objects.filter(location_type=LocationType.objects.get(name="Campus")).first()
        cls.manufacturer = Manufacturer.objects.first()
        cls.device_role = Role.objects.get_for_model(Device).first()
        cls.device_status = Status.objects.get_for_model(Device).first()
        cls.interface_status = Status.objects.get_for_model(Interface).first()
        cls.cable_status = Status.objects.get_for_model(Cable).get(name="Connected")
        cls.circuit_status = Status.objects.get_for_model(Circuit).first()

    def _create_device(self, name="Breakout Device", pattern="{parent}.{position}"):
        device_type = DeviceType.objects.create(
            manufacturer=self.manufacturer,
            model=f"{name} Type",
            breakout_subinterface_name_pattern=pattern,
        )
        return Device.objects.create(
            name=name,
            device_type=device_type,
            role=self.device_role,
            location=self.location,
            status=self.device_status,
        )

    def _create_interface(
        self, *, device=None, module=None, name, interface_type=InterfaceTypeChoices.TYPE_100GE_QSFP28
    ):
        return Interface.objects.create(
            device=device,
            module=module,
            name=name,
            type=interface_type,
            status=self.interface_status,
        )

    def _create_breakout_type(self, name="test_utils 1x4 breakout", b_connectors=4, total_lanes=4):
        # Use a test-specific name prefix. Migrations already create defaults like "1x4 Breakout",
        # and MySQL treats names like that as duplicates regardless of capitalization.
        cable_type = CableType(name=name, a_connectors=1, b_connectors=b_connectors, total_lanes=total_lanes)
        cable_type.validated_save()
        return cable_type

    def _create_breakout_cable(self, trunk, fanouts, cable_type=None):
        cable_type = cable_type or self._create_breakout_type()
        cable = Cable(termination_a=trunk, termination_b=fanouts[0], cable_type=cable_type, status=self.cable_status)
        cable.validated_save()
        for connector, fanout in enumerate(fanouts[1:], start=2):
            cable.add_termination(fanout, "B", connector=connector)
        return cable

    def _create_non_interface_trunk(self, device, model_name):
        if model_name == "circuittermination":
            circuit = Circuit.objects.create(
                cid=f"Trunk Circuit {Circuit.objects.count() + 1}",
                provider=Provider.objects.first(),
                circuit_type=CircuitType.objects.first(),
                status=self.circuit_status,
            )
            return CircuitTermination.objects.create(circuit=circuit, location=self.location, term_side="A")

        if model_name == "frontport":
            rear_port = RearPort.objects.create(
                device=device,
                name=f"Rear Port {RearPort.objects.count() + 1}",
                positions=4,
            )
            return FrontPort.objects.create(
                device=device,
                name=f"Front Port {FrontPort.objects.count() + 1}",
                rear_port=rear_port,
                rear_port_position=1,
            )

        if model_name == "rearport":
            return RearPort.objects.create(device=device, name=f"Rear Port {RearPort.objects.count() + 1}", positions=4)

        raise NotImplementedError(f"No test trunk factory for {model_name}")

    def test_creates_device_breakout_subinterfaces(self):
        """Create virtual children for every mapped breakout position on a device interface trunk."""
        device = self._create_device()
        trunk = self._create_interface(device=device, name="Ethernet1")
        fanouts = [self._create_interface(device=device, name=f"Ethernet1/{i}") for i in range(1, 5)]
        cable = self._create_breakout_cable(trunk, fanouts)

        created = create_breakout_subinterfaces(cable)

        self.assertEqual(len(created), 4)
        self.assertEqual(
            list(trunk.child_interfaces.order_by("breakout_position").values_list("name", "breakout_position")),
            [("Ethernet1.1", 1), ("Ethernet1.2", 2), ("Ethernet1.3", 3), ("Ethernet1.4", 4)],
        )
        self.assertTrue(all(child.type == InterfaceTypeChoices.TYPE_VIRTUAL for child in created))

    def test_creates_module_breakout_subinterfaces(self):
        """Create virtual children on the same module as a module interface trunk."""
        from nautobot.dcim.models import Module, ModuleBay, ModuleType

        module_type = ModuleType.objects.create(
            manufacturer=self.manufacturer,
            model="Breakout Module Type",
        )
        module_status = Status.objects.get_for_model(Module).first()
        device = self._create_device(name="Fanout Device")
        module_bay = ModuleBay.objects.create(parent_device=device, name="slot 1")
        module = Module.objects.create(
            module_type=module_type,
            status=module_status,
            location=self.location,
            parent_module_bay=module_bay,
        )
        trunk = self._create_interface(device=device, module=module, name="Ethernet2")
        fanouts = [self._create_interface(device=device, name=f"Ethernet2/{i}") for i in range(1, 5)]
        cable = self._create_breakout_cable(trunk, fanouts)

        created = create_breakout_subinterfaces(cable)

        self.assertEqual(len(created), 4)
        self.assertEqual(
            list(trunk.child_interfaces.order_by("breakout_position").values_list("name", "module", "device")),
            [
                ("Ethernet2.1", module.pk, device.pk),
                ("Ethernet2.2", module.pk, device.pk),
                ("Ethernet2.3", module.pk, device.pk),
                ("Ethernet2.4", module.pk, device.pk),
            ],
        )

    def test_position_index_token_renders_zero_based_names(self):
        """Render {position_index} as zero-based while storing breakout_position as one-based."""
        device = self._create_device(pattern="{parent}s{position_index}")
        trunk = self._create_interface(device=device, name="swp1")
        fanouts = [self._create_interface(device=device, name=f"peer{i}") for i in range(2)]
        cable = self._create_breakout_cable(
            trunk,
            fanouts,
            cable_type=self._create_breakout_type(name="test_utils position index 1x2", b_connectors=2, total_lanes=2),
        )

        created = create_breakout_subinterfaces(cable)

        self.assertEqual(len(created), 2)
        self.assertEqual(
            list(trunk.child_interfaces.order_by("breakout_position").values_list("name", "breakout_position")),
            [("swp1s0", 1), ("swp1s1", 2)],
        )

    def test_blank_pattern_skips(self):
        """Do not create children when the trunk interface hardware type has no naming pattern."""
        device = self._create_device(pattern="")
        trunk = self._create_interface(device=device, name="Ethernet3")
        fanouts = [self._create_interface(device=device, name=f"Ethernet3/{i}") for i in range(1, 5)]
        cable = self._create_breakout_cable(trunk, fanouts)

        created = create_breakout_subinterfaces(cable)

        self.assertEqual(created, [])
        self.assertEqual(trunk.child_interfaces.count(), 0)

    def test_existing_child_is_preserved(self):
        """Preserve an existing child for a breakout position and create only missing children."""
        device = self._create_device()
        trunk = self._create_interface(device=device, name="Ethernet4")
        existing_child = Interface.objects.create(
            device=device,
            name="Existing Child",
            type=InterfaceTypeChoices.TYPE_VIRTUAL,
            status=self.interface_status,
            parent_interface=trunk,
            breakout_position=1,
        )
        fanouts = [self._create_interface(device=device, name=f"Ethernet4/{i}") for i in range(2)]
        cable = self._create_breakout_cable(
            trunk,
            fanouts,
            cable_type=self._create_breakout_type(name="test_utils existing child 1x2", b_connectors=2, total_lanes=2),
        )

        created = create_breakout_subinterfaces(cable)

        self.assertEqual(len(created), 1)
        self.assertEqual(created[0].name, "Ethernet4.2")
        self.assertEqual(created[0].breakout_position, 2)
        # Reload the original row to prove it was preserved. If it was deleted, this raises Interface.DoesNotExist.
        existing_child.refresh_from_db()
        self.assertEqual(existing_child.parent_interface, trunk)
        self.assertTrue(Interface.objects.filter(pk=existing_child.pk).exists())
        self.assertEqual(
            list(trunk.child_interfaces.order_by("breakout_position").values_list("name", "breakout_position")),
            [("Existing Child", 1), ("Ethernet4.2", 2)],
        )

    def test_name_collision_raises_validation_error(self):
        """Raise ValidationError when a generated child name already exists on the same device."""
        device = self._create_device()
        trunk = self._create_interface(device=device, name="Ethernet5")
        self._create_interface(device=device, name="Ethernet5.1")
        fanouts = [self._create_interface(device=device, name=f"Ethernet5/{i}") for i in range(2)]
        cable = self._create_breakout_cable(
            trunk,
            fanouts,
            cable_type=self._create_breakout_type(name="test_utils collision 1x2", b_connectors=2, total_lanes=2),
        )

        with self.assertRaisesRegex(ValidationError, "already in use"):
            create_breakout_subinterfaces(cable)

        self.assertEqual(trunk.child_interfaces.count(), 0)

    def test_non_breakout_cable_skips(self):
        """Return no created interfaces for a cable without a breakout cable type."""
        device = self._create_device()
        interface_a = self._create_interface(device=device, name="Ethernet6")
        interface_b = self._create_interface(device=device, name="Ethernet7")
        cable = Cable(termination_a=interface_a, termination_b=interface_b, status=self.cable_status)
        cable.validated_save()

        created = create_breakout_subinterfaces(cable)

        self.assertEqual(created, [])
        self.assertEqual(interface_a.child_interfaces.count(), 0)

    def test_non_interface_trunk_side_skips(self):
        """Return no created interfaces when the breakout trunk termination cannot own subinterfaces."""
        for model_name in sorted(BREAKOUT_COMPATIBLE_TERMINATION_TYPES - {"interface"}):
            with self.subTest(model_name=model_name):
                device = self._create_device(name=f"{model_name} Trunk Device")
                trunk = self._create_non_interface_trunk(device, model_name)
                fanouts = [self._create_interface(device=device, name=f"{model_name} Fanout {i}") for i in range(1, 5)]
                cable_type = self._create_breakout_type(name=f"test_utils {model_name} 1x4 breakout")
                cable = self._create_breakout_cable(trunk, fanouts, cable_type=cable_type)

                created = create_breakout_subinterfaces(cable)

                self.assertEqual(created, [])
                self.assertEqual(Interface.objects.filter(parent_interface__isnull=False).count(), 0)
