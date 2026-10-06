"""Helpers shared by the `ExportObjectList` and `ImportObjects` system Jobs and the commands that run them."""

import csv
from enum import Enum
import json
import re

from django.core.exceptions import FieldError, ObjectDoesNotExist, ValidationError
from rest_framework import serializers
import yaml

from nautobot.core.constants import CSV_NO_OBJECT
from nautobot.core.models.querysets import RestrictedQuerySet
from nautobot.core.utils.requests import mock_wsgi_request

# A YAML block-mapping key at the start of a line: `records:`, `model: dcim.device`.
_YAML_MAPPING_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_.-]*\s*:(\s|$)")


class ImportRowOutcome(Enum):
    """What importing one row of data did, when it succeeded. An unchanged row's save is rolled back."""

    CREATED = "created"
    UPDATED = "updated"
    UNCHANGED = "unchanged"


def restricted_queryset(model, user, action):
    """Every object of `model` that `user` may perform `action` (`"view"`, `"add"`, ...) on, unfiltered and unordered.

    A model whose default manager is not one of Nautobot's has no `restrict()` to call: `auth.Group` and
    `contenttypes.ContentType` are plain Django models, and `users.User`'s manager extends Django's own
    `UserManager`. Wrapping such a model in a `RestrictedQuerySet` applies object permissions to it all the
    same, which is what `users.api.views` does for the very same reason.
    """
    queryset = model.objects.all()
    if not hasattr(queryset, "restrict"):
        queryset = RestrictedQuerySet(model=model)
    return queryset.restrict(user, action)


def import_serializer_context(user):
    """The serializer context an import deserializes under.

    Carries a request, built as `web_request_context` builds one, because some serializers take the owning
    user from it rather than from the data -- `TokenSerializer` and `SavedViewSerializer` both read
    `context["request"].user`, and without it neither model can be imported at all. A Job knows who is
    running it, so there is a real answer to give them.
    """
    request = mock_wsgi_request(user=user, SERVER_NAME="import_objects")
    return {"request": request}


def parse_field_name_list(value):
    """
    Normalize a user-provided list of field names (a comma/space/semicolon-separated string, or a list)
    into a list, or None if no fields were provided.

    Used for both of the Jobs' field-name inputs: `ExportObjectList.export_fields` and `ImportObjects.match_fields`.
    """
    if not value:
        return None
    if isinstance(value, str):
        fields = [field for field in re.split(r"[\s,;]+", value.strip()) if field]
    else:
        fields = [field for field in value if field]
    return fields or None


def _row_key(match_field):
    """The key a record carries a match field's value under: every record spells its primary key `id`."""
    return "id" if match_field == "pk" else match_field


def _match_serializer(serializer_class):
    return serializer_class(context={"request": None, "depth": 0})


def _is_queryset_lookup(queryset, lookup):
    """Whether `queryset` can filter on `lookup`, which a model field or a queryset convenience can provide."""
    try:
        queryset.filter(**{lookup: None})
    except FieldError:
        return False
    return True


def _unusable_match_fields(match_fields, serializer):
    """The match fields that aren't a writable, single-valued field of `serializer` that its model can filter on.

    A match field has to be something a record gives a value for, and that value has to identify one thing:
    a read-only field (`display`) is dropped by the parser, and a to-many field (`tags`) holds a set. It also
    has to be something existing records can be looked up by, which a serializer-only field such as
    IPAddress's write-only `namespace` is not.
    """
    queryset = serializer.Meta.model.objects.none()
    unusable = []
    for field in match_fields:
        if _row_key(field) == "id":
            continue
        serializer_field = serializer.fields.get(field)
        if (
            serializer_field is None
            or serializer_field.read_only
            or serializer_field.source == "*"
            or isinstance(serializer_field, (serializers.ManyRelatedField, serializers.ListSerializer))
            or not _is_queryset_lookup(queryset, serializer_field.source.replace(".", "__"))
        ):
            unusable.append(field)
    return unusable


def natural_key_match_fields(model, serializer_class):
    """The model's default match fields: its natural key, as the serializer fields that its lookups start from.

    A Device's natural key lookups `name`, `tenant__name` and `location__name` (etc.) make the match fields
    `name`, `tenant` and `location`. A `pk` natural key is matched on `id`.

    A serializer whose model's natural key isn't spelled in its own fields declares its match fields instead,
    as `Meta.import_match_fields`: an IPAddress is keyed on `host`, which its serializer reads only as part
    of `address`.

    Returns:
        (list): The match fields, or None if the model has no identifiable natural key, or one that the
            serializer can't match on.
    """
    match_fields = getattr(serializer_class.Meta, "import_match_fields", None)
    if match_fields is not None:
        match_fields = list(match_fields)
    else:
        try:
            lookups = model.csv_natural_key_field_lookups()
        except AttributeError:
            # How `BaseModel.natural_key_field_lookups` reports a model with no identifiable natural key
            return None
        match_fields = []
        for lookup in lookups:
            head = _row_key(lookup.split("__", 1)[0])
            if head not in match_fields:
                match_fields.append(head)
    if _unusable_match_fields(match_fields, _match_serializer(serializer_class)):
        return None
    return match_fields


def resolve_match_fields(model, serializer_class, data, match_fields_param, directive_match_fields):
    """
    Resolve the effective match key and where it came from, by precedence.

    An explicit run parameter wins, then a directive carried in the file itself, then the model default
    (the `id` column if present in the data, otherwise the model's natural key). Matched records are
    updated in place; unmatched rows are created.

    Returns:
        tuple: `(effective_match_fields, source)` where `source` is one of `"run parameter"`,
        `"file directive"`, or `"default"`. For a model with no usable natural key (and no `id`
        column), returns `(None, None)` — the import is then create-only.
    """
    explicit_match_fields = parse_field_name_list(match_fields_param)
    if explicit_match_fields:
        return explicit_match_fields, "run parameter"
    if directive_match_fields:
        return directive_match_fields, "file directive"
    # Any record, not just the first: JSON and YAML records needn't all have the same keys
    if any("id" in row for row in data):
        return ["id"], "default"
    match_fields = natural_key_match_fields(model, serializer_class)
    if match_fields is None:
        return None, None
    return match_fields, "default"


def validate_match_fields(match_fields, serializer_class):
    """
    Confirm that each of the given match fields is a writable, single-valued field of the given serializer,
    which existing records can be looked up by.

    A related field is matched as a whole (`location`), by whatever reference the record gives for it, so a
    lookup into one (`location__name`) is not a match field.

    Raises:
        ValueError: identifying any unusable fields.
    """
    invalid = _unusable_match_fields(match_fields, _match_serializer(serializer_class))
    if invalid:
        raise ValueError(
            f"Invalid match field(s): {', '.join(invalid)}. "
            "Match fields must be writable fields of the serializer for this content-type that existing records "
            'can be looked up by, such as "name" or "location", not lookups such as "location__name", to-many '
            'fields such as "tags", or fields that exist only on the serializer.'
        )


def _require_match_fields(row_data, match_fields):
    """Raise ValueError naming any match field that the row gives no value for."""
    missing = [field for field in match_fields if _row_key(field) not in row_data]
    if missing:
        raise ValueError(f"Match field(s) not present in the import data: {', '.join(missing)}")


def build_match_filter(row_data, match_fields, serializer):
    """
    Build ORM filter parameters from a parsed row of import data, restricted to the given match fields.

    Each value is read by the serializer field it belongs to, so that matching resolves a related object
    exactly as saving the row will: `location: {"name": "Site A"}` becomes that Location, and
    `tenant: None` becomes `tenant=None`, which matches records with no tenant.

    Args:
        row_data (dict): One parsed record (as produced by the import parser).
        match_fields (list): Serializer field names to match on, as `validate_match_fields()` accepts.
        serializer (Serializer): An instance of the serializer the rows are imported with.

    Returns:
        (dict): Parameters suitable for `queryset.get(**params)`.

    Raises:
        ValueError: if any match field has no value in the row data, or a value that doesn't resolve.
    """
    _require_match_fields(row_data, match_fields)
    params = {}
    for field in match_fields:
        value = row_data[_row_key(field)]
        if _row_key(field) == "id":
            params["pk"] = value
            continue
        serializer_field = serializer.fields[field]
        if value is not None:
            try:
                value = serializer_field.to_internal_value(value)
            except serializers.ValidationError as exc:
                details = exc.detail if isinstance(exc.detail, list) else [exc.detail]
                raise ValueError(f"Match field {field}: {'; '.join(str(detail) for detail in details)}") from exc
        params[serializer_field.source.replace(".", "__")] = value
    return params


def match_key_for_row(row_data, match_fields):
    """Reduce a row's match-field values to a hashable key, for uniqueness checking within a file.

    Read from the row as written rather than resolved, since that would cost a query per relation per row.
    """
    _require_match_fields(row_data, match_fields)
    return json.dumps({field: row_data[_row_key(field)] for field in match_fields}, sort_keys=True, default=str)


def validate_match_uniqueness_within_file(data, match_fields):
    """
    Confirm that the given match fields uniquely identify every record within the import data.

    Rows missing values for the match fields are skipped here; they are reported individually
    during the import itself.

    Raises:
        ValueError: identifying the duplicated rows if the match fields are not unique within the file.
    """
    seen = {}
    duplicates = {}
    for row_number, row_data in enumerate(data, start=1):
        try:
            key = match_key_for_row(row_data, match_fields)
        except ValueError:
            continue
        if key in seen:
            duplicates.setdefault(seen[key], []).append(row_number)
        else:
            seen[key] = row_number
    if duplicates:
        details = "; ".join(
            f"row {first_row} is duplicated by row(s) {', '.join(str(r) for r in duplicate_rows)}"
            for first_row, duplicate_rows in duplicates.items()
        )
        raise ValueError(
            f"The match fields ({', '.join(match_fields)}) do not uniquely identify each row in the file: {details}"
        )


def find_existing_object(queryset, filter_params):
    """
    Look up the single existing object matching the given filter parameters.

    Returns:
        (BaseModel): The matched object, or None if nothing matched.

    Raises:
        MultipleObjectsReturned: if more than one existing record matches.
        ValueError: if the filter parameters aren't valid lookups for this model.
    """
    try:
        return queryset.get(**filter_params)
    except ObjectDoesNotExist:
        return None
    except (FieldError, ValidationError) as exc:
        # FieldError: a match field that isn't a database lookup for this model.
        # ValidationError: a match value of the wrong type, e.g. a non-UUID string matched against the pk.
        raise ValueError(str(exc)) from exc


def change_snapshot(serializer_class, instance):
    """The instance's writable fields, as an export would write them, for detecting what an import changed.

    Taken with the serializer that saves the row, so that it covers exactly the fields a row can set, spelled
    as the file spells them (`location__name`). Read-only fields such as `last_updated` are left out.
    """
    serializer = serializer_class(instance, context={"request": None}, for_import_export=True)
    fields = serializer.fields
    return {
        key: value
        for key, value in serializer.data.items()
        # A related field is exported as its natural-key lookups (`location__name`), named for the field
        if not getattr(fields.get(key.split("__", 1)[0]), "read_only", False)
    }


def write_only_field_names(serializer_class):
    """The names of the fields that `change_snapshot()` can't read, and so can't compare.

    Determined with every field shown, as the snapshot has them: a REST serializer also marks the M2M fields it
    omits by default, such as `VRF.import_targets`, as write-only.
    """
    fields = serializer_class(context={"request": None}, for_import_export=True).fields
    return {name for name, field in fields.items() if field.write_only}


def write_only_changes(serializer, match_fields, write_only_fields):
    """The write-only fields a validated row sets, other than its match fields, as `{field: new_value}`.

    Such a field (`User.password`) can't be compared, so each one set is assumed to be a change, since
    otherwise a row changing only that field would be rolled back as unchanged. A match field is excluded, as
    it equals the matched object's own value.

    Args:
        serializer (Serializer): The row's serializer, after a successful `is_valid()`.
        match_fields (list): The import's match fields, if any.
        write_only_fields (set): As returned by `write_only_field_names()`.
    """
    return {
        name: serializer.validated_data[serializer.fields[name].source]
        for name in write_only_fields
        if name in serializer.fields
        and serializer.fields[name].source in serializer.validated_data
        and name not in (match_fields or ())
    }


def format_change_diff(before, changed, sensitive_fields=(), write_only_fields=()):
    """Render a `shallow_compare_dict()` result as `` `field`: `old` → `new`, ... `` for the Job log.

    Fields and values are set as code, as the log is rendered as Markdown. Old values come from `before`. A
    sensitive field's values are shown as `(redacted)`, and a write-only field's unreadable old value as
    `(unknown)`.
    """

    def display(field, value):
        # A relation's natural-key lookup reads CSV_NO_OBJECT, whatever the import format, when it has no object
        if value is None or value == "" or ("__" in field and value == CSV_NO_OBJECT):
            return "∅"
        if isinstance(value, (list, dict)):
            value = json.dumps(value, default=str, ensure_ascii=False)
        return f"`{value}`"

    def describe(field, new):
        if field in sensitive_fields:
            return f"`{field}`: (redacted) → (redacted)"
        old = "(unknown)" if field in write_only_fields else display(field, before.get(field))
        return f"`{field}`: {old} → {display(field, new)}"

    return ", ".join(describe(field, new) for field, new in changed.items())


def detect_import_format(filename=None, text=None):
    """Detect the import format ("csv"/"json"/"yaml") from a filename extension, then the content, else CSV.

    Shared by the ImportObjects job and the `import_objects` management command so extension/content
    sniffing stays consistent between them.
    """
    lowered = (str(filename) if filename else "").lower()
    if lowered.endswith(".json"):
        return "json"
    if lowered.endswith((".yaml", ".yml")):
        return "yaml"
    if lowered.endswith(".csv"):
        return "csv"

    for line in (text or "").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            # A blank line, a YAML comment, or a CSV file's leading Nautobot directive row. None of the
            # three identifies a format, so the question is settled by the first line of real content --
            # which for a directive-carrying CSV is its header row.
            continue
        if line.startswith(("{", "[")):
            return "json"
        if line.startswith(("---", "%YAML", "- ")) or _YAML_MAPPING_RE.match(line):
            return "yaml"
        break
    return "csv"


def peek_import_model(text, import_format):
    """The `model` an import file declares for itself, or None if it declares none.

    Read without a serializer, deliberately: choosing a serializer is what knowing the model is *for*, so
    the parsers cannot answer this -- they are handed a serializer before they read a byte. The Job
    therefore still requires its `content_type`, and cross-checks the file's declaration against it; this
    is for callers that want the file to supply the answer, such as the `import_objects` command.

    Args:
        text (str): The decoded file contents.
        import_format (str): "csv", "json" or "yaml", as `detect_import_format()` returns.

    Returns:
        (str): The declared `app_label.model`, or None.
    """
    from nautobot.core.api.import_export import IMPORT_DOCUMENT_MODEL_KEY
    from nautobot.core.api.parsers import NautobotCSVParser

    if import_format == "csv":
        for line in text.splitlines():
            if not line.strip():
                continue
            if not line.lstrip().startswith("#"):
                # The header row: any directive would have preceded it
                return None
            cell = next(csv.reader([line]), [""])[0]
            model = NautobotCSVParser.parse_directive_cell(cell).get(IMPORT_DOCUMENT_MODEL_KEY)
            if model:
                return model
        return None

    payload = json.loads(text) if import_format == "json" else yaml.safe_load(text)
    model = payload.get(IMPORT_DOCUMENT_MODEL_KEY) if isinstance(payload, dict) else None
    if model is not None and not isinstance(model, str):
        # Reported rather than treated as absent, which would claim the data declares no model when it
        # declares an unusable one
        raise ValueError(f'"{IMPORT_DOCUMENT_MODEL_KEY}" must be a string, not {type(model).__name__}')
    return model
