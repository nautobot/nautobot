"""Match-key resolution and record-matching helpers for the ImportObjects system job."""

import re

# A YAML block-mapping key at the start of a line: `records:`, `model: dcim.device`.
_YAML_MAPPING_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_.-]*\s*:(\s|$)")


def parse_match_fields(value):
    """
    Normalize a user-provided match-fields value (a comma/space/semicolon-separated string, or a list)
    into a list of field names, or None if no fields were provided.
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
