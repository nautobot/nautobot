"""The fields of a model a condition can name, and what a form needs to know about each.

A condition addresses the change record, not the model, so what it can name is whatever
`serialize_object_v2` puts there. Read from the same serializer, so the two cannot drift apart.
"""

from functools import reduce

from django.core.exceptions import FieldDoesNotExist
from django.urls import NoReverseMatch, reverse
from rest_framework import relations, serializers

from nautobot.core.api.utils import get_serializer_for_model
from nautobot.core.models.fields import ColorField, ForeignKeyLimitedByContentTypes
from nautobot.core.utils.lookup import get_route_for_model
from nautobot.extras.conditions.operators import KIND_BOOLEAN, KIND_DATE, KIND_LIST, KIND_NUMBER, KIND_TEXT

# What the operators compare against, keyed by serializer field. Most specific first: `EmailField` is a `CharField`.
KIND_BY_SERIALIZER_FIELD = (
    ((serializers.BooleanField,), KIND_BOOLEAN),
    ((serializers.DateTimeField, serializers.DateField), KIND_DATE),
    ((serializers.IntegerField, serializers.FloatField, serializers.DecimalField), KIND_NUMBER),
    ((serializers.ListSerializer, serializers.ListField, relations.ManyRelatedField), KIND_LIST),
    ((serializers.CharField, serializers.ChoiceField, serializers.UUIDField), KIND_TEXT),
)


def addressable_fields(*models):
    """The fields a condition can name, as they appear in a change record.

    With more than one model, only the fields they all carry, since one condition is checked against
    each. Every entry has `name` and `label`, and may have `kind`, `picker`, `values_url`, `subfields`.
    """
    if not models:
        return []
    labels = [f"{model._meta.app_label}.{model._meta.model_name}" for model in models]
    return reduce(_in_both, (_described_fields_of(model, labels) for model in models))


def _described_fields_of(model, labels):
    # The context `serialize_object_v2` serializes with, so this lists what a record actually holds.
    serializer = get_serializer_for_model(model)(context={"request": None, "depth": 1, "exclude_m2m": False})
    return [_entry_for(name, field, labels, model) for name, field in _payload_fields(serializer, model)]


def _where_values_are_listed(model, name, related_model, labels):
    """Where a form can read the objects this relation points at, or None if it cannot be reached."""
    try:
        url = reverse(get_route_for_model(related_model, "list", api=True))
    except NoReverseMatch:
        return None
    # A status or a role is asked for only the ones the watched types can hold. Offering one no
    # circuit can have would invite a rule that never runs.
    if labels and isinstance(_model_field(model, name), ForeignKeyLimitedByContentTypes):
        url += "?" + "&".join(f"content_types={label}" for label in labels)
    return url


def _in_both(described, other):
    by_name = {entry["name"]: entry for entry in other}
    shared = []
    for entry in described:
        match = by_name.get(entry["name"])
        if match is None:
            continue
        if "subfields" in entry:
            also = {sub["name"] for sub in match.get("subfields", ())}
            entry = {**entry, "subfields": [sub for sub in entry["subfields"] if sub["name"] in also]}
        shared.append(entry)
    return shared


def _payload_fields(serializer, model):
    """The serializer's fields, minus those a change record never carries."""
    for name, field in serializer.fields.items():
        # A source of `*` is computed and a source the model has is read off the instance. Anything else
        # is a queryset annotation, which a change record never carries.
        if field.source == "*" or hasattr(model, field.source):
            yield name, field


def _stands_for_another_object(field):
    """Whether the record renders this as a mapping of another object, which no comparison matches."""
    # `source != "*"` keeps a plain string sourced from the whole object, such as the record's own `url`.
    return isinstance(field, (serializers.BaseSerializer, relations.RelatedField)) and field.source != "*"


def _model_field(model, name):
    """The model's own field behind a serializer field, or None when there is not one."""
    try:
        return model._meta.get_field(name) if model is not None else None
    except FieldDoesNotExist:
        return None


def _kind_of(field):
    for classes, kind in KIND_BY_SERIALIZER_FIELD:
        if isinstance(field, classes):
            return kind
    return None


def _entry_for(name, field, labels, model):
    described = {"name": name, "label": field.label or name}
    kind = _kind_of(field)
    if kind is not None:
        described["kind"] = kind
    if isinstance(_model_field(model, name), ColorField):
        # Still text to compare, but a form has a swatch picker for it rather than a box to type hex in.
        described["picker"] = "color"
    nested = getattr(field, "fields", None)
    related_model = getattr(getattr(field, "Meta", None), "model", None)
    if nested is not None and related_model is not None:
        values_url = _where_values_are_listed(model, name, related_model, labels)
        if values_url is not None:
            described["values_url"] = values_url
        # One level only. A path that stops at a mapping matches nothing, so a relation inside a
        # relation is not worth offering.
        described["subfields"] = [
            _entry_for(sub_name, sub_field, (), related_model)
            for sub_name, sub_field in _payload_fields(field, related_model)
            if not _stands_for_another_object(sub_field)
        ]
    return described
