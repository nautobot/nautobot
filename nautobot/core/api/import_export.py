"""The import/export wire formats: the JSON/YAML document, and the flat natural-key representation.

`ExportObjectList` builds a document from serializer output and the JSON/YAML import parsers read the same
shape back, so the format lives here rather than on either side of it: the metadata keys, the flat-to-nested
record reshaping, and the reader-side normalization all belong together, and can be exercised without
running a Job or an HTTP request.

CSV's equivalent lives in `NautobotCSVRenderer` because `text/csv` is also a REST API representation; this
format is not (yet) negotiable over HTTP, so it is plain functions rather than a DRF renderer. Should
`?format=...` support for it be added later, the renderer would be a thin wrapper over these.
"""

from dataclasses import dataclass

from django.core.exceptions import FieldDoesNotExist
from rest_framework import serializers

from nautobot.core.api.exceptions import SerializerNotFound
from nautobot.core.api.utils import get_serializer_for_model
from nautobot.core.constants import CSV_NO_OBJECT
from nautobot.core.utils.permissions import permission_is_exempt

# Keys/values for the metadata format shared by CSV/JSON/YAML import and export. In JSON/YAML these are
# document keys; in CSV the version appears as the leading `# key=value` directive, which is also what
# identifies the row as Nautobot's (there is no separate marker).
# The version continues Nautobot's existing lineage: 1 was Nautobot 1.x and 2 was 2.x through 3.2, neither of
# which declared a version, so a file with no version key is either version 1 or 2.
IMPORT_DOCUMENT_VERSION = 3
IMPORT_DOCUMENT_VERSION_KEY = "nautobot_import_version"
# The versions an import will read. A file declaring no version at all is accepted rather than assumed to
# be unreadable, per the lineage described above.
SUPPORTED_IMPORT_DOCUMENT_VERSIONS = (IMPORT_DOCUMENT_VERSION,)
IMPORT_DOCUMENT_MODEL_KEY = "model"
IMPORT_DOCUMENT_MATCH_FIELDS_KEY = "match_fields"
IMPORT_DOCUMENT_RECORDS_KEY = "records"
IMPORT_DOCUMENT_METADATA_KEYS = (
    IMPORT_DOCUMENT_VERSION_KEY,
    IMPORT_DOCUMENT_MODEL_KEY,
    IMPORT_DOCUMENT_MATCH_FIELDS_KEY,
)

# Serializer fields that describe the API representation rather than the object, and so are omitted.
EXCLUDED_DOCUMENT_FIELDS = ("url", "notes_url")

# Serializer fields a flat (CSV) export does not emit as columns of their own: the two above, plus the three
# that hold a collection of other data rather than a value of the object. `custom_fields` is replaced by a
# `cf_<key>` column per custom field (`NautobotCSVRenderer.get_headers`), while `computed_fields` and
# `relationships` have no flat spelling at all.
EXCLUDED_CSV_FIELDS = (*EXCLUDED_DOCUMENT_FIELDS, "computed_fields", "custom_fields", "relationships")

# The fields that identify an object rather than describe it, in the order they should lead: a flat export
# puts these columns first whatever the serializer's own order (`NautobotCSVRenderer.get_headers`), and the
# export field picker lists them first for the same reason -- they are what someone looks for first.
PRIORITY_CSV_FIELDS = ("name", "display", "composite_key", "id")

# Maximum number of relations one export field-selection path may traverse (`a__b__c__d` = 3).
#
# This counts only the hops *named in the path*. A path that ends at a relation is expanded to that
# relation's natural-key lookups, which add hops of their own, and those are deliberately not counted: the
# expansion is how a relation is represented rather than anything the user asked for, and an unrestricted
# export of the same model already emits it -- `dcim.CableToCableTermination` emits
# `front_port__rear_port__device__tenant__name` (depth 4) with no selection at all. Counting it would make a
# selective export stricter than a full one, and would reject bare field names such as
# `CableToCableTermination.front_port` with no shorter spelling available.
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


def _order_by_selection(mapping, field_order):
    """`mapping` with its keys in `field_order`, each key taking the earliest entry it equals or nests under.

    The same rule `NautobotCSVRenderer.get_headers()` orders columns by, so that a selection lays a
    document out in the order it asked for exactly as it lays out CSV columns. Keys the selection does not
    name -- which an unrestricted export is entirely made of -- sort last, and an empty selection leaves
    the mapping alone rather than imposing an order of its own.
    """
    if not field_order:
        return mapping

    def selection_index(key):
        for position, selected in enumerate(field_order):
            if key == selected or key.startswith(f"{selected}__"):
                return (position, key)
        return (len(field_order), key)

    return {key: mapping[key] for key in sorted(mapping, key=selection_index)}


def build_document_records(serializer_data, field_order=None):
    """Reshape flat serializer records into the nested representation used by JSON/YAML exports.

    Flattened natural-key lookups (`location__name`) nest under their parent key; enum dicts collapse to
    their value; url fields are dropped. A selection orders the keys, as it orders CSV's columns.

    Custom fields have two spellings, chosen by what the selection asks for: `custom_fields` (or no
    selection at all) keeps the whole dict, while individual `cf_<key>` entries are emitted as top-level
    `cf_<key>` keys -- the same spelling CSV uses, since one custom field cannot be named inside the dict.

    Args:
        serializer_data (list): Flat records, as produced by a serializer in natural-key export mode.
        field_order (list, optional): The export field selection, if one is in effect.

    Returns:
        list: The nested record dicts.
    """
    selected_custom_fields = None
    if field_order and "custom_fields" not in field_order:
        selected_custom_fields = [entry for entry in field_order if entry.startswith("cf_")]

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
        # Ordered before nesting so that the order reaches inside a relation too: `nest_flat_dict()`
        # builds each level in the order it meets the keys, so `location__name` before `location__id`
        # here is `name` before `id` within `location` there.
        reshaped = _order_by_selection(reshaped, field_order)
        # Only CSV_NO_OBJECT needs mapping: it is produced by the natural-key annotation itself (for an
        # absent relation), whereas nulls already arrive as real None in this mode. CSV_NULL_TYPE is
        # deliberately not listed, so a value that is literally the string "NULL" survives intact.
        nested = nest_flat_dict(reshaped, (CSV_NO_OBJECT,))
        for head in flattened_heads:
            # Collapse each null relation to a single None, at the depth the sentinel actually reports
            nested[head] = _prune_missing_references(null_prefixes, head, nested.get(head))
        if selected_custom_fields is not None:
            # After nesting, not before: a custom-field key may itself contain `__` (auto-slugification
            # never produces one, but a key can be set explicitly), and `nest_flat_dict` would split it.
            custom_fields = nested.pop("custom_fields", {})
            for entry in selected_custom_fields:
                nested[entry] = custom_fields.get(entry.removeprefix("cf_"))
            # Again, the custom fields having arrived after everything else: a selection that names one
            # between two ordinary fields puts it there, as it does in CSV.
            nested = _order_by_selection(nested, field_order)
        records.append(nested)
    return records


def _model_field_for(serializer, field):
    """The model field that `field` reads, or None if it does not correspond to one.

    Every segment of a path past the head is emitted as a database lookup, so it has to be a column the
    database can resolve. `display` is a model *property*, and `url`, `object_type` and `natural_slug` are
    computed by the serializer; none is queryable, so all four exist only on the object being exported.
    """
    try:
        return serializer.Meta.model._meta.get_field(field.source)
    except (AttributeError, FieldDoesNotExist):
        # A serializer-only field (no model field of that name), or a serializer with no model at all
        return None


def _needs_a_queryset_annotation(serializer, field):
    """Whether `field` reads an instance attribute that the model does not itself provide.

    Such a field renders only where something has annotated the queryset to put the attribute there: the
    related-object counts a list view shows (`device_count`, `rack_count`, ...) are `annotate()` calls
    made by the API viewset that serves them, or by the table that displays them. An export builds its
    own queryset and annotates nothing, so DRF finds no attribute to read and skips the field -- which,
    for a field named in a selection, would leave the file silently missing a requested column.

    A field sourced from `"*"` reads the whole object rather than an attribute of it (`display`,
    `object_type`, `natural_slug`), and so is never in this position.
    """
    if not field.source_attrs:
        return False
    if _model_field_for(serializer, field) is not None:
        return False
    model = getattr(getattr(serializer, "Meta", None), "model", None)
    return model is not None and not hasattr(model, field.source_attrs[0])


def _traversable_relation_target(serializer, field):
    """The model that `field` traverses to, or None if a `__` path cannot continue through it.

    The *model* is the authority here, not the serializer field. DRF's `RelatedField` covers things that are
    not model relations at all -- `url` is a `HyperlinkedIdentityField` sourced from `"*"`, i.e. the object
    itself -- while a genuine foreign key may be represented by a field that declares neither a queryset nor
    a related model (`ContentTypeField`).

    To-many relations return None: a nested path is emitted as one flat database lookup, which cannot
    express a value per member. Selecting the field itself works (its members render through
    `_get_m2m_natural_key_values`), so this is a limit of the mechanism rather than of the file format --
    which can already carry a per-member-field list, as `NautobotCSVParser` accepts on import.
    """
    model_field = _model_field_for(serializer, field)
    if model_field is None or model_field.many_to_many or model_field.one_to_many:
        return None
    # None for a non-relational field, which is exactly the "cannot be expanded" answer
    return model_field.related_model


@dataclass
class ExportFieldPath:
    """One field path an export may select, as `enumerate_field_paths()` offers it."""

    # The `__`-separated path that selects the field, e.g. `device_type__manufacturer__name`.
    path: str
    # The path this one nests under: all but the last segment, except that a `cf_<key>` nests under
    # `custom_fields`. None at the top level.
    parent: str | None
    # The field's own human-readable name, e.g. "Manufacturer".
    label: str
    # Whether an import needs this field to create a record. Only ever true at the top level, as an import
    # looks related objects up rather than creating them.
    required: bool
    # Whether the path names a related object, which exports as the fields that identify it.
    relation: bool
    # For a related object with paths nested under it, those of them that make up its natural key; see
    # `_natural_key_descendants()`. None otherwise.
    natural_key: list[str] | None = None


def natural_key_lookups_for(model):
    """`model.csv_natural_key_field_lookups()`, or None if `model` is None or has no such natural key.

    `ContentType` and `Group`, for example, are not Nautobot models, and are exported in a representation of
    their own rather than as lookups.
    """
    lookups_method = getattr(model, "csv_natural_key_field_lookups", None)
    if lookups_method is None:
        return None
    try:
        return lookups_method()
    except AttributeError:
        # How `BaseModel.natural_key_field_lookups` reports a model with no identifiable natural key.
        return None


def expand_relation_paths(model, paths):
    """Expand each nested path that ends at a related object into that object's natural-key lookups.

    Without this, such a path would export the related object's primary key. A bare relation such as
    `location` needs no expansion, as the serializer already exports it by natural key.

    Where a shallower relation's natural key continues through the rest of the path and names every field of
    the related object's own natural key, its lookups are used instead, so that a natural key the export field
    picker cut short is completed rather than restarted. They may follow a relation less deeply than the
    related object's own would -- a Location's ancestry, say, beyond which there is nothing to export -- but
    they must name each of its fields, or they would only pass through the object rather than identify it.

    Example (a Location tree three levels deep):
        >>> expand_relation_paths(SoftwareImageFile, ["image_file_name", "software_version__platform"])
        ["image_file_name", "software_version__platform__name"]
        >>> expand_relation_paths(Device, ["location__parent__parent"])  # not the 3 lookups of a Location
        ["location__parent__parent__name"]
        >>> # An IPAddress's natural key passes through its parent Prefix's namespace, which alone is not enough
        >>> expand_relation_paths(Interface, ["device__primary_ip4__parent"])
        ["device__primary_ip4__parent__namespace__name", "device__primary_ip4__parent__network", ...]

    Paths are kept in order; any other path is returned unchanged.
    """
    expanded = []
    for path in paths:
        replacement = [path]
        segments = path.split("__")
        # The model reached by each segment of the path, while the path keeps reaching related objects.
        reached = []
        related_model = model
        for segment in segments:
            try:
                field = related_model._meta.get_field(segment)
            except FieldDoesNotExist:
                break
            related_model = field.related_model if not (field.many_to_many or field.one_to_many) else None
            if related_model is None:
                break
            reached.append(related_model)
        own_lookups = natural_key_lookups_for(reached[-1]) if 1 < len(segments) == len(reached) else None
        if own_lookups:
            own_fields = {lookup.split("__", 1)[0] for lookup in own_lookups}
            replacement = [f"{path}__{lookup}" for lookup in own_lookups]
            for depth in range(1, len(segments)):
                remainder = "__".join(segments[depth:])
                tails = [
                    lookup.removeprefix(f"{remainder}__")
                    for lookup in natural_key_lookups_for(reached[depth - 1]) or ()
                    if lookup.startswith(f"{remainder}__")
                ]
                if own_fields <= {tail.split("__", 1)[0] for tail in tails}:
                    replacement = [f"{path}__{tail}" for tail in tails]
                    break
        expanded.extend(entry for entry in replacement if entry not in expanded)
    return expanded


def _view_permission_error(path, model, user):
    """The validation error for `path` if `user` may not view `model`, else None (also for a `model` of None)."""
    if model is None:
        return None
    permission = f"{model._meta.app_label}.view_{model._meta.model_name}"
    if permission_is_exempt(permission) or user.has_perm(permission):
        return None
    return f'"{path}": requires permission to view {model._meta.label_lower}; without it, only "id" may be selected'


def _selects_only_a_natural_key(model, path):
    """Whether `path` selects nothing but (part of) the natural key of the relation of `model` it starts with.

    Such a path exports no more than the bare relation does -- `location__name` is one of the columns `location`
    exports -- and the bare relation needs no permission to view the related model, so neither does this.

    Example:
        >>> _selects_only_a_natural_key(Device, "location__parent__name")
        True
        >>> _selects_only_a_natural_key(Device, "location__description")
        False
    """
    head = path.split("__", 1)[0]
    try:
        field = model._meta.get_field(head)
    except FieldDoesNotExist:
        return False
    if field.many_to_many or field.one_to_many:
        return False
    lookups = natural_key_lookups_for(field.related_model)
    if not lookups:
        return False
    natural_key = {f"{head}__{lookup}" for lookup in lookups}
    # A natural key's `pk` lookup is selected as `id`, the serializer's name for it.
    selected = [
        expanded.removesuffix("__id") + "__pk" if expanded.endswith("__id") else expanded
        for expanded in expand_relation_paths(model, [path])
    ]
    return set(selected) <= natural_key


def validate_field_paths(serializer_class, paths, *, user, max_depth=EXPORT_FIELD_MAX_DEPTH):
    """
    Validate a list of `__`-separated field-selection paths against a serializer's field graph.

    A path's head must be a readable field of the serializer *as an export instantiates it* (or a `cf_<key>`
    custom-field reference), and must be one an export can actually emit -- not write-only, and not
    dependent on a queryset annotation an export does not make (see `_needs_a_queryset_annotation`). Each
    additional segment must traverse a single-valued relation of the model --
    see `_traversable_relation_target` -- and is then resolved against the related model's serializer.
    Traversal into a to-many relation is not supported; see `_traversable_relation_target`.
    Paths that reach a related model without a known serializer are accepted and left to the database
    to validate.

    `max_depth` bounds the relations a path may name; the natural-key expansion of a path that ends at a
    relation is not counted against it. See `EXPORT_FIELD_MAX_DEPTH`.

    `user` must hold `view` permission on every model a path reaches into, `id` excepted -- including the
    model a nested path ends at, when that path is expanded to its natural key. A path selecting only part of a
    top-level relation's natural key is excepted too, as it exports no more than the bare relation, which is
    not checked. Required, with no value that disables the check; pass an `AnonymousUser` to permit nothing.

    Raises:
        ValueError: describing every invalid path.
    """
    # Instantiated the way `ExportObjectList._get_serializer_data` does, so that the field set vetted here is
    # the one the export will actually emit: `for_import_export=True` is what makes the opt-in M2M fields readable
    # (`OptInFieldsMixin._readable_m2m_sources`), and without it a column the export produces by default --
    # `dcim.devicetype.software_image_files`, say -- could not be named explicitly.
    # Related serializers below are deliberately *not* built this way: a selection only applies at the root
    # (`NaturalKeyRepresentationMixin` ignores `export_fields` when nested), and a nested path is emitted as a
    # database lookup, which a to-many field cannot satisfy.
    root_serializer = serializer_class(context={"request": None, "depth": 0}, for_import_export=True)
    errors = []
    for path in paths:
        parts = path.split("__")
        if len(parts) - 1 > max_depth:
            errors.append(f'"{path}" traverses more than {max_depth} relations')
            continue
        if parts[0].startswith("cf_"):
            if len(parts) > 1:
                errors.append(f'"{path}": custom-field references cannot be expanded')
                continue
            # Keys via the serializer's `custom_fields` field, so `nautobot.core` need not import
            # `nautobot.extras`; a model with no custom fields has no such field, hence no valid keys.
            key = parts[0].removeprefix("cf_")
            if key not in getattr(root_serializer.fields.get("custom_fields"), "custom_field_keys", ()):
                errors.append(f'"{path}": unknown custom field "{key}"')
            continue
        check_permissions = len(parts) == 1 or not _selects_only_a_natural_key(serializer_class.Meta.model, path)
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
                if index > 0 and _model_field_for(serializer, field) is None:
                    # TODO: these *should* be selectable -- they are ordinary readable fields at the root.
                    #   Supporting them means excluding them from the natural-key `Case` query and resolving
                    #   them per row instead (`display` is `getattr(obj, "display", str(obj))`), which is a
                    #   change to `NaturalKeyRepresentationMixin` rather than to validation. Rejected for
                    #   now only so the Job fails cleanly instead of raising `FieldDoesNotExist` from deep
                    #   inside the query construction.
                    errors.append(f'"{path}": "{part}" cannot yet be selected through a relation')
                elif _needs_a_queryset_annotation(serializer, field):
                    # Rejected for the same reason as a write-only field: DRF skips it rather than
                    # raising, so the file would come out missing a column that was asked for by name.
                    errors.append(f'"{path}": "{part}" is computed for display only and cannot be exported')
                elif index > 0 and check_permissions:
                    # A nested path ending at a related object is expanded to its natural key
                    # (`expand_relation_paths()`), which reads that object as surely as naming its fields would.
                    related_model = _traversable_relation_target(serializer, field)
                    if natural_key_lookups_for(related_model) and (
                        error := _view_permission_error(path, related_model, user)
                    ):
                        errors.append(error)
                break
            if isinstance(field, serializers.ManyRelatedField):
                errors.append(f'"{path}": cannot traverse into many-to-many field "{part}"')
                break
            related_model = _traversable_relation_target(serializer, field)
            if related_model is None:
                errors.append(f'"{path}": "{part}" is not a related field and cannot be expanded')
                break
            # `id` is exempt, being what an unviewable relation is reduced to; `display` is intended to join
            # it once selectable through a relation at all (see below). Checked before the remaining
            # segments are resolved, so this does not report whether a field a user cannot see exists.
            if (
                check_permissions
                and parts[index + 1 :] != ["id"]
                and (error := _view_permission_error(path, related_model, user))
            ):
                errors.append(error)
                break
            try:
                serializer = get_serializer_for_model(related_model)(context={"request": None, "depth": 0})
            except SerializerNotFound:
                # A related model with no serializer of its own: accept the rest of the path and leave it
                # to the database to validate.
                break
    if errors:
        raise ValueError(f"Invalid field selection: {'; '.join(errors)}")


def enumerate_field_paths(serializer_class, *, max_segments=EXPORT_FIELD_MAX_DEPTH, for_csv=True):
    """
    Every field path a selection may name for this serializer, in an order meant to be read by a person.

    Among the fields of one object -- the top-level rows, or the fields nested under one relation -- what
    identifies it leads (`PRIORITY_CSV_FIELDS`, as in an unordered export's columns), then the fields an
    import requires, then the rest, each of those two groups alphabetical, and `custom_fields` last with
    its own fields nested under it. Only the root has a required group, nothing below it being required
    of anyone (see `required` under Returns). Serializer declaration order is deliberately not used: it is
    rarely arranged with intent, so it reads as arbitrary in a list someone has to find a field in.

    This is the order the fields are *offered* in, which is only the starting point for a selection: the
    order a selection is submitted in is the order its columns come out in, and rearranging it is what the
    picker is for.

    The counterpart to `validate_field_paths()`, and for the shape of a path its subset: what is offered
    here validates, so a UI built on it cannot propose a column the export would reject or silently drop.
    Where the two differ on shape, this is the stricter one:

    * The fields that hold a collection of other data (`EXCLUDED_CSV_FIELDS`) are left out below the root,
      `custom_fields` included -- it is reachable as a model field (`_custom_field_data`) through a
      relation, but a column of raw JSON is not a useful thing to offer.
    * A to-many field is not offered through a relation. One flat lookup cannot express a value per member,
      so the query would multiply rows; selecting it at the root is fine, where its members render as a
      joined list.

    Permissions are deliberately *not* consulted: this enumerates what the data model allows, and
    `validate_field_paths()` remains the single authority on what a given user may select -- it refuses a
    path into a model the user cannot view, with a message naming the permission. Gating here instead would
    mean a picker that renders differently per user and a second place for the rule to be wrong, in exchange
    for hiding a path the run would reject anyway.

    `max_segments` bounds the segments a path may have, rather than the relations it traverses as
    `EXPORT_FIELD_MAX_DEPTH` does, so the default enumerates one relation less deep than a hand-written
    selection may name. The field graph fans out fast enough that the last level is mostly noise.

    Args:
        serializer_class: The serializer of the model being exported.
        max_segments (int): Longest path to enumerate, counted in `__`-separated segments.
        for_csv (bool): Whether the paths are for a flat (CSV) export, which has fewer emittable fields
            than the document formats.

    A relation is only descended into if an export represents it by its natural key's lookups (see
    `natural_key_lookups_for()`). One represented any other way -- a `ContentType`, say -- is offered as
    a field of its own with nothing under it, since what is under it would not be what selecting it gives.

    Returns:
        list[ExportFieldPath]: The offered paths, in reading order.
    """
    # `custom_fields` is offered at the root even though a flat export emits no column of that name: naming
    # it asks for every custom field of the object at once -- including any added after the selection was
    # made -- which the individual `cf_<key>` entries cannot express, and it is how a document export spells
    # the whole nested dict. Reached through a relation there is no such expansion, only a lookup returning
    # the raw JSON of `_custom_field_data`, so there it stays unoffered along with the other containers.
    excluded_below_root = EXCLUDED_CSV_FIELDS
    excluded_at_root = tuple(
        name for name in (EXCLUDED_CSV_FIELDS if for_csv else EXCLUDED_DOCUMENT_FIELDS) if name != "custom_fields"
    )
    paths = []
    # The model each offered relation leads to, for resolving its natural key once everything is offered.
    relation_models = {}
    # Per model, since `Location`'s lookups query how deeply locations are nested.
    natural_key_lookups = {}

    def _natural_key_lookups(model):
        if model not in natural_key_lookups:
            natural_key_lookups[model] = natural_key_lookups_for(model)
        return natural_key_lookups[model]

    def _sort_key(field_name, field):
        if field_name in PRIORITY_CSV_FIELDS:
            # What identifies the object, ahead of everything and in their own order.
            return (0, PRIORITY_CSV_FIELDS.index(field_name), "")
        if field_name == "custom_fields":
            # Last, with its own fields nested under it: whatever this model happens to have been given,
            # rather than part of its shape.
            return (3, 0, field_name)
        return (1 if field.required else 2, 0, field_name)

    def _ordered_fields(serializer):
        """This object's fields, in the order a person reads them; see this function's docstring."""
        return sorted(serializer.fields.items(), key=lambda item: _sort_key(*item))

    def _walk(prefix, serializer, segments):
        for field_name, field in _ordered_fields(serializer):
            if field_name in (excluded_below_root if prefix else excluded_at_root):
                continue
            if field.write_only or _needs_a_queryset_annotation(serializer, field):
                # Not emitted at all, and so not selectable; `validate_field_paths()` explains both.
                continue
            if prefix and (
                _model_field_for(serializer, field) is None or isinstance(field, serializers.ManyRelatedField)
            ):
                # Past the head a segment becomes a database lookup, which reaches model columns only, and
                # cannot be a to-many.
                continue
            path = f"{prefix}__{field_name}" if prefix else field_name
            # Resolved before the depth check, not after: a relation at the deepest offered level has no
            # fields listed under it, but selecting it still exports its natural key, and a UI has no
            # other way to tell that from an ordinary field.
            related_model = _traversable_relation_target(serializer, field)
            paths.append(
                ExportFieldPath(
                    path=path,
                    parent=prefix or None,
                    label=str(field.label),
                    # Required only where it means anything: at the root, where an import creates the record.
                    required=field.required and not prefix,
                    relation=related_model is not None,
                )
            )
            if related_model is None:
                continue
            relation_models[path] = related_model
            if segments >= max_segments or _natural_key_lookups(related_model) is None:
                continue
            try:
                related_serializer = get_serializer_for_model(related_model)(context={"request": None, "depth": 0})
            except SerializerNotFound:
                # No serializer to enumerate. A hand-written path into it is still accepted, so this
                # narrows what is offered rather than what is possible.
                continue
            _walk(path, related_serializer, segments + 1)

    # Instantiated as `validate_field_paths()` does, and for the same reason: the field set enumerated here
    # has to be the one the export will actually emit.
    root_serializer = serializer_class(context={"request": None, "depth": 0}, for_import_export=True)
    _walk("", root_serializer, 1)

    if for_csv:
        # One column per custom field, which is how CSV spells a single one; last, as `get_headers()` orders
        # them. Nested under `custom_fields`, which asks for all of them at once, so that the two spellings
        # read as what they are -- the whole and its parts -- rather than as overlapping options.
        custom_fields_field = root_serializer.fields.get("custom_fields")
        custom_field_keys = getattr(custom_fields_field, "custom_field_keys", ())
        custom_field_labels = getattr(custom_fields_field, "custom_field_labels", {}) if custom_field_keys else {}
        paths.extend(
            ExportFieldPath(
                path=f"cf_{key}",
                parent="custom_fields",
                label=custom_field_labels.get(key) or key,
                required=False,
                relation=False,
            )
            for key in sorted(custom_field_keys)
        )

    offered = {entry.path for entry in paths}
    parents = {entry.parent for entry in paths}
    for entry in paths:
        if entry.path in parents and entry.path in relation_models:
            entry.natural_key = _natural_key_descendants(
                entry.path, _natural_key_lookups(relation_models[entry.path]), offered
            )

    return paths


def _natural_key_descendants(path, lookups, offered):
    """The paths in `offered` that select the natural key of the relation `path`, given its `lookups`.

    A lookup too deep to be offered is cut off at the deepest offered relation along it, which exports the
    rest of the lookup as its own natural key.

    Example:
        >>> _natural_key_descendants(
        ...     "location",
        ...     ["name", "parent__name", "parent__parent__name"],
        ...     {"location__name", "location__parent__name", "location__parent__parent", ...},
        ... )
        ["location__name", "location__parent__name", "location__parent__parent"]
    """
    descendants = []
    for lookup in lookups or ():
        # A lookup spells the primary key `pk`, where a serializer -- and so a path -- spells it `id`.
        segments = ["id" if segment == "pk" else segment for segment in lookup.split("__")]
        for depth in range(len(segments), 0, -1):
            candidate = "__".join((path, *segments[:depth]))
            if candidate in offered:
                if candidate not in descendants:
                    descendants.append(candidate)
                break
    return descendants
