"""Tests for `nautobot.extras.conditions.operators`."""

from decimal import Decimal
from unittest import TestCase

from django.test import tag

from nautobot.extras.conditions.operators import (
    _as_bool,
    _as_number,
    _as_target_list,
    _as_text,
    _comparable_pair,
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
    ORDERABLE_KINDS,
    SET_MEMBER_KINDS,
    takes_a_set,
    TEXTUAL_KINDS,
)


@tag("unit")
class AsNumberTest(TestCase):
    def test_native_numbers(self):
        self.assertEqual(_as_number(1500), Decimal("1500"))
        self.assertEqual(_as_number(15.5), Decimal("15.5"))
        self.assertEqual(_as_number(Decimal("9216")), Decimal("9216"))

    def test_numeric_strings(self):
        self.assertEqual(_as_number("9000"), Decimal("9000"))
        self.assertEqual(_as_number("  9000  "), Decimal("9000"))
        self.assertEqual(_as_number("-1.5"), Decimal("-1.5"))

    def test_non_numbers_are_none(self):
        for value in ("Active", "", None, [], {}, "1500 bytes"):
            with self.subTest(value=value):
                self.assertIsNone(_as_number(value))

    def test_thousands_separators(self):
        """A comma is not a thousands separator: in half of Europe `9,000` is nine, so accepting it
        would make the same rule mean different numbers to different readers. Python's underscore
        separator is unambiguous and `Decimal` already accepts it, so it passes through."""
        self.assertIsNone(_as_number("9,000"))
        self.assertIsNone(_as_number("9 000"))
        self.assertEqual(_as_number("9_000"), Decimal("9000"))

    def test_bool_is_not_a_number(self):
        """Python's bool subclasses int; treating it as one would order booleans as 0 and 1."""
        self.assertIsNone(_as_number(True))
        self.assertIsNone(_as_number(False))

    def test_float_repr_does_not_leak(self):
        """`Decimal(str(value))` uses the shortest round-trip repr, so 0.1 stays 0.1."""
        self.assertEqual(_as_number(0.1), Decimal("0.1"))
        self.assertEqual(_as_number(1500.0), _as_number("1500"))

    def test_nan_is_not_a_number(self):
        """Decimal parses NaN, then raises on ordering; rejecting it here keeps `gt` a verdict."""
        self.assertIsNone(_as_number(float("nan")))
        self.assertIsNone(_as_number("nan"))
        self.assertIsNone(_as_number(Decimal("NaN")))


@tag("unit")
class AsTextTest(TestCase):
    def test_none_becomes_empty_string(self):
        """Documented in `_as_text`: `= ""` matches both an empty and an unset field."""
        self.assertEqual(_as_text(None), "")

    def test_values_stringify(self):
        self.assertEqual(_as_text("Active"), "Active")
        self.assertEqual(_as_text(1500), "1500")
        self.assertEqual(_as_text(True), "True")

    def test_whitespace_is_preserved(self):
        """The value side is recorded data and is never trimmed: a field that really holds a padded
        string must not match its unpadded spelling. Targets are stripped where they are parsed
        (`_as_bool`, `_as_target_list`), and the form strips its input before storing."""
        self.assertEqual(_as_text(" Active "), " Active ")
        self.assertEqual(_as_text("\tsw-01\n"), "\tsw-01\n")


@tag("unit")
class AsBoolTest(TestCase):
    """Only what this wrapper adds to `is_truthy`.

    The accepted spellings are `is_truthy`'s contract and are covered by `IsTruthyTest` in
    `nautobot/core/tests/test_utils.py`.
    """

    def test_delegates_to_is_truthy(self):
        """One case per direction, enough to catch a dropped or inverted delegation."""
        self.assertIs(_as_bool("yes"), True)
        self.assertIs(_as_bool("no"), False)

    def test_unparseable_target_is_none_not_an_error(self):
        """`is_truthy` raises ValueError; absorbing it is this wrapper's reason to exist.

        A stored condition must never become a dispatch-time exception, so an unparseable target
        yields None and the row simply fails to match. This is deliberately not Python truthiness:
        `bool(2)` and `bool("banana")` are True, but a target is a spelling the user typed, and only
        the spellings `is_truthy` knows count as one.
        """
        for target in ("banana", "", "2", None, 1500, []):
            with self.subTest(target=target):
                self.assertIsNone(_as_bool(target))

    def test_padding_is_stripped_before_parsing(self):
        """`is_truthy` does not strip, so `_as_bool` does.

        A form strips its input before storing; a target written straight through the REST API does
        not, and a padded spelling must not become a silently unmatchable rule.
        """
        self.assertIs(_as_bool(" yes "), True)
        self.assertIs(_as_bool("true\n"), True)
        self.assertIs(_as_bool("\toff "), False)

    def test_non_string_targets_resolve(self):
        """A JSON `true` from the REST API arrives as a bool, not a string; `_as_text` routes it."""
        self.assertIs(_as_bool(True), True)
        self.assertIs(_as_bool(False), False)


@tag("unit")
class AsTargetListTest(TestCase):
    """Two input shapes, one output: the form's list and the API's comma-separated string."""

    def test_list_from_multi_value_field_passes_through(self):
        self.assertEqual(_as_target_list(["Active", "Planned"]), ["Active", "Planned"])

    def test_list_entries_are_stripped_and_stringified(self):
        self.assertEqual(_as_target_list([" a ", 1500, True]), ["a", "1500", "True"])

    def test_list_entry_keeps_its_comma(self):
        """The whole point of accepting a list: a value containing a comma is expressible."""
        self.assertEqual(_as_target_list(["Warsaw, Main", "Krakow"]), ["Warsaw, Main", "Krakow"])

    def test_string_is_split_on_commas(self):
        self.assertEqual(_as_target_list("Active, Planned"), ["Active", "Planned"])

    def test_string_is_not_iterated_character_by_character(self):
        self.assertEqual(_as_target_list("Active"), ["Active"])

    def test_blank_entries_are_dropped(self):
        """Since a missing value compares as "", a stray blank target would match every unset field."""
        self.assertEqual(_as_target_list("a,b,"), ["a", "b"])
        self.assertEqual(_as_target_list("a, ,b"), ["a", "b"])
        self.assertEqual(_as_target_list(["a", "", "  "]), ["a"])

    def test_empty_inputs_are_empty(self):
        for target in ("", None, [], ",,"):
            with self.subTest(target=target):
                self.assertEqual(_as_target_list(target), [])


@tag("unit")
class ComparablePairTest(TestCase):
    """The one conversion rule `=` and the ordering operators share."""

    def test_both_numeric_gives_decimals(self):
        self.assertEqual(_comparable_pair(1500, "1500.0"), (Decimal("1500"), Decimal("1500.0")))
        self.assertEqual(_comparable_pair("10000", "9000"), (Decimal("10000"), Decimal("9000")))

    def test_string_value_gives_text(self):
        """A string value compares as text even against a numeric target."""
        self.assertEqual(_comparable_pair("sw-01", "9000"), ("sw-01", "9000"))

    def test_number_against_non_numeric_target_is_incomparable(self):
        """Ordering a number against a word by its spelling would be meaningless."""
        self.assertIsNone(_comparable_pair(9000, "sw-01"))
        self.assertIsNone(_comparable_pair(float("nan"), "9000"))

    def test_non_scalars_are_incomparable(self):
        for value in (None, True, ["a"], {}, b"bytes", object()):
            with self.subTest(value=value):
                self.assertIsNone(_comparable_pair(value, "x"))


@tag("unit")
class FieldMatchesTest(TestCase):
    """The full comparison matrix, one row per cell of the module docstring's table.

    Each row is (value from the captured change, operator key, target as stored on the row, expected
    verdict, why the case exists). Values arrive in the shapes the payload produces: numbers as
    numbers, booleans as booleans, related objects reduced to text, tags as lists. Targets arrive
    as the form stores them: a string, or a list for a set-valued operator.
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
        (1500.0, "=", "1500", True, "float vs numeric string"),
        (Decimal("10.50"), "=", "10.5", True, "Decimal vs numeric string, trailing zero disregarded"),
        (0.1, "=", "0.1", True, "float repr does not leak into equality"),
        (0, "=", "0", True, "zero equals zero, not falsy-fails-equals"),
        (1500, "=", "abc", False, "a number never equals a non-numeric target"),
        ("Active", "=", "Active", True, "plain text equality"),
        ("Active", "=", "active", False, "text equality is case-sensitive"),
        (None, "=", "", True, "None compares as empty string (see _as_text)"),
        # --- equals: lists are sets ---
        (["a", "b"], "=", ["a", "b"], True, "same members"),
        (["a", "b"], "=", ["b", "a"], True, "order disregarded"),
        (["a", "b"], "=", ["b", "a", "a"], True, "repetition disregarded"),
        (["a", "b"], "=", "b, a", True, "string target works for lists too"),
        (["a", "b"], "=", ["a"], False, "missing member"),
        (["a"], "=", ["a", "b"], False, "extra member in target"),
        (["critical"], "=", "critical", True, "one-element list equals its single member as a set"),
        ([], "=", [], True, "empty list equals empty target: no tags"),
        ([], "=", ["a"], False, "empty list does not equal a non-empty target"),
        # --- ordering: numeric when both sides look numeric ---
        (9216, "gt", "9000", True, "int vs numeric string compares arithmetically"),
        ("10000", "gt", "9000", True, "the case naive text comparison gets wrong ('1' < '9')"),
        ("1000", "gt", "9000", False, "and the reverse, so the numeric path is proven both ways"),
        (1500, "gt", "9000", False, "arithmetic below threshold"),
        (15.5, "gt", "15", True, "float orders numerically"),
        (Decimal("9000.00"), "gte", "9000", True, "Decimal orders numerically"),
        (9216, "gt", "abc", False, "a number has no ordering against a non-numeric target"),
        (9000, "gte", "9000", True, "gte boundary"),
        (9000, "gt", "9000", False, "gt boundary"),
        (1500, "lt", "9000", True, "lt"),
        (9000, "lte", "9000", True, "lte boundary"),
        # --- ordering: text and dates go lexicographic ---
        ("name-b", "gt", "name-a", True, "text orders lexicographically"),
        ("2026-08-26", "gt", "2026-01-01", True, "ISO date ordering agrees with chronology"),
        ("2026-08-26T10:00:00Z", "lt", "2027-01-01", True, "datetime vs date still orders"),
        (None, "gt", "9000", False, "a missing value has no ordering"),
        (None, "lt", "9000", False, "a missing value is not 'less than everything' either"),
        # --- ordering: booleans and lists have none ---
        (True, "gt", "0", False, "boolean has no ordering (would otherwise read 'True' > '0')"),
        (False, "lte", "1", False, "boolean has no ordering"),
        (["a"], "gt", "a", False, "list has no ordering"),
        # --- in: equals any of ---
        ("Active", "in", "Active, Planned", True, "scalar in a comma-separated string, spaces trimmed"),
        ("Active", "in", ["Active", "Planned"], True, "scalar in a list target from the form"),
        ("Retired", "in", "Active, Planned", False, "scalar not in the list"),
        ("Warsaw, Main", "in", ["Warsaw, Main", "Krakow"], True, "list target keeps a value's comma"),
        (1500, "in", "1500.0,9000", True, "membership inherits numeric equality"),
        (True, "in", "yes,no", True, "membership inherits boolean equality"),
        (["core", "warsaw"], "in", "critical,core", True, "list field matches when any entry is a target"),
        (["warsaw"], "in", "critical,core", False, "list field with no matching entry"),
        ([1500], "in", ["1500.0"], True, "list entries also inherit numeric equality"),
        ("x", "in", "", False, "empty target list matches nothing"),
        ("x", "in", [], False, "empty list target matches nothing"),
        # --- contains: strings only ---
        ("Warsaw-DC1", "contains", "DC", True, "substring in text"),
        ("Warsaw-DC1", "contains", "dc", False, "substring is case-sensitive"),
        ("2026-08-26", "contains", "-08-", True, "a date is a string, so substring works"),
        (1500, "contains", "50", False, "no substring matching on a number"),
        (True, "contains", "ru", False, "no substring matching on a boolean"),
        (["a", "b"], "contains", "b", False, "no substring matching on a list; lists use in"),
        (None, "contains", "", False, "a missing value is not a string"),
        # --- startswith / endswith: strings only ---
        ("2026-08-26T10:00", "startswith", "2026-08", True, "date prefix works as a month filter"),
        ("device-01", "endswith", "01", True, "endswith on text"),
        ("device-01", "startswith", "DEV", False, "prefix is case-sensitive"),
        (1500, "startswith", "15", False, "no affix matching on a number"),
        (True, "endswith", "ue", False, "no affix matching on a boolean"),
        (None, "startswith", "", False, "a missing value is not a string"),
        # --- unknown operator ---
        ("x", "regex", "x", False, "unknown operator fails the row instead of raising"),
        ("x", "", "x", False, "empty operator key"),
    )

    def test_matrix(self):
        for value, operator_key, target, expected, description in self.CASES:
            with self.subTest(description, value=value, operator=operator_key, target=target):
                self.assertIs(field_matches(value, operator_key, target), expected)

    def test_never_raises_on_odd_values(self):
        """Whatever the captured change contains, a comparison is a verdict, never an exception.

        This asserts a bool rather than False because some odd-looking inputs legitimately match:
        None equals "" by design, and a nested list still contains its scalar entries. The stricter
        claim for values that can never match is `test_non_scalar_values_never_match`.
        """
        odd_values = (None, {}, {"name": "Active"}, ["a", ["nested"]], object(), b"bytes", float("nan"))
        odd_targets = ("target", "", None, ["a", "b"], [], 1500)
        for operator_key in FIELD_OPERATOR_KEYS:
            for value in odd_values:
                for target in odd_targets:
                    with self.subTest(operator=operator_key, value=value, target=target):
                        self.assertIsInstance(field_matches(value, operator_key, target), bool)

    def test_non_scalar_values_never_match(self):
        """A mapping (a relation without a sub-field), bytes, an arbitrary object, NaN: none of these
        is a scalar a target could describe, so every operator returns False."""
        garbage = ({}, {"name": "Active"}, object(), b"bytes", float("nan"))
        targets = ("target", "", "9000", "nan", "{}", ["a", "b"], [])
        for operator_key in FIELD_OPERATOR_KEYS:
            for value in garbage:
                for target in targets:
                    with self.subTest(operator=operator_key, value=value, target=target):
                        self.assertIs(field_matches(value, operator_key, target), False)


@tag("unit")
class OperatorsForKindTest(TestCase):
    """What the form's operator dropdown offers per field kind."""

    def test_boolean_gets_equality_only(self):
        self.assertEqual([op.key for op in operators_for_kind(KIND_BOOLEAN)], ["="])

    def test_number_gets_equality_ordering_and_membership(self):
        self.assertEqual(
            [op.key for op in operators_for_kind(KIND_NUMBER)],
            ["=", "gt", "gte", "lt", "lte", "in"],
        )

    def test_text_gets_every_operator(self):
        self.assertEqual(operators_for_kind(KIND_TEXT), OPERATORS)

    def test_date_is_offered_the_same_as_text(self):
        """A date is an ISO 8601 string in the payload, so every text operator makes sense for it."""
        self.assertEqual(operators_for_kind(KIND_DATE), operators_for_kind(KIND_TEXT))

    def test_list_gets_set_equality_and_membership(self):
        self.assertEqual([op.key for op in operators_for_kind(KIND_LIST)], ["=", "in"])

    def test_unknown_kind_gets_every_operator(self):
        """An unclassified field type must get the full list, not an empty dropdown."""
        self.assertEqual(operators_for_kind("geo"), OPERATORS)
        self.assertEqual(operators_for_kind(None), OPERATORS)

    def test_every_operator_is_reachable_from_some_kind(self):
        """An operator no kind offers is dead UI: it can be stored but never picked."""
        reachable = set()
        for kind in ALL_KINDS:
            reachable.update(op.key for op in operators_for_kind(kind))
        self.assertEqual(reachable, set(FIELD_OPERATOR_KEYS))


@tag("unit")
class TakesASetTest(TestCase):
    """Which operator-kind pairs get the multi-value widget."""

    def test_in_always_takes_a_set(self):
        for kind in ALL_KINDS:
            with self.subTest(kind=kind):
                self.assertTrue(takes_a_set("in", kind))

    def test_equals_takes_a_set_for_lists_only(self):
        self.assertTrue(takes_a_set("=", KIND_LIST))
        for kind in ALL_KINDS - {KIND_LIST}:
            with self.subTest(kind=kind):
                self.assertFalse(takes_a_set("=", kind))

    def test_single_valued_operators_never_take_a_set(self):
        for operator_key in ("gt", "gte", "lt", "lte", "contains", "startswith", "endswith"):
            for kind in ALL_KINDS:
                with self.subTest(operator=operator_key, kind=kind):
                    self.assertFalse(takes_a_set(operator_key, kind))


@tag("unit")
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

    def test_kind_groups_are_subsets_of_all_kinds(self):
        for name, group in (
            ("TEXTUAL_KINDS", TEXTUAL_KINDS),
            ("ORDERABLE_KINDS", ORDERABLE_KINDS),
            ("SET_MEMBER_KINDS", SET_MEMBER_KINDS),
        ):
            with self.subTest(group=name):
                self.assertTrue(group <= ALL_KINDS)
                self.assertTrue(group)

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
