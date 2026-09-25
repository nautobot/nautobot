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
    Restate one row's errors with its number.

    `code` and `params` are carried over so a caller can still point at the field at fault rather than
    only print a sentence.
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

    Args:
        value: The submitted conditions.

    Raises:
        ValidationError: If `value` is not a list, or any row is incorrectly formed. Messages count rows
            from one, the way a person reads them; `params["index"]` is the row's position in the list,
            for a caller that has to find it again.
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
