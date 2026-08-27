"""Scope and conditions: deciding, per change event, whether a Webhook or Job Hook fires.

The pieces here know nothing about which model owns them. A Webhook and a Job Hook both carry a
`scope_filter` and a list of `conditions`, and both will be evaluated by one engine, which is what
keeps their behaviour identical instead of merely similar.

"""

from nautobot.extras.conditions.operators import (
    field_matches,
    FIELD_OPERATORS,
    KIND_BOOLEAN,
    KIND_DATE,
    KIND_LIST,
    KIND_NUMBER,
    KIND_TEXT,
    operators_for_kind,
)
from nautobot.extras.conditions.payload import (
    build_event_payload,
    event_value,
    field_value,
)

__all__ = (
    "FIELD_OPERATORS",
    "KIND_BOOLEAN",
    "KIND_DATE",
    "KIND_LIST",
    "KIND_NUMBER",
    "KIND_TEXT",
    "build_event_payload",
    "event_value",
    "field_matches",
    "field_value",
    "operators_for_kind",
)
