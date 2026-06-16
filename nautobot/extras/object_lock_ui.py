"""Shared helpers for surfacing Object Lock state in the Web UI and GraphQL."""

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

from django import forms
from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.db.models import Q
from django.utils.html import format_html

from nautobot.core.forms import StaticSelect2
from nautobot.core.forms.constants import BOOLEAN_WITH_BLANK_CHOICES
from nautobot.extras.models import ObjectLock


@dataclass
class LockState:
    """Aggregated, presentation-ready lock state for a single object.

    Built once per page from a single bulk query; never triggers a per-object query.
    """

    is_locked: bool = False
    locked_for_delete: bool = False
    locked_for_update: bool = False
    active_lock_count: int = 0
    earliest_expiry: Optional[datetime] = None
    source_keys: list = field(default_factory=list)


def lock_state_for_objects(objects):
    """Map ``object.pk`` -> :class:`LockState` for every *locked* object in ``objects``.

    Performs **exactly one** database query regardless of how many objects are passed (content-type
    lookups are deduped per distinct model and served from Django's ContentType cache). Objects with no
    active lock are simply absent from the returned dict, so ``object.pk in result`` is the "is locked"
    test. Keys are ``uuid.UUID`` instances matching ``object.pk``, because ``ObjectLock.object_id`` is a
    ``UUIDField`` and ``values()`` yields native UUIDs.

    Args:
        objects (iterable): Model instances. They need not share a content type.

    Returns:
        dict: ``{object_pk: LockState}`` for locked objects only.
    """
    if not settings.OBJECT_LOCK_ENFORCED:
        return {}  # kill switch: the whole feature (enforcement + surfacing) is off
    objects = list(objects)
    if not objects:
        return {}

    # Group target PKs by content type so the single query can match (content_type, object_id) pairs.
    # Dedupe content-type lookups by class so get_for_model is called once per distinct model.
    ct_by_class = {}
    pks_by_ct = defaultdict(set)
    for obj in objects:
        ct_id = ct_by_class.get(obj.__class__)
        if ct_id is None:
            ct_id = ContentType.objects.get_for_model(obj).pk
            ct_by_class[obj.__class__] = ct_id
        pks_by_ct[ct_id].add(obj.pk)

    query = Q()
    for ct_id, pks in pks_by_ct.items():
        query |= Q(content_type_id=ct_id, object_id__in=pks)

    states = {}
    claims = (
        ObjectLock.objects.active()
        .filter(query)
        .values(
            "object_id",
            "prevent_delete",
            "prevent_update",
            "expires",
            "source_key",
        )
    )
    for claim in claims:
        pk = claim["object_id"]
        state = states.setdefault(pk, LockState())
        state.is_locked = True
        state.active_lock_count += 1
        state.locked_for_delete = state.locked_for_delete or claim["prevent_delete"]
        state.locked_for_update = state.locked_for_update or claim["prevent_update"]
        if claim["source_key"]:
            state.source_keys.append(claim["source_key"])
        expires = claim["expires"]
        if expires is not None and (state.earliest_expiry is None or expires < state.earliest_expiry):
            state.earliest_expiry = expires

    return states


# Material Design Icon name per lock mode.
LOCK_GLYPHS = {
    "delete": "mdi-lock",
    "update": "mdi-pencil-lock",
    "both": "mdi-lock-alert",
}

LOCK_PROTECTION_BLURB = "protected against accidental deletion/edits via the UI, API, and Jobs"


def _glyph_token(state):
    """Return the single glyph token best describing ``state``: "both", "delete", "update", or None."""
    if state.locked_for_delete and state.locked_for_update:
        return "both"
    if state.locked_for_delete:
        return "delete"
    if state.locked_for_update:
        return "update"
    return None


def summarize_modes(state):
    """Return a human label naming all active lock modes (e.g. "Delete-locked and update-locked")."""
    if state.locked_for_delete and state.locked_for_update:
        return "Delete-locked and update-locked"
    if state.locked_for_delete:
        return "Delete-locked"
    if state.locked_for_update:
        return "Update-locked"
    return ""


def render_lock_glyph(state, *, include_metadata=True):
    """Render a single lock glyph for ``state`` as safe HTML, or "" if unlocked.

    Meaning is carried by the glyph shape + ``title`` + ``aria-label`` — never by color alone.

    Args:
        state (LockState): The aggregated lock state.
        include_metadata (bool): When False (viewer lacks ``view_objectlock``), the tooltip is generic
            and omits counts / expiry / sources.
    """
    token = _glyph_token(state)
    if token is None:
        return ""
    label = summarize_modes(state)
    if include_metadata:
        bits = [label, f"{state.active_lock_count} active lock(s)"]
        if state.earliest_expiry is not None:
            bits.append(f"earliest expiry {state.earliest_expiry:%Y-%m-%d %H:%M} UTC")
        if state.source_keys:
            bits.append(f"sources: {', '.join(sorted(set(state.source_keys)))}")
        tooltip = "; ".join(bits)
    else:
        tooltip = f"{label}. Lock details are restricted to authorized users."
    # LOCK_GLYPHS[token] is a fixed constant; the tooltip is passed as a format_html arg so any
    # lock-sourced text (e.g. source_keys) is HTML-escaped.
    return format_html(
        '<i class="mdi {}" role="img" title="{}" aria-label="{}"></i> ',
        LOCK_GLYPHS[token],
        tooltip,
        tooltip,
    )


def user_can_view_lock_metadata(user):
    """Return True if ``user`` may see richer lock metadata (gated behind ``extras.view_objectlock``).

    Args:
        user: A Django user instance, or None / anonymous user.

    Returns:
        bool: True when the user holds the ``extras.view_objectlock`` permission (superusers included
            via ``has_perm``).
    """
    if user is None or not getattr(user, "is_authenticated", False):
        return False
    return user.has_perm("extras.view_objectlock")


class ObjectLockQuickFilterFormMixin(forms.Form):
    """Mixin adding a single "Locked" quick-filter to a list-view filter form.

    Backed by the ``is_locked`` filterset filter. Lock state is intentionally NOT a sortable column;
    this checkbox is the entire "find locked objects" affordance.
    """

    is_locked = forms.NullBooleanField(
        required=False,
        label="Locked",
        widget=StaticSelect2(choices=BOOLEAN_WITH_BLANK_CHOICES),
    )
