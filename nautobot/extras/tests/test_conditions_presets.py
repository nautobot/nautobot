"""Tests for `nautobot.extras.conditions.presets`."""

import re
from unittest import TestCase

from django.core.exceptions import ValidationError
from django.test import tag

from nautobot.extras.conditions.presets import (
    BUILTIN_CONDITION_PRESETS,
    ConditionPreset,
    FIELD_CHANGED,
    FIELD_OPERATOR,
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
class PresetParameterCleanTest(TestCase):
    """The parameter validates its own value - kind, requiredness and choices live with it."""

    def test_required_rejects_missing_and_empty(self):
        parameter = PresetParameter(name="field", label="Field")
        for value in (None, ""):
            with self.subTest(value=value):
                with self.assertRaisesRegex(ValidationError, re.escape("`field` is required")):
                    parameter.clean(value)

    def test_optional_accepts_missing(self):
        PresetParameter(name="note", label="Note", required=False).clean(None)

    def test_non_string_rejected_by_type_name(self):
        """Storage is uniformly text; coercion happens at comparison time, in one place."""
        with self.assertRaisesRegex(ValidationError, re.escape("must be a string, not int")):
            PresetParameter(name="value", label="Value").clean(5)

    def test_choice_enforces_declared_values(self):
        parameter = PresetParameter(name="op", label="Op", kind="choice", choices=(("=", "eq"), ("gt", "gt")))
        parameter.clean("gt")
        with self.assertRaisesRegex(ValidationError, re.escape("must be one of: =, gt")):
            parameter.clean("regex")

    def test_context_name_applies_the_prefix(self):
        self.assertEqual(PresetParameter(name="field", label="Field").context_name, f"{PARAM_CONTEXT_PREFIX}field")


@tag("unit")
class CleanParamsTest(TestCase):
    """The preset checks what only it can know; errors carry the preset key for multi-row forms."""

    def test_none_means_no_params_and_fails_on_required(self):
        with self.assertRaisesRegex(ValidationError, re.escape("Preset `field_changed`")):
            FIELD_CHANGED.clean_params(None)

    def test_non_mapping_rejected(self):
        with self.assertRaisesRegex(ValidationError, re.escape("must be a mapping")):
            FIELD_CHANGED.clean_params(["field"])

    def test_unknown_parameters_named_alongside_accepted(self):
        with self.assertRaisesRegex(ValidationError, re.escape("does not accept parameter(s): extra")):
            FIELD_CHANGED.clean_params({"field": "status", "extra": "x"})

    def test_parameter_error_is_wrapped_with_preset_context(self):
        try:
            FIELD_OPERATOR.clean_params({"field": "mtu", "operator": "gt"})
        except ValidationError as error:
            message = "; ".join(error.messages)
            self.assertIn("field_compare", message)
            self.assertIn("`value` is required", message)
        else:
            self.fail("ValidationError not raised")

    def test_valid_params_pass(self):
        FIELD_OPERATOR.clean_params({"field": "mtu", "operator": "gt", "value": "9000"})
        FIELD_TRANSITION.clean_params({"field": "status", "from": "Staged", "to": "Active"})


@tag("unit")
class ContextVariablesTest(TestCase):
    """The single producer of the `param_*` convention the sources consume."""

    def test_values_map_under_prefixed_names(self):
        context = FIELD_TRANSITION.context_variables({"field": "status", "from": "Staged", "to": "Active"})
        self.assertEqual(context, {"param_field": "status", "param_from": "Staged", "param_to": "Active"})

    def test_every_declared_parameter_is_present_missing_as_none(self):
        """An expression must never meet Jinja2 Undefined for its own parameter."""
        context = FIELD_OPERATOR.context_variables({"field": "mtu"})
        self.assertEqual(context, {"param_field": "mtu", "param_operator": None, "param_value": None})
        self.assertEqual(USER_IS.context_variables(None), {"param_username": None})

    def test_undeclared_params_do_not_leak_into_context(self):
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

    def test_field_changed_guards_against_creates(self):
        """On a create, differences.added holds the whole object; without the event guard every
        field would count as changed on every create. Documented semantics, not an optimisation."""
        self.assertTrue(FIELD_CHANGED.source.startswith("event == 'updated' and "))

    def test_sources_only_use_parameters_they_declare(self):
        """Every `param_*` a source references must be produced by context_variables - a typo in
        either place would render as Undefined, i.e. a silent false, with no error anywhere."""
        for preset in BUILTIN_CONDITION_PRESETS:
            with self.subTest(preset=preset.key):
                used = set(re.findall(rf"{PARAM_CONTEXT_PREFIX}\w+", preset.source))
                produced = set(preset.context_variables({}))
                self.assertLessEqual(used, produced)

    def test_presets_are_immutable(self):
        with self.assertRaises(AttributeError):
            FIELD_TRANSITION.source = "true"

    def test_schema_serialization_shape(self):
        """The catalog endpoint and the form read this shape; external tooling builds rules from it."""
        as_dict = FIELD_OPERATOR.as_dict()
        self.assertEqual(set(as_dict), {"key", "label", "description", "params_schema"})
        operator_schema = as_dict["params_schema"][1]
        self.assertEqual(operator_schema["kind"], "choice")
        self.assertEqual(operator_schema["choices"][0], {"value": "=", "label": "= (equals)"})
