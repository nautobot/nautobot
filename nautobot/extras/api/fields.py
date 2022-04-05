from collections import OrderedDict

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


class StatusSerializerField(serializers.SlugRelatedField):
    """Serializer field for `Status` object fields."""

    show_choices = True

    def __init__(self, **kwargs):
        kwargs.setdefault("slug_field", "slug")
        super().__init__(**kwargs)

    def to_representation(self, obj):
        """Make this field compatible w/ the existing API for `ChoiceField`."""
        if obj == "":
            return None

        return OrderedDict(
            [
                ("value", obj.slug),
                ("label", str(obj)),
            ]
        )

    def to_internal_value(self, data):
        """Always lower-case the custom choice value."""
        if hasattr(data, "lower"):
            data = data.lower()
        return super().to_internal_value(data)

    def get_queryset(self):
        """Only emit status options for this model/field combination."""
        queryset = super().get_queryset()
        model = self.parent.Meta.model
        return queryset.get_for_model(model)

    def get_choices(self, cutoff=None):
        """
        Return a nested list of dicts for enum choices.

        This had to be overloaded since the base method calls
        `to_representation()` which in our case is an OrderedDict and can't be
        nested.
        """
        queryset = self.get_queryset()
        if queryset is None:
            # Ensure that field.choices returns something sensible
            # even when accessed with a read-only field.
            return {}

        if cutoff is not None:
            queryset = queryset[:cutoff]

        return OrderedDict([(item.slug, self.display_value(item)) for item in queryset])
