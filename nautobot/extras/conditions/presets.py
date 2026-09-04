"""Catalog of built-in condition presets.

A preset pairs a parameter schema with a fixed Jinja2 expression, so the common conditions ("this
field changed", "this field went from X to Y") need no expression written by the user.

User-supplied values never become part of the expression text. They enter the render context as
`param_*` variables, produced by `ConditionPreset.context_variables`, so each expression is a constant
that compiles once and contains nothing user-written.

There is no negated variant of any preset; negation is the condition row's `negate` flag.
"""

from dataclasses import dataclass

from django.core.exceptions import ValidationError

from nautobot.extras.conditions.operators import FIELD_OPERATORS
from nautobot.extras.registry import registry

# Parameter kinds. `FIELD` names a field on the watched model, which lets the form offer a picker;
# `VALUE` is a value to compare against, whose widget and canonical type the form derives from the
# chosen field's kind; `CHOICE` is one of a fixed set of values the parameter itself declares.
PARAM_KIND_FIELD = "field"
PARAM_KIND_VALUE = "value"
PARAM_KIND_CHOICE = "choice"

# Prefix under which a preset's parameters appear in its expression's render context.
PARAM_CONTEXT_PREFIX = "param_"


class ConditionPresetError(ValidationError):
    """Stored values do not fit a preset. `params` names the preset and, where one is at fault, the parameter."""

    code = "condition_preset"

    def __init__(self, message, **params):
        super().__init__(message, code=self.code, params=params)


@dataclass(frozen=True)
class PresetParameter:
    """One parameter a preset accepts from the user. It validates its own values (`clean`)."""

    name: str
    label: str
    kind: str = PARAM_KIND_VALUE
    required: bool = True
    help_text: str = ""
    # For a `choice` parameter, the accepted `(value, label)` pairs. Empty for any other kind.
    choices: tuple[tuple[str, str], ...] = ()
    # Whether a list of values is accepted as well as a single one. `operators.takes_a_set` decides
    # when the form offers one.
    multiple: bool = False

    def __post_init__(self):
        if not self.name.isidentifier():
            raise ValueError(
                f"Parameter name `{self.name}` must be a valid identifier: it becomes the `{self.context_name}` variable."
            )

    @property
    def context_name(self):
        """The name under which this parameter appears in the expression's render context."""
        return f"{PARAM_CONTEXT_PREFIX}{self.name}"

    def clean(self, value):
        """
        Validate one user-supplied value against this parameter's schema.

        Raises:
            ConditionPresetError: If a required value is missing or empty, the value is not a JSON
                scalar (or a list of strings, for a `multiple` parameter), or a choice parameter is
                given a value outside its declared choices. `params["parameter"]` is this parameter.
        """
        if self.required and value in (None, "", []):
            raise ConditionPresetError(f"Parameter `{self.name}` is required.", parameter=self.name)
        if isinstance(value, (list, tuple)):
            if not self.multiple:
                raise ConditionPresetError(
                    f"Parameter `{self.name}` takes a single value, not a list.", parameter=self.name
                )
            if not all(isinstance(item, str) for item in value):
                raise ConditionPresetError(f"Parameter `{self.name}` entries must be strings.", parameter=self.name)
        elif value is not None and not isinstance(value, (str, int, float, bool)):
            raise ConditionPresetError(
                f"Parameter `{self.name}` must be a string, number or boolean, not {type(value).__name__}.",
                parameter=self.name,
            )
        if self.choices and value:
            allowed = [choice_value for choice_value, _ in self.choices]
            if value not in allowed:
                raise ConditionPresetError(
                    f"Parameter `{self.name}` must be one of: {', '.join(allowed)}.", parameter=self.name
                )

    def as_dict(self):
        return {
            "name": self.name,
            "label": self.label,
            "kind": self.kind,
            "required": self.required,
            "multiple": self.multiple,
            "help_text": self.help_text,
            "choices": [{"value": value, "label": label} for value, label in self.choices],
        }


@dataclass(frozen=True)
class ConditionPreset:
    """A built-in condition type offered by the rule form."""

    key: str
    label: str
    description: str
    # A Jinja2 expression, not a template: no `{{ }}` or `{% %}`. Evaluates to a boolean. It sees the
    # payload keys, this preset's `param_*` variables, and `field_value` / `field_matches`.
    source: str
    parameters: tuple[PresetParameter, ...] = ()

    def __post_init__(self):
        if not self.key.isidentifier():
            raise ValueError(f"Preset key `{self.key}` must be a valid identifier.")

    @property
    def parameters_schema(self):
        """JSON-serializable description of this preset's parameters, for the API and the form."""
        return [parameter.as_dict() for parameter in self.parameters]

    def as_dict(self):
        return {
            "key": self.key,
            "label": self.label,
            "description": self.description,
            "parameters_schema": self.parameters_schema,
        }

    def clean_values(self, values):
        """
        Validate the user-supplied `values` mapping against this preset's parameters.

        The preset checks that `values` is a mapping with no unknown names; each parameter checks
        its own value.

        Raises:
            ConditionPresetError: If `values` is not a mapping, names an unknown parameter, or any
                parameter's own validation fails. `params["preset"]` is this preset; a parameter's
                error also carries `params["parameter"]`.
        """
        if values is None:
            values = {}
        if not isinstance(values, dict):
            raise ConditionPresetError(f"Preset `{self.key}` values must be a mapping.", preset=self.key)

        known = {parameter.name for parameter in self.parameters}
        unknown = sorted(set(values) - known)
        if unknown:
            raise ConditionPresetError(
                f"Preset `{self.key}` does not accept parameter(s): {', '.join(unknown)}. "
                f"Accepted: {', '.join(sorted(known)) or 'none'}.",
                preset=self.key,
                unknown=unknown,
            )

        for parameter in self.parameters:
            try:
                parameter.clean(values.get(parameter.name))
            except ConditionPresetError as error:
                raise ConditionPresetError(
                    f"Preset `{self.key}`: {error.message}", **error.params, preset=self.key
                ) from error

    def context_variables(self, values):
        """
        Map stored `values` to the `param_*` variables this preset's expression reads.

        Every declared parameter is present in the result, so the expression never meets Jinja2
        `Undefined` for its own parameters. An optional parameter that was not given is None. A
        required one that was not given raises, so `check` reports the row as broken instead of
        evaluating it against None.

        Raises:
            ConditionPresetError: If a required parameter has no value. `params["missing"]` lists them.
        """
        values = values or {}
        missing = [
            parameter.name
            for parameter in self.parameters
            if parameter.required and values.get(parameter.name) in (None, "", [])
        ]
        if missing:
            raise ConditionPresetError(
                f"Preset `{self.key}` is missing required parameter(s): {', '.join(missing)}.",
                preset=self.key,
                missing=missing,
            )
        return {parameter.context_name: values.get(parameter.name) for parameter in self.parameters}


def register_condition_preset(preset):
    """
    Register a `ConditionPreset` so the rule form and the API catalog will offer it.

    Registering the same preset object twice is a no-op, so an App whose `ready()` runs more than
    once does not error. Registering a *different* preset under an existing key is a conflict.
    """
    if not isinstance(preset, ConditionPreset):
        raise TypeError(f"{preset} must be an instance of ConditionPreset")
    existing = registry["condition_presets"].get(preset.key)
    if existing is not None:
        if existing == preset:
            return
        raise KeyError(f"A different condition preset is already registered under key `{preset.key}`")
    registry["condition_presets"][preset.key] = preset


def get_condition_preset(key):
    """Return the registered `ConditionPreset` for `key`, or None if there is no such preset."""
    return registry["condition_presets"].get(key)


def get_condition_presets():
    """Return all registered presets, ordered by key."""
    return [registry["condition_presets"][key] for key in sorted(registry["condition_presets"])]


#
# Built-in presets
#

FIELD_TRANSITION = ConditionPreset(
    key="field_transition",
    label="Field transition",
    description="Fires when a field moves from one specific value to another specific value.",
    # A transition is an update by definition: on a create `prechange` is None, on a delete
    # `postchange` is None.
    source=(
        "event == 'updated'"
        " and field_value(snapshots.prechange, param_field) == param_from"
        " and field_value(snapshots.postchange, param_field) == param_to"
    ),
    parameters=(
        PresetParameter(name="field", label="Field", kind=PARAM_KIND_FIELD, help_text="Field to watch."),
        PresetParameter(name="from", label="From", help_text="Value the field must have had before the change."),
        PresetParameter(name="to", label="To", help_text="Value the field must have after the change."),
    ),
)

FIELD_CHANGED = ConditionPreset(
    key="field_changed",
    label="Field changed",
    description="Fires when a field's value changed within an update, regardless of what it changed to.",
    # Compares the addressed value on both sides rather than looking the field up in
    # `differences`, whose keys are top-level and would never contain a sub-field path like
    # `status.name`.
    source=(
        "event == 'updated'"
        " and field_value(snapshots.prechange, param_field) != field_value(snapshots.postchange, param_field)"
    ),
    parameters=(PresetParameter(name="field", label="Field", kind=PARAM_KIND_FIELD, help_text="Field to watch."),),
)

FIELD_COMPARE = ConditionPreset(
    key="field_compare",
    label="Field compare",
    description=(
        "Fires when a field compares as chosen against a value. The comparison reads the object's "
        "recorded state: after the change for creates and updates, the last known state for deletes."
    ),
    # `data` rather than `snapshots.postchange`: it holds the recorded state for every event type,
    # including the last known state on a delete, where `postchange` is None.
    source="field_matches(field_value(data, param_field), param_operator, param_value)",
    parameters=(
        PresetParameter(name="field", label="Field", kind=PARAM_KIND_FIELD, help_text="Field to compare."),
        PresetParameter(
            name="operator",
            label="Operator",
            kind=PARAM_KIND_CHOICE,
            choices=FIELD_OPERATORS,
            help_text="How to compare. Ordering operators compare numerically when both sides are numbers.",
        ),
        PresetParameter(
            name="value",
            label="Value",
            multiple=True,
            help_text="Value to compare against. A set of values for `in`, and for `=` on a many-valued field.",
        ),
    ),
)

USER_IS = ConditionPreset(
    key="user_is",
    label="User is",
    description=(
        "Fires only when a specific user made the change. Combine with the row's `not` flag to "
        "ignore an automation account instead."
    ),
    source="username == param_username",
    parameters=(
        PresetParameter(name="username", label="Username", help_text="Username that must have made the change."),
    ),
)

BUILTIN_CONDITION_PRESETS = (
    FIELD_TRANSITION,
    FIELD_CHANGED,
    FIELD_COMPARE,
    USER_IS,
)


def register_builtin_condition_presets():
    """Register the presets Nautobot ships with. Called from `ExtrasConfig.ready()`."""
    for preset in BUILTIN_CONDITION_PRESETS:
        register_condition_preset(preset)
