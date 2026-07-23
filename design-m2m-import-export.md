# Design Note — General Many-to-Many Support in Import / Export

Status: **proposal, for review.** The direction in §4d (class E is imported/exported by **targeting the
through model directly**, not from either side of the M2M) was agreed in offline discussion and is
recorded here as the chosen approach; the rest remains open for review. No code changes are made pending
approval.
Companion to `trd-csv-import-export.md` and `qa-test-plan-import-export.md`.

## 1. Problem

Two gaps surfaced while exporting VLANs (a VLAN with 2 `locations` produced a file with **no `locations` column**):

1. **The field picker is symmetric, but export and import needs are not.** A single helper
   (`get_csv_form_fields_from_serializer_class`) feeds *both* the export field-selection tree and the
   import field-reference table. It skips `read_only` fields and (until reverted) only surfaced the
   default M2M subset (`tags`/`content_types`/`object_types`). So a read-only M2M like `locations` is
   never offered as an export column — you can only get it via "leave everything unchecked = all
   fields," never as a curated selection.

2. **Read-only M2M don't round-trip.** Even when an export *does* include such a field, its serializer
   is `read_only`, so a re-import silently drops it. Making import write these fields is not a flag —
   they are managed through **association / through models**, each with its own semantics.

The goal of this note is a coherent, general model for M2M in import/export, rather than per-field
patches.

## 2. Taxonomy of M2M fields

Every M2M relation falls into one of the classes below. The classification signal is **not** Django's
`through._meta.auto_created` alone — Nautobot mixes `associated_object_metadata` and
`associated_data_compliance` (GenericRelations) plus `created`/`last_updated` into most through models,
so nearly all report a truthy `auto_created`. The real question is: **does the through row carry
user-meaningful fields beyond the two foreign keys?** (ignoring `id`, `created`, `last_updated`,
`associated_object_metadata`, `associated_data_compliance`).

| Class | Example | Serializer | Through carries data? | Export today | Import today |
|-------|---------|-----------|----------------------|--------------|--------------|
| **A. Scalar-keyed, writable** | `tags` | writable (taggit) | n/a (special) | ✅ comma list | ✅ |
| **B. Composite-keyed, writable** | `Device.software_image_files`, `Interface.tagged_vlans` | writable, auto-through | no | ✅ JSON cell | ✅ |
| **C. ContentType** | `content_types`, `object_types` | writable, auto-through | no | ✅ `app.model` | ✅ |
| **D. Read-only, join-only through** | `VLAN.locations` (`VLANLocationAssignment`) | `read_only` | **no** (only the 2 FKs + auto metadata) | ⚠️ only via "all fields" | ❌ dropped |
| **E. Read-only, data-carrying through** | `SecretsGroup.secrets` (`access_type`,`secret_type`), `VRF.devices` (`rd`,`name`), `Interface.ip_addresses` (7 `is_*` flags) | `read_only` | **yes** | ⚠️ only via "all fields", and member NK alone loses the through data | ❌ dropped |
| **F. Reverse FK / one-to-many** | `Cable.terminations` | (nested only) | n/a | ❌ excluded (can't flatten) | ❌ |

Classes **A/B/C already work** both directions. The work is in **D**, **E**, and the picker.

Measured inventory across all Nautobot core apps (see §3 for the classifier used): **11** class D fields
and **9** genuinely class E fields (over 6 distinct through models, tabulated in §4d). Everything else is
class A/B/C, or class F.

> Note: `software_image_files` spans two classes depending on the model. `Device.software_image_files`
> and `VirtualMachine.software_image_files` are writable over an auto-through (class B), while
> `DeviceType.software_image_files` is `read_only` over the custom `DeviceTypeToSoftwareImageFile`
> (class D). Don't treat the field name as a class.

## 3. Classification signal (proposed helper)

Add a single source of truth for "how importable/round-trippable is this M2M":

```python
# Auto-managed columns, and the GenericForeignKey id column that taggit-style throughs carry --
# `content_type` is caught by the FK scan but `object_id` is a plain concrete field and would
# otherwise make every tagged model look like class E.
IGNORED_THROUGH_FIELDS = {"id", "object_id", "created", "last_updated",
                          "associated_object_metadata", "associated_data_compliance"}

def m2m_through_profile(model, field_name):
    """Return one of: 'auto' (no through / auto-through), 'join' (custom through, FKs only),
    'data' (custom through with user fields), or 'reverse' (not a forward M2M)."""
    f = model._meta.get_field(field_name)
    if not f.many_to_many:
        return "reverse"
    through = f.remote_field.through
    if through._meta.auto_created:
        return "auto"
    if issubclass(through, GenericUUIDTaggedItemBase):  # nautobot.extras.models.TaggedItem
        return "auto"  # taggit is special-cased end to end; see §6
    fk_names = {x.name for x in through._meta.get_fields() if x.many_to_one}
    extra = [x for x in through._meta.get_fields()
             if x.concrete and x.name not in fk_names and x.name not in IGNORED_THROUGH_FIELDS]
    return "data" if extra else "join"
```

- `auto` / `join` → **round-trippable by member natural key** (import can set the relation).
- `data` → **not** round-trippable by member NK alone; the through row is the unit of import/export
  instead (§4d).

Known pitfalls this version handles, each of which silently mis-routes §4c if missed:

- **taggit.** `extras.TaggedItem`'s only non-FK concrete field is `object_id` (the GFK id column), so a
  naive scan classifies **all ~60** `tags` fields as `data` and sends every tagged model down the
  class-E refusal path. Both the `IGNORED_THROUGH_FIELDS` entry and the explicit short-circuit are
  belt-and-braces here; keep at least one.
- **`dcim.CableToCableTermination`.** Reports `cable_end`, `connector`, and one column per termination
  type as "extra", so `Cable.interfaces`, `Cable.front_ports`, … land in `data`. These aren't in the
  `Cable` serializer at all and are really class F; filter on serializer presence before profiling, or
  exclude them explicitly.
- **`auto_created` is a model class, not `True`.** Django sets it to the creating model, so test it for
  truthiness (as above) rather than `is True`.

## 4. Proposed design

### 4a. Decouple the export and import field lists

Split the shared helper by intent:

- **Export tree** — offer every *readable* field, including `read_only` ones and all M2M
  (classes A–E). This matches what an "all fields" export already produces, so a curated selection can
  include `locations`.
- **Import reference** — offer every *writable* field (classes A–C today), **plus** class D once 4c
  makes it importable. Class E is deliberately **not** offered here; it is imported via its through
  model (§4d).

Mechanically: add `include_read_only` (and keep `exclude_m2m=False`) to
`get_csv_form_fields_from_serializer_class`, or split into `exportable_fields()` /
`importable_fields()`. The export path passes `include_read_only=True`; the import path does not.
Also guard the `child_relation.queryset.model` lookup, which is `None` for read-only M2M.

### 4b. Export (read side) — all classes

No serializer changes needed; the export job already sets `exclude_m2m=False` and can read everything.
Once the picker offers the fields (4a), classes A–E all export:

- D/E scalar members → comma list; composite members → JSON cell (existing machinery).
- For **class E**, a member-NK-only cell **loses the through data** (`priority`, `access_type`, the
  `is_*` flags, …). It is therefore **export-only**: useful for reading and for diffing, never a
  round-trip artifact. Emit a one-time INFO/WARNING naming the field *and the through content-type to
  use instead* (§4d) so the message is actionable rather than just apologetic.

The earlier "E-rich" idea — exporting each member as `{"member": <nk>, "priority": 10}` so a future
import could reconstruct the through rows — is **dropped**. Targeting the through model directly gets
the same fidelity out of the existing FK-natural-key flattening, with no new wire format to define,
parse, or validate.

Keeping the lossy class-E column at all is deliberate: "all fields" exports it today, so removing it
would be a regression for anyone already relying on it.

### 4c. Import (write side)

The `ImportObjects` job resolves each row through the serializer, then — for M2M the serializer won't
accept — applies them **after** `save()` via the ORM, keyed on the `m2m_through_profile`:

- **auto / join (class B, C, D)** → resolve each member by natural key (reusing the existing
  related-object resolution + error messaging), then `getattr(obj, field).set(members)`. This makes
  `VLAN.locations` round-trip.
- **data (class E)** → **not** written from a member-NK cell. Log a WARNING that names the field, the
  reason, and the remedy — e.g. *"`SecretsGroup.secrets` is managed via `extras.SecretsGroupAssociation`,
  which carries additional attributes (`access_type`, `secret_type`); import that content-type directly
  to set these associations."* Never silently drop.
- Permissions: setting a read-only-but-join M2M still requires the appropriate permission on the
  relation / through model; the job must enforce it, consistent with §15 of the QA plan.

### 4d. Class E: the through model is the unit of import/export

**Decision (offline):** class E associations are imported and exported by targeting the **through model
directly** as its own content-type, rather than from either side of the M2M.

This needs no new machinery. All six class E through models already have serializers *and* registered
API routes, and both jobs can already select them — `ExportObjectList`'s content-type picker filters
only on `can_view`, and `ImportObjects` on `can_add` + `has_serializer`:

| Through model | Through data | Exposed as (M2M side) |
|---|---|---|
| `ipam.IPAddressToInterface` | `is_source`, `is_destination`, `is_default`, `is_preferred`, `is_primary`, `is_secondary`, `is_standby` | `Interface.ip_addresses`, `VMInterface.ip_addresses` |
| `ipam.VRFDeviceAssignment` | `rd`, `name` | `VRF.devices`, `VRF.virtual_device_contexts`, `VRF.virtual_machines` |
| `extras.SecretsGroupAssociation` | `access_type`, `secret_type` | `SecretsGroup.secrets` |
| `extras.DynamicGroupMembership` | `operator`, `weight` | `DynamicGroup.children` |
| `dcim.InterfaceRedundancyGroupAssociation` | `priority` | `InterfaceRedundancyGroup.interfaces` |
| `extras.UserSavedViewAssociation` | `view_name` | `User.default_saved_views` |

Beyond avoiding a bespoke format, there is a correctness argument: **for some through models there is no
"other side" to import from.** `VRFDeviceAssignment` backs three separate M2M fields (`devices`,
`virtual_device_contexts`, `virtual_machines`), and `IPAddressToInterface` backs two (`Interface` and
`VMInterface`). Member-NK columns on those fields are partial views of one table, and a declarative
`.set()` from any one of them would have to avoid clobbering the rows owned by the others. Targeting the
through model is the only representation that can express the table faithfully.

Consequences to document for users:

- **Full-fidelity restore is a multi-document operation with an ordering constraint.** Restoring a
  SecretsGroup and its secret assignments takes ≥2 files, applied in dependency order: both endpoint
  object types first, then the association rows. This is the main cost of the approach (see §6).
- **Membership semantics differ from class D.** Class D's `.set()` is declarative — the file replaces
  the membership. Through-row import is ordinary per-row upsert, i.e. **additive**: associations absent
  from the file are not deleted. Users will read both as "the same kind of thing," so this must be
  explicit in the docs rather than discovered.
- **Endpoints are referenced by nested natural key**, e.g. an `IPAddressToInterface` row identifies its
  interface as `interface__device__name` + `interface__name`. That is the existing nested-reference
  machinery, but note it consumes relation depth against `EXPORT_FIELD_MAX_DEPTH` (currently 3).

### 4e. Round-trip semantics matrix

| Class | Export | Import | Round-trips? |
|-------|--------|--------|--------------|
| A tags | ✅ | ✅ | ✅ |
| B composite (auto-through) | ✅ | ✅ | ✅ |
| C content_types | ✅ | ✅ | ✅ |
| D join-only read-only (`locations`) | ✅ (after 4a) | ✅ (via post-save `.set()`, 4c) | ✅ (new) |
| E data-carrying read-only | ✅ export-only from the M2M side (lossy, warned) | ⚠️ warned & skipped from the M2M side | ✅ **via the through model as its own content-type** (4d) |
| F reverse/one-to-many | ❌ | ❌ | n/a |

## 5. Phasing

1. **Phase 1 — Export parity + picker decouple (4a, 4b).** Low risk, no serializer changes.
   Delivers the user's immediate need (`locations` selectable and exported). Classes D/E export.
2. **Phase 2 — Import round-trip for join-only M2M (4c auto/join).** Medium. Adds post-save M2M
   application in `ImportObjects` + the `m2m_through_profile` helper + permission checks. Makes class D
   round-trip.
3. **Phase 3 — Bless and document the through-model path for class E (4d).** Small: the mechanism
   already works today. The work is the actionable warning in 4b/4c, a docs section covering the
   multi-document ordering and the additive-vs-declarative difference, and round-trip tests over at
   least `SecretsGroupAssociation` (simple 2-FK + data) and `VRFDeviceAssignment` (multi-sided).

Phase 3 replaces the previously-proposed "E-rich" phase, which is dropped (§4b).

## 6. Risks & edge cases

- **`associated_*` GenericRelations** must be excluded from the through-field scan, or every through
  looks like class E. (Signal in §3 handles this.)
- **`tags`** is taggit-special (through `TaggedItem` with a GFK); keep the existing special-casing
  rather than routing it through the generic path — and note the `object_id` trap in §3, which makes the
  naive classifier claim all ~60 `tags` fields are class E.
- **Cross-document ordering (new).** Class E restores span multiple files whose apply order matters
  (endpoints before associations). There is no ordering mechanism in the import job today; the near-term
  answer is documentation plus a clear resolution error when an endpoint is missing. A manifest or
  multi-document bundle would be a larger follow-up.
- **Asymmetric membership semantics (new).** Class D import is declarative (`.set()` replaces); class E
  through-row import is additive (absent rows are not deleted). Deleting stale associations remains a
  manual step.
- **Ordering / uniqueness**: `.set()` replaces the full membership; confirm that's the desired import
  semantic (declarative — the file is the source of truth) vs additive.
- **Reverse accessors** (class F) remain excluded — they multiply rows and can't be flattened.
- **Performance**: post-save `.set()` adds queries per row; batch where possible.

## 7. Open questions for review

1. Phase 1 only for now, or Phase 1+2 together (so `locations` fully round-trips)?
2. Class E export from the M2M side: keep the lossy member-NK column (as §4b recommends, since "all
   fields" already emits it) or drop it entirely so the through model is the only representation?
3. Import M2M semantics for class D: **declarative `.set()`** (file replaces membership) — agreed? And
   is the resulting asymmetry with class E's additive through-row import acceptable, or should class E
   grow a declarative mode?
4. Should read-only *non-M2M* fields (e.g. `created`, computed counts) also be offered in the export
   tree, or only read-only **M2M**? (Offering all readable fields is simplest and matches "all
   fields", but adds `url`/`display`/`object_type` noise.)
5. Do the six class E through models need UI list/detail views to make the workflow discoverable, or is
   API/job-level access sufficient for now? (`IPAddressToInterface` currently has only a bulk-create UI
   viewset; `VRFDeviceAssignment` has a table and filterset but no list view.)
