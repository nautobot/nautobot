"""Tests for `nautobot.extras.conditions.expressions`."""

from django.test import SimpleTestCase, tag

from nautobot.extras.conditions.expressions import compile_condition, ConditionError


@tag("unit")
class CompileConditionTest(SimpleTestCase):
    def test_compiles_and_evaluates_a_bare_expression(self):
        compiled = compile_condition("data.mtu > 9000")
        self.assertTrue(compiled(data={"mtu": 9216}))
        self.assertFalse(compiled(data={"mtu": 1500}))

    def test_package_helpers_are_available(self):
        compiled = compile_condition("field_matches(field_value(data, 'status.name'), '=', 'Active')")
        self.assertTrue(compiled(data={"status": {"name": "Active"}}))

    def test_missing_nested_value_is_falsy_not_an_error(self):
        """`snapshots.postchange.status` on a delete, where `postchange` is None."""
        compiled = compile_condition("snapshots.postchange.status.name == 'Active'")
        self.assertFalse(compiled(snapshots={"postchange": None}))
        self.assertFalse(compiled(snapshots={}))

    def test_syntax_error_raises_condition_error(self):
        for source in ("data.mtu >", "data.mtu > 9000 and", "'unterminated", "if data.mtu"):
            with self.subTest(source=source):
                with self.assertRaisesRegex(ConditionError, "Invalid condition expression"):
                    compile_condition(source)

    def test_same_source_compiles_once(self):
        self.assertIs(compile_condition("data.mtu > 1"), compile_condition("data.mtu > 1"))

    def test_failed_compilation_is_not_cached(self):
        misses_before = compile_condition.cache_info().misses
        for _ in range(2):
            with self.assertRaises(ConditionError):
                compile_condition("data.mtu >")
        self.assertEqual(compile_condition.cache_info().misses, misses_before + 2)
