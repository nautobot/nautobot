# Importing and Exporting Objects

Nautobot can export any list of objects to a file and import objects back from a file, in **CSV**, **JSON**, or **YAML** formats. Imports support create only mode as well as update (or upsert) mode, in which you can match on a user definable field.

Both actions are accessible every object list view under the **Actions ▾** menu and are driven by two system Jobs, surfaced on :

- **Export to file** — runs the `Export Object List` job.
- **Import from file** — runs the `Import Objects` job.

Because they are Jobs, you need the *run* permission for them in addition to the relevant model permissions (see [Permissions](#permissions)), and each run produces a Job Result with a full log.

## Exporting

From any supported list view, choose **Actions ▾ → Export to file**. The Export job opens in a modal where you choose the format, optionally pick and order the fields, and optionally scope the export to what you are currently filter and sort criteria. When the job finishes, the result modal downloads the file automatically and offers a **Download** button.

### Choosing a format

| Format | What you get |
|--------|--------------|
| **CSV** | One header row of field paths, one row per object. UTF-8 with a leading BOM (opens cleanly in Excel). The first line is a `# nautobot-import:` directive (see [The self-describing file](#the-self-describing-file)). |
| **JSON** | A metadata *document* wrapping a list of records with related fields nested (see [Automatic nesting](#automatic-nesting)). |
| **YAML** | The same document as JSON, in YAML. For **Device Types** specifically, YAML produces the [devicetype-library](https://github.com/nautobot/devicetype-library)-compatible format instead. |
| **Auto** | Uses the saved view's configured format if you are on a saved view, otherwise CSV. |

### Selecting fields to export

The **Fields to Export** control lets you choose exactly which fields end up in the file, and in what order.

- **Leave everything unchecked to export every field.**
- Check individual fields to export only those, and **drag the top-level rows** to set the column order (nested fields move with their parent).
- Related objects are shown as expandable rows. Expanding a relation reveals its own fields, nested up to **three** levels deep (for example `device_type` → `device_type__manufacturer` → `device_type__manufacturer__name`).
- **Selecting a relation itself** (e.g. `device_type`) exports that object's **natural key** — the minimal set of columns that uniquely identifies it (`device_type__manufacturer__name` and `device_type__model`).
- Selecting *specific* child fields of a relation (e.g. only `device_type__model`) exports just those columns. Choosing the parent and choosing its children are mutually exclusive — picking children unchecks the parent, and re-checking the parent clears the children.
- Many-to-many fields (like `tags`) are offered only at the top level, not nested under another relation.
- Fields that are required to create the object on import are marked with a red asterisk (`*`).

!!! tip
    If you select only *some* of a relation's natural-key columns, the resulting file may not be able to resolve that relation on import. Prefer selecting the whole relation (its natural key) unless you specifically don't need it to round-trip or know that data is uniquly identfiable in your environment.

### Scoping with "Use Current View"

By default an export includes **every** object of that type, in the model's default order — regardless of any filtering you have applied to the list. To export just a subset:

1. Filter (and optionally sort) the list the way you want.
2. Open **Export to file** and tick **Use Current View**.
3. Run.

The export then reflects the current **filters** and **sort** order and — on a **saved view** — its saved field selection and format as well. Anything you set explicitly in the form (a format, a field selection) still takes precedence over the saved view's configuration.

A stale or deleted saved-view reference is handled gracefully (the export falls back to a full export rather than erroring), and a sort on a column that can't be sorted (for example a computed column) is ignored — the export still succeeds in default order.

## The self-describing file

Every export records *how it should be re-imported* — specifically, which field(s) identify an existing record (the **match key**). This is what lets you export, edit, and re-import with zero configuration.

- **CSV** carries the match key in a directive on the first line:

    ```csv
    # nautobot-import: match_fields=name
    name,description
    Cisco,Cisco Systems
    ```

- **JSON / YAML** carry it in the document metadata:

    ```yaml
    nautobot_import: "1"
    model: dcim.manufacturer
    match_fields: [name]
    records:
      - name: Cisco
        description: Cisco Systems
    ```

By default the match key is the object's `id` column (if present) or, failing that, the model's **natural key** — both of which are guaranteed unique, so matches are unambiguous.

### Choosing your own match key — but you own the uniqueness

You can override the match key by setting **Match Existing Records On** in the import form (the `match_fields` run parameter) or by editing the directive/metadata in the file. This is powerful — you can key on any field(s) meaningful to your data, such as a device name, serial number, or an asset tag which are not guaranteed to be unique from the data model perspective.

The catch: **if you pick your own match key, you are responsible for its uniqueness.** Nautobot does not require your chosen fields to be backed by a database uniqueness constraint. If two rows in your file share the same match values you'll get a clear "does not uniquely identify each row" error, and if your match values happen to match more than one existing object the import will refuse that row rather than guess. When in doubt, key on the natural key or `id`, which are always safe.

The precedence, highest to lowest, is:

1. the `match_fields` **run parameter** (what you type in the form),
2. the **file's** own directive / metadata, then
3. the **default** (`id` if present, otherwise the natural key).

## Automatic nesting

Related objects are represented differently per format, but always by their **natural key** (never by internal UUIDs), so files stay human-readable and portable between systems.

- **CSV** flattens relations into `__`-joined columns: `device_type__manufacturer__name`, `device_type__model`. On import these are automatically re-nested and resolved back to the related object.
- **JSON / YAML** nest relations as sub-objects:

    ```yaml
    - name: core-router-01
      device_type:
        manufacturer:
          name: Cisco
        model: ISR4331
      status:
        name: Active
    ```

Both representations are accepted on import, you can hand-write flat `__` columns in a YAML file if you prefer, and they'll be nested for you.

**Many-to-many** fields are represented by their members' natural keys. Today:

- Members with a single-value natural key (e.g. `tags`, or route targets) export as a comma-separated list: `"tag-a,tag-b"`.
- Members with a composite natural key (e.g. `software_image_files`) export as a JSON array of natural-key objects in a single cell.
- `content_types` / `object_types` export as `app_label.model` strings (e.g. `dcim.device`).

!!! note
    Many-to-many support in import/export is still being expanded. Some relationships that are managed through association tables (for example a VLAN's `locations`) may not yet appear as selectable columns or round-trip on import. Use the REST API for those until fuller support lands.

**Empty and null values** use two sentinels so that "no related object" round-trips unambiguously:

- `NoObject` — the related object is absent (a null foreign key).
- `NULL` — a scalar field whose value is null.

## Importing

Choose **Actions ▾ → Import from file**, then either paste the data into the **Import Data** box or upload a file. The format is auto-detected from the content (or the file extension); you can also force it. A field-reference table in the modal lists every importable column for the selected content type, whether it's required, and what each expects.

Each record is matched against existing objects using the [match key](#the-self-describing-file):

- **No match → create.** A new object is created (requires *add* permission).
- **Match with changes → update in place.** The existing object is updated (requires *change* permission). Each changed field is logged as `field: old → new`.
- **Match with no changes → unchanged.** The row is skipped entirely — **no write and no change-log entry** — and counted as `unchanged`. Re-importing an unmodified file is therefore fully idempotent. (Per-row "no change" messages are logged only at DEBUG level.)

The Job Result summarizes how many objects were created, updated, and left unchanged.

### Rolling back on failure

The **Rollback Changes on Failure** toggle controls what happens when a row fails validation:

- **On** — the entire import is wrapped in a transaction; if any row fails, *all* rows are rolled back and nothing is persisted.
- **Off** — good rows are committed and bad rows are reported individually; the job reports a partial failure.

Either way, unrecognized columns/fields are rejected up front with an error that names the offending field (rather than being silently ignored), and a database error on one row does not crash the whole job.

## Round-tripping

Because exports are self-describing, the common workflows need no configuration:

- **Bulk edit** — export to CSV, edit values in a spreadsheet, re-import. Only the rows you changed are updated; the rest are reported as unchanged.
- **Clone/seed between environments** — export from one Nautobot, import into another. Relations resolve by natural key as long as the referenced objects exist in the target.

## REST API and CSV compatibility

Requesting `?format=csv` on a REST API list endpoint follows the same representation rules, with backwards-compatible many-to-many handling controlled by the `exclude_m2m` query parameter:

| Request | Many-to-many columns |
|---------|----------------------|
| `?format=csv` (default) | Only the historical default subset — `tags`, `content_types`, `object_types` — is included. Other M2M fields (e.g. `software_image_files`) are omitted, so existing consumers see no new columns. |
| `?format=csv&exclude_m2m=false` | All many-to-many fields are included (opt-in), matching what the **Export to file** job produces. |
| `?format=csv&exclude_m2m=true` | All many-to-many fields are excluded, including `tags`. |

JSON/GraphQL responses are unaffected and continue to include the default M2M subset as before.

## Permissions

| Action | Permissions required |
|--------|----------------------|
| Export | Run permission for the `Export Object List` job, plus *view* permission on the model. |
| Import (create rows) | Run permission for the `Import Objects` job, plus *add* permission on the model. |
| Import (update rows) | Run permission for the `Import Objects` job, plus *change* permission on the model. |

The **Export to file** / **Import from file** menu items render as disabled (not hidden) for users who lack the job's run permission or when the job is disabled.
