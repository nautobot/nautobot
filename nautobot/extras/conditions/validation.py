"""Validating a whole stored list of condition rows.

`rows` and `presets` decide what makes a single row valid; this module runs that over a list and
reports every bad row at once, each message numbered.

The only caller is `ConditionsField.validate()`. A form, a serializer and a `validated_save()` all
reach it through `Model.full_clean()`.
"""

from django.core.exceptions import ValidationError

from nautobot.extras.conditions.errors import ConditionValidationError
from nautobot.extras.conditions.rows import ConditionRow


def _numbered(index, error):
    """
    Restate one row's errors as numbered ones, keeping enough to find the row again.

    `params` carries the row's `index` alongside whatever the original error said about itself (`key`,
    `preset`, `parameter`), so a caller can point at the field at fault rather than only print a
    sentence. The original `code` is kept, so which layer refused the row survives the renumbering.
    """
    params = dict(getattr(error, "params", None) or {})
    return [
        ConditionValidationError(
            f"Condition {index + 1}: {message}",
            code=getattr(error, "code", None),
            **params,
            index=index,
        )
        for message in error.messages
    ]


def validate_conditions(value):
    """
    Check that every row in `value` could be stored and run.

    Every bad row is reported, so three incorrectly formed rows are fixed in one pass rather than one
    save per row.

    Args:
        value: The submitted conditions.

    Raises:
        ValidationError: If `value` is not a list, or any row is incorrectly formed. Each message is
            numbered and carries `params["index"]`.
    """
    if not isinstance(value, list):
        raise ConditionValidationError(f"Conditions must be a list of condition rows, not {type(value).__name__}.")

    issues = []
    for index, row in enumerate(value):
        try:
            ConditionRow.from_dict(row).clean()
        except ValidationError as error:
            issues.extend(_numbered(index, error))

    if issues:
        raise ValidationError(issues)
