from rest_framework import serializers


class MultipleChoiceJSONField(serializers.MultipleChoiceField):
    """A MultipleChoiceField that renders the received value as a JSON-compatible list rather than a set."""

    def to_internal_value(self, data):
        set_value = super().to_internal_value(data)
        return sorted(set_value)
