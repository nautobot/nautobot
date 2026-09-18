"""Tests for `nautobot.extras.conditions.validation`."""

from django.core.exceptions import ValidationError
from django.test import SimpleTestCase, tag

from nautobot.extras.conditions.errors import ConditionValidationError
from nautobot.extras.conditions.presets import ConditionPresetError, register_builtin_condition_presets
from nautobot.extras.conditions.rows import ConditionRowError
from nautobot.extras.conditions.validation import validate_conditions

EXPRESSION = {"type": "expression", "source": "data.mtu > 9000"}
PRESET = {"type": "preset", "preset": "field_compare", "values": {"field": "mtu", "operator": "gt", "value": 9000}}
# A row of each kind that fails for its own reason, so one list can show both codes at once.
BAD_EXPRESSION = {"type": "expression", "source": "data.mtu >"}
BAD_PRESET = {"type": "preset", "preset": "field_compare", "values": {"field": "mtu"}}
# A good row between two bad ones, so the numbering has to skip row 2.
MIXED_ROWS = [BAD_EXPRESSION, EXPRESSION, BAD_PRESET]


class ValidationTestCase(SimpleTestCase):
    """`SimpleTestCase`: validating a row compiles its expression, which needs Django's Jinja engine."""

    def setUp(self):
        super().setUp()
        register_builtin_condition_presets()

    def assertRefused(self, value):
        """Run `validate_conditions` expecting it to refuse, and hand back the error it raised."""
        with self.assertRaises(ValidationError) as caught:
            validate_conditions(value)
        return caught.exception


@tag("unit")
class ListOfRowsTest(ValidationTestCase):
    def test_a_list_of_good_rows_passes(self):
        self.assertIsNone(validate_conditions([EXPRESSION, PRESET]))

    def test_an_empty_list_passes(self):
        """No conditions means every change passes, so an empty list is not an error."""
        self.assertIsNone(validate_conditions([]))

    def test_anything_but_a_list_is_refused_by_its_type(self):
        """Turning an empty value into `[]` is the field's job, so validation sees - and names - what arrived."""
        for value, type_name in ((None, "NoneType"), ("", "str"), ({}, "dict"), (EXPRESSION, "dict")):
            with self.subTest(value=value):
                error = self.assertRefused(value)
                self.assertIsInstance(error, ConditionValidationError)
                self.assertEqual(error.code, ConditionValidationError.code)
                self.assertIn(f"not {type_name}", error.messages[0])


@tag("unit")
class ErrorReportingTest(ValidationTestCase):
    def test_every_bad_row_is_reported_in_one_pass(self):
        """Both bad rows come back from one call, so they are fixed in one pass rather than one save each."""
        self.assertEqual(len(self.assertRefused(MIXED_ROWS).messages), 2)

    def test_numbers_count_rows_from_one(self):
        messages = self.assertRefused(MIXED_ROWS).messages
        self.assertTrue(messages[0].startswith("Condition 1: "), messages[0])
        self.assertTrue(messages[1].startswith("Condition 3: "), messages[1])

    def test_index_counts_from_zero(self):
        problems = self.assertRefused(MIXED_ROWS).error_list
        self.assertEqual([problem.params["index"] for problem in problems], [0, 2])

    def test_each_problem_keeps_its_original_code(self):
        problems = self.assertRefused([BAD_EXPRESSION, BAD_PRESET]).error_list
        self.assertEqual([problem.code for problem in problems], [ConditionRowError.code, ConditionPresetError.code])

    def test_a_rows_own_params_survive_renumbering(self):
        """`index` is added to what the row said about itself, rather than replacing it."""
        expression_problem, preset_problem = self.assertRefused([BAD_EXPRESSION, BAD_PRESET]).error_list
        self.assertEqual(expression_problem.params["key"], "source")
        self.assertEqual(preset_problem.params["preset"], "field_compare")
        self.assertEqual(preset_problem.params["parameter"], "operator")


@tag("unit")
class PercentSignTest(ValidationTestCase):
    """A message can quote what the user wrote, and Django renders these errors as `message % params`.

    Reading `.messages` is the whole point of each assertion here: an unescaped `%` raises there rather
    than in the code under test, so a person would meet it while being shown their own mistake.
    """

    def test_a_jinja_error_naming_a_percent_renders(self):
        error = self.assertRefused([{"type": "expression", "source": "data.mtu > % 9000"}])
        self.assertIn("unexpected '%'", error.messages[0])

    def test_a_template_delimiter_renders(self):
        error = self.assertRefused([{"type": "expression", "source": "{% if data.mtu %}x{% endif %}"}])
        self.assertIn("{%", error.messages[0])
