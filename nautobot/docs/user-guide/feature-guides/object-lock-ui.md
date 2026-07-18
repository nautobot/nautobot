# Object Lock: Visibility and Bulk Management

Object Lock protects an existing object so it cannot be accidentally deleted and/or modified through the Web UI, REST API, or Jobs. This guide covers the visibility and bulk-management surfaces. For the underlying model and enforcement, see the [Object Lock platform reference](../platform-functionality/object-lock.md).

!!! note
    Object Lock protects against *accidental* deletion/edits via the UI, API, and Jobs. It is not a security control against a motivated actor, and it does not police raw bulk-ORM or shell access (those are documented, permitted bypasses).

## Seeing locks in list views

Locked objects show a lock glyph next to their name:

- Padlock (`mdi-lock`) — delete-locked.
- Pencil-with-lock (`mdi-pencil-lock`) — update-locked.
- Padlock-with-alert (`mdi-lock-alert`) — both.

Hover the glyph for a tooltip with the mode(s), active-lock count, earliest expiry, and source summary (the richer details require the **view object lock** permission). To find only locked objects, use the **Locked** quick-filter in the filter form. Lock state is intentionally not a sortable column.

!!! note
    A few list views render the primary column as a linkified template (for example Prefixes and IP Addresses); those do not yet show the inline glyph, so the absence of a glyph there does not by itself mean an object is unlocked — open the detail page to confirm.

## Seeing locks on a detail page

A banner names every active mode and the number of contributing locks. The **Locks** panel lists each active claim (mode, source, creating user, reason, created, expiry) with a glyph legend. Without the **view object lock** permission you see a generic summary and the note "Lock details are restricted to authorized users."

## Why Edit/Delete is blocked, and how to proceed

Only the affected action is disabled: a delete lock disables **Delete**, an update lock disables **Edit**, and a lock that does both disables both. The unaffected action stays usable. A disabled action is still present, with an explanation reachable by keyboard and screen reader. To proceed, release the relevant locks you own from the **Locks** panel — a live counter shows how many remain and re-enables the action when it reaches zero. If locks held by *other* sources remain, the panel tells you who holds them and to contact an administrator; ordinary users can only release their own claims. Releasing another source's claim requires the **force release object lock** permission.

When a lock freezes only specific fields (rather than the whole object), the object's **edit form** opens normally but those fields are rendered disabled, with an explanation in their help text, so you can still edit the unfrozen fields. A change to a frozen field is rejected server-side regardless.

## Bulk lock and release

Bulk actions appear on list views for users with the relevant permission: **Lock Selected** requires the **add object lock** permission, and **Release Selected** requires the **delete object lock** permission.

**Lock Selected** opens a form for the mode, a reason, a required expiry, and a source key, and creates one claim per selected object. UI-created locks always require an explicit expiry, unlike programmatic locks, which fall back to the default TTL. If some selected objects are already locked, the confirmation lists them and offers to proceed with only the unlocked ones. Both actions run as a background Job whose result reports how many objects were actioned and how many were skipped. Releasing another source's claim still requires the **force release object lock** permission.

!!! warning
    Bulk release removes lock protection from the selected objects. Once released, those objects can be edited or deleted by anyone with the usual model permissions.

## GraphQL

Every object type exposes `is_locked`, `locked_for_delete`, `locked_for_update`, `locked_fields`, and a `locks` list. `locks` and `locked_fields` honor the **view object lock** permission. The `ObjectLock` type is itself queryable and filterable (e.g. `{ object_locks(prevent_delete: true) { reason source_key } }`).
