"""Validating a stored list of condition rows.

`row_errors` reports each row's own complaints, for the editor, which shows one inside the row it
belongs to. `validate_conditions` raises, for `ConditionsField.validate()`, where the reader has no
row in front of them, so each message names the row and the preset.
"""

from django.core.exceptions import ValidationError

from nautobot.extras.conditions.errors import ConditionValidationError
from nautobot.extras.conditions.rows import ConditionRow


def _restated_out_of_context(index, error):
    """Restate one row's errors with the row number, and the preset where a parameter is at fault."""
    params = dict(getattr(error, "params", None) or {})
    # A preset's own complaints already name it, so only a parameter's needs placing.
    named = f"Preset `{params['preset']}`. " if params.get("parameter") and params.get("preset") else ""
    return [
        ConditionValidationError(
            f"Condition {index + 1}: {named}{message}",
            code=getattr(error, "code", None),
            **params,
            index=index,
        )
        for message in error.messages
    ]


def row_errors(value):
    """Each bad row's own error, keyed by its position. Nothing to report for a value that is not a list."""
    if not isinstance(value, list):
        return {}
    errors = {}
    for index, row in enumerate(value):
        try:
            ConditionRow.from_dict(row).clean()
        except ValidationError as error:
            errors[index] = error
    return errors


def validate_conditions(value):
    """Check that every row in `value` could be stored and run.

    Raises `ValidationError`, whose `params` carry `index` and `parameter`. A REST client sees only
    the message, so that has to name the row itself.
    """
    if not isinstance(value, list):
        raise ConditionValidationError(f"Conditions must be a list of condition rows, not {type(value).__name__}.")

    issues = []
    for index, error in row_errors(value).items():
        issues.extend(_restated_out_of_context(index, error))

    if issues:
        raise ValidationError(issues)
