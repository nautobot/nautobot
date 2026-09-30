"""The exception every condition error is built from."""

from django.core.exceptions import ValidationError


class ConditionValidationError(ValidationError):
    """Something in a stored condition is incorrectly formed.

    It is a `ValidationError`, so a form, a serializer and `full_clean()` all render it the way they
    render their own errors. Subclasses set a `code` naming what refused the data, and pass `params`
    saying where the fault is: a row key, a preset, a parameter, an index.

    A `%` in the message is doubled on the way in. Django renders these as `message % params`, and the
    text can quote whatever the user wrote - `data.mtu > % 9000` comes back from Jinja2 as
    `unexpected '%'`. Left alone, that raises a `ValueError` the first time anyone tries to display it.
    Reading `.messages` undoes the doubling, so wrapping one of these errors in another is safe.
    """

    code = "conditions"

    def __init__(self, message, code=None, **params):
        super().__init__(message.replace("%", "%%"), code=code or self.code, params=params)
