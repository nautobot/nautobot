"""Tests for `nautobot.extras.conditions.rows`."""

import re
from unittest import TestCase

from django.core.exceptions import ValidationError
from django.test import SimpleTestCase, tag

from nautobot.extras.conditions.presets import (
    ConditionPresetError,
    FIELD_COMPARE,
    FIELD_TRANSITION,
    register_builtin_condition_presets,
)
from nautobot.extras.conditions.rows import ConditionRow, ConditionRowError, ExpressionRow, PresetRow

EXPRESSION = {"type": "expression", "source": "data.mtu > 9000"}
PRESET = {"type": "preset", "preset": "field_compare", "values": {"field": "mtu", "operator": "gt", "value": 9000}}


class RowsTestCase(TestCase):
    def setUp(self):
        super().setUp()
        register_builtin_condition_presets()

    def assertRowError(self, row, key, message_fragment):
        with self.assertRaisesRegex(ConditionRowError, re.escape(message_fragment)) as caught:
            ConditionRow.from_dict(row)
        self.assertEqual(caught.exception.params["key"], key)


@tag("unit")
class FromDictTest(RowsTestCase):
    def test_row_error_is_a_validation_error_with_the_row_code(self):
        """`full_clean()` and forms handle it as any ValidationError; callers can also catch it by type."""
        with self.assertRaises(ValidationError) as caught:
            ConditionRow.from_dict("not a row")
        self.assertIsInstance(caught.exception, ConditionRowError)
        self.assertEqual(caught.exception.code, ConditionRowError.code)

    def test_expression_row(self):
        row = ConditionRow.from_dict(EXPRESSION)
        self.assertIsInstance(row, ExpressionRow)
        self.assertEqual(row.source, "data.mtu > 9000")
        self.assertFalse(row.negate)

    def test_preset_row(self):
        row = ConditionRow.from_dict(PRESET)
        self.assertIsInstance(row, PresetRow)
        self.assertIs(row.preset, FIELD_COMPARE)
        self.assertEqual(row.values, PRESET["values"])

    def test_negate_is_read_for_both_types(self):
        self.assertTrue(ConditionRow.from_dict({**EXPRESSION, "negate": True}).negate)
        self.assertTrue(ConditionRow.from_dict({**PRESET, "negate": True}).negate)

    def test_preset_values_default_to_empty(self):
        row = ConditionRow.from_dict({"type": "preset", "preset": "field_changed"})
        self.assertEqual(row.values, {})

    def test_non_mapping_rejected(self):
        for row in (["type", "expression"], "expression", None, 5):
            with self.subTest(row=row):
                self.assertRowError(row, "type", "must be a mapping")

    def test_unknown_or_missing_type_rejected(self):
        self.assertRowError({"type": "regex", "source": "x"}, "type", "Unknown condition row type `regex`")
        self.assertRowError({"source": "x"}, "type", "Unknown condition row type `None`")

    def test_negate_must_be_a_boolean(self):
        self.assertRowError({**EXPRESSION, "negate": "yes"}, "negate", "`negate` must be a boolean")

    def test_unknown_keys_rejected_per_type(self):
        self.assertRowError({**EXPRESSION, "values": {}}, "values", "does not accept key(s): values")
        self.assertRowError({**PRESET, "source": "x"}, "source", "does not accept key(s): source")
        self.assertRowError({**PRESET, "params": {}}, "params", "does not accept key(s): params")


@tag("unit")
class ExpressionShapeTest(RowsTestCase):
    def test_source_must_be_a_non_empty_string(self):
        for source in (None, "", "   ", 5, ["x"]):
            with self.subTest(source=source):
                self.assertRowError({"type": "expression", "source": source}, "source", "non-empty `source`")

    def test_template_delimiters_rejected_with_guidance(self):
        for source in ("{{ data.mtu > 9000 }}", "{% if data.mtu %}true{% endif %}"):
            with self.subTest(source=source):
                self.assertRowError({"type": "expression", "source": source}, "source", "bare expression")

    def test_multiline_source_is_fine(self):
        row = ConditionRow.from_dict({"type": "expression", "source": "data.mtu > 9000\nand data.name"})
        self.assertIn("\n", row.source)


@tag("unit")
class PresetShapeTest(RowsTestCase):
    def test_unknown_preset_rejected(self):
        self.assertRowError({"type": "preset", "preset": "no_such"}, "preset", "Unknown condition preset `no_such`")
        self.assertRowError({"type": "preset"}, "preset", "Unknown condition preset `None`")

    def test_values_must_be_a_mapping(self):
        self.assertRowError({**PRESET, "values": ["mtu"]}, "values", "`values` must be a mapping")


@tag("unit")
class ResolveTest(RowsTestCase):
    def test_expression_resolves_to_its_own_source_and_no_context(self):
        self.assertEqual(ConditionRow.from_dict(EXPRESSION).resolve(), ("data.mtu > 9000", {}))

    def test_preset_resolves_to_catalog_source_and_param_variables(self):
        source, context = ConditionRow.from_dict(PRESET).resolve()
        self.assertEqual(source, FIELD_COMPARE.source)
        self.assertEqual(context, {"param_field": "mtu", "param_operator": "gt", "param_value": 9000})

    def test_preset_missing_required_value_raises_at_resolve(self):
        row = ConditionRow.from_dict({"type": "preset", "preset": "field_compare", "values": {"field": "mtu"}})
        with self.assertRaises(ConditionPresetError):
            row.resolve()

    def test_base_class_implements_nothing(self):
        base = ConditionRow(negate=False)
        for method in (base.clean, base.resolve, base.to_dict):
            with self.subTest(method=method.__name__):
                with self.assertRaises(NotImplementedError):
                    method()


@tag("unit")
class CleanTest(RowsTestCase, SimpleTestCase):
    """`SimpleTestCase`: compiling an expression needs Django's Jinja engine, not the database."""

    def test_expression_clean_compiles_the_source(self):
        ConditionRow.from_dict(EXPRESSION).clean()

    def test_expression_syntax_error_refused_at_source(self):
        row = ConditionRow.from_dict({"type": "expression", "source": "data.mtu >"})
        with self.assertRaisesRegex(ConditionRowError, "Invalid condition expression") as caught:
            row.clean()
        self.assertEqual(caught.exception.params["key"], "source")

    def test_preset_clean_delegates_to_clean_values(self):
        ConditionRow.from_dict(PRESET).clean()
        bad = ConditionRow.from_dict({**PRESET, "values": {"field": "mtu", "operator": "regex", "value": 9000}})
        with self.assertRaises(ConditionPresetError) as caught:
            bad.clean()
        self.assertEqual(caught.exception.params["parameter"], "operator")

    def test_from_dict_does_not_validate_values(self):
        """Shape now, values at save: an unknown value name parses and fails only in `clean()`."""
        row = ConditionRow.from_dict({**PRESET, "values": {**PRESET["values"], "extra": "x"}})
        with self.assertRaises(ValidationError):
            row.clean()


@tag("unit")
class ToDictTest(RowsTestCase):
    def test_expression_round_trips_with_negate_made_explicit(self):
        self.assertEqual(
            ConditionRow.from_dict(EXPRESSION).to_dict(),
            {"type": "expression", "source": "data.mtu > 9000", "negate": False},
        )

    def test_preset_round_trips_with_declared_values_only(self):
        row = ConditionRow.from_dict({**PRESET, "values": {**PRESET["values"], "extra": "x"}})
        self.assertEqual(
            row.to_dict(),
            {"type": "preset", "preset": "field_compare", "values": PRESET["values"], "negate": False},
        )

    def test_to_dict_output_parses_back_equal(self):
        for stored in (EXPRESSION, PRESET, {**PRESET, "negate": True}):
            with self.subTest(stored=stored):
                row = ConditionRow.from_dict(stored)
                self.assertEqual(ConditionRow.from_dict(row.to_dict()), row)

    def test_transition_values_keep_declared_order(self):
        row = ConditionRow.from_dict(
            {
                "type": "preset",
                "preset": "field_transition",
                "values": {"to": "Active", "field": "status", "from": "Staged"},
            }
        )
        self.assertEqual(list(row.to_dict()["values"]), [parameter.name for parameter in FIELD_TRANSITION.parameters])
