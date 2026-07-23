# Configurable Import / Export with Upsert — Manual QA Test Plan

Scope: the CSV/JSON/YAML configurable export, the update-or-create import, and their job-modal UI, as described in `trd-csv-import-export.md`. Use a model with rich relations (**dcim.device** is the primary target — FK natural keys, composite-key M2M `software_image_files`, scalar M2M `tags`) and a simple model (**extras.status**) for basic cases. Unless noted, "the list view" means the model's list page and "Actions ▾" is its top-right action dropdown.

Legend for exact strings referenced: the export dropdown item is **Export to file**; the import item is **Import from file**; the shared modal is `#nautobot-generic-modal`; the export field control is labeled **Fields to Export**; the scope toggle is **Use Current View**.

---

## 1. Export — launch & job modal

| # | Test | Steps | Expected |
|---|------|-------|----------|
| 1.1 | Export opens in the modal | Devices list > Actions ▾ > **Export to file**. | A modal opens in-page (does NOT navigate to a new page). It shows the ExportObjectList job form: Content Type (pre-set to `dcim \| device`), Format, Export Template, **Fields to Export**, **Use Current View**, and a **Run Job Now** button. |
| 1.2 | Modal shell present on list pages | On any standard list view, inspect page source. | Exactly one `<div id="nautobot-generic-modal">` is present (included by `generic/object_list.html`). |
| 1.3 | Cancel/close | Open the Export modal, click **Cancel** (or the ✕). | Modal closes; no job is enqueued; list view unchanged. |
| 1.4 | Plain export (defaults) | Actions ▾ > Export to file > **Run Job Now** with no changes. | Job runs; result modal shows Status **Completed**; a `*.csv` file is produced containing all fields for all objects; file's first line is `# nautobot-import: match_fields=id` (or the model's natural key). |

## 2. Export — field selection (tree picker)

| # | Test | Steps | Expected |
|---|------|-------|----------|
| 2.1 | Default = visible columns | Devices list (default columns) > Export to file. Inspect **Fields to Export**. | The checkboxes pre-checked match the list's currently visible columns (e.g. `name`, `status`, `tenant`, `role`, `device_type…`). |
| 2.2 | Expand a relation | Click the caret on the far right of the `device_type` row. | Row expands to show indented nested columns (`device_type__manufacturer`, `device_type__model`, `device_type__part_number`, …). Caret flips to up-chevron. |
| 2.3 | Collapsed by default | Open the control fresh. | All relation groups start **collapsed** (only top-level rows shown; carets are down-chevrons). |
| 2.4 | 3-level depth | Expand `device_type`, then `device_type__manufacturer`. | You can drill to `device_type__manufacturer__name` (3 segments). No option deeper than 3 `__`-segments is offered. |
| 2.5 | Relation = natural key | Select `device_type` only (no children), Format CSV, Run. | Output columns are `device_type__manufacturer__name` and `device_type__model` (DeviceType's natural key). |
| 2.6 | Mutual exclusivity | With `device_type` checked, check `device_type__model`. | `device_type` auto-unchecks and shows an **indeterminate** (dash) state; the export now contains only `device_type__model`. |
| 2.7 | Re-select parent clears children | After 2.6, re-check `device_type`. | Its nested checkboxes clear; parent becomes checked; export reverts to the natural-key columns. |
| 2.8 | Drag to reorder | Drag the `name` row below `status` in the top-level list; Run. | Exported CSV column order reflects the dragged order (drag handle appears on hover). |
| 2.9 | Top-level M2M offered | Inspect top-level rows for Device. | `tags` and (where applicable) `content_types` appear as selectable top-level rows. |
| 2.10 | Nested M2M NOT offered | Expand `status`. | No `status__content_types` (or any nested M2M) option is offered — M2M is only selectable at the top level. |
| 2.11 | Required marker | Inspect a model with a required field (e.g. Status `name`). | Required (for re-import) fields are marked with a red `*`. |

## 3. Export — formats & document structure

| # | Test | Steps | Expected |
|---|------|-------|----------|
| 3.1 | CSV export | Export to file, Format **CSV**, Run. | `*.csv` file; flat header of serializer field paths; UTF-8 BOM present; nested relations as `a__b__name` columns. |
| 3.2 | JSON document | Statuses list > Export to file, Format **JSON**, Run, download. | JSON document with header `"nautobot_import": "1"`, `"model": "extras.status"`, `"match_fields": [...]`, then `"records": [ {...}, ... ]`; related fields nested under their parent key, not flattened. |
| 3.3 | YAML document (generic model) | Statuses > Export to file, Format **YAML**, Run. | Single YAML document: `nautobot_import: "1"`, `model: extras.status`, `match_fields:`, `records:`. Does NOT error for a model without `to_yaml()`. |
| 3.4 | Device-type library YAML | Device Types > Export to file, Format **YAML**, Run. | File `nautobot_device_types.yaml`; devicetype-library-compatible YAML (uses `to_yaml()`), not the generic document. |
| 3.5 | Auto format = CSV | Export to file, leave Format on **Auto (saved view's format, otherwise CSV)**, Run (not on a saved view). | A CSV is produced (auto falls back to CSV). |
| 3.6 | Saved-view format applies (regression) | On a saved view whose `export_config.format` = `json`, Export to file with **Use Current View** on and Format **Auto**, Run. | A **JSON** file is produced (saved format is honored — not silently forced to CSV). |
| 3.7 | Explicit format overrides saved | Same saved view (saved format json), but pick Format **CSV**, Run. | A CSV file is produced (explicit choice wins over saved format). |

## 4. Export — "Use Current View" (filters + sort)

| # | Test | Steps | Expected |
|---|------|-------|----------|
| 4.1 | Toggle description | Open Export to file, read the **Use Current View** help text. | States it applies the current view's filters and sort order (and, for a saved view, its saved fields/format), and that when off every object is exported in default order. |
| 4.2 | Off = full export (default) | Filter Devices to one site, Export to file WITHOUT ticking Use Current View, Run. | Export contains **all** devices (filter ignored), model default order. |
| 4.3 | On = filtered | Same filtered list, Export to file with **Use Current View** ticked, Run. | Export contains only the filtered devices. |
| 4.4 | On = sorted | Sort the list by a column (e.g. `-name`), Export to file with Use Current View on, Run. | Rows are ordered by that column in that direction. |
| 4.5 | On = saved view fields/format | On a saved view with a saved field selection and format, Export to file with Use Current View on, Run. | The saved view's fields and format are applied (in addition to its filters/sort). |
| 4.6 | Non-sortable sort key | Trigger an export with `use_current_view=true` and a `sort` param that isn't a model field/`cf_` (e.g. a computed column). | Export still succeeds; a **WARNING** log entry `Ignoring sort on \`<key>\`; not a sortable field for this model` is recorded; default order used. |
| 4.7 | Related/cf sort allowed | Export with Use Current View on and `sort=location__name` (or `sort=cf_<key>`). | Sort is applied (head-segment validation permits related-field and custom-field sorts). |
| 4.8 | Stale saved_view id | Export with `use_current_view=true` and `query_string=saved_view=<deleted-uuid>`. | Export succeeds as a plain full export (no crash / no `SavedView.DoesNotExist`). |

## 5. Export — result modal & download

| # | Test | Steps | Expected |
|---|------|-------|----------|
| 5.1 | Result polling | Run an export; watch the result modal. | Modal shows Job Status label + spinner while running, then Status **Completed** with Duration. |
| 5.2 | Auto-download | On completion of an export. | The file downloads automatically (browser download starts without leaving the page). |
| 5.3 | Download button | On the completed result modal. | A green **Download <filename>** button is present and re-downloads the file when clicked. |
| 5.4 | View Job Results | Click **View Job Results** on the modal. | Navigates to the JobResult detail page, where the same file is linked. |
| 5.5 | Failed export | Force a failure (e.g. invalid field selection via API), observe modal. | Status **Failed**; no Download button; error visible in job log. |

## 6. Export — M2M & related-field representation

| # | Test | Steps | Expected |
|---|------|-------|----------|
| 6.1 | Scalar M2M — tags (special case) | Tag a device with `a,b,c`; export `name,tags` as CSV. | `tags` cell = `"a,b,c"` (quoted comma-separated list of names). Verifies the django-taggit `TaggableManager` path specifically. |
| 6.2 | Scalar M2M — generic (non-tags) | On a plain scalar-keyed M2M (e.g. VRFs > export `name,import_targets`, RouteTarget natural key = `name`), Run CSV. | Cell = comma-separated member natural keys (e.g. `"65000:1,65000:2"`), same as tags — confirms a non-taggit `ManyRelatedField` renders identically. |
| 6.3 | Composite M2M (JSON cell) | Attach 2 `software_image_files` to a device; export including `software_image_files` as CSV. | Cell is a JSON array of dicts, e.g. `[{"image_file_name": "...", "software_version__platform__name": "...", "software_version__version": "..."}]`. |
| 6.4 | Content-type M2M | Export a Status's `content_types`. | Cell = `"dcim.device,dcim.location"` (app_label.model strings, not UUIDs or dicts). |
| 6.5 | Null FK → `NoObject` | Export a device with no `tenant`. | `tenant__name` cell = `NoObject` (the whole related object is absent). |
| 6.6 | Null scalar → `NULL` | Export a device with a nullable scalar field unset (e.g. `asset_tag` = None), CSV. | `asset_tag` cell = `NULL` (distinct from `NoObject`, which is only used for absent related objects). |
| 6.7 | Composite M2M with special chars | Export M2M whose member value contains a comma/quote/apostrophe (e.g. `St. John's`). | Value is JSON-encoded and correctly escaped; opening/saving in Excel preserves it. |

## 7. Export — match-key stamping

| # | Test | Steps | Expected |
|---|------|-------|----------|
| 7.1 | Directive stamped (CSV) | Export Statuses to CSV with default fields. | First line: `# nautobot-import: match_fields=id` (or `name` if no `id` column). |
| 7.2 | Document match_fields (JSON) | Export Statuses to JSON. | Document has `"match_fields": ["id"]` (or natural key). |
| 7.3 | Document match_fields (YAML) | Export Statuses to YAML. | Document has `match_fields: [id]` (or natural key) — same key the JSON document carries. |
| 7.4 | Directive omitted when key not covered | Export Statuses selecting **only** `color` (omitting `name`/`id`), CSV. | No `# nautobot-import:` directive row is written (the selection can't resolve a match key). |

## 8. Import — launch, data entry & field reference

| # | Test | Steps | Expected |
|---|------|-------|----------|
| 8.1 | Import opens in the modal | Devices list > Actions ▾ > **Import from file**. | The ImportObjects job form opens in `#nautobot-generic-modal` with Content Type (pre-set), **Import Data (CSV/JSON/YAML)** textarea, **Import File (CSV/JSON/YAML)** upload, **Match Existing Records On**, **Rollback Changes on Failure**. |
| 8.2 | Field-reference table | In the import modal, observe (Content Type pre-set to Device). | A table lists Device's importable columns with columns Field / Required / Related Object / Choices / Description; required fields marked with a green check. |
| 8.3 | Field table updates on content-type change | Change Content Type to `circuits \| circuit termination`. | Table repopulates with that model's fields (e.g. `upstream_speed` appears; Device-only fields gone). |
| 8.4 | Paste import — all formats | Paste CSV, then a JSON document, then a YAML document into the Import Data textarea (separate runs), Run each. | Each run auto-detects its format and imports the rows; result modal shows the summary each time. |
| 8.5 | File upload import — all formats | Attach a `.csv`, then a `.json`, then a `.yaml` file (separate runs), Run each. | Each file is read, its format auto-detected, and imported; result modal shows the summary each time. |
| 8.6 | List refresh on close | After a successful import that creates records, close the result modal. | The list view refreshes and shows the newly created/updated objects. |

## 9. Import — upsert semantics (create / update / unchanged)

| # | Test | Steps | Expected |
|---|------|-------|----------|
| 9.1 | Create new | Import a CSV of new Statuses (names not present). Run. | Rows created; summary `created: N, updated: 0, unchanged: 0`. |
| 9.2 | Update existing | Import `name,color` for an existing Status with a changed color, `match_fields=name`. | Record updated in place (no duplicate); summary `updated: 1`; per-row log `Row 1: Updated record "<name>" (color: <old> → <new>)`. |
| 9.3 | Mixed upsert | Import a file where some rows match and some don't. | Summary distinguishes `created` and `updated` counts; both applied in one run. |
| 9.4 | Idempotent re-import | Import a file (9.2), then import the identical file again. | Second run: `created: 0, updated: 0, unchanged: 1`; the record's `last_updated` is unchanged; **no** new ObjectChange is created. |
| 9.5 | Unchanged logging (default) | Run the idempotent re-import (9.4) at default log level. | No INFO log line for the unchanged row; summary line `Left 1 <model> object(s) unchanged (identical data, skipped)`. |
| 9.6 | Unchanged logging (debug) | View the JobResult log filtered to DEBUG. | A DEBUG entry `Row 1: No changes for record "<name>"` is present. |
| 9.7 | Empty result warning | Import a file that matches nothing and creates nothing (e.g. all rows fail). | WARNING `No <model> objects were created or updated`; job reports failure. |

## 10. Import — match fields (resolution & precedence)

| # | Test | Steps | Expected |
|---|------|-------|----------|
| 10.1 | Explicit run parameter | Import with **Match Existing Records On** = `name`. | Records matched on `name`; summary `effective_match_fields: ["name"]`, `match_fields_source: "run parameter"`. |
| 10.2 | File directive (CSV) | Import a CSV whose first line is `# nautobot-import: match_fields=name` and no run param. | Matched on `name`; `match_fields_source: "file directive"`. |
| 10.3 | Document match_fields (JSON) | Import a JSON document with `match_fields: [name]`, no run param. | Matched on `name`; source is the file directive. |
| 10.4 | Document match_fields (YAML) | Import a YAML document with `match_fields: [name]`, no run param. | Matched on `name`; source is the file directive (same document-carried key as JSON). |
| 10.5 | Run param overrides directive | Import a CSV with directive `match_fields=color` but run param `name`. | `name` is used (`match_fields_source: "run parameter"`). |
| 10.6 | Default match key | Import with no param and no directive, `id` column present. | Matched on `id` (`match_fields_source: "default"`). |
| 10.7 | Default missing → create | Import with default match key but a row missing the key value. | Row is created as new (not an error). |
| 10.8 | Non-unique match in file | Import where two rows share the same `match_fields` values. | Clear error naming the ambiguity; import fails (or that row fails) per rollback setting. |
| 10.9 | Multiple existing matches | `match_fields` matches >1 existing record for a row. | Error `Row N: Multiple existing records match on (<fields>); cannot determine which to update`. |

## 11. Import — formats & auto-detection

| # | Test | Steps | Expected |
|---|------|-------|----------|
| 11.1 | CSV import | Import CSV, Format auto. | Parsed as CSV. |
| 11.2 | JSON document import | Import a JSON document, Format auto. | Parsed as JSON; `model`/`match_fields` from document applied. |
| 11.3 | YAML document import | Import a YAML document (`---`/`nautobot_import:`), Format auto. | Auto-detected as YAML from content; imported. |
| 11.4 | Bare JSON array | Import a bare `[ {...}, ... ]` (no document) with Content Type set. | Imports using the form's content type. |
| 11.5 | Model mismatch | Import a document with `model: dcim.device` while Content Type = Status. | Error: the file declares model "dcim.device" but import requested for "extras.status". |
| 11.6 | Unsupported format | Run import with `import_format=xml`. | Fails with `Unsupported import format "xml"`. |

## 12. Import — strictness & related-object resolution

| # | Test | Steps | Expected |
|---|------|-------|----------|
| 12.1 | Unknown field rejected (#6464) | Import a CSV/JSON with a column `my-fav-field` not on the model. | Import fails with an error naming the unrecognized field (`my-fav-field`); nothing silently ignored (Job path). |
| 12.2 | Ambiguous related reference | Import Devices whose `device_type` reference is `{manufacturer: <uuid>}` only (no model). | Error `Row N: device_type: Could not resolve a single DeviceType — manufacturer=<uuid> matches <N> records. Add field(s) that uniquely identify it: any values unique in your data work, and its natural key (manufacturer__name, model) or its \`id\` (UUID) are always unique. …` |
| 12.3 | Related object not found | Import with `status__name=DoesNotExist`. | Error `No Status matches name=DoesNotExist. Reference it by field(s) unique in your data — …natural key (name) or its \`id\` (UUID)… — and check the values are correct.` |
| 12.4 | Related resolved by natural key | Import Devices with `device_type__manufacturer__name` + `device_type__model` set. | device_type resolves uniquely; rows import. |
| 12.5 | DB constraint error is row-scoped | Import a row that triggers a DB uniqueness/IntegrityError not caught by serializer validation. | The whole job does NOT crash; a `Row N: <error>` is logged, `validation_failed` set; remaining rows still process. |
| 12.6 | Rollback on failure | Import with **Rollback Changes on Failure** on and one bad row. | All rows rolled back (`Rolling back all N records.`); nothing persisted; job fails. |
| 12.7 | No-rollback partial | Import with rollback OFF and one bad row mid-file. | Good rows persist; bad row logged; job reports partial failure. |

## 13. Import — M2M & sentinels

*Intended behavior: an empty cell, the `NULL` sentinel, and the `NoObject` sentinel are all equivalent on import — each clears the field/relation to null. (Note: today an empty string on a scalar field is preserved as `""`, not coerced to null; 13.7 verifies whether the equivalence holds and flags any gap.)*

| # | Test | Steps | Expected |
|---|------|-------|----------|
| 13.1 | Scalar M2M import | Import `name,tags` with `tags` = `"a,b"`. | Device gets tags a and b (2 members). |
| 13.2 | Composite M2M via JSON cell | Import the JSON-cell form of `software_image_files` (round-trip of the 6.3 export). | The exact 2 software image files are set. |
| 13.3 | Composite M2M via parallel columns | Import `software_image_files__software_version` + `software_image_files__image_file_name` as parallel comma lists. | Members resolved from paired values. |
| 13.4 | M2M value-count mismatch | Import parallel M2M columns with mismatched counts. | Error `Incorrect number of values provided for the software_image_files field`. |
| 13.5 | `NoObject` sentinel | Import a related field cell = `NoObject`. | The relation is set to null/none for that row (not treated as a literal). |
| 13.6 | `NULL` sentinel | Import a field cell = `NULL`. | The value is set to null/none for that row (parser swaps `NULL` → `None`), matching 13.5's `NoObject` behavior. |
| 13.7 | Empty ≡ `NULL` ≡ `NoObject` | Import the same optional field three ways: empty cell, `NULL`, `NoObject`. | All three clear the field to null (equivalent). Document any divergence (e.g. empty string preserved on a scalar field) as a defect against the intended equivalence. |

## 14. Round-trip

| # | Test | Steps | Expected |
|---|------|-------|----------|
| 14.1 | CSV round-trip (no config) | Export Devices to CSV; re-import the unmodified file with NO parameters. | Imports cleanly as an update (directive supplies the key); summary `unchanged` = row count (idempotent). |
| 14.2 | JSON round-trip | Export to JSON; edit one field; re-import unmodified document. | Only the edited record updates; others `unchanged`. |
| 14.3 | Edited round-trip | Export CSV, change `color` on 2 rows in a spreadsheet, save, re-import. | Exactly those 2 rows `updated` (with diff logged); rest `unchanged`. |
| 14.4 | Full-field vs selected round-trip | Export with `device_type` (relation) selected; re-import. | device_type resolves (natural key present); round-trips cleanly (contrast with 12.2's partial selection). |

## 15. Permissions & access control

| # | Test | Steps | Expected |
|---|------|-------|----------|
| 15.1 | Export requires view perm | As a user WITHOUT `view_<model>`, run the export job. | Job fails: `User "<user>" does not have permission to view <model> objects`; no file. |
| 15.2 | Export button disabled without run perm | As a user who can view the list but cannot run the ExportObjectList job (job not viewable/enabled), open Actions ▾. | **Export to file** renders **disabled** (`disabled`, `aria-disabled="true"`, title `You do not have permission to run this Job.` or `Job is not enabled.`) — not clickable, not hidden. |
| 15.3 | Import button disabled without run perm | Same for **Import from file**. | Rendered disabled with the same title logic. |
| 15.4 | Import needs add/change | As a user with add but not change perm, import a file that would update existing records. | Update rows fail with `Row N: User "<user>" does not have permission to update an object with these attributes`; job reports failure. |
| 15.5 | Update-restricted match is unmatched | As a change-restricted user, import a row matching a record they can't change. | Treated as unmatched → create attempt → surfaces a uniqueness error rather than modifying/exposing the record. |

## 16. REST API CSV backwards-compatibility

| # | Test | Steps | Expected |
|---|------|-------|----------|
| 16.1 | Plain API CSV omits newly-supported composite M2M | `GET /api/dcim/devices/?format=csv` (no `exclude_m2m`). | CSV keeps the historical default subset (`tags`, `content_types`) but **omits** the newly-supported composite-key M2M columns (e.g. no `software_image_files` column) — old consumers see no new columns. |
| 16.2 | API CSV opt-in composite M2M | `GET /api/dcim/devices/?format=csv&exclude_m2m=false`. | Composite-key M2M columns (e.g. `software_image_files`) now included (explicit opt-in). |
| 16.3 | API CSV all-M2M excluded | `GET /api/dcim/devices/?format=csv&exclude_m2m=true`. | All M2M columns removed, including `tags` (performance opt-out). |
| 16.4 | API JSON unaffected | `GET /api/dcim/devices/?format=json`. | Default M2M subset (`tags`, `content_types`, `object_types`) still present as before. |

## 17. Regression / edge cases

| # | Test | Steps | Expected |
|---|------|-------|----------|
| 17.1 | Empty content type in picker | Open the export field control before a content type is resolvable. | Control renders empty (no error). |
| 17.2 | Import with only file, no text | Provide a file but leave the textarea empty. | File is used; import runs. |
| 17.3 | Neither data nor file | Run import with both empty. | Fails: `Either csv_data or csv_file must be provided`. |
| 17.4 | DeviceType single-record import unaffected | Device Types > Actions ▾. | Two import entries: **Import from JSON/YAML (single record)** (full page) and **Import from file (multiple records)** — the single-record path is unchanged by this feature. |
| 17.5 | Custom-field export selection | Export a model with a custom field, selecting `cf_<key>`. | The exported column/JSON contains the custom-field value. |
