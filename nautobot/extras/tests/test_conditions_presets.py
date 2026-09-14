"""Tests for `nautobot.extras.conditions.presets`."""

import re
from unittest import TestCase

from django.core.exceptions import ValidationError
from django.test import tag

from nautobot.extras.conditions.presets import (
    BUILTIN_CONDITION_PRESETS,
    ConditionPreset,
    ConditionPresetError,
    FIELD_CHANGED,
    FIELD_COMPARE,
    FIELD_TRANSITION,
    get_condition_preset,
    get_condition_presets,
    PARAM_CONTEXT_PREFIX,
    PresetParameter,
    register_builtin_condition_presets,
    register_condition_preset,
    USER_IS,
)
from nautobot.extras.registry import registry


def make_preset(key="test_preset", source="true", parameters=()):
    return ConditionPreset(key=key, label="Test", description="", source=source, parameters=parameters)


class RegistryIsolationMixin:
    """Track and remove everything a test registers, so the global registry stays clean."""

    def setUp(self):
        super().setUp()
        self._keys_before = set(registry["condition_presets"])

    def tearDown(self):
        for key in set(registry["condition_presets"]) - self._keys_before:
            del registry["condition_presets"][key]
        super().tearDown()


@tag("unit")
class DefinitionValidationTest(TestCase):
    """Names that end up as identifiers are checked when the preset is defined."""

    def test_parameter_name_must_be_an_identifier(self):
        """The name becomes the `param_<name>` variable in the expression."""
        for name in ("my parameter", "1st", "field-name", ""):
            with self.subTest(name=name):
                with self.assertRaisesRegex(ValueError, re.escape(f"`{name}` must be a valid identifier")):
                    PresetParameter(name=name, label="x")

    def test_preset_key_must_be_an_identifier(self):
        for key in ("field compare", "field-compare", "1field", ""):
            with self.subTest(key=key):
                with self.assertRaisesRegex(ValueError, re.escape(f"`{key}` must be a valid identifier")):
                    make_preset(key=key)

    def test_identifiers_pass(self):
        PresetParameter(name="from_value", label="x")
        make_preset(key="my_preset_2")


@tag("unit")
class PresetParameterCleanTest(TestCase):
    """The parameter validates its own value - kind, requiredness and choices live with it."""

    def test_required_rejects_missing_and_empty(self):
        parameter = PresetParameter(name="field", label="Field")
        for value in (None, ""):
            with self.subTest(value=value):
                with self.assertRaisesRegex(ConditionPresetError, re.escape("`field` is required")):
                    parameter.clean(value)

    def test_optional_accepts_missing(self):
        PresetParameter(name="note", label="Note", required=False).clean(None)

    def test_json_scalars_accepted(self):
        """The form stores the target in the canonical type for the field's kind."""
        parameter = PresetParameter(name="value", label="Value")
        for value in ("Active", 9000, 15.5, True, False):
            with self.subTest(value=value):
                parameter.clean(value)

    def test_non_scalar_rejected_by_type_name(self):
        with self.assertRaisesRegex(ConditionPresetError, re.escape("must be a string, number or boolean, not dict")):
            PresetParameter(name="value", label="Value").clean({"a": 1})

    def test_choice_enforces_declared_values(self):
        parameter = PresetParameter(name="op", label="Op", kind="choice", choices=(("=", "eq"), ("gt", "gt")))
        parameter.clean("gt")
        with self.assertRaisesRegex(ConditionPresetError, re.escape("must be one of: =, gt")):
            parameter.clean("regex")

    def test_multiple_accepts_a_list_of_strings(self):
        """The form's MultiValueCharField stores a list; `_as_target_list` accepts it downstream."""
        parameter = PresetParameter(name="value", label="Value", multiple=True)
        parameter.clean(["a", "b"])
        parameter.clean("a,b")

    def test_multiple_rejects_non_string_entries(self):
        """Storage is uniformly text, inside a list as much as outside it."""
        parameter = PresetParameter(name="value", label="Value", multiple=True)
        with self.assertRaisesRegex(ConditionPresetError, re.escape("entries must be strings")):
            parameter.clean(["a", 1500])

    def test_single_valued_parameter_rejects_a_list(self):
        """A list left over from a set-valued operator must fail loudly, not silently never match."""
        with self.assertRaisesRegex(ConditionPresetError, re.escape("takes a single value, not a list")):
            PresetParameter(name="field", label="Field").clean(["a"])

    def test_required_rejects_empty_list(self):
        with self.assertRaisesRegex(ConditionPresetError, re.escape("`value` is required")):
            PresetParameter(name="value", label="Value", multiple=True).clean([])

    def test_context_name_applies_the_prefix(self):
        self.assertEqual(PresetParameter(name="field", label="Field").context_name, f"{PARAM_CONTEXT_PREFIX}field")


@tag("unit")
class CleanValuesTest(TestCase):
    """The preset checks what only it can know; errors carry preset and parameter as structured data."""

    def test_none_means_no_params_and_fails_on_required(self):
        with self.assertRaisesRegex(ConditionPresetError, re.escape("Preset `field_changed`")):
            FIELD_CHANGED.clean_values(None)

    def test_non_mapping_rejected(self):
        with self.assertRaisesRegex(ConditionPresetError, re.escape("must be a mapping")):
            FIELD_CHANGED.clean_values(["field"])

    def test_unknown_parameters_named_alongside_accepted(self):
        with self.assertRaisesRegex(ConditionPresetError, re.escape("does not accept parameter(s): extra")):
            FIELD_CHANGED.clean_values({"field": "status", "extra": "x"})

    def test_preset_error_is_a_validation_error(self):
        """`full_clean()` and forms handle it as any ValidationError; callers can also catch it by type."""
        with self.assertRaises(ValidationError) as caught:
            FIELD_CHANGED.clean_values(None)
        self.assertIsInstance(caught.exception, ConditionPresetError)

    def test_parameter_error_carries_preset_and_parameter_as_params(self):
        """A form re-shapes these onto its own fields via `code` and `params`, not by parsing text."""
        with self.assertRaises(ConditionPresetError) as caught:
            FIELD_COMPARE.clean_values({"field": "mtu", "operator": "gt"})
        error = caught.exception
        self.assertEqual(error.code, ConditionPresetError.code)
        self.assertEqual(error.params["preset"], "field_compare")
        self.assertEqual(error.params["parameter"], "value")
        self.assertIn("field_compare", error.message)
        self.assertIn("`value` is required", error.message)

    def test_preset_level_errors_carry_the_preset_key(self):
        for values in (["field"], {"field": "x", "extra": "y"}):
            with self.subTest(values=values):
                with self.assertRaises(ConditionPresetError) as caught:
                    FIELD_CHANGED.clean_values(values)
                self.assertEqual(caught.exception.code, ConditionPresetError.code)
                self.assertEqual(caught.exception.params["preset"], "field_changed")

    def test_valid_params_pass(self):
        FIELD_COMPARE.clean_values({"field": "mtu", "operator": "gt", "value": "9000"})
        FIELD_TRANSITION.clean_values({"field": "status", "from": "Staged", "to": "Active"})


@tag("unit")
class ContextVariablesTest(TestCase):
    """The single producer of the `param_*` convention the sources consume."""

    def test_values_map_under_prefixed_names(self):
        context = FIELD_TRANSITION.context_variables({"field": "status", "from": "Staged", "to": "Active"})
        self.assertEqual(context, {"param_field": "status", "param_from": "Staged", "param_to": "Active"})

    def test_missing_optional_parameter_is_none(self):
        """An expression must never meet Jinja2 Undefined for its own parameter."""
        preset = make_preset(
            parameters=(
                PresetParameter(name="field", label="Field"),
                PresetParameter(name="note", label="Note", required=False),
            )
        )
        self.assertEqual(preset.context_variables({"field": "mtu"}), {"param_field": "mtu", "param_note": None})

    def test_missing_required_parameter_raises(self):
        """A broken row is an error for the engine's fail-closed path to log, not a None to compare
        against another None and quietly fire on."""
        with self.assertRaises(ConditionPresetError) as caught:
            FIELD_COMPARE.context_variables({"field": "mtu"})
        self.assertEqual(caught.exception.code, ConditionPresetError.code)
        self.assertEqual(caught.exception.params["preset"], "field_compare")
        self.assertEqual(caught.exception.params["missing"], ["operator", "value"])
        with self.assertRaises(ConditionPresetError):
            USER_IS.context_variables(None)

    def test_undeclared_values_do_not_leak_into_context(self):
        """`context_variables` iterates declared parameters, so a stray stored key (edited JSON,
        an older schema) cannot smuggle a variable into the expression's namespace."""
        context = USER_IS.context_variables({"username": "kasia", "rogue": "x"})
        self.assertEqual(context, {"param_username": "kasia"})


@tag("unit")
class RegistrationTest(RegistryIsolationMixin, TestCase):
    def test_register_and_get(self):
        preset = make_preset()
        register_condition_preset(preset)
        self.assertIs(get_condition_preset("test_preset"), preset)

    def test_registering_the_same_object_twice_is_a_noop(self):
        """An App's ready() may run more than once; the second pass must not error."""
        preset = make_preset()
        register_condition_preset(preset)
        register_condition_preset(preset)
        register_condition_preset(make_preset())  # equal by value counts as "the same" too
        self.assertIs(get_condition_preset("test_preset"), preset)

    def test_registering_a_different_preset_under_an_existing_key_conflicts(self):
        register_condition_preset(make_preset())
        with self.assertRaises(KeyError):
            register_condition_preset(make_preset(source="false"))

    def test_only_condition_presets_are_accepted(self):
        with self.assertRaises(TypeError):
            register_condition_preset({"key": "dict_in_disguise"})

    def test_get_condition_presets_orders_by_key(self):
        register_condition_preset(make_preset(key="zzz_last"))
        register_condition_preset(make_preset(key="aaa_first"))
        keys = [preset.key for preset in get_condition_presets()]
        self.assertEqual(keys, sorted(keys))

    def test_unknown_key_is_none(self):
        self.assertIsNone(get_condition_preset("no_such_preset"))


@tag("unit")
class BuiltinCatalogTest(RegistryIsolationMixin, TestCase):
    """Structural pins on what ships. A change here changes existing rules' behaviour on upgrade -
    which is sometimes the point (the field_changed guard was exactly that), but never an accident."""

    def test_builtin_registration_is_idempotent_and_complete(self):
        register_builtin_condition_presets()
        register_builtin_condition_presets()
        for preset in BUILTIN_CONDITION_PRESETS:
            self.assertIs(get_condition_preset(preset.key), preset)

    def test_shipped_keys_exactly(self):
        self.assertEqual(
            [preset.key for preset in BUILTIN_CONDITION_PRESETS],
            ["field_transition", "field_changed", "field_compare", "user_is"],
        )

    def test_no_negated_twin_ships(self):
        """Negation is the row's `negate` flag; a `user_is_not` preset would be a second negation
        path for the two to drift apart on."""
        self.assertNotIn("user_is_not", [preset.key for preset in BUILTIN_CONDITION_PRESETS])

    def test_field_transition_guards_against_creates(self):
        """A transition is an update by definition; the guard says so rather than relying on the
        None comparisons on create and delete happening to fail."""
        self.assertTrue(FIELD_TRANSITION.source.startswith("event == 'updated'"))

    def test_field_changed_guards_against_creates(self):
        """On a create `prechange` is None, so without the event guard `None != value` would count
        every field of every new object as changed."""
        self.assertTrue(FIELD_CHANGED.source.startswith("event == 'updated' and "))

    def test_sources_do_not_read_differences(self):
        """`differences` keys are top-level field names; a sub-field path would never be found there."""
        for preset in BUILTIN_CONDITION_PRESETS:
            with self.subTest(preset=preset.key):
                self.assertNotIn("differences", preset.source)

    def test_sources_only_use_parameters_they_declare(self):
        """Every `param_*` a source references must be produced by context_variables - a typo in
        either place would render as Undefined, i.e. a silent false, with no error anywhere."""
        for preset in BUILTIN_CONDITION_PRESETS:
            with self.subTest(preset=preset.key):
                used = set(re.findall(rf"{PARAM_CONTEXT_PREFIX}\w+", preset.source))
                declared = {parameter.context_name for parameter in preset.parameters}
                self.assertLessEqual(used, declared)

    def test_presets_are_immutable(self):
        with self.assertRaises(AttributeError):
            FIELD_TRANSITION.source = "true"

    def test_schema_serialization_shape(self):
        """The catalog endpoint and the form read this shape; external tooling builds rules from it."""
        as_dict = FIELD_COMPARE.as_dict()
        self.assertEqual(set(as_dict), {"key", "label", "description", "parameters_schema"})
        operator_schema, value_schema = as_dict["parameters_schema"][1], as_dict["parameters_schema"][2]
        self.assertEqual(operator_schema["kind"], "choice")
        self.assertEqual(operator_schema["choices"][0], {"value": "=", "label": "= (equals)"})
        self.assertTrue(value_schema["multiple"])
        self.assertFalse(operator_schema["multiple"])
