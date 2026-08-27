"""Catalog of built-in condition presets.

A preset is a parameter schema paired with a Jinja2 expression written by a Nautobot developer. It
exists so the common conditions ("this field changed", "this field went from X to Y") need no
expression written by the user at all.

What a user fills in never becomes part of the expression text. Parameters are handed to the
expression as context variables (`param_field`, `param_from`, and so on) at the moment it runs, so a
preset's expression is a constant that compiles exactly once and there is no string assembly
anywhere for a user to inject into. The `param_` convention has exactly one owner:
`ConditionPreset.context_variables` produces the mapping, and the sources below consume it.

There is deliberately no negated twin of any preset. Negation is the condition row's `negate` flag,
which inverts presets and raw expressions alike.
"""

from dataclasses import dataclass, field as dataclass_field

from django.core.exceptions import ValidationError

from nautobot.extras.conditions.operators import FIELD_OPERATORS
from nautobot.extras.registry import registry

# Parameter kinds. `FIELD` names a field on the watched model, which lets the UI offer a picker
# rather than a free-text box; `STRING` is an arbitrary value to compare against; `CHOICE` is one of
# a fixed set of values the parameter itself declares.
PARAM_KIND_FIELD = "field"
PARAM_KIND_STRING = "string"
PARAM_KIND_CHOICE = "choice"

# Prefix under which a preset's parameters appear in its expression's render context.
PARAM_CONTEXT_PREFIX = "param_"


@dataclass(frozen=True)
class PresetParameter:
    """One parameter a preset accepts from the user.

    The parameter owns its own validation (`clean`): it is the one thing that knows its kind,
    whether it is required, and which choices it allows, so the preset delegates per-value checks
    here instead of re-deriving them from the schema.
    """

    name: str
    label: str
    kind: str = PARAM_KIND_STRING
    required: bool = True
    help_text: str = ""
    # For a `choice` parameter, the accepted `(value, label)` pairs. Empty for any other kind.
    choices: tuple = ()

    @property
    def context_name(self):
        """The name under which this parameter appears in the expression's render context."""
        return f"{PARAM_CONTEXT_PREFIX}{self.name}"

    def clean(self, value):
        """
        Validate one user-supplied value against this parameter's schema.

        Raises:
            ValidationError: If a required value is missing or empty, the value is not a string, or
                a choice parameter is given a value outside its declared choices.
        """
        if self.required and (value is None or value == ""):
            raise ValidationError(f"Parameter `{self.name}` is required.")
        if value is not None and not isinstance(value, str):
            raise ValidationError(f"Parameter `{self.name}` must be a string, not {type(value).__name__}.")
        if self.choices and value:
            allowed = [choice_value for choice_value, _ in self.choices]
            if value not in allowed:
                raise ValidationError(f"Parameter `{self.name}` must be one of: {', '.join(allowed)}.")

    def as_dict(self):
        return {
            "name": self.name,
            "label": self.label,
            "kind": self.kind,
            "required": self.required,
            "help_text": self.help_text,
            "choices": [{"value": value, "label": label} for value, label in self.choices],
        }


@dataclass(frozen=True)
class ConditionPreset:
    """A built-in condition type offered by the rule form."""

    key: str
    label: str
    description: str
    source: str
    parameters: tuple = dataclass_field(default_factory=tuple)

    @property
    def params_schema(self):
        """JSON-serializable description of this preset's parameters, for the API and the form."""
        return [parameter.as_dict() for parameter in self.parameters]

    def as_dict(self):
        return {
            "key": self.key,
            "label": self.label,
            "description": self.description,
            "params_schema": self.params_schema,
        }

    def clean_params(self, params):
        """
        Validate user-supplied `params` against this preset's schema.

        The preset checks what only it can know (the value is a mapping, no unknown names); each
        parameter checks its own value. Errors carry the preset key so a multi-row form can say
        which row's which field is wrong.

        Raises:
            ValidationError: If `params` is not a mapping, names an unknown parameter, or any
                parameter's own validation fails.
        """
        if params is None:
            params = {}
        if not isinstance(params, dict):
            raise ValidationError(f"Preset `{self.key}` params must be a mapping.")

        known = {parameter.name for parameter in self.parameters}
        unknown = sorted(set(params) - known)
        if unknown:
            raise ValidationError(
                f"Preset `{self.key}` does not accept parameter(s): {', '.join(unknown)}. "
                f"Accepted: {', '.join(sorted(known)) or 'none'}."
            )

        for parameter in self.parameters:
            try:
                parameter.clean(params.get(parameter.name))
            except ValidationError as error:
                raise ValidationError(f"Preset `{self.key}`: {'; '.join(error.messages)}") from error

    def context_variables(self, params):
        """
        Map stored form values to the `param_*` variables this preset's expression reads.

        Every declared parameter is present in the result, an absent or optional one as None, so the
        expression never meets Jinja2 `Undefined` for its own parameters and needs no is-defined
        guards. This method is the single producer of the `param_` naming convention; the engine
        renders with exactly this mapping and never builds the names itself.
        """
        params = params or {}
        return {parameter.context_name: params.get(parameter.name) for parameter in self.parameters}


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
    source=(
        "field_value(snapshots.prechange, param_field) == param_from"
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
    # The event guard is what keeps this honest on creates: a freshly created object's differences
    # contain the whole object, so without it every field would count as "changed" on every create.
    source="event == 'updated' and param_field in (snapshots.differences.added or {})",
    parameters=(PresetParameter(name="field", label="Field", kind=PARAM_KIND_FIELD, help_text="Field to watch."),),
)

FIELD_OPERATOR = ConditionPreset(
    key="field_compare",
    label="Field compare",
    description=(
        "Fires when a field compares as chosen against a value. The comparison reads the object's "
        "recorded state: after the change for creates and updates, the last known state for deletes."
    ),
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
            help_text="Entered and stored as text; how it compares is decided by the operator (numbers numerically, dates as ISO strings, booleans case-insensitively).",
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
    FIELD_OPERATOR,
    USER_IS,
)


def register_builtin_condition_presets():
    """Register the presets Nautobot ships with. Called from `ExtrasConfig.ready()`."""
    for preset in BUILTIN_CONDITION_PRESETS:
        register_condition_preset(preset)
