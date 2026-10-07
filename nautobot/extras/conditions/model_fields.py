"""The fields of a model a condition can name, and what a form needs to know about each.

A condition addresses the change record, not the model, so what it can name is whatever
`serialize_object_v2` puts there. Read from the same serializer, so the two cannot drift apart. Custom
fields are not fields of the serializer, so they are read from `CustomField`, the set the record is
written from.
"""

from functools import reduce

from django.core.exceptions import FieldDoesNotExist
from django.urls import NoReverseMatch, reverse
from rest_framework import relations, serializers

from nautobot.core.api.utils import get_serializer_for_model
from nautobot.core.models.fields import ColorField, ForeignKeyLimitedByContentTypes, TagsField
from nautobot.core.utils.lookup import get_route_for_model
from nautobot.extras.api.customfields import CustomFieldsDataField
from nautobot.extras.choices import CustomFieldTypeChoices
from nautobot.extras.conditions.operators import KIND_BOOLEAN, KIND_DATE, KIND_LIST, KIND_NUMBER, KIND_TEXT
from nautobot.extras.models import CustomField, CustomFieldChoice

# What the operators compare against, keyed by serializer field. Most specific first: `EmailField` is a `CharField`.
KIND_BY_SERIALIZER_FIELD = (
    ((serializers.BooleanField,), KIND_BOOLEAN),
    ((serializers.DateTimeField, serializers.DateField), KIND_DATE),
    ((serializers.IntegerField, serializers.FloatField, serializers.DecimalField), KIND_NUMBER),
    ((serializers.ListSerializer, serializers.ListField, relations.ManyRelatedField), KIND_LIST),
    ((serializers.CharField, serializers.ChoiceField, serializers.UUIDField), KIND_TEXT),
)

# What the operators compare against, keyed by custom field type. JSON is absent, having no kind.
KIND_BY_CUSTOM_FIELD_TYPE = {
    **dict.fromkeys(CustomFieldTypeChoices.TEXT_LIKE_TYPES, KIND_TEXT),
    CustomFieldTypeChoices.TYPE_SELECT: KIND_TEXT,
    CustomFieldTypeChoices.TYPE_MULTISELECT: KIND_LIST,
    CustomFieldTypeChoices.TYPE_INTEGER: KIND_NUMBER,
    CustomFieldTypeChoices.TYPE_BOOLEAN: KIND_BOOLEAN,
    CustomFieldTypeChoices.TYPE_DATE: KIND_DATE,
    CustomFieldTypeChoices.TYPE_DATETIME: KIND_DATE,
}


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
    return list(_entries_for_fields(_payload_fields(serializer, model), labels, model))


def _entries_for_fields(named_fields, labels, model):
    """One entry for each field, except `custom_fields`, which gives one entry for each custom field."""
    for name, field in named_fields:
        if isinstance(field, CustomFieldsDataField):
            yield from _custom_field_entries(name, model)
        else:
            yield _entry_for(name, field, labels, model)


def _custom_field_entries(name, model):
    """One field for each custom field the record carries under `name`, less those no operator compares."""
    choices_url = reverse(get_route_for_model(CustomFieldChoice, "list", api=True))
    for custom_field in CustomField.objects.get_for_model(model, get_queryset=False):
        kind = KIND_BY_CUSTOM_FIELD_TYPE.get(custom_field.type)
        if kind is None:
            continue
        entry = {"name": f"{name}.{custom_field.key}", "label": custom_field.label, "kind": kind}
        if custom_field.type in CustomFieldTypeChoices.SELECTION_TYPES:
            entry["values_url"] = f"{choices_url}?custom_field={custom_field.key}"
        yield entry


def _where_values_are_listed(model, name, related_model, labels):
    """Where a form can read the objects this relation points at, or None if it cannot be reached."""
    try:
        url = reverse(get_route_for_model(related_model, "list", api=True))
    except NoReverseMatch:
        return None
    # A status, a role or a tag is asked for only the ones the watched content types can hold.
    if labels and isinstance(_model_field(model, name), (ForeignKeyLimitedByContentTypes, TagsField)):
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
    one_object_or_field = field.child if isinstance(field, serializers.ListSerializer) else field
    nested = getattr(one_object_or_field, "fields", None)
    related_model = getattr(getattr(one_object_or_field, "Meta", None), "model", None)
    if nested is not None and related_model is not None:
        values_url = _where_values_are_listed(model, name, related_model, labels)
        if values_url is not None:
            described["values_url"] = values_url
        # A many-valued relation is compared whole, so it has no sub-field.
        if kind != KIND_LIST:
            fields_that_are_not_relations = (
                (sub_name, sub_field)
                for sub_name, sub_field in _payload_fields(one_object_or_field, related_model)
                if not _stands_for_another_object(sub_field)
            )
            described["subfields"] = list(_entries_for_fields(fields_that_are_not_relations, (), related_model))
    return described
