from django.core.exceptions import ValidationError

from nautobot.core.testing import TestCase
from nautobot.dcim.utils import generate_cable_breakout_mapping, validate_cable_breakout_mapping


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
        validate_cable_breakout_mapping(mapping)
        # validate_cable_breakout_mapping fills in missing labels (using the entry index as string).
        self.assertEqual(mapping[0]["label"], "0")
        self.assertEqual(mapping[1]["label"], "1")
