# Object Lock

Object Lock lets a trusted actor declare that an existing object **must not be deleted and/or
modified** until the lock is released. It is a safety/integrity feature that prevents *accidental*
removal or modification of objects something depends on — for example, an SSoT run that needs a
`Manufacturer` to persist for the duration of a sync.

**Scope in this release:** enforcement is **global** — a lock on any UUID-PK object is honored, and the
bulk **Lock/Release** list actions appear on every lockable model. The REST lock-state fields
(`is_locked`, `locked_for_delete`, …) and the edit-form frozen-field behavior are wired on
**`Manufacturer`** as the reference integration.

## What Object Lock does and does not protect

Enforcement applies to changes made through the **Web UI, the REST API, and Jobs** — every path
that carries a change context and fires Django save/delete signals. The following are **explicit,
permitted bypasses** (not policed gaps), because server/shell access is already trusted:

- the interactive shell (`nbshell`);
- custom management commands and raw scripts;
- raw bulk-ORM operations (`bulk_update()`, `QuerySet.update()`, `bulk_create()`, `_raw_delete()`).
  These skip Django's save signals, so a locked object **can** still be changed by them — including
  in-tree code paths that use bulk writes (for example IPAM prefix/IP reparenting). A queryset
  `.delete()` differs: because deletion fires a per-row signal, it is enforced when run under a change
  context (UI/REST/Job); from the shell or a management command (no change context) it bypasses like the others.

Object Lock is **not** a security control against a motivated actor, and it does not replace RBAC.
It is also **not** a hard concurrency barrier: a lock is honored by writes that *begin after* it
commits, so an operation already in flight when the lock is placed — most realistically a
long-running Job started beforehand — may still finish its writes. Apply locks before launching a
long Job over the same objects, or re-run the Job afterward to pick up locks placed during it.

## Lock claims

Each lock is one claim by one source on one object. An object is:

- **Delete-locked** if at least one active claim sets `prevent_delete` (the default).
- **Update-locked** if at least one active claim sets `prevent_update`.

Multiple sources may lock the same object independently (reference counting); releasing one claim
leaves the others in force. Every lock records who/what created it and why, and has an optional
expiry (TTL).

## Creating and releasing locks

Programmatically:

```python
from nautobot.extras.models import ObjectLock

# Lock a single object for the duration of a block (releases on exit; default TTL is a crash backstop):
with ObjectLock.objects.locked(manufacturer, reason="ACME SSoT sync", requesting_user=user):
    ...  # work that depends on the manufacturer

# Lock many objects at once:
with ObjectLock.objects.locked(manufacturers, reason="ACME SSoT sync", requesting_user=user):
    ...

# Imperative (single object):
ObjectLock.objects.lock(manufacturer, prevent_delete=True, requesting_user=user)
ObjectLock.objects.release(manufacturer, source_key="...")

# Imperative (many objects):
ObjectLock.objects.lock_many(manufacturers, prevent_delete=True, requesting_user=user)
ObjectLock.objects.release_many(manufacturers, source_key="...")
```

`locked()` accepts either a single object or an iterable; `lock_many` / `release_many` always
take an iterable.

Each claim is identified by a `source_key` — a stable string naming the locking source. `lock()`
auto-generates one when you omit it; pass the same `source_key` to `release()` to remove that
specific claim.

Via the REST API: `POST /api/dcim/manufacturers/{id}/lock/` and `.../release/`. The `release` action
**requires** a `source_key` in the request body identifying the claim to remove (releasing with no
`source_key` returns a `400`). When you create a lock without supplying your own `source_key`, the
server auto-generates one and returns it in the `lock` response body — capture that value and pass it
back as `{"source_key": "<key from lock response>"}` to release that specific claim. Lock records are
also listable and deletable at `/api/extras/object-locks/`, but cannot be created or edited in place
there — always use the per-object `lock` / `release` actions, which derive and preserve attribution.

### Expiry and indefinite locks

Every lock has an expiry. When `expires` is omitted, the lock inherits `OBJECT_LOCK_DEFAULT_TTL`
(24 hours by default) — a backstop so a forgotten or crashed-process lock cannot protect an object
forever. Pass an explicit `expires` (any future datetime) to set a different lifetime, such as a
far-future date for a long change freeze.

To create a lock with **no expiry**, a programmatic caller passes `expires=None` together with
`_expires_explicit=True`; alternatively, setting `OBJECT_LOCK_DEFAULT_TTL = None` in
`nautobot_config.py` makes every lock that omits `expires` indefinite. An indefinite lock is **never**
reaped by the expiry sweep (only orphan cleanup can remove it), so it must be released explicitly —
prefer a generous explicit `expires` over an indefinite lock unless a process guarantees release.

## Viewing locks

Active lock records are visible in the Nautobot UI under
**Extensibility → Logging → Object Locks**, gated by the `extras.view_objectlock` permission.

Locks are change-logged like any other object: each lock create/release (and the sweep Job's
cleanup) writes a change-log entry, so lock activity is auditable from the change log. Because locks
are high-churn, expect this to add change-log volume proportional to how heavily the feature is used.
The sweep change-logs each record it removes, so a run that reaps N expired or orphaned locks writes N
change-log entries — size its schedule with that volume in mind.

### Querying lock state via GraphQL

Every object type exposes Object Lock state in GraphQL:

- `is_locked`, `locked_for_delete`, `locked_for_update` (Boolean) — always visible.
- `locked_fields` (`[String]`) and `locks` (the underlying `ObjectLock` records) — returned only to
  callers holding `extras.view_objectlock`; otherwise they resolve to empty.

Lock state is available inline on every object, and the `ObjectLock` records are also exposed as a
top-level `object_locks` query (filterable like any other type; the records themselves are gated by
`extras.view_objectlock`):

```graphql
query { manufacturers { name is_locked locked_for_update locked_fields } }
query { object_locks(prevent_delete: true) { reason source_key } }
```

## Modifying a locked object (bypass)

Authorized code (holding the `extras.bypass_objectlock` permission) may modify a locked object
without releasing the lock:

```python
from nautobot.extras.locking import bypass_object_lock

with bypass_object_lock():
    obj.description = "…"
    obj.save()
```

The context manager re-checks the permission on every entry and raises `PermissionDenied` if the
active change-context user lacks it. Every bypass attempts to write an `ObjectLockBypassAudit` record in
the same transaction as the write it permits. Audit-write failures are deliberately **swallowed** (logged,
and counted by `nautobot_object_lock_bypass_audit_failures_total`) so a logging failure can never block an
intentionally authorized write — so in that rare failure case a bypass can commit without its audit row.
Alert on any increase in that counter.

Bypass is **programmatic only** — there is no UI or REST API affordance for it in this release; it is
for trusted code paths (Jobs, SSoT, the shell). The `ObjectLockBypassAudit` records are reviewable by
superusers in the Django admin (read-only) under **Extras → Object Lock bypass audits**.

## Permissions

| Permission | Grants |
|---|---|
| `extras.view_objectlock` | View locks and lock metadata |
| `extras.add_objectlock` | Create (lock) |
| `extras.change_objectlock` | (Reserved) Locks are not edited in place — release and re-lock to change |
| `extras.delete_objectlock` | Release your own claims |
| `extras.bypass_objectlock` | Use the bypass context manager |
| `extras.force_release_objectlock` | Release a claim created by a different source |

Grant `add_objectlock` narrowly — it is the trust boundary.

## Configuration

| Setting | Environment variable | Default | Purpose |
|---|---|---|---|
| `OBJECT_LOCK_ENFORCED` | `NAUTOBOT_OBJECT_LOCK_ENFORCED` | `True` | Kill switch for the **whole feature**: `False` turns off enforcement and all *visible* surfacing — no glyphs or banners, and the lock-state filters report nothing locked. The REST/GraphQL `is_locked` / `locked_for_*` / `locked_fields` fields stay in the schema but resolve to unlocked/empty. **Restart-only** (read at startup). |
| `OBJECT_LOCK_DEFAULT_TTL` | `NAUTOBOT_OBJECT_LOCK_DEFAULT_TTL` | `86400` (24 h) | Default TTL (seconds) for locks created without an explicit `expires`. The environment variable is integer-only; set `OBJECT_LOCK_DEFAULT_TTL = None` in `nautobot_config.py` (not via the env var) for indefinite-by-default locks — see [Expiry and indefinite locks](#expiry-and-indefinite-locks). |

Both settings are read from environment variables at startup. To disable enforcement:

```bash
NAUTOBOT_OBJECT_LOCK_ENFORCED=False
```

With the kill switch off, Object Lock is fully dormant: nothing is enforced and nothing renders as locked
— no glyphs or banners, and the lock-state filters report nothing locked. The REST/GraphQL `is_locked` /
`locked_for_*` / `locked_fields` fields stay in the schema (so client code keeps working) but always
resolve to unlocked/empty. Because the value is read at startup, toggling it requires a **service
restart** — treat it as a deploy-time control, not an in-incident live switch.

## Maintenance

The **Object Lock Sweep** system Job purges expired and orphaned lock *records*. It ships enabled but
is **not** auto-scheduled — schedule it to run periodically (e.g. daily) under **Jobs → Object Lock
Sweep → Schedule**, assigning an owner so the scheduler accepts it. Expired locks stop enforcing the
moment they expire (enforcement ignores them live), so the sweep is housekeeping that keeps the lock
table tidy, not a control over whether an expired lock blocks. Monitor its last-success age under
**Jobs → Job Results**.

**Schedule it after install.** If the sweep never runs, expired and orphaned lock *records*
accumulate indefinitely: enforcement is unaffected (expired locks are ignored the moment they
expire), but the `extras_objectlock` table grows without bound. Alert on the
`nautobot_object_lock_sweep_last_success_timestamp_seconds` metric so a sweep that has never run — or
has silently stopped — is caught.

### Upgrade impact

**Enforcement is global from the migration that adds Object Lock onward.** After upgrade, any existing
Job, SSoT sync, or REST/UI client that writes to an object someone has locked starts receiving an
`ObjectLockedError` (HTTP **409** over REST) where it previously succeeded. Before upgrading: identify
automation that writes to lockable objects, decide whether it should be exempt, and grant it
`extras.bypass_objectlock` (its writes are then audited) — or coordinate so it doesn't run against locked
objects. Out-of-band ORM writes (nbshell, migrations, raw bulk operations) are **not** enforced and need
no change.

`ObjectLock` references its target's content type through a `PROTECT` foreign key, so a `ContentType`
that still has lock records cannot be deleted. If you **uninstall an app** whose models hold locks,
Nautobot's stale-content-type cleanup is blocked until those locks are gone. Run the **Object Lock
Sweep** first: it treats locks whose target model is no longer installed as orphaned and purges them,
clearing the way for content-type cleanup.

## Field-Level Locking

An Object Lock with `prevent_update=True` may carry a `locked_fields` list. When set, only those fields are frozen and every other field of the object remains editable. An update lock with an empty or absent `locked_fields` freezes the **whole object**. Delete locking (`prevent_delete`) is never affected by field scoping.

### What can be frozen

- **Concrete model fields** (e.g. `description`, `name`).
- **Custom-field keys** (the keys under `_custom_field_data`).
- **Many-to-many relations** (e.g. `tags`), enforced through a dedicated `m2m_changed` handler because M2M edits do not fire `pre_save`.

`locked_fields` names are validated server-side at creation (model `clean()`, the manager guard, and the REST serializer) against the target model's real fields and custom-field keys; an unknown name is rejected with a validation error.

### How enforcement works

On a save of an update-locked object, the lock handler computes which of the frozen fields actually changed and raises only if at least one did — it never silently reverts a value. Prior values come from the change-context pre-save snapshot when one is cached; for objects that already have change history (the typical lock target) no snapshot is cached, so the handler performs one extra database read to fetch prior values. This read happens only on a gate hit (i.e. only for objects whose type currently has an active lock). On a blocked REST write, the 409 response body lists the offending (frozen, changed) field names. Those names are shown only to callers holding the `extras.view_objectlock` permission; everyone else receives a generic message. In the Web UI, the object's edit form additionally renders the frozen fields as disabled (the rest stay editable) — a convenience layer over the authoritative server-side check.

### Composition across multiple locks

If several locks target the same object, the effective frozen-field set is the **union** of their `locked_fields`. A single whole-object update lock freezes everything regardless of other claims.

### Bypass

`bypass_object_lock()` suspends both whole-object and field-scoped checks. When a bypass suspends another source's frozen fields, the durable bypass audit record notes the suspended fields and flags that another source's claim was overridden.

### Limitations

- **Many-to-many enforcement is forward-side only.** Editing `obj.tags` is enforced; mutating the relation from the reverse accessor is treated as a documented bypass to avoid a per-object query fan-out.
- **Stale field names (drift).** If a later migration renames or removes a field, a lock's stored name no longer matches a real field. Enforcement is fail-closed (any save of the object surfaces the drift as a blocked change), and operators can audit drift programmatically via `nautobot.extras.locking.find_stale_locked_fields()`.

## See also

- [Object Lock UI feature guide](../feature-guides/object-lock-ui.md) — an operator's walkthrough of the list, detail, and bulk surfaces.
- [Object Lock Internals](../../development/core/object-lock-internals.md) — the developer architecture reference.
