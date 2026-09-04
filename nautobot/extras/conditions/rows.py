"""Condition rows: the stored shape of one condition, and what it resolves to for the engine.

A Webhook or Job Hook stores its conditions as a JSON list of rows. A row is either a preset chosen
from the catalog with the values the user filled in, or a raw Jinja2 expression the user wrote:

    {"type": "preset", "preset": "field_compare", "values": {"field": "mtu", "operator": "gt", "value": 9000}}
    {"type": "expression", "source": "data.mtu > 9000 and username != 'test'"}

Both may carry `"negate": true`, which inverts the row's verdict.

`ConditionRow.from_dict` is the one place that reads that shape. The form, the REST API and the
model's `clean()` use it with `clean()` to validate what is being saved; the engine uses it with
`resolve()` to get an expression and its context variables.
"""

from dataclasses import dataclass
from typing import ClassVar

from django.core.exceptions import ValidationError

from nautobot.extras.choices import ConditionTypeChoices
from nautobot.extras.conditions.expressions import compile_condition, ConditionError
from nautobot.extras.conditions.presets import ConditionPreset, get_condition_preset


class ConditionRowError(ValidationError):
    """A stored condition row is malformed. `params["key"]` names the row key at fault."""

    code = "condition_row"

    def __init__(self, message, key):
        super().__init__(message, code=self.code, params={"key": key})


@dataclass(frozen=True)
class ConditionRow:
    """One stored condition. Subclasses know how to resolve themselves; the engine decides what passes."""

    negate: bool
    # Keys a stored row of this type may carry. Subclasses set it.
    _allowed_keys: ClassVar[frozenset[str]] = frozenset()

    @staticmethod
    def from_dict(row):
        """
        Parse a stored row into an `ExpressionRow` or a `PresetRow`.

        Checks shape only: the keys present, their types, and that a named preset exists. Values are
        not validated here - that is `clean()`, run at save time.

        Raises:
            ValidationError: If the row is not a mapping, has an unknown `type`, carries keys the type
                does not accept, or fails the type's own shape checks below.
        """
        if not isinstance(row, dict):
            raise ConditionRowError(f"A condition row must be a mapping, not {type(row).__name__}.", key="type")

        negate = row.get("negate", False)
        if not isinstance(negate, bool):
            raise ConditionRowError(f"`negate` must be a boolean, not {type(negate).__name__}.", key="negate")

        row_type = row.get("type")
        if row_type == ConditionTypeChoices.TYPE_EXPRESSION:
            return ExpressionRow._parse(row, negate)
        if row_type == ConditionTypeChoices.TYPE_PRESET:
            return PresetRow._parse(row, negate)
        raise ConditionRowError(f"Unknown condition row type `{row_type}`.", key="type")

    @classmethod
    def _reject_unknown_keys(cls, row):
        unknown = sorted(set(row) - cls._allowed_keys)
        if unknown:
            raise ConditionRowError(f"Condition row does not accept key(s): {', '.join(unknown)}.", key=unknown[0])

    def clean(self):
        """Validate beyond shape, for saving. Subclasses override."""
        raise NotImplementedError

    def resolve(self):
        """Return `(source, context_variables)` for the engine. Subclasses override."""
        raise NotImplementedError

    def to_dict(self):
        """The row in its canonical stored shape. Subclasses override."""
        raise NotImplementedError


@dataclass(frozen=True)
class ExpressionRow(ConditionRow):
    """A raw Jinja2 expression written by the user.

    `source` is a bare expression, not a template: no `{{ }}` or `{% %}`. It sees the payload keys
    (`event`, `data`, `snapshots`, ...) and the `field_value` / `field_matches` helpers.
    """

    _allowed_keys = frozenset({"type", "source", "negate"})
    source: str

    @classmethod
    def _parse(cls, row, negate):
        cls._reject_unknown_keys(row)
        source = row.get("source")
        if not isinstance(source, str) or not source.strip():
            raise ConditionRowError("An expression row needs a non-empty `source`.", key="source")
        for delimiter in ("{{", "{%"):
            if delimiter in source:
                # Django interpolates `message % params`, so the `%` in `{%` has to be doubled.
                raise ConditionRowError(
                    f"A condition is a bare expression, not a template: remove the `{delimiter.replace('%', '%%')}`.",
                    key="source",
                )
        return cls(source=source, negate=negate)

    def clean(self):
        """Compile the source, so a syntax error is refused at save time.

        Raises:
            ValidationError: With `key="source"` and the compiler's message.
        """
        try:
            compile_condition(self.source)
        except ConditionError as error:
            raise ConditionRowError(str(error), key="source") from error

    def resolve(self):
        return self.source, {}

    def to_dict(self):
        return {"type": ConditionTypeChoices.TYPE_EXPRESSION, "source": self.source, "negate": self.negate}


@dataclass(frozen=True)
class PresetRow(ConditionRow):
    """A catalog preset plus the values the user filled in for its parameters."""

    _allowed_keys = frozenset({"type", "preset", "values", "negate"})
    preset: ConditionPreset
    values: dict

    @classmethod
    def _parse(cls, row, negate):
        cls._reject_unknown_keys(row)
        preset = get_condition_preset(row.get("preset"))
        if preset is None:
            raise ConditionRowError(f"Unknown condition preset `{row.get('preset')}`.", key="preset")
        values = row.get("values")
        if values is None:
            values = {}
        if not isinstance(values, dict):
            raise ConditionRowError(f"`values` must be a mapping, not {type(values).__name__}.", key="values")
        return cls(preset=preset, values=values, negate=negate)

    def clean(self):
        self.preset.clean_values(self.values)

    def resolve(self):
        return self.preset.source, self.preset.context_variables(self.values)

    def to_dict(self):
        declared = [parameter.name for parameter in self.preset.parameters]
        return {
            "type": ConditionTypeChoices.TYPE_PRESET,
            "preset": self.preset.key,
            "values": {name: self.values[name] for name in declared if name in self.values},
            "negate": self.negate,
        }
