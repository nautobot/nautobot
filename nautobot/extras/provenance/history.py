"""Replay an object's changelog one field at a time.

Every save of a change-logged object writes an ``ObjectChange`` row holding a full snapshot of the object
(``object_data_v2``, or the older flat ``object_data``). Nautobot shows these snapshots per change; this module
turns them into a per-field timeline by walking the changes oldest first and recording each point where one
key's value differs from the previous snapshot.
"""

from dataclasses import dataclass
from typing import Any

# A snapshot exists but holds no value for the requested path (for example an old ``object_data`` row that
# predates the key). Distinct from ``None``, which is a real stored value.
UNAVAILABLE = object()

ACTION_CREATE = "create"


@dataclass(frozen=True)
class HistoryEntry:  # pylint: disable=too-many-instance-attributes
    """One value a field held, and the change that set it."""

    value: Any
    time: Any
    user_name: str
    user_pk: Any
    action: str
    change_context: str
    change_context_detail: str
    change_pk: Any

    def to_dict(self) -> dict[str, Any]:
        """Return the JSON-serializable form used by the REST API."""
        return {
            "value": self.value,
            "time": self.time.isoformat() if hasattr(self.time, "isoformat") else self.time,
            "user_name": self.user_name,
            "user_id": str(self.user_pk) if self.user_pk is not None else None,
            "action": self.action,
            "change_context": self.change_context,
            "change_context_detail": self.change_context_detail,
            "change_id": str(self.change_pk),
        }


@dataclass
class FieldHistory:
    """The values one field has held, newest first."""

    entries: list[HistoryEntry]
    change_count: int
    truncated: bool
    updates: int | None = None  # set by field_history; counted over all entries, not only the limited slice

    @property
    def last_changed(self) -> HistoryEntry | None:
        """Return the most recent entry, or None when nothing is on record."""
        return self.entries[0] if self.entries else None

    @property
    def update_count(self) -> int:
        """Return how many recorded values were set after creation; 0 means the field was never edited."""
        if self.updates is not None:
            return self.updates
        return sum(1 for entry in self.entries if entry.action != ACTION_CREATE)

    def to_dict(self) -> dict[str, Any]:
        """Return the JSON-serializable form used by the REST API."""
        return {
            "change_count": self.change_count,
            "update_count": self.update_count,
            "truncated": self.truncated,
            "entries": [entry.to_dict() for entry in self.entries],
        }


def snapshot_value(change, path: str) -> Any:
    """Return the value at dotted ``path`` in the change's snapshot, or ``UNAVAILABLE``.

    ``object_data_v2`` is preferred; ``object_data`` is the fallback for rows written before v2 existed.
    """
    data = change.object_data_v2 or change.object_data or {}
    for part in path.split("."):
        if not isinstance(data, dict) or part not in data:
            return UNAVAILABLE
        data = data[part]
    return data


def _is_related(value: Any) -> bool:
    return isinstance(value, dict) and "id" in value


def values_equal(a: Any, b: Any) -> bool:
    """Compare two snapshot values.

    Related objects are compared by ``id`` so that renaming a Status does not register as a change on every
    object that uses it. Everything else is compared structurally.
    """
    if _is_related(a) and _is_related(b):
        return a["id"] == b["id"]
    if isinstance(a, list) and isinstance(b, list) and a and b and all(_is_related(x) for x in a + b):
        return sorted(x["id"] for x in a) == sorted(x["id"] for x in b)
    return a == b


def field_history(changes, path: str, limit: int = 10) -> FieldHistory:
    """Replay ``changes`` (oldest first) and return the history of the value at ``path``.

    An entry is recorded for the create, and for every later change whose snapshot holds a different value
    than the previous snapshot that had the key. Snapshots without the key are skipped. ``truncated`` is set
    when the oldest change on record is not a create, since the values before it are unknown.
    """
    entries: list[HistoryEntry] = []
    previous: Any = UNAVAILABLE
    truncated = False

    for index, change in enumerate(changes):
        if index == 0 and change.action != ACTION_CREATE:
            truncated = True
        value = snapshot_value(change, path)
        if value is UNAVAILABLE:
            continue
        if previous is UNAVAILABLE or change.action == ACTION_CREATE or not values_equal(value, previous):
            entries.append(
                HistoryEntry(
                    value=value,
                    time=change.time,
                    user_name=change.user_name,
                    user_pk=getattr(change, "user_id", None),
                    action=change.action,
                    change_context=change.change_context,
                    change_context_detail=change.change_context_detail,
                    change_pk=change.pk,
                )
            )
        previous = value

    entries.reverse()
    change_count = len(entries)
    updates = sum(1 for entry in entries if entry.action != ACTION_CREATE)
    if limit:
        entries = entries[:limit]
    return FieldHistory(entries=entries, change_count=change_count, truncated=truncated, updates=updates)
