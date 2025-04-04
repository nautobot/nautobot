from django.forms.fields import CallableChoiceIterator
from rest_framework import serializers


class MultipleChoiceJSONField(serializers.MultipleChoiceField):
    """A MultipleChoiceField that renders the received value as a JSON-compatible list rather than a set."""

    def __init__(self, **kwargs):
        """Overload default choices handling to also accept a callable."""
        choices = kwargs.get("choices")
        if callable(choices):
            kwargs["choices"] = CallableChoiceIterator(choices)
        super().__init__(**kwargs)

    def to_internal_value(self, data):
        set_value = super().to_internal_value(data)
        return sorted(set_value)
