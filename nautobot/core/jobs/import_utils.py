"""Helpers shared by the `ExportObjectList` and `ImportObjects` system Jobs and the commands that run them."""

import csv
import json
import re

import yaml

# A YAML block-mapping key at the start of a line: `records:`, `model: dcim.device`.
_YAML_MAPPING_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_.-]*\s*:(\s|$)")


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
