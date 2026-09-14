"""Conditions: whether a change passes a list of stored condition rows.

A row is a preset from the catalog with values filled in, or a raw Jinja2 expression. `check()` takes
the rows and the payload of a change and returns a `Verdict`. Nothing here knows which model or action
owns the rows.

Modules, in dependency order: `operators` (comparisons), `payload` (the frozen picture of a change),
`presets` (the catalog), `expressions` (compiling Jinja2), `rows` (the stored shape), `check`.
"""

from nautobot.extras.conditions.check import check, check_row, RowVerdict, Verdict
from nautobot.extras.conditions.expressions import compile_condition, ConditionError
from nautobot.extras.conditions.operators import (
    field_matches,
    FIELD_OPERATORS,
    KIND_BOOLEAN,
    KIND_DATE,
    KIND_LIST,
    KIND_NUMBER,
    KIND_TEXT,
    operators_for_kind,
    takes_a_set,
)
from nautobot.extras.conditions.payload import build_event_payload, field_value
from nautobot.extras.conditions.presets import (
    ConditionPreset,
    ConditionPresetError,
    get_condition_preset,
    get_condition_presets,
    PARAM_KIND_CHOICE,
    PARAM_KIND_FIELD,
    PARAM_KIND_VALUE,
    PresetParameter,
    register_condition_preset,
)
from nautobot.extras.conditions.rows import ConditionRow, ConditionRowError, ExpressionRow, PresetRow

__all__ = (
    "FIELD_OPERATORS",
    "KIND_BOOLEAN",
    "KIND_DATE",
    "KIND_LIST",
    "KIND_NUMBER",
    "KIND_TEXT",
    "PARAM_KIND_CHOICE",
    "PARAM_KIND_FIELD",
    "PARAM_KIND_VALUE",
    "ConditionError",
    "ConditionPreset",
    "ConditionPresetError",
    "ConditionRow",
    "ConditionRowError",
    "ExpressionRow",
    "PresetParameter",
    "PresetRow",
    "RowVerdict",
    "Verdict",
    "build_event_payload",
    "check",
    "check_row",
    "compile_condition",
    "field_matches",
    "field_value",
    "get_condition_preset",
    "get_condition_presets",
    "operators_for_kind",
    "register_condition_preset",
    "takes_a_set",
)
