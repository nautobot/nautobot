"""Builds the frozen picture of a change that conditions are evaluated against.

The payload's shape is defined in one place, `_assemble_payload`, and uses the same variable names as
the webhook body-template context.
"""

from nautobot.extras.choices import ObjectChangeActionChoices


def field_value(container, path):
    """
    Look up a field by dotted path in a serialized object.

    A related object is serialized as a mapping and is addressed by sub-field: `status.name`,
    `primary_ip4.address`. A path that stops at a mapping returns the mapping itself. Only mappings
    are walked; a path into a list (`tags.name`) resolves to None.

    Args:
        container (dict): Usually the serialized object, but any mapping will do.
        path (str): A field name, optionally dotted.

    Returns:
        The value at that path, or None if any segment is missing or the path is empty.
    """
    if not path:
        return None
    current = container
    for segment in str(path).split("."):
        if not isinstance(current, dict) or segment not in current:
            return None
        current = current[segment]
    return current


def _assemble_payload(*, event, timestamp, model, username, request_id, data, snapshots):
    """The one place the payload's shape is defined. These keys are what condition expressions read."""
    return {
        "event": event,
        "timestamp": timestamp,
        "model": model,
        "username": username,
        "request_id": request_id,
        "data": data,
        "snapshots": snapshots,
    }


def build_event_payload(object_change, snapshots=None):
    """
    Assemble the payload for `object_change`.

    Args:
        object_change (ObjectChange): The change to describe.
        snapshots (dict): Optional precomputed `{"prechange": ..., "postchange": ..., "differences": ...}`.
            Computed here, with one query, when omitted.

    Returns:
        (dict): The frozen event payload conditions are evaluated against.
    """
    if snapshots is None:
        snapshots = object_change.get_snapshots()
    return _assemble_payload(
        event=dict(ObjectChangeActionChoices)[object_change.action].lower(),
        timestamp=str(object_change.time),
        model=object_change.changed_object_type.model,
        username=object_change.user_name,
        request_id=str(object_change.request_id),
        data=object_change.object_data_v2,
        snapshots=snapshots,
    )
