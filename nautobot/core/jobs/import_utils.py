"""Match-key resolution and record-matching helpers for the ImportObjects system job."""

import re


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
    head = (text or "").lstrip()[:200]
    if head.startswith(("{", "[")):
        return "json"
    if head.startswith(("---", "%YAML")) or "nautobot_import:" in head:
        return "yaml"
    return "csv"
