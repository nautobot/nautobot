"""Object Lock enforcement core: exception, bypass, gate cache, and signal gate."""

import contextlib
from contextlib import contextmanager
import contextvars
import logging
import random

from django.core.cache import cache
from django.core.exceptions import FieldDoesNotExist, PermissionDenied
from django.db.models import ProtectedError
from prometheus_client import Counter, Gauge
import redis.exceptions

logger = logging.getLogger(__name__)

GATE_MODE_DELETE = "delete"
GATE_MODE_UPDATE = "update"

# Cache keys
_GATE_CACHE_KEY = "nautobot.extras.object_lock.gate"
_GATE_GENERATION_CACHE_KEY = "nautobot.extras.object_lock.gate_token"
_GATE_REBUILD_LOCK_KEY = "nautobot.extras.object_lock.gate_rebuild"

# Jittered TTL bounds (seconds) so routine expiry is not synchronized across workers.
_GATE_TTL_MIN = 50
_GATE_TTL_MAX = 70

object_lock_gate_rebuild_counter = Counter(
    name="nautobot_object_lock_gate_rebuilds_total",
    documentation="Number of times the Object Lock content-type gate was rebuilt from the database.",
)
object_lock_gate_unreadable_counter = Counter(
    name="nautobot_object_lock_gate_unreadable_total",
    documentation="Number of times the Object Lock gate was unreadable and rebuilt from an error (near-lapse alarm).",
)
object_lock_blocked_counter = Counter(
    name="nautobot_object_lock_blocked_total",
    documentation="Number of writes blocked by an Object Lock.",
    labelnames=("mode",),
)
object_lock_bypass_counter = Counter(
    name="nautobot_object_lock_bypass_total",
    documentation="Number of Object Lock bypass invocations.",
)
object_lock_sweep_last_success_gauge = Gauge(
    name="nautobot_object_lock_sweep_last_success_timestamp_seconds",
    documentation=(
        "Unix timestamp of the last completed Object Lock sweep. Set even if some content types failed: "
        "alert on staleness for liveness, and on the failure counter below for per-run errors."
    ),
)
object_lock_sweep_failed_content_types_counter = Counter(
    name="nautobot_object_lock_sweep_failed_content_types_total",
    documentation="Number of content types that failed during an Object Lock sweep (alert on a rising rate).",
)
object_lock_bypass_audit_failures_counter = Counter(
    name="nautobot_object_lock_bypass_audit_failures_total",
    documentation=(
        "Number of Object Lock bypass-audit writes that failed. A non-zero value means a bypass was "
        "permitted without a durable audit row — alert on any increase for compliance."
    ),
)


class _AllFieldsFrozen:
    """Sentinel meaning 'every field is frozen' (a whole-object update lock is active)."""

    def __repr__(self):
        return "ALL_FIELDS_FROZEN"

    def __contains__(self, item):
        # Any field name is considered frozen.
        return True


ALL_FIELDS_FROZEN = _AllFieldsFrozen()


def get_frozen_fields_for_object(content_type_id, object_id):
    """Return the effective frozen-field set for an object across all active update-locked claims.

    Args:
        content_type_id (int): ContentType id of the target.
        object_id (uuid.UUID | str): Primary key of the target.

    Returns:
        set | _AllFieldsFrozen: The union of `locked_fields` across active update claims. Returns
        `ALL_FIELDS_FROZEN` if any active update claim is whole-object (empty/None locked_fields).
        Returns an empty set if there are no active update claims.
    """
    from nautobot.extras.models import ObjectLock  # local import to avoid app-loading circulars

    claims = ObjectLock.objects.active().filter(
        content_type_id=content_type_id,
        object_id=object_id,
        prevent_update=True,
    )

    frozen = set()
    for locked_fields in claims.values_list("locked_fields", flat=True):
        if not locked_fields:
            # A whole-object update claim freezes everything; short-circuit.
            return ALL_FIELDS_FROZEN
        frozen.update(locked_fields)
    return frozen


# ContextVar — False by default; set True only inside bypass_object_lock().
_bypass_active: contextvars.ContextVar[bool] = contextvars.ContextVar("object_lock_bypass_active", default=False)


class ObjectLockedError(ProtectedError):
    """
    Raised when a delete or update is blocked by an active Object Lock.

    Subclasses Django's `ProtectedError` so that existing delete views render it through
    their existing "cannot delete" handling. Unlike a foreign-key `PROTECT` error, this
    indicates an explicit Object Lock claim.
    """

    def __init__(self, msg, protected_objects=None, offending_fields=None):
        # The frozen field name(s) whose change triggered a field-level block (empty for whole-object
        # or delete locks). Surfaced ONLY to view_objectlock holders in the 409 body.
        self.offending_fields = list(offending_fields or [])
        # ProtectedError.__init__ sets args=(msg, objects), which would make str(self) render as a
        # "('msg', [...])" tuple. Initialize the parent, then restore args to just the message.
        super().__init__(msg, protected_objects or [])
        self.args = (msg,)


def _jittered_ttl():
    return random.randint(_GATE_TTL_MIN, _GATE_TTL_MAX)  # noqa: S311 (not security-sensitive)


def _build_gate_from_db():
    """Rebuild the per-mode locked-content-type sets directly from the database."""

    from nautobot.extras.models.object_locks import ObjectLock

    active = ObjectLock.objects.active()
    delete_cts = frozenset(active.filter(prevent_delete=True).values_list("content_type_id", flat=True).distinct())
    update_cts = frozenset(active.filter(prevent_update=True).values_list("content_type_id", flat=True).distinct())
    return {GATE_MODE_DELETE: delete_cts, GATE_MODE_UPDATE: update_cts}


def _current_token():
    from nautobot.extras.models.object_locks import ObjectLockGeneration

    return ObjectLockGeneration.current()


_GATE_SNAPSHOT_ATTR = "_object_lock_gate"


def _compute_gate():
    """Resolve the gate from the token-keyed cache, rebuilding from the DB on a miss or stale token.

    Returns `{GATE_MODE_DELETE: frozenset(...), GATE_MODE_UPDATE: frozenset(...)}`.
    """
    db_token = None
    try:
        cached = cache.get(_GATE_CACHE_KEY)
        cached_token = cache.get(_GATE_GENERATION_CACHE_KEY)
        db_token = _current_token()
        if cached is not None and cached_token == db_token:
            return cached
    except (redis.exceptions.ConnectionError, redis.exceptions.TimeoutError):
        logger.warning("Object Lock gate cache unreadable; rebuilding from database (fail-closed).")
        object_lock_gate_unreadable_counter.inc()
        # Fall through to a DB rebuild without touching the cache further.
        return _build_gate_from_db()

    # Cache miss or stale: rebuild, single-flighted to avoid a stampede.
    if db_token is None:
        db_token = _current_token()
    try:
        with cache.lock(_GATE_REBUILD_LOCK_KEY, blocking_timeout=5, timeout=30):
            # Re-check after acquiring the lock — another worker may have rebuilt it.
            cached = cache.get(_GATE_CACHE_KEY)
            cached_token = cache.get(_GATE_GENERATION_CACHE_KEY)
            if cached is not None and cached_token == db_token:
                return cached
            gate = _build_gate_from_db()
            object_lock_gate_rebuild_counter.inc()
            cache.set(_GATE_CACHE_KEY, gate, timeout=_jittered_ttl())
            cache.set(_GATE_GENERATION_CACHE_KEY, db_token, timeout=_jittered_ttl())
            return gate
    except (redis.exceptions.ConnectionError, redis.exceptions.TimeoutError, redis.exceptions.LockError):
        # LockError = could not acquire the rebuild lock within blocking_timeout; fall back to an
        # uncached DB build rather than 500 the request.
        logger.warning("Object Lock gate rebuild could not use cache; rebuilding from database directly.")
        object_lock_gate_unreadable_counter.inc()
        return _build_gate_from_db()


def get_gate():
    """Return `{GATE_MODE_DELETE: frozenset(ct_ids), GATE_MODE_UPDATE: frozenset(ct_ids)}`.

    With an active change context, the gate is computed once and cached on the context object, so
    later calls within the same request/job return the snapshot without further token/cache/DB access.
    Without a change context (out-of-band ORM, nbshell, management commands) it is computed fresh
    on every call.
    """
    from nautobot.extras.signals import change_context_state

    ctx = change_context_state.get()
    if ctx is not None:
        gate = getattr(ctx, _GATE_SNAPSHOT_ATTR, None)
        if gate is None:
            gate = _compute_gate()
            setattr(ctx, _GATE_SNAPSHOT_ATTR, gate)
        return gate

    # No change context: compute fresh each call (out-of-band path).
    return _compute_gate()


def invalidate_gate_cache():
    """Drop the cached gate so the next read rebuilds. Safe if Redis is unavailable."""
    with contextlib.suppress(redis.exceptions.ConnectionError, redis.exceptions.TimeoutError):
        cache.delete(_GATE_CACHE_KEY)
        cache.delete(_GATE_GENERATION_CACHE_KEY)


def clear_gate_snapshot():
    """Drop the per-request gate snapshot so the next get_gate() recomputes within the same context.

    Without this, a lock created mid-request would be missed by later writes in that same change
    context, which would otherwise reuse the snapshot taken before the lock existed.
    """
    from nautobot.extras.signals import change_context_state

    ctx = change_context_state.get()
    if ctx is not None and hasattr(ctx, _GATE_SNAPSHOT_ATTR):
        delattr(ctx, _GATE_SNAPSHOT_ATTR)


def _active_claims(content_type_id, object_id, mode):
    """Live indexed query for active claims on (content_type, object_id) for the given mode."""

    from nautobot.extras.models.object_locks import ObjectLock

    qs = ObjectLock.objects.active().filter(content_type_id=content_type_id, object_id=object_id)
    if mode == GATE_MODE_DELETE:
        qs = qs.filter(prevent_delete=True)
    else:
        qs = qs.filter(prevent_update=True)
    return qs


def build_locked_message(claims, mode):
    """Build the actionable, customized user-facing message for a blocked operation.

    Args:
        claims: Iterable of ObjectLock instances blocking the operation.
        mode: GATE_MODE_DELETE or GATE_MODE_UPDATE.

    Returns:
        A human-readable string explaining why the operation was blocked and what to do.
    """
    verb = "deleted" if mode == GATE_MODE_DELETE else "modified"
    sources = ", ".join(sorted({c.source_key for c in claims})) or "an unknown source"
    # Lead with the operator-meaningful "why" (reason, then source_detail), keeping the technical
    # source_key as a secondary identifier so a UUID auto-key isn't all the user sees.
    why = ", ".join(sorted({c.reason for c in claims if c.reason})) or ", ".join(
        sorted({c.source_detail for c in claims if c.source_detail})
    )
    identity = f"reason: {why}; source(s): {sources}" if why else f"source(s): {sources}"
    return (
        f"This object cannot be {verb} because it is held by an Object Lock "
        f"(mode: {mode}; {identity}). "
        f"Release the lock or contact an administrator to release it."
    )


def is_bypass_active():
    """Return True if an Object Lock bypass is currently active in this context."""
    return _bypass_active.get()


@contextmanager
def bypass_object_lock():
    """Allow authorized code to modify a locked object without releasing the lock.

    Re-checks `extras.bypass_objectlock` against the active change-context user on EVERY entry
    (never a cached decision). The flag is reset in try/finally so it cannot leak. Entry logs an INFO
    line and increments the bypass counter; the durable `ObjectLockBypassAudit` row is written
    downstream by `_write_bypass_audit()` once per actual write to a locked object while this bypass is
    active (see `enforce_object_lock` / `enforce_m2m_change`), not on context entry — a bypass that
    touches no locked objects writes no audit rows.

    Raises:
        PermissionDenied: If the active change-context user lacks `extras.bypass_objectlock`,
            or if no change-context user can be determined.
    """
    from nautobot.extras.signals import change_context_state

    change_context = change_context_state.get()
    user = change_context.get_user() if change_context is not None else None
    if user is None or not user.has_perm("extras.bypass_objectlock"):
        raise PermissionDenied("You do not have permission to bypass Object Locks (extras.bypass_objectlock).")

    change_id = getattr(change_context, "change_id", None)
    logger.info(
        "Object Lock bypass entered by user=%s change_id=%s",
        getattr(user, "username", user),
        change_id,
        extra={"user_id": str(getattr(user, "pk", "")), "change_id": str(change_id)},
    )
    object_lock_bypass_counter.inc()

    token = _bypass_active.set(True)
    try:
        yield
    finally:
        _bypass_active.reset(token)


def enforce_object_lock(sender, instance, mode):
    """Gate decision for a save/delete of `instance` under `mode` (GATE_MODE_DELETE/UPDATE).

    Assumes enforcement is enabled and a change context exists (the receiver checks those first).
    Raises ObjectLockedError if a live claim blocks the operation; otherwise returns None.
    When a bypass is active the write is permitted and a durable `ObjectLockBypassAudit` row
    is written so every override is permanently recorded.

    Args:
        sender: The model class of the object being saved or deleted.
        instance: The model instance being saved or deleted.
        mode: GATE_MODE_DELETE or GATE_MODE_UPDATE.

    Raises:
        ObjectLockedError: When an active lock claim blocks the operation and no bypass is active.
    """
    from django.contrib.contenttypes.models import ContentType

    content_type_id = ContentType.objects.get_for_model(sender).id
    gate = get_gate()
    if content_type_id not in gate[mode]:
        return  # common path: one in-memory set test, no query
    claims = list(_active_claims(content_type_id, instance.pk, mode))
    if not claims:
        return
    if is_bypass_active():
        _write_bypass_audit(claims, content_type_id, instance)
        return
    # Field-level update locks: block only when a FROZEN field actually changed.
    # A whole-object claim (ALL_FIELDS_FROZEN) and any delete lock still block unconditionally.
    offending_fields = []
    if mode == GATE_MODE_UPDATE:
        frozen = get_frozen_fields_for_object(content_type_id, instance.pk)
        if frozen is not ALL_FIELDS_FROZEN:
            changed = get_changed_fields(instance, frozen)
            if not changed:
                return  # only unfrozen fields changed -> permitted
            offending_fields = sorted(changed)
    object_lock_blocked_counter.labels(mode=mode).inc()
    raise ObjectLockedError(build_locked_message(claims, mode), [instance], offending_fields=offending_fields)


def enforce_m2m_change(instance, field_name, action):
    """Raise ObjectLockedError if a frozen M2M field of an update-locked object is being changed.

    M2M edits (`.add()`/`.remove()`/`.set()`/`.clear()`) never fire `pre_save`, so this
    is the enforcement entry point for the `m2m_changed` receiver. It mirrors the gate -> frozen
    -> claims -> bypass-audit -> raise flow of `enforce_object_lock`, but blocks when `field_name`
    is frozen rather than diffing concrete columns.

    Args:
        instance (BaseModel): The forward-side object whose M2M relation is mutating.
        field_name (str): The M2M field name on `instance` (e.g. "tags").
        action (str): The m2m_changed action; only "pre_add"/"pre_remove"/"pre_clear" enforce.

    Raises:
        ObjectLockedError: When a frozen M2M field is being changed and no bypass is active.
    """
    from django.contrib.contenttypes.models import ContentType

    if action not in ("pre_add", "pre_remove", "pre_clear"):
        return
    if not getattr(instance, "present_in_database", False):
        return
    content_type_id = ContentType.objects.get_for_model(instance).id
    if content_type_id not in get_gate()[GATE_MODE_UPDATE]:
        return  # gate miss
    frozen = get_frozen_fields_for_object(content_type_id, instance.pk)
    if frozen is not ALL_FIELDS_FROZEN and field_name not in frozen:
        return  # this M2M field isn't frozen
    claims = list(_active_claims(content_type_id, instance.pk, GATE_MODE_UPDATE))
    if not claims:
        return
    if is_bypass_active():
        _write_bypass_audit(claims, content_type_id, instance)
        return
    object_lock_blocked_counter.labels(mode=GATE_MODE_UPDATE).inc()
    raise ObjectLockedError(build_locked_message(claims, GATE_MODE_UPDATE), [instance], offending_fields=[field_name])


def _write_bypass_audit(claims, content_type_id, instance):
    """Persist a durable `ObjectLockBypassAudit` row for an active bypass override.

    Called from `enforce_object_lock` and `enforce_m2m_change` when a bypass is active and live claims
    exist. Records the union of frozen fields across all suspended claims and whether any claim was
    created by a user other than the bypassing user. Errors are logged but never re-raised so a logging
    failure cannot silently block a write that was intentionally authorised.

    Args:
        claims: List of ObjectLock instances being overridden.
        content_type_id: Integer PK of the ContentType for the target object.
        instance: The model instance being saved, deleted, or whose M2M relation is mutating under bypass.
    """
    from nautobot.extras.models.object_locks import ObjectLockBypassAudit
    from nautobot.extras.signals import change_context_state

    change_context = change_context_state.get()
    user = change_context.get_user() if change_context is not None else None
    change_id = getattr(change_context, "change_id", None)
    suspended_source_keys = [c.source_key for c in claims]

    # Compute the union of all frozen fields across suspended claims.  A whole-object
    # claim (empty/None locked_fields) is represented by the sentinel "*".
    frozen_fields: set[str] = set()
    for c in claims:
        if c.locked_fields:
            frozen_fields.update(c.locked_fields)
        else:
            frozen_fields.add("*")
    suspended_fields = sorted(frozen_fields)

    # Flag when at least one suspended claim was created by someone other than the
    # bypassing user (indicates a cross-source override worthy of attention).
    user_pk = getattr(user, "pk", None)
    suspended_other_source = any(c.created_by_id != user_pk for c in claims)

    try:
        ObjectLockBypassAudit.objects.create(
            user=user,
            content_type_id=content_type_id,
            object_id=instance.pk,
            change_id=change_id,
            suspended_source_keys=suspended_source_keys,
            suspended_fields=suspended_fields,
            suspended_other_source=suspended_other_source,
        )
        logger.info(
            "Object Lock bypass audit written: user=%s object=%s(%s) overrides=%s fields=%s other_source=%s change_id=%s",
            getattr(user, "username", user),
            type(instance).__name__,
            instance.pk,
            suspended_source_keys,
            suspended_fields,
            suspended_other_source,
            change_id,
        )
    except Exception:
        object_lock_bypass_audit_failures_counter.inc()
        logger.exception(
            "Failed to write ObjectLockBypassAudit for object=%s(%s); bypass was still permitted.",
            type(instance).__name__,
            instance.pk,
        )


def _prior_data_from_snapshot(instance):
    """Return the pre-save serialized snapshot dict for `instance` if the change context cached one.

    Returns:
        dict | None: Serialized field data keyed by field name, or None if no snapshot is cached.
    """
    from nautobot.extras.signals import change_context_state  # local import to avoid circular import

    change_context = change_context_state.get()
    if change_context is None:
        return None
    pre_object_data = getattr(change_context, "pre_object_data", None)
    if not pre_object_data:
        return None
    return pre_object_data.get(str(instance.pk))


def _custom_field_keys(candidate_fields, instance):
    """Classify candidate_fields into (concrete_field_names, custom_field_keys, unknown_names).

    Custom-field keys are identified authoritatively from the model's `CustomField` set, NOT from
    the instance's `_custom_field_data` dict (which is empty until a value is set). A name that is a
    valid but non-concrete relation (m2m / reverse) is omitted from all three sets — m2m freezing is
    enforced by the `m2m_changed` receiver and reverse relations are not assigned on a `save()`.
    A name that resolves to no field and is not a custom-field key is **drift** (the field was renamed
    or removed after the lock was created); such names are returned as `unknown_names` so the caller
    can fail closed rather than silently freeze nothing.

    Args:
        candidate_fields (Iterable[str]): Field names to classify.
        instance (BaseModel): The model instance being saved.

    Returns:
        tuple[set, set, set]: (concrete_field_names, custom_field_keys, unknown_names)
    """
    model = type(instance)
    cf_key_names = set()
    if hasattr(model, "_custom_field_data"):
        from nautobot.extras.models import CustomField

        cf_key_names = set(CustomField.objects.get_for_model(model).values_list("key", flat=True))

    cf_keys = set()
    concrete = set()
    unknown = set()
    for name in candidate_fields:
        if name in cf_key_names:
            cf_keys.add(name)
            continue
        try:
            field = model._meta.get_field(name)
        except FieldDoesNotExist:
            unknown.add(name)  # drifted/removed frozen name -> caller fails closed
            continue
        # Only diff concrete, non-m2m columns here; m2m/reverse relations are handled elsewhere.
        if getattr(field, "concrete", False) and not field.many_to_many:
            concrete.add(name)
    return concrete, cf_keys, unknown


def _attr_value(instance, name):
    """Return the raw stored attribute value for a concrete field (FK -> the `_id` column value).

    Args:
        instance (BaseModel): The model instance.
        name (str): The field name.

    Returns:
        The raw attribute value (e.g. the integer/UUID FK column value for relation fields).
    """
    field = instance._meta.get_field(name)
    if field.is_relation and field.many_to_one:
        return getattr(instance, field.attname)  # e.g. "manufacturer_id"
    return getattr(instance, field.attname, getattr(instance, name, None))


def _serialize_field_value(instance, name):
    """Serialize one field of `instance` the same way snapshots store it (best-effort, string-comparable).

    Args:
        instance (BaseModel): The model instance.
        name (str): The field name.

    Returns:
        A JSON-stable value suitable for comparison against snapshot data.
    """
    import json

    from django.core.serializers.json import DjangoJSONEncoder

    value = _attr_value(instance, name)
    if value is None:
        return None
    try:
        return json.loads(json.dumps(value, cls=DjangoJSONEncoder))
    except TypeError:
        return str(value)


def get_changed_fields(instance, candidate_fields):
    """Return the subset of `candidate_fields` whose value changed on `instance`.

    Prior values come from the change-context pre-save snapshot when present; otherwise from a
    single DB read of the saved row. Fail-closed: if a prior value cannot be determined (no
    snapshot and the row is not yet in the database), the field is reported as changed.

    Args:
        instance (BaseModel): The object being saved (carries new in-memory values).
        candidate_fields (Iterable[str]): Field names (concrete or custom-field keys) to check.

    Returns:
        set: Names from `candidate_fields` that changed.
    """
    candidate_fields = set(candidate_fields)
    if not candidate_fields:
        return set()

    concrete_fields, cf_keys, unknown_fields = _custom_field_keys(candidate_fields, instance)
    # Drifted/removed frozen names (no longer a real field or custom-field key) fail closed: a frozen
    # name we can no longer evaluate is reported as changed so the drift surfaces.
    changed = set(unknown_fields)
    snapshot = _prior_data_from_snapshot(instance)

    # ---- Custom-field keys: compare against the snapshot or the DB row. ----
    if cf_keys:
        prior_cf = None
        if snapshot is not None:
            prior_cf = snapshot.get("custom_fields") or snapshot.get("_custom_field_data") or {}
        elif instance.present_in_database:
            prior_cf = (
                type(instance).objects.filter(pk=instance.pk).values_list("_custom_field_data", flat=True).first()
            ) or {}
        new_cf = getattr(instance, "_custom_field_data", {}) or {}
        for key in cf_keys:
            if prior_cf is None:
                changed.add(key)  # fail-closed
            elif prior_cf.get(key) != new_cf.get(key):
                changed.add(key)

    # ---- Concrete fields. ----
    if concrete_fields:
        if snapshot is not None:
            for name in concrete_fields:
                if name not in snapshot:
                    changed.add(name)  # fail-closed: snapshot doesn't cover this field
                elif snapshot.get(name) != _serialize_field_value(instance, name):
                    changed.add(name)
        elif instance.present_in_database:
            prior = type(instance).objects.filter(pk=instance.pk).values(*concrete_fields).first()
            if prior is None:
                changed |= concrete_fields  # fail-closed
            else:
                for name in concrete_fields:
                    if prior.get(name) != _attr_value(instance, name):
                        changed.add(name)
        else:
            changed |= concrete_fields  # fail-closed: not in DB and no snapshot

    return changed


def find_stale_locked_fields():
    """Return locks whose stored `locked_fields` reference names no longer valid on the target model.

    A field-scoped lock can drift if a later migration renames or removes a field; the
    stored name then freezes nothing real. This auditor surfaces such locks for operator cleanup (e.g.
    from a management command). Enforcement already fails closed on drift — see `get_changed_fields`.

    Returns:
        list[dict]: One entry per affected lock: `{"lock_id", "content_type_id", "stale_fields"}`.
    """
    from nautobot.extras.models import CustomField, ObjectLock

    results = []
    valid_by_ct = {}
    qs = ObjectLock.objects.exclude(locked_fields__isnull=True).exclude(locked_fields=[])
    for lock in qs.iterator():
        model = lock.content_type.model_class()
        if model is None:
            # The target model no longer exists at all -> every name is stale.
            results.append(
                {"lock_id": lock.pk, "content_type_id": lock.content_type_id, "stale_fields": list(lock.locked_fields)}
            )
            continue
        if lock.content_type_id not in valid_by_ct:
            names = {f.name for f in model._meta.get_fields()}
            if hasattr(model, "_custom_field_data"):
                names |= set(CustomField.objects.get_for_model(model).values_list("key", flat=True))
            valid_by_ct[lock.content_type_id] = names
        stale = [name for name in lock.locked_fields if name not in valid_by_ct[lock.content_type_id]]
        if stale:
            results.append({"lock_id": lock.pk, "content_type_id": lock.content_type_id, "stale_fields": stale})
    return results
