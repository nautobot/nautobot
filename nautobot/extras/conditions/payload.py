"""Builds the frozen picture of a change that conditions are evaluated against.

The payload's shape is defined in exactly one place (`_assemble_payload`), and every entry point is a
thin wrapper that only decides where the ingredients come from. That is deliberate: the shape is a
user-facing contract - condition expressions and preset sources read these names - and two assembly
sites would be two places for it to drift apart.

The payload deliberately uses the same variable names as the webhook body-template context, so an
expression that works in one works in the other.
"""

from nautobot.extras.choices import ObjectChangeActionChoices

# Keys checked, in order, when reducing a nested object to a single comparable value.
_VALUE_KEYS = ("value", "name", "display", "id")


def event_value(value):
    """
    Reduce a serialized field value to the scalar a condition should compare against.

    An object's serialization records a related object as a nested mapping (`{"id": ..., "name":
    "Active", ...}`) when the newer serializer is in play, and as a bare primary key when falling
    back to the older one. A user writing `status` equals `Active` should not have to know which
    they got, so both are reduced here to the same comparable value.

    Lists are normalized element by element; anything else is returned unchanged.
    """
    if isinstance(value, dict):
        for key in _VALUE_KEYS:
            if key in value:
                return value[key]
        return value
    if isinstance(value, (list, tuple)):
        return [event_value(item) for item in value]
    return value


def field_value(container, path):
    """
    Look up a field by name, following dots into nested values.

    `status` and `status.name` should both work: the first because a related object is reduced to a single
    comparable value by `event_value`, the second because people reasonably expect to reach inside it. A
    plain subscript cannot do the second (`data["status.name"]` looks for a key with a dot in its name),
    so the path is walked a segment at a time.

    Args:
        container (dict): Usually the serialized object, but any mapping will do.
        path (str): A field name, optionally dotted, e.g. `status` or `primary_ip4.address`.

    Returns:
        The value at that path reduced by `event_value`, or None if any segment is missing.
    """
    if not path:
        return None
    current = container
    for segment in str(path).split("."):
        if isinstance(current, dict):
            if segment not in current:
                return None
            current = current[segment]
        else:
            return None
    return event_value(current)


def _serialized_data(object_change):
    """Return the post-change serialization recorded on an ObjectChange, preferring the newer form."""
    data = object_change.object_data_v2
    if data is None:
        data = object_change.object_data
    return data


def _assemble_payload(*, event, timestamp, model, username, request_id, data, snapshots):
    """The one place the payload's shape is defined.

    Every key here is contract, not plumbing: stored condition expressions read these names, and they
    mirror the webhook body-template context. Adding, renaming or removing a key changes what every
    saved rule can see, so a change here is an API change and needs the documentation to move with it.

    Keyword-only on purpose: seven same-typed arguments in positional order is how `username` ends up
    holding a timestamp two refactors from now.
    """
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

    This is the only public builder. Callers that already hold computed snapshots must pass them in:
    the dispatch loop computes snapshots once per change and shares them with webhooks and event
    brokers, and deciding whether to fire must not pay that query a second time. Omitting `snapshots`
    is for callers that have nothing but the ObjectChange row, and costs one query here.

    Args:
        object_change (ObjectChange): The change to describe.
        snapshots (dict): Optional precomputed `{"prechange": ..., "postchange": ..., "differences": ...}`.

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
        data=_serialized_data(object_change),
        snapshots=snapshots,
    )
