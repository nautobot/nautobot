"""Model fields specific to `nautobot.extras`."""

from django.core.serializers.json import DjangoJSONEncoder
from django.db import models

from nautobot.core.forms import fields
from nautobot.extras.conditions.validation import validate_conditions


class ConditionsField(models.JSONField):
    """
    An ordered list of condition rows, all of which must pass.

    The field validates and normalises itself, so a model that carries it needs no `clean()` of its own.
    """

    description = "An ordered list of condition rows, all of which must pass"

    def __init__(self, *args, **kwargs):
        kwargs["default"] = list
        kwargs["blank"] = True
        kwargs["encoder"] = DjangoJSONEncoder
        kwargs["help_text"] = (
            "An ordered list of condition rows, all of which must pass. An empty list means every change "
            "of the selected object type(s) passes."
        )
        super().__init__(*args, **kwargs)

    def formfield(self, **kwargs):
        """Render with `core.forms.fields.JSONField`, which shows an empty value as empty, not as `null`."""
        return super().formfield(**{"form_class": fields.JSONField, **kwargs})  # pylint: disable=no-member # https://github.com/pylint-dev/pylint-django/issues/477

    def validate(self, value, model_instance):
        """
        Reject rows that could not be stored or run.

        Raises:
            ValidationError: With one numbered message per incorrectly formed row. See
                `nautobot.extras.conditions.validation.validate_conditions`.
        """
        super().validate(value, model_instance)  # pylint: disable=no-member # https://github.com/pylint-dev/pylint-django/issues/477
        validate_conditions(value)

    def pre_save(self, model_instance, add):
        """
        Store `[]` for every way of saying "no conditions", so the column only ever holds a list.

        An empty form field arrives as `None`, an API caller can send `""`, and `{}` is valid JSON that a
        person may well type into a JSON widget. `clean_fields()` skips a `blank=True` field holding any of
        those, so none of them reaches `validate()` - they are settled here, on the way to the database,
        where a bare `save()` passes too.
        """
        value = getattr(model_instance, self.attname)
        if value in self.empty_values:
            value = []
        setattr(model_instance, self.attname, value)
        return value
