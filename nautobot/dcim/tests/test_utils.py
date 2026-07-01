from django.core.exceptions import ValidationError

from nautobot.core.testing import TestCase
from nautobot.dcim.models import Device, DeviceType, Interface, Location, LocationType, Manufacturer
from nautobot.dcim.utils import (
    build_connector_row_layout,
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
