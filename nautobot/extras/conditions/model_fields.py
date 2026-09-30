"""The fields of a model a condition can name, and what a form needs to know about each.

A condition addresses the serialized change record, not the model, so what can be named is whatever
`serialize_object_v2` puts in that record. Everything here is derived from the same serializer it uses,
so the two cannot drift apart.
"""

from functools import reduce

from django.core.exceptions import FieldDoesNotExist
from django.urls import NoReverseMatch, reverse
from rest_framework import relations, serializers

from nautobot.core.api.utils import get_serializer_for_model
from nautobot.core.models.fields import ColorField, ForeignKeyLimitedByContentTypes
from nautobot.core.utils.lookup import get_route_for_model
from nautobot.extras.conditions.operators import KIND_BOOLEAN, KIND_DATE, KIND_LIST, KIND_NUMBER, KIND_TEXT

# What the operators compare against, keyed by what the serializer renders. Most specific first, because
# `EmailField` is a `CharField` and `DateTimeField` is not a `DateField`. A field matching none of these
# is left without a kind, which `operators_for_kind` reads as "offer everything".
KIND_BY_SERIALIZER_FIELD = (
    ((serializers.BooleanField,), KIND_BOOLEAN),
    ((serializers.DateTimeField, serializers.DateField), KIND_DATE),
    ((serializers.IntegerField, serializers.FloatField, serializers.DecimalField), KIND_NUMBER),
    ((serializers.ListSerializer, serializers.ListField, relations.ManyRelatedField), KIND_LIST),
    ((serializers.CharField, serializers.ChoiceField, serializers.UUIDField), KIND_TEXT),
)


def addressable_fields(*models):
    """
    The fields a condition can name, as they appear in a change record.

    Args:
        *models: The models whose changes the conditions are checked against. With more than one, only
            the fields they all carry are returned, since one condition is checked against every one.

    Returns:
        (list): One entry per field, in the order the serializer declares them, with `"name"` and
            `"label"` always, `"kind"` when the value's type is known, `"widget"` when a form has a
            better control than a text box, and `"values_url"` and `"subfields"` on a relation.
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
    """Where a form can read the objects this relation can point at, or None if it cannot be reached.

    A relation whose choices the declaring model narrows, a status or a role, is asked for only the ones
    the watched types can hold. Offering a status no circuit can have would invite a rule that never runs.
    """
    try:
        url = reverse(get_route_for_model(related_model, "list", api=True))
    except NoReverseMatch:
        return None
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
        # A field sourced from the whole object is computed, and one sourced from a model attribute is
        # read off the instance. Anything else is an annotation, supplied by a queryset that a change
        # record is not built from.
        if field.source == "*" or hasattr(model, field.source):
            yield name, field


def _stands_for_another_object(field):
    """Whether the record renders this as a mapping of a different object, which no comparison matches.

    A link to the object being described, such as its own `url`, is sourced from the whole object and is
    a plain string, so it stays.
    """
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
        described["widget"] = "color"
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
