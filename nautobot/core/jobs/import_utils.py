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
