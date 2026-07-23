"""Helpers shared by the `ExportObjectList` and `ImportObjects` system Jobs and the commands that run them."""

import csv
import json
import re

from django.core.exceptions import FieldError, ObjectDoesNotExist, ValidationError
import yaml

from nautobot.core.api.utils import dict_to_filter_params
from nautobot.core.utils.requests import mock_wsgi_request

# A YAML block-mapping key at the start of a line: `records:`, `model: dcim.device`.
_YAML_MAPPING_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_.-]*\s*:(\s|$)")


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

    Used for both of the Jobs' field-name inputs: `ExportObjectList.export_fields` and, once matching is
    implemented, `ImportObjects.match_fields`.
    """
    if not value:
        return None
    if isinstance(value, str):
        fields = [field for field in re.split(r"[\s,;]+", value.strip()) if field]
    else:
        fields = [field for field in value if field]
    return fields or None


def default_match_fields(model, header_fields=None):
    """
    The default match fields for a model: the pk if an `id` column is present in the data,
    otherwise the model's natural key field lookups.
    """
    if header_fields and "id" in header_fields:
        return ["id"]
    return list(model.csv_natural_key_field_lookups())


def resolve_match_fields(model, data, match_fields_param, directive_match_fields):
    """
    Resolve the effective match key and where it came from, by precedence.

    An explicit run parameter wins, then a directive carried in the file itself, then the model default
    (the `id` column if present in the data, otherwise the model's natural key). Matched records are
    updated in place; unmatched rows are created.

    Returns:
        tuple: `(effective_match_fields, source)` where `source` is one of `"run parameter"`,
        `"file directive"`, or `"default"`. For a model with no identifiable natural key (and no `id`
        column), returns `(None, None)` — the import is then create-only.
    """
    explicit_match_fields = parse_field_name_list(match_fields_param)
    if explicit_match_fields:
        return explicit_match_fields, "run parameter"
    if directive_match_fields:
        return directive_match_fields, "file directive"
    header_fields = list(data[0].keys()) if data else []
    try:
        return default_match_fields(model, header_fields), "default"
    except AttributeError:
        return None, None


def validate_match_fields(match_fields, serializer_class):
    """
    Confirm that each of the given match fields corresponds to a field of the given serializer.

    Match fields may be bare serializer field names (`name`, `location`) or nested lookups into a related
    field (`location__name`); in the latter case only the head of the lookup is validated here, as the
    remainder is validated by the database when matching.

    Raises:
        ValueError: identifying any unrecognized fields.
    """
    serializer = serializer_class(context={"request": None, "depth": 0})
    invalid = []
    for field in match_fields:
        head = field.split("__", 1)[0]
        if head not in ("id", "pk") and head not in serializer.fields:
            invalid.append(field)
    if invalid:
        raise ValueError(
            f"Unknown match field(s): {', '.join(invalid)}. "
            "Match fields must be field names of the serializer for this content-type."
        )


def build_match_filter(row_data, match_fields):
    """
    Build ORM filter parameters from a parsed row of import data, restricted to the given match fields.

    Args:
        row_data (dict): One parsed record (as produced by the import parser), possibly containing nested
            dicts for related fields.
        match_fields (list): Field names to match on; a bare related field name (e.g. `location`) matches
            all of the row's lookups into that field (e.g. `location__name`, `location__parent__name`).

    Returns:
        (dict): Parameters suitable for `queryset.get(**params)`.

    Raises:
        ValueError: if any match field has no corresponding value in the row data.
    """
    flat_data = dict_to_filter_params(row_data)
    params = {}
    missing = []
    for field in match_fields:
        matched = {key: value for key, value in flat_data.items() if key == field or key.startswith(f"{field}__")}
        if not matched:
            missing.append(field)
        params.update(matched)
    if missing:
        raise ValueError(f"Match field(s) not present in the import data: {', '.join(missing)}")
    if "id" in params:
        params["pk"] = params.pop("id")
    return params


def match_key_for_row(row_data, match_fields):
    """Reduce a row's match-field values to a hashable key, for uniqueness checking within a file."""
    return json.dumps(build_match_filter(row_data, match_fields), sort_keys=True, default=str)


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
