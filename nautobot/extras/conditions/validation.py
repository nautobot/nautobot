"""Validating a whole stored list of condition rows.

`rows` and `presets` decide what makes a single row valid. This module runs that over a list, and
offers the answer two ways, because the two readers are not in the same position.

`row_problems` hands back each row's own complaints, for the editor, which shows one inside the row it
belongs to and needs no more said. `validate_conditions` raises, for `ConditionsField.validate()`,
which a form, a serializer and a `validated_save()` all reach through `Model.full_clean()`, and whose
reader has no row in front of them, so each message names the row and the preset.
"""

from django.core.exceptions import ValidationError

from nautobot.extras.conditions.errors import ConditionValidationError
from nautobot.extras.conditions.rows import ConditionRow


def _restated_out_of_context(index, error):
    """
    Restate one row's errors for a reader who is not looking at the row.

    A row says neither its own number nor, for a parameter, the preset that declares it, both being
    plain to anyone reading the row itself. Away from it they have to be said. A preset's own complaints
    already name it, so only a parameter's are placed.

    `code` and `params` are carried over so a caller can still point at the control at fault rather
    than only print a sentence.
    """
    params = dict(getattr(error, "params", None) or {})
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


def row_problems(value):
    """Each row's own complaints, keyed by its position, for a caller that shows them in place.

    The messages are the rows' own and carry no number: an editor putting one inside the row it belongs
    to does not have to say which row that is. A value that is not a list has no rows to complain about.
    """
    if not isinstance(value, list):
        return {}
    problems = {}
    for index, row in enumerate(value):
        try:
            ConditionRow.from_dict(row).clean()
        except ValidationError as error:
            problems[index] = error
    return problems


def validate_conditions(value):
    """
    Check that every row in `value` could be stored and run.

    Args:
        value: The submitted conditions.

    Raises:
        ValidationError: If `value` is not a list, or any row is incorrectly formed. Each message names
            the row, counted from one the way a person reads it, and the preset where a parameter is at
            fault. That sentence is all a REST client is given, `params` reaching no further than
            Python, so `params["index"]` and `params["parameter"]` are for a caller in this process.
    """
    if not isinstance(value, list):
        raise ConditionValidationError(f"Conditions must be a list of condition rows, not {type(value).__name__}.")

    issues = []
    for index, error in row_problems(value).items():
        issues.extend(_restated_out_of_context(index, error))

    if issues:
        raise ValidationError(issues)
