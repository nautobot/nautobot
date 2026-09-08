"""Condition rows: a preset from the catalog with its values, or a raw Jinja2 expression, either one
optionally negated."""

from abc import ABC, abstractmethod
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
class ConditionRow(ABC):
    """One stored condition. Subclasses know how to resolve themselves; `check` decides what passes."""

    negate: bool  # inverts the row's result
    _allowed_keys: ClassVar[frozenset[str]] = frozenset()

    @staticmethod
    def from_dict(row):
        """
        Parse a row into an `ExpressionRow` or a `PresetRow`.

            {"type": "preset", "preset": "field_compare", "values": {"field": "mtu", "operator": "gt", "value": 9000}}
            {"type": "expression", "source": "data.mtu > 9000", "negate": true}

        Checks structure only: which keys are present, their types, that a named preset exists and
        that its values use declared names. Values themselves are validated by `clean()`.

        Raises:
            ConditionRowError: If the row is not a mapping, has an unknown `type`, carries keys the
                type does not accept, or fails the type's own checks.
        """
        if not isinstance(row, dict):
            raise ConditionRowError(f"A condition row must be a mapping, not {type(row).__name__}.", key="type")

        row_type = row.get("type")
        if row_type == ConditionTypeChoices.TYPE_EXPRESSION:
            return ExpressionRow.from_dict(row)
        if row_type == ConditionTypeChoices.TYPE_PRESET:
            return PresetRow.from_dict(row)
        raise ConditionRowError(f"Unknown condition row type `{row_type}`.", key="type")

    @classmethod
    def _common_fields(cls, row):
        """Check the keys a row of this type may carry and return its `negate`."""
        unknown = sorted(set(row) - cls._allowed_keys)
        if unknown:
            raise ConditionRowError(f"Condition row does not accept key(s): {', '.join(unknown)}.", key=unknown[0])
        negate = row.get("negate", False)
        if not isinstance(negate, bool):
            raise ConditionRowError(f"`negate` must be a boolean, not {type(negate).__name__}.", key="negate")
        return negate

    @abstractmethod
    def clean(self):
        """Validate beyond shape, for saving. Subclasses override."""

    @abstractmethod
    def resolve(self):
        """Return `(source, context_variables)` for `check`. Subclasses override."""

    @abstractmethod
    def to_dict(self):
        """The row in its canonical stored shape. Subclasses override."""


@dataclass(frozen=True)
class ExpressionRow(ConditionRow):
    """A raw Jinja2 expression written by the user.

    `source` is a bare expression, not a template: no `{{ }}` or `{% %}`. It sees the payload keys
    (`event`, `data`, `snapshots`, ...) and the `field_value` / `field_matches` helpers.
    """

    _allowed_keys = frozenset({"type", "source", "negate"})
    source: str

    @classmethod
    def from_dict(cls, row):
        negate = cls._common_fields(row)
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
            ConditionRowError: With `key="source"` and the compiler's message.
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
    def from_dict(cls, row):
        negate = cls._common_fields(row)
        preset = get_condition_preset(row.get("preset"))
        if preset is None:
            raise ConditionRowError(f"Unknown condition preset `{row.get('preset')}`.", key="preset")
        values = row.get("values")
        if values is None:
            values = {}
        if not isinstance(values, dict):
            raise ConditionRowError(f"`values` must be a mapping, not {type(values).__name__}.", key="values")
        unknown = sorted(set(values) - {parameter.name for parameter in preset.parameters})
        if unknown:
            raise ConditionRowError(
                f"Preset `{preset.key}` does not accept value(s): {', '.join(unknown)}.", key="values"
            )
        return cls(preset=preset, values=values, negate=negate)

    def clean(self):
        self.preset.clean_values(self.values)

    def resolve(self):
        return self.preset.source, self.preset.context_variables(self.values)

    def to_dict(self):
        return {
            "type": ConditionTypeChoices.TYPE_PRESET,
            "preset": self.preset.key,
            "values": dict(self.values),
            "negate": self.negate,
        }
