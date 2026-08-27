"""Tests for `nautobot.extras.conditions.operators`."""

from decimal import Decimal
from unittest import TestCase

from nautobot.extras.conditions.operators import (
    _as_bool,
    _as_number,
    _as_text,
    ALL_KINDS,
    field_matches,
    FIELD_OPERATOR_KEYS,
    FIELD_OPERATORS,
    KIND_BOOLEAN,
    KIND_DATE,
    KIND_LIST,
    KIND_NUMBER,
    KIND_TEXT,
    OPERATOR_REGISTRY,
    OPERATORS,
    operators_for_kind,
)


class AsNumberTest(TestCase):
    """It is precisely this numeric type forcing that makes the expression `mtu gt 9000` arithmetic rather than alphabetic."""

    def test_native_numbers(self):
        self.assertEqual(_as_number(1500), Decimal("1500"))
        self.assertEqual(_as_number(15.5), Decimal("15.5"))
        self.assertEqual(_as_number(Decimal("9216")), Decimal("9216"))

    def test_numeric_strings(self):
        self.assertEqual(_as_number("9000"), Decimal("9000"))
        self.assertEqual(_as_number("  9000  "), Decimal("9000"))
        self.assertEqual(_as_number("-1.5"), Decimal("-1.5"))

    def test_non_numbers_are_none(self):
        for value in ("Active", "", None, [], {}, "9,000", "1500 bytes"):
            with self.subTest(value=value):
                self.assertIsNone(_as_number(value))

    def test_bool_is_not_a_number(self):
        """`True gt 0` reading as `1 > 0` would be a surprise."""
        self.assertIsNone(_as_number(True))
        self.assertIsNone(_as_number(False))


class AsTextTest(TestCase):
    def test_none_becomes_empty_string(self):
        """choice: `= ""` matches both an empty and an unset field."""
        self.assertEqual(_as_text(None), "")

    def test_values_stringify(self):
        self.assertEqual(_as_text("Active"), "Active")
        self.assertEqual(_as_text(1500), "1500")
        self.assertEqual(_as_text(True), "True")


class AsBoolTest(TestCase):
    def test_truthy_spellings(self):
        for text in ("true", "True", "TRUE", " yes ", "on", "1"):
            with self.subTest(text=text):
                self.assertIs(_as_bool(text), True)

    def test_falsy_spellings(self):
        for text in ("false", "False", "no", "off", "0"):
            with self.subTest(text=text):
                self.assertIs(_as_bool(text), False)

    def test_garbage_is_none(self):
        for text in ("banana", "", "2", None):
            with self.subTest(text=text):
                self.assertIsNone(_as_bool(text))


class FieldMatchesTest(TestCase):
    """The full comparison matrix.

    Each row is (value from the captured change, operator key, target as typed on the form,
    expected verdict, why the case exists). Values deliberately arrive in the shapes the payload
    produces: numbers as numbers, booleans as booleans, related objects reduced to text, tags as
    lists — while the target is always a string, because that is what the form stores.
    """

    CASES = (
        # --- equals: booleans ---
        (True, "=", "true", True, "bool field matches lowercase 'true' from the form"),
        (True, "=", "True", True, "bool field matches Python-style 'True'"),
        (True, "=", "1", True, "bool field matches '1'"),
        (False, "=", "no", True, "bool field matches 'no'"),
        (True, "=", "false", False, "bool mismatch"),
        (True, "=", "banana", False, "unparseable bool target fails, does not error"),
        (False, "=", "", False, "empty target is not a boolean spelling"),
        # --- equals: numbers and text ---
        ("1500", "=", "1500.0", True, "numeric strings compare numerically"),
        (1500, "=", "1500", True, "number vs numeric string"),
        (0, "=", "0", True, "zero equals zero, not falsy-fails-equals"),
        ("Active", "=", "Active", True, "plain text equality"),
        ("Active", "=", "active", False, "text equality is case-sensitive"),
        (None, "=", "", True, "None folds to empty string (documented)"),
        (["critical"], "=", "critical", False, "a list never equals a scalar"),
        # --- ordering: numeric when both sides look numeric ---
        (9216, "gt", "9000", True, "int vs numeric string compares arithmetically"),
        ("10000", "gt", "9000", True, "the case naive text comparison gets wrong ('1' < '9')"),
        (1500, "gt", "9000", False, "arithmetic below threshold"),
        (9000, "gte", "9000", True, "gte boundary"),
        (9000, "gt", "9000", False, "gt boundary"),
        (1500, "lt", "9000", True, "lt"),
        (9000, "lte", "9000", True, "lte boundary"),
        # --- ordering: lexicographic fallback ---
        ("name-b", "gt", "name-a", True, "text falls back to lexicographic order"),
        (None, "gt", "9000", False, "missing value: '' vs '9000' lexicographically"),
        # --- ordering: ISO dates, by design not by accident ---
        ("2026-08-26", "gt", "2026-01-01", True, "ISO date ordering agrees with chronology"),
        ("2026-08-26T10:00:00Z", "lt", "2027-01-01", True, "datetime vs date prefix still orders"),
        # --- in ---
        ("Active", "in", "Active, Planned", True, "scalar in a comma-separated list, spaces trimmed"),
        ("Retired", "in", "Active, Planned", False, "scalar not in the list"),
        (["core", "warsaw"], "in", "critical,core", True, "list field matches when ANY entry is wanted"),
        (["warsaw"], "in", "critical,core", False, "list field with no wanted entry"),
        (1500, "in", "1500,9000", True, "number stringifies for membership"),
        ("x", "in", "", False, "empty target list matches nothing"),
        # --- contains ---
        ("Warsaw-DC1", "contains", "DC", True, "substring in text"),
        (["a", "b"], "contains", "b", True, "element in a list field"),
        (["a", "b"], "contains", "c", False, "element absent from a list field"),
        (1500, "contains", "50", True, "number treated as text: documented quirk, form hides it via applies_to"),
        # --- startswith / endswith ---
        ("2026-08-26T10:00", "startswith", "2026-08", True, "date prefix works as a month filter"),
        ("device-01", "endswith", "01", True, "endswith on text"),
        ("device-01", "startswith", "DEV", False, "prefix is case-sensitive"),
        (None, "startswith", "", True, "'' startswith '' is True: vacuous but consistent"),
        # --- unknown operator ---
        ("x", "regex", "x", False, "unknown operator fails the row instead of raising"),
        ("x", "", "x", False, "empty operator key"),
    )

    def test_matrix(self):
        for value, operator_key, target, expected, description in self.CASES:
            with self.subTest(description, value=value, operator=operator_key, target=target):
                self.assertIs(field_matches(value, operator_key, target), expected)

    def test_never_raises_on_odd_values(self):
        """Whatever the captured change contains, a comparison is a verdict, never an exception."""
        odd_values = (None, {}, {"name": "Active"}, ["a", ["nested"]], object(), b"bytes", float("nan"))
        for operator_key in FIELD_OPERATOR_KEYS:
            for value in odd_values:
                with self.subTest(operator=operator_key, value=value):
                    result = field_matches(value, operator_key, "target")
                    self.assertIsInstance(result, bool)


class OperatorsForKindTest(TestCase):
    def test_boolean_gets_only_meaningful_operators(self):
        self.assertEqual([op.key for op in operators_for_kind(KIND_BOOLEAN)], ["=", "in"])

    def test_number_gets_equality_ordering_and_membership(self):
        self.assertEqual([op.key for op in operators_for_kind(KIND_NUMBER)], ["=", "gt", "gte", "lt", "lte", "in"])

    def test_date_gets_ordering_and_prefixes(self):
        keys = [op.key for op in operators_for_kind(KIND_DATE)]
        self.assertIn("gt", keys)
        self.assertIn("startswith", keys)
        self.assertNotIn("contains", keys)

    def test_list_gets_membership_only(self):
        self.assertEqual([op.key for op in operators_for_kind(KIND_LIST)], ["in", "contains"])

    def test_text_excludes_ordering(self):
        keys = [op.key for op in operators_for_kind(KIND_TEXT)]
        self.assertNotIn("gt", keys)
        self.assertIn("contains", keys)

    def test_unknown_kind_degrades_to_everything(self):
        """An unclassified field type must get today's behaviour, not an empty dropdown."""
        self.assertEqual(operators_for_kind("geo"), OPERATORS)
        self.assertEqual(operators_for_kind(None), OPERATORS)

    def test_every_operator_is_reachable_from_some_kind(self):
        """An operator no kind offers is dead UI: it can be stored but never picked."""
        reachable = set()
        for kind in ALL_KINDS:
            reachable.update(op.key for op in operators_for_kind(kind))
        self.assertEqual(reachable, set(FIELD_OPERATOR_KEYS))


class OperatorRegistryTest(TestCase):
    """Consistency of the module's public structures with each other."""

    def test_registry_covers_all_operators_bijectively(self):
        self.assertEqual(len(OPERATOR_REGISTRY), len(OPERATORS))
        for operator in OPERATORS:
            self.assertIs(OPERATOR_REGISTRY[operator.key], operator)

    def test_field_operators_shape_and_order(self):
        """`FIELD_OPERATORS` feeds Django choices and the preset parameter schema: (key, label), form order."""
        self.assertEqual(FIELD_OPERATORS, tuple((op.key, op.label) for op in OPERATORS))
        self.assertEqual(FIELD_OPERATOR_KEYS, tuple(op.key for op in OPERATORS))

    def test_applies_to_uses_known_kinds_only(self):
        for operator in OPERATORS:
            with self.subTest(operator=operator.key):
                self.assertTrue(operator.applies_to <= ALL_KINDS)
                self.assertTrue(operator.applies_to, "an operator applying to nothing is unpickable")

    def test_operators_are_immutable(self):
        with self.assertRaises(AttributeError):
            OPERATORS[0].key = "hacked"

    def test_no_not_equals_operator(self):
        """Negation is the row's `negate` flag; a second negation path would let the two drift."""
        self.assertNotIn("!=", FIELD_OPERATOR_KEYS)
        self.assertNotIn("ne", FIELD_OPERATOR_KEYS)
