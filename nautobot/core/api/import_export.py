"""The import/export wire formats: the JSON/YAML document, and the flat natural-key representation.

`ExportObjectList` builds a document from serializer output and the JSON/YAML import parsers read the same
shape back, so the format lives here rather than on either side of it: the metadata keys, the flat-to-nested
record reshaping, and the reader-side normalization all belong together, and can be exercised without
running a Job or an HTTP request.

CSV's equivalent lives in `NautobotCSVRenderer` because `text/csv` is also a REST API representation; this
format is not (yet) negotiable over HTTP, so it is plain functions rather than a DRF renderer. Should
`?format=...` support for it be added later, the renderer would be a thin wrapper over these.
"""

from django.core.exceptions import FieldDoesNotExist
from rest_framework import serializers

from nautobot.core.api.exceptions import SerializerNotFound
from nautobot.core.api.utils import get_serializer_for_model
from nautobot.core.constants import CSV_NO_OBJECT

# Keys/values for the metadata format shared by CSV/JSON/YAML import and export. In JSON/YAML these are
# document keys; in CSV the version appears as the leading `# key=value` directive, which is also what
# identifies the row as Nautobot's (there is no separate marker).
# The version continues Nautobot's existing lineage: 1 was Nautobot 1.x and 2 was 2.x through 3.2, neither of
# which declared a version, so a file with no version key is either version 1 or 2.
IMPORT_DOCUMENT_VERSION = 3
IMPORT_DOCUMENT_VERSION_KEY = "nautobot_import_version"
IMPORT_DOCUMENT_MODEL_KEY = "model"
IMPORT_DOCUMENT_MATCH_FIELDS_KEY = "match_fields"
IMPORT_DOCUMENT_RECORDS_KEY = "records"

# Serializer fields that describe the API representation rather than the object, and so are omitted.
EXCLUDED_DOCUMENT_FIELDS = ("url", "notes_url")

# Maximum relation-traversal depth permitted in an export field selection (e.g. a__b__c__d = depth 3).
EXPORT_FIELD_MAX_DEPTH = 3


def build_import_metadata(model_label, match_fields=None):
    """The self-describing metadata every export stamps onto its output.

    Shared by both output shapes so a version bump or key rename reaches both: JSON/YAML nests it alongside
    `records` (`build_import_document`), CSV renders it as the leading directive row
    (`NautobotCSVRenderer.render_directive_row`). Insertion order is preserved for readable output.

    Args:
        model_label (str): The `app_label.model` the records belong to.
        match_fields (list, optional): Fields an importer should match on; omitted when falsy.
    """
    metadata = {
        IMPORT_DOCUMENT_VERSION_KEY: IMPORT_DOCUMENT_VERSION,
        IMPORT_DOCUMENT_MODEL_KEY: model_label,
    }
    if match_fields:
        metadata[IMPORT_DOCUMENT_MATCH_FIELDS_KEY] = list(match_fields)
    return metadata


def build_import_document(model_label, records, match_fields=None):
    """Wrap records in the metadata document understood by the JSON/YAML import parsers.

    Args:
        model_label (str): The `app_label.model` the records belong to.
        records (list): The reshaped record dicts, e.g. from `build_document_records`.
        match_fields (list, optional): The fields an importer should match existing records on.

    Returns:
        dict: The metadata document.
    """
    document = build_import_metadata(model_label, match_fields=match_fields)
    document[IMPORT_DOCUMENT_RECORDS_KEY] = records
    return document


def nest_flat_dict(data, null_sentinels=()):
    """
    Convert a dictionary with flat keys separated by '__' into a nested dictionary structure.

    Args:
        data (dict): e.g. `{"name": "Interface 4", "device__name": "Device 1", "device__tenant__name": ""}`
        null_sentinels (iterable): leaf values to replace with None (e.g. the CSV "NoObject"/"NULL" markers).

    Returns:
        (dict): The nested equivalent, e.g. `{"name": "Interface 4", "device": {"name": "Device 1", "tenant": {"name": ""}}}`
    """

    def insert_nested_dict(keys, value, current_dict):
        key = keys[0]
        if len(keys) == 1:
            current_dict[key] = None if value in null_sentinels else value
        else:
            current_dict[key] = current_dict.get(key, {})
            insert_nested_dict(keys[1:], value, current_dict[key])

    result_dict = {}
    for original_key, original_value in data.items():
        split_keys = original_key.split("__")
        insert_nested_dict(split_keys, original_value, result_dict)

    return result_dict


def _null_reference_prefixes(flat_record):
    """The relation paths that a `CSV_NO_OBJECT` in `flat_record` reports as null.

    The annotation that emits the sentinel tests `<relation>__isnull` on the lookup's *parent* relation
    (`BaseModelSerializer._get_lookup_field_name_and_output_field`, which drops the lookup's final
    segment), so `location__parent__name: NoObject` means `location__parent` is null and says nothing
    about `location` itself. When the relation itself is null, its own natural-key lookup
    (`location__name`) is a sentinel too, which is what marks the head as null.

    Read from the pre-nesting record because `nest_flat_dict` maps `CSV_NO_OBJECT` ("no related object
    at this hop") and `CSV_NULL_TYPE` ("the object exists; this one field of it is null") both to None,
    erasing the distinction this relies on.
    """
    return {key.rsplit("__", 1)[0] for key, value in flat_record.items() if "__" in key and value == CSV_NO_OBJECT}


def _prune_missing_references(null_prefixes, prefix, value):
    """Replace each subtree named by `null_prefixes` with a bare None, recursing through the rest."""
    if prefix in null_prefixes:
        return None
    if isinstance(value, dict):
        return {key: _prune_missing_references(null_prefixes, f"{prefix}__{key}", val) for key, val in value.items()}
    return value


def build_document_records(serializer_data):
    """Reshape flat serializer records into the nested representation used by JSON/YAML exports.

    Flattened natural-key lookups (`location__name`) nest under their parent key; enum dicts collapse to
    their value; url fields are dropped.

    Args:
        serializer_data (list): Flat records, as produced by a serializer in natural-key export mode.

    Returns:
        list: The nested record dicts.
    """
    records = []
    for record in serializer_data:
        reshaped = {}
        flattened_heads = set()
        for key, value in record.items():
            if key in EXCLUDED_DOCUMENT_FIELDS:
                continue
            if isinstance(value, dict) and "value" in value and "label" in value:
                # An enum type
                value = value["value"]
            head = key.split("__", 1)[0]
            if "__" in key:
                flattened_heads.add(head)
            reshaped[key] = value
        null_prefixes = _null_reference_prefixes(reshaped)
        # Only CSV_NO_OBJECT needs mapping: it is produced by the natural-key annotation itself (for an
        # absent relation), whereas nulls already arrive as real None in this mode. CSV_NULL_TYPE is
        # deliberately not listed, so a value that is literally the string "NULL" survives intact.
        nested = nest_flat_dict(reshaped, (CSV_NO_OBJECT,))
        for head in flattened_heads:
            # Collapse each null relation to a single None, at the depth the sentinel actually reports
            nested[head] = _prune_missing_references(null_prefixes, head, nested.get(head))
        records.append(nested)
    return records


def _traversable_relation_target(serializer, field):
    """The model that `field` traverses to, or None if a `__` path cannot continue through it.

    The *model* is the authority here, not the serializer field. DRF's `RelatedField` covers things that are
    not model relations at all -- `url` is a `HyperlinkedIdentityField` sourced from `"*"`, i.e. the object
    itself -- while a genuine foreign key may be represented by a field that declares neither a queryset nor
    a related model (`ContentTypeField`). Since a path is ultimately emitted as a database lookup, what the
    model says is what will actually work.

    To-many relations return None: traversing one would multiply rows, and the lookup the export emits for a
    nested path cannot express it.
    """
    try:
        model_field = serializer.Meta.model._meta.get_field(field.source)
    except (AttributeError, FieldDoesNotExist):
        # A serializer-only field (no model field of that name), or a serializer with no model at all
        return None
    if model_field.many_to_many or model_field.one_to_many:
        return None
    # None for a non-relational field, which is exactly the "cannot be expanded" answer
    return model_field.related_model


def validate_field_paths(serializer_class, paths, max_depth=EXPORT_FIELD_MAX_DEPTH):
    """
    Validate a list of `__`-separated field-selection paths against a serializer's field graph.

    A path's head must be a readable field of the serializer *as an export instantiates it* (or a `cf_<key>`
    custom-field reference). Each additional segment must traverse a single-valued relation of the model --
    see `_traversable_relation_target` -- and is then resolved against the related model's serializer.
    Traversal into a to-many relation is not supported (it would multiply rows).
    Paths that reach a related model without a known serializer are accepted and left to the database
    to validate.

    Raises:
        ValueError: describing every invalid path.
    """
    # Instantiated the way `ExportObjectList._get_serializer_data` does, so that the field set vetted here is
    # the one the export will actually emit: `exporting=True` is what makes the opt-in M2M fields readable
    # (`OptInFieldsMixin._readable_m2m_sources`), and without it a column the export produces by default --
    # `dcim.devicetype.software_image_files`, say -- could not be named explicitly.
    # Related serializers below are deliberately *not* built this way: a selection only applies at the root
    # (`NaturalKeyRepresentationMixin` ignores `export_fields` when nested), and a nested path is emitted as a
    # database lookup, which a to-many field cannot satisfy.
    root_serializer = serializer_class(context={"request": None, "depth": 0}, exporting=True)
    errors = []
    for path in paths:
        parts = path.split("__")
        if len(parts) - 1 > max_depth:
            errors.append(f'"{path}" exceeds the maximum relation depth of {max_depth}')
            continue
        if parts[0].startswith("cf_"):
            if len(parts) > 1:
                errors.append(f'"{path}": custom-field references cannot be expanded')
            continue
        serializer = root_serializer
        for index, part in enumerate(parts):
            field = serializer.fields.get(part)
            if field is None:
                errors.append(f'"{path}": unknown field "{part}"')
                break
            if field.write_only:
                # Present in `fields` but not in `_readable_fields`, so `to_representation` never emits it:
                # accepting it would write a file with a column silently missing (or, if it were the only
                # selection, no columns at all).
                errors.append(f'"{path}": "{part}" is write-only and cannot be exported')
                break
            if index == len(parts) - 1:
                break
            if isinstance(field, serializers.ManyRelatedField):
                errors.append(f'"{path}": cannot traverse into many-to-many field "{part}"')
                break
            related_model = _traversable_relation_target(serializer, field)
            if related_model is None:
                errors.append(f'"{path}": "{part}" is not a related field and cannot be expanded')
                break
            try:
                serializer = get_serializer_for_model(related_model)(context={"request": None, "depth": 0})
            except SerializerNotFound:
                # A related model with no serializer of its own: accept the rest of the path and leave it
                # to the database to validate.
                break
    if errors:
        raise ValueError(f"Invalid field selection: {'; '.join(errors)}")
