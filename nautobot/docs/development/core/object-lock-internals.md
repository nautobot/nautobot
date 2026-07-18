# Object Lock Internals

This document explains how the Object Lock feature is built so that a developer new to it can navigate
the code, extend it to new models, and reason about its performance and security properties. For the
operator-facing description see the [Object Lock user guide](../../user-guide/platform-functionality/object-lock.md).

## What Object Lock is

An Object Lock is a claim, placed by some source, that an existing object must not be deleted and/or
modified. It is:

- **Reference-counted** — many independent claims (keyed by `source_key`) can lock the same object;
  releasing one leaves the others in force.
- **Attributable** — every claim records who/what created it (`source_context`, `source_detail`,
  `created_by`), derived server-side and never accepted from caller input. The `source_key` is a
  caller-supplied claim identifier (auto-generated when omitted) used for idempotency and reference counting.
- **Time-bounded** — a claim may carry an `expires` timestamp; expired claims stop enforcing and are
  swept away by a system Job.

Enforcement applies to writes that go through Django signals with an active change context — the UI,
the REST API, and Jobs. Out-of-band ORM access (the `nbshell`, migrations, `bulk_update()` /
`bulk_create()` / `QuerySet.update()`) is **deliberately not blocked**; it is the documented escape
hatch. A `QuerySet.delete()` differs from those: it fires a per-row `pre_delete`, so it **is** enforced
when run under a UI/REST/Job change context — but from `nbshell` or migrations (no change context) it
bypasses just like the other out-of-band paths.

## Data model

`nautobot/extras/models/object_locks.py` defines three models:

- **`ObjectLock`** — one claim. A `GenericForeignKey` (`content_type` + `object_id`) targets any
  UUID-PK `BaseModel`. `prevent_delete` / `prevent_update` are the mode flags; `locked_fields` (JSON)
  optionally narrows an update lock to specific fields. A unique constraint on
  `(content_type, object_id, source_key)` is what makes claims reference-counted. The
  `ObjectLockManager` exposes the programmatic API: `lock()`, `release()`, `lock_many()`,
  `release_many()`, and the `locked()` context manager, plus the `active()` queryset filter
  (`expires` null or in the future).
- **`ObjectLockBypassAudit`** — an immutable row written every time an authorized bypass lets an
  otherwise-blocked write through (see [Bypass](#bypass-and-audit)).
- **`ObjectLockGeneration`** — a single-row monotonic counter, bumped in the same transaction as any
  lock create/update/delete. It lets workers detect that their cached gate is stale without a
  timestamp comparison, and it survives a Redis flush.

Attribution is resolved by `_derive_attribution()` from the active change context, so callers cannot
spoof it.

## Enforcement architecture

Enforcement lives in `nautobot/extras/locking.py` and is wired by three **global** signal receivers in
`nautobot/extras/signals.py`:

```text
pre_save    -> _object_lock_enforce_update -> enforce_object_lock(..., UPDATE)
pre_delete  -> _object_lock_enforce_delete -> enforce_object_lock(..., DELETE)
m2m_changed -> _object_lock_enforce_m2m    -> enforce_m2m_change(...)   # m2m edits never fire pre_save
```

Because these fire on **every** model write, the no-lock path must be cheap. Each receiver short-circuits
in this order:

1. `settings.OBJECT_LOCK_ENFORCED` is `False` -> return (the kill switch, checked before any
   cache access).
2. No active change context -> return (out-of-band ORM is not enforced).
3. The instance's content type is not in the **gate** -> return.

### The gate

The gate is `{"delete": frozenset(content_type_ids), "update": frozenset(content_type_ids)}` — the set
of content types that currently hold at least one active lock of each mode. `get_gate()`:

- With an active change context, computes the gate once and caches it on the context object, so every
  subsequent write in the same request/Job reuses the snapshot with no further token/cache/DB access.
- Otherwise computes it fresh each call.

`_compute_gate()` reads the gate from Redis keyed by the `ObjectLockGeneration` token; on a miss or a
stale token it rebuilds from the database under a single-flight lock and re-caches. If Redis is
unreachable it rebuilds directly from the database (fail-closed). The `post_save` / `post_delete`
receiver on `ObjectLock` bumps the generation token and drops the cache so the next read rebuilds.

The result: when nothing of a model's type is locked, a write costs **one in-memory set membership
test** and zero queries. Only when the content type is gated does `enforce_object_lock` run the live
claim query.

**Snapshot freshness boundary.** The per-request/Job snapshot is computed once and refreshed only when
*that same context* creates or deletes a lock (via `clear_gate_snapshot()`). A lock placed by a
*different* worker after the snapshot is taken is not reflected until the current request/Job ends —
the deliberate cost of reading the generation token at most once per request. This fails safe in the
blocking direction (a snapshot may be *broader* than reality), but the *narrower* direction means a
long-running Job can still write to a type that was locked mid-run by another worker. Place locks
before launching a long job over the same type, or re-run the job to pick up locks placed during it.

### enforce_object_lock

Once the gate says the type is locked, `enforce_object_lock`:

1. Loads the live active claims for `(content_type, object_id, mode)`.
2. If none, returns (the gate can be momentarily broader than reality).
3. If a [bypass](#bypass-and-audit) is active, writes an audit row and permits the write.
4. For an update, applies [field-level](#field-level-locking) scoping.
5. Otherwise raises `ObjectLockedError`.

`ObjectLockedError` subclasses Django's `ProtectedError` so existing "cannot delete" handling renders
it, and it carries `offending_fields` for the REST 409 body.

## Field-level locking

A claim with a non-empty `locked_fields` freezes only those fields; an empty/null `locked_fields` is a
whole-object lock. The sentinel `ALL_FIELDS_FROZEN` represents "everything" so call sites don't special-case it.

`get_frozen_fields_for_object()` unions `locked_fields` across active **update** claims (field scoping
only applies to updates), returning `ALL_FIELDS_FROZEN` if any whole-object update claim exists.
`get_changed_fields()` then decides whether a frozen field actually changed, comparing against the
change-context snapshot when present, else a single DB read. It is **fail-closed**: if a prior value
cannot be proven (no snapshot, row not yet in the database) or a frozen name no longer resolves to a
real field (drift), the field is reported as changed and the write is blocked. `find_stale_locked_fields()`
audits for such drift.

In the Web UI, `LockedFieldsFormMixin` (mixed into a model's edit form — e.g. `ManufacturerForm`) resolves
the same frozen-field set from the bound instance and renders those fields disabled, matching the
server-side rule. It is the reference for extending the in-form experience to other models.

## Bypass and audit

`bypass_object_lock()` is a context manager for code that must legitimately write through a lock. It
re-checks `extras.bypass_objectlock` against the active change-context user on **every** entry (never a
cached decision), sets the bypass flag, and resets it in `finally` so it cannot leak. The audit row
itself is written by `enforce_object_lock` / `enforce_m2m_change` (via `_write_bypass_audit()`) on each
otherwise-blocked write the bypass lets through — not on context-manager entry.

## Surfaces

| Surface | Where | Notes |
| --- | --- | --- |
| Programmatic | `ObjectLockManager` (`models/object_locks.py`) | `lock()` / `release()` / `locked()` |
| REST API | `api/object_locks.py` | `ObjectLockableSerializerMixin` adds read-only `is_locked` / `locked_for_*` / `locked_fields`; `ObjectLockableModelViewSetMixin` adds POST `lock` / `release` actions; blocked writes return a gated 409 (`build_object_locked_response` in `api/object_locks.py`, invoked from a thin hook in `core/api/views.py`) |
| Web UI | `object_lock_ui.py`, `template_content.py`, `core/tables.py`, `object_retrieve.html` | List glyph, detail banner + Locks panel, per-mode blocked Edit/Delete affordances |
| GraphQL | `graphql/object_lock.py` (extras; invoked by `core/graphql/schema.py` via a thin lazy import) | `is_locked` / `locked_for_*` / `locked_fields` / `locks` |
| System Jobs | `jobs_object_lock_sweep.py`, `core/jobs/object_lock_bulk.py` | Sweep of expired/orphaned locks; bulk lock/release |
| Bypass / audit | `locking.py` (`bypass_object_lock`), `admin.py` (`ObjectLockBypassAuditAdmin`) | Programmatic-only bypass; `ObjectLockBypassAudit` rows are read-only in the Django admin |

`lock_state_for_objects()` (`object_lock_ui.py`) resolves the `LockState` for any set of objects in a
single query and is the shared backbone for the list glyph, the detail banner/panel, and GraphQL.

## Permissions

| Permission | Grants |
| --- | --- |
| `extras.add_objectlock` | Place locks — the trust boundary |
| `extras.delete_objectlock` | Release your own claims |
| `extras.force_release_objectlock` | Release another source's claims |
| `extras.bypass_objectlock` | Write through a lock (audited) |
| `extras.view_objectlock` | See lock metadata (sources, frozen fields) |

## Settings

- `OBJECT_LOCK_ENFORCED` (env `NAUTOBOT_OBJECT_LOCK_ENFORCED`, default `True`) — the kill switch.
- `OBJECT_LOCK_DEFAULT_TTL` (env `NAUTOBOT_OBJECT_LOCK_DEFAULT_TTL`, default 86400) — TTL applied to a
  programmatic lock when `expires` is omitted.

## Metrics

Object Lock exports the following Prometheus metrics (defined in `nautobot/extras/locking.py`, scraped
on the standard Nautobot `/metrics` endpoint):

| Metric | Type | Labels | Meaning |
| --- | --- | --- | --- |
| `nautobot_object_lock_gate_rebuilds_total` | Counter | — | Times the content-type gate was rebuilt from the database. |
| `nautobot_object_lock_gate_unreadable_total` | Counter | — | Times the gate was unreadable and rebuilt from an error (near-lapse alarm — alert if rising). |
| `nautobot_object_lock_blocked_total` | Counter | `mode` (`update`/`delete`) | Writes blocked by an active lock. |
| `nautobot_object_lock_bypass_total` | Counter | — | `bypass_object_lock()` invocations. |
| `nautobot_object_lock_bypass_audit_failures_total` | Counter | — | A bypass was permitted but its `ObjectLockBypassAudit` row failed to write (compliance gap — alert on any increase). |
| `nautobot_object_lock_sweep_last_success_timestamp_seconds` | Gauge | — | Unix timestamp of the last completed sweep; alert on staleness for liveness. |
| `nautobot_object_lock_sweep_failed_content_types_total` | Counter | — | Content types that failed during a sweep; alert on a rising rate. |

## Adding Object Lock to a model

Enforcement is global, so a lock on *any* UUID-PK `BaseModel` is honored without per-model wiring. The
**surfacing** is opt-in and demonstrated on `Manufacturer`:

- REST: mix `ObjectLockableSerializerMixin` and `ObjectLockableModelViewSetMixin` (both importable from
  `nautobot.apps.api`) into the model's serializer and viewset.
- Forms: mix `LockedFieldsFormMixin` (`nautobot.apps.forms`) into the model's edit form so frozen fields
  render disabled.
- Filters: mix `ObjectLockableFilterSetMixin` (`nautobot.apps.filters`) into the model's filterset to
  expose the lock filters.
- UI: the list glyph, detail banner, and Locks panel are registered for every lockable model
  automatically by `register_object_lock_ui()` (called from `ExtrasConfig.ready()`), so no per-model
  template work is needed.

## Performance invariants

These are asserted as query-count tests (not wall-clock) in `tests/test_object_locks.py` (the
write-path invariants) and `tests/test_object_lock_ui.py` (the list-view single-query invariant):

- A write against an unlocked type issues no `extras_objectlock` query.
- With the kill switch off, no gate/cache/DB access happens at all.
- The gate token is read at most once per request/Job (the per-context snapshot).
- List views resolve lock state for the whole page in one query.

## Guardrails

An allowlist CI test (`nautobot/core/tests/test_object_lock_lint.py`) flags new `bulk_update()`,
`bulk_create()`, and `_raw_delete()` call sites added outside its allowlist, so those raw-ORM bypasses
cannot be introduced silently. It deliberately does **not** match `QuerySet.update()` / `.delete()`
(the `Model.objects.filter(...).update(...)` idiom): those are documented, permitted bypasses — and a
queryset `.delete()` still fires per-instance `pre_delete`, so deletion is enforced under a change
context (UI/REST/Job), though it still bypasses from the shell/migrations like the other raw paths.
Treat the lint as a tripwire for the specific raw-bulk methods it names, not as proof the entire
boundary is sealed.

## Sweep and change logging

The Object Lock Sweep removes records with a bulk `QuerySet.delete()`. The global change-log
`pre_delete` receiver (`_handle_deleted_object`) disables Django's fast-delete path app-wide — the same
property that keeps bulk deletes *enforced* — so the sweep fires a per-row `pre_delete`. Running as the
**`ObjectLockSweep` Job** (inside a change context), each removed lock is therefore change-logged: one
`ObjectChange` per record, so a run that reaps N locks writes N entries.

Calling the underlying `purge_expired_and_orphaned_locks()` function **directly** (from `nbshell`, a
migration, or a test helper) runs with no change context, so `_handle_deleted_object` short-circuits
and those deletions are **not** change-logged — consistent with the out-of-band ORM bypass.
