# Test Matrix — Configurable Import / Export with Upsert

A naming-convention-driven catalog of the automated tests. **Planning artifact** — stubs carry one-line
docstrings, no bodies. Companion to `trd-csv-import-export.md`, `qa-test-plan-import-export.md`, and
`design-m2m-import-export.md`.

## Key idea: test the shared core once, not per format

The format (CSV/JSON/YAML) is a **thin adapter**; all field-type handling is centralized. So instead of a
`format × field_type` cross-product (~300 cells), we test three layers:

1. **Core** — field-type logic, parametrized over `field_type`, **format-agnostic**. This is the bulk.
2. **Adapter** — each format's serialize/parse, parametrized over `format`, on **one canonical record**,
   asserting all formats converge to the identical core representation.
3. **End-to-end** — a few real-job round-trips per format on a canonical mixed object, to catch wiring.

Format parity then follows from (2)+(3) rather than from running every type through every format.

### Shared functions under test (`foo`)

| Layer | Function(s) — the real `foo` | Direction |
|---|---|---|
| Core repr | serializer CSV `to_representation` (`_get_m2m_natural_key_values`, `_get_natural_key_lookups_value_for_field`, sentinels); job wrapper `ExportObjectList._get_serializer_data` | export |
| Core parse/normalize | `NautobotCSVParser.row_elements_to_data`, `ImportDocumentParserMixin.record_to_data` → both call `nest_flat_dict` | import |
| Core upsert | `ImportObjects._perform_operation` / `_perform_atomic_operation` + `serialize_object` + `shallow_compare_dict` | import |
| Core resolution | `WritableNestedSerializer` / `dict_to_filter_params` (FK/nested/GFK → object) | import |
| Shared flat↔nested | `nest_flat_dict` | both |
| Shared envelope | `build_import_document` / `ImportDocumentParserMixin.unwrap_document` | both |
| Shared match key | `parse_match_fields`, `default_match_fields`, `build_match_filter`, `validate_match_fields`, `validate_match_uniqueness_within_file` | import |
| Format adapters (thin) | `NautobotCSVRenderer` / `NautobotCSVParser.load`; `_build_document_records` + json/yaml dump / `NautobotJSON|YAMLImportParser.load` | both |
| Format detect | `detect_import_format` | import |

## Existing coverage (before stubbing) & QA-plan mapping

Most of this matrix is **already covered** by existing unit tests — the net-new work is a handful of
gaps plus the structural (adapter-convergence) framing. Legend: ✅ covered · ◑ partial · 🆕 gap ·
⏭️ deferred/TBD. "QA §" refers to `qa-test-plan-import-export.md`.

> **Implemented:** this matrix is realized in `nautobot/core/tests/test_import_export.py` (84 tests),
> which consolidates the former `ExportObjectListTest`/`ImportObjectsTestCase` (from `test_jobs.py`),
> the pure-function helpers, and the §16 CSV tests under the matrix naming/layering. The
> "Existing test" column below records where each cell originated before consolidation; the
> lower-level serializer/parser unit tests remain in `test_csv.py`/`test_api.py`.

| Matrix stub / area | QA § | Existing test (pre-consolidation) | Status |
|---|---|---|---|
| `core_export__scalar` | 3.1 | `test_export_all_to_csv` | ✅ |
| `core_export__fk` | 6 | `test_csv_export_related_serializer_methods` (test_csv) | ✅ |
| `core_export__nested` | 3.2 | `test_export_json_document_with_nested_related_fields` | ✅ |
| `core_export__m2m_tags` | 6.1 | `test_tags_export_as_comma_separated_names` (test_csv) | ✅ |
| `core_export__m2m_composite` | 6.3 | `test_composite_m2m_exports_as_json_cell` (test_csv) | ✅ |
| `core_export__m2m_ct` | 6.4 | `test_csv_export_related_serializer_methods` | ◑ |
| `core_export__null_fk_noobject` | 6.5 | `CSVParsingRelatedTestCase` (`NoObject`) | ✅ |
| `core_export__null_scalar_null` | 6.6 | `CSVParsingRelatedTestCase` (`CSV_NULL_TYPE`) | ✅ |
| `core_export__choice` | — | — | 🆕 |
| `core_export__cf` | 17.5 | — | 🆕 |
| `core_export__gfk` | — | — | 🆕 (open Q1) |
| `core_import__fk` / `nested` | 12.4 | `WritableNestedSerializerTest` (test_api) | ✅ |
| `core_import__m2m_*` | 13.1–13.3 | `test_m2m_field_import`, `test_m2m_round_trip_import` (test_csv) | ✅ |
| `core_import__gfk` | — | `test_csv_import_contact_assignment` | ◑ (contact assoc.) |
| `core_import__cf` | — | — | 🆕 |
| `core_import__null_clears_value` / `noobject_clears_fk` | 13.5–13.6 | — | 🆕 |
| `core_upsert__scalar__update` | 9.2 | `test_csv_import_update_logs_field_diff` | ✅ |
| `core_upsert__scalar__unchanged` / `__unchanged_no_objectchange` | 9.4–9.5 | `test_csv_import_unchanged_rows_skipped_idempotently` | ✅ |
| `core_upsert__mixed` | 9.3 | `test_csv_import_upsert_mixed_update_and_create` | ✅ |
| `core_upsert__fk/m2m__update` | 9 | — | 🆕 |
| `nest_flat_dict` / envelope units | — | `NautobotCSVParserTest`, directive round-trips | ◑ (via e2e) |
| `adapter_export__csv/json/yaml` | 3.1–3.3 | `test_export_all_to_csv`, `_json_document`, `_generic_yaml_document` | ✅ |
| `adapter_export__yaml_devicetype_library` | 3.4 | `test_export_devicetype_to_yaml` | ✅ |
| `adapter_import__csv` | — | `NautobotCSVParserTest` | ✅ |
| `adapter_import__json/yaml`, bare list | 11.2–11.4 | `test_json_export_import_round_trip_update`, `test_yaml_bare_list_import` | ✅ |
| `adapter_import__autodetect` | 11 | — | 🆕 |
| `e2e_roundtrip__csv` | 14.1/14.3 | `test_csv_export_import_round_trip_update` | ✅ |
| `e2e_roundtrip__json` | 14.2 | `test_json_export_import_round_trip_update` | ✅ |
| `e2e_roundtrip__yaml` | 14 | — | 🆕 |
| `match_default_id` / `_natural_key` | 10.5–10.6 | `test_csv_import_default_id_match`, `_default_natural_key_upsert` | ✅ |
| `match_param` / `_directive_csv` / `_precedence` | 10.1/10.2/10.5 | `test_csv_import_update_with_match_fields_param`, `_with_file_directive`, `_param_overrides_directive` | ✅ |
| `match_nonunique_dupe_in_file` / `matches_multiple_existing` | 10.8/10.9 | `test_csv_import_update_non_unique_match_in_file`, `_multiple_existing_matches` | ✅ |
| `match_user_unique_ok` / `_composite` / `_missing_value_creates` | 10.6–10.7 | — | 🆕 |
| `scope_full_default` / `_sort` / `_saved_view` | 4.2/4.4/4.5 | `test_export_without_current_view_ignores_filters`, `_current_view_applies_sort`, `_uses_saved_view_export_config` (+5 saved-view variants) | ✅ |
| `scope_saved_view_stale` / `_bad_sort_key` / `_related_and_cf_sort` | 4.6–4.8 | — | 🆕 |
| `select_subset` / `_relation_natural_key` / `_depth_capped` | 2 | `test_export_fields_selection_csv`, `_fields_form_expands_single_fk_relations` | ✅ |
| `select_order_drag` / `_required_marker` / `_m2m_top_level_only` / `_cf` | 2 | — | 🆕 (mostly UI) |
| `mode_create_only_match_exists` | — | — | ⏭️ (open Q2) |
| `sentinel_empty_equiv_null_noobject` | 13.7 | — | ⏭️ (`@expectedFailure`, §13 gap) |
| `value_unicode_and_bom` | — | `test_csv_import_with_utf_8_with_bom_encoding`, `test_parse_directive_with_byte_order_mark` | ✅ |
| `value_special_chars_*` | 6.7 | — | 🆕 |
| `error_unknown_field` | 12.1 | `test_csv_import_unknown_column_rejected`, `test_json_import_unknown_field_rejected` | ✅ |
| `error_model_mismatch` | 11.5 | `test_import_document_model_mismatch` | ✅ |
| `error_db_constraint_row_scoped` | 12.5 | `test_csv_import_bad_row` | ◑ |
| `error_no_data_no_file` | 17.3 | `test_import_without_data` | ✅ |
| `error_unsupported_format` / `_empty_file` / `_ambiguous_reference` / `_related_not_found` | 11.6/12.2/12.3 | — | 🆕 |
| `rollback_on` / `rollback_off` | 12.6/12.7 | `test_csv_import_bad_row` | ◑ |
| `perm_export_requires_view` | 15.1 | `test_export_without_permission`, `_with_constrained_permission` | ✅ |
| `perm_import_create_requires_add` / `_update_requires_change` | 15.4 | `test_csv_import_without_permission`, `_update_without_change_permission` | ✅ |
| `perm_*_button_disabled` / `_restricted_match` | 15.2/15.3/15.5 | dcim `test_list_has_correct_links` (buttons) | ◑ (UI) |
| `rest_json_m2m_subset_unaffected` | 16.4 | api `exclude_m2m` tests (test_api, ipam, dcim) | ✅ |
| `rest_csv_default/_false/_true` | 16.1–16.3 | — | 🆕 (only JSON `exclude_m2m` is unit-tested) |
| `input_cli_*` | — | `test_export_then_import_round_trip` (test_commands) | ✅ |
| import modal UI, field table | 8.1–8.3 | `test_import_objects_ui.py` (integration), `test_export_job_form_modal_renders_field_selector` | ✅ |

**Net-new stubs actually needed (the 🆕/⏭️ rows):** `choice`/`cf`/`gfk` core repr; cf import + sentinel-clears-on-import; fk/m2m *update* diffs; direct `nest_flat_dict`/envelope units; `autodetect`; **`yaml` e2e round-trip**; `user_unique`/`composite`/`missing-value` match cases; `stale saved view`/`bad sort`/`related+cf sort` scope; UI selection cases (drag/required-marker/top-level-M2M/cf); create-only-match (Q2); empty≡null gap (`@expectedFailure`); special-chars; `unsupported_format`/`empty_file`/`ambiguous_reference`/`related_not_found`; explicit rollback on/off; restricted-match perm; **`rest_csv_*` (§16 CSV-specific)**; deferred through-M2M (§12).

## Naming convention

```
test_<layer>_<direction>__<field_type|format>[__<operation>]   # cube layers
test_<area>_<case>                                             # single-axis areas
```

| Segment | Vocabulary |
|---|---|
| `layer` | `core` · `adapter` · `e2e` |
| `direction` | `export` · `import` · `roundtrip` |
| `field_type` | `scalar` · `choice` · `cf` · `fk` · `nested` · `m2m_tags` · `m2m_composite` · `m2m_ct` · `gfk` |
| `format` | `csv` · `json` · `yaml` |
| `operation` | `create` · `update` · `unchanged` · `mixed` |
| `area` | `match` · `scope` · `select` · `mode` · `sentinel` · `error` · `perm` · `rest` · `input` |

---

## Layer 1 — Core (parametrized over field_type, format-agnostic)

### 1a. Export representation

Drive one test method with a `FIELD_TYPE_CASES` table; each case asserts the flat representation
(`_get_serializer_data` / serializer CSV output) for that type. No format involved.

```python
FIELD_TYPE_CASES = ["scalar", "choice", "cf", "fk", "nested",
                    "m2m_tags", "m2m_composite", "m2m_ct", "gfk"]  # gfk: TBD, open Q1

class CoreExportReprTests(TestCase):
    """Serializer flat representation is correct per field type (parametrized)."""

    def test_core_export__scalar(self): ...
    def test_core_export__choice(self):        """Enum → value, not {value,label}."""
    def test_core_export__cf(self):            """cf_<key> column."""
    def test_core_export__fk(self):            """FK → flattened natural-key columns."""
    def test_core_export__nested(self):        """Depth-3 __ columns."""
    def test_core_export__m2m_tags(self):      """Scalar-keyed → comma list."""
    def test_core_export__m2m_composite(self): """Composite-keyed → JSON array."""
    def test_core_export__m2m_ct(self):        """content_types → app_label.model."""
    def test_core_export__gfk(self): ...       # TBD: open Q1
    # sentinels are representation concerns, so they live here too:
    def test_core_export__null_fk_noobject(self): ...
    def test_core_export__null_scalar_null(self): ...
```

### 1b. Import normalize + resolution + upsert

Parse→normalize (`record_to_data`/`row_elements_to_data`) and resolution/diff (`_perform_operation`)
per type, format-agnostic (feed the normalized dict directly, no file text).

```python
class CoreImportResolveTests(TestCase):
    """Normalized record resolves to the right object/value per field type."""

    def test_core_import__scalar(self): ...
    def test_core_import__cf(self): ...
    def test_core_import__fk(self):            """FK resolved from natural-key dict."""
    def test_core_import__nested(self): ...
    def test_core_import__m2m_tags(self): ...
    def test_core_import__m2m_composite(self): ...
    def test_core_import__m2m_ct(self): ...
    def test_core_import__gfk(self): ...       # TBD: open Q1
    def test_core_import__noobject_clears_fk(self): ...
    def test_core_import__null_clears_value(self): ...

class CoreUpsertTests(TestCase):
    """create/update/unchanged detection per type (via _perform_operation)."""

    def test_core_upsert__scalar__create(self): ...
    def test_core_upsert__scalar__update(self):     """diff logged old → new."""
    def test_core_upsert__scalar__unchanged(self):  """No write, no ObjectChange."""
    def test_core_upsert__fk__update(self): ...
    def test_core_upsert__m2m_tags__update(self):   """Declarative set; order-insensitive unchanged."""
    def test_core_upsert__m2m_composite__update(self): ...
    def test_core_upsert__mixed(self):              """create + update + unchanged in one batch."""
    def test_core_upsert__unchanged_no_objectchange(self): ...
```

### 1c. Shared pure helpers (direct unit tests)

```python
class NestFlatDictTests(SimpleTestCase):
    def test_core_nest__flat_to_nested(self): ...
    def test_core_nest__nested_passthrough(self): ...
    def test_core_nest__sentinels(self):       """NoObject/NULL handled."""
    def test_core_nest__m2m_list(self): ...

class ImportDocumentTests(SimpleTestCase):
    def test_core_document__build(self):       """build_import_document shape/order."""
    def test_core_document__unwrap(self):      """unwrap_document splits metadata/records."""
    def test_core_document__unwrap_bare_list(self): ...
    def test_core_document__unwrap_bad_version(self): ...
```

---

## Layer 2 — Format adapters (parametrized over format, one canonical record)

Prove each format faithfully serializes/parses a single canonical mixed record, and that all three
converge to the **identical** core dict. This is where format count lives — and it's ~2 per format.

```python
CANONICAL = {...}  # one record touching scalar, fk, nested, m2m_tags, m2m_composite, m2m_ct, sentinels

class ExportAdapterTests(TestCase):
    def test_adapter_export__csv(self):   """Flat dict → CSV → reparse → equals core dict."""
    def test_adapter_export__json(self):  """Flat dict → document → equals reshaped core dict."""
    def test_adapter_export__yaml(self): ...
    def test_adapter_export__yaml_devicetype_library(self): """Device Type YAML special-case format."""

class ImportAdapterTests(TestCase):
    def test_adapter_import__csv(self):   """CSV text → normalized dict == canonical."""
    def test_adapter_import__json(self): ...
    def test_adapter_import__yaml(self): ...
    def test_adapter_import__autodetect(self): """detect_import_format picks the right parser."""
    def test_adapter_import__flat_keys_in_json(self): """Flat __ keys inside JSON still nest."""
```

---

## Layer 3 — End-to-end round-trip (parametrized over format)

A handful of real-job runs on a canonical object covering all types, per format — integration only.
Beyond the per-format canonical round-trip, a few **explicit type×format pins** guard the gnarliest
integration paths (where the adapter and a specific type interact non-trivially).

```python
class RoundTripE2ETests(TestCase):
    # per-format canonical (all types in one object)
    def test_e2e_roundtrip__csv(self):        """Export → re-import unmodified → all unchanged. QA 14.1/14.3 ✅ (test_csv_export_import_round_trip_update)."""
    def test_e2e_roundtrip__json(self):       """QA 14.2 ✅ (test_json_export_import_round_trip_update)."""
    def test_e2e_roundtrip__yaml(self):       """QA 14. 🆕 — no existing YAML e2e round-trip."""
    def test_e2e_roundtrip__csv_edited(self): """Edit N rows → exactly N updated. QA 14.3."""

    # explicit high-risk type×format pins (not left to structural parity alone)
    def test_e2e_pin__csv_m2m_composite(self):  """JSON-in-a-CSV-cell quoting survives Excel-style round-trip. QA 6.3/13.2."""
    def test_e2e_pin__csv_special_chars(self):  """Comma/quote/apostrophe in a composite M2M member (St. John's). QA 6.7."""
    def test_e2e_pin__json_nested(self):        """Depth-3 nested FK sub-objects resolve on import. QA 3.2/12.4."""
    def test_e2e_pin__yaml_m2m_composite(self): """Composite M2M through YAML load/dump. QA 6.3."""
    def test_e2e_pin__csv_gfk_contact(self):    """GFK (contact assignment) round-trip. ◑ extends test_csv_import_contact_assignment."""
```

---

## Single-axis areas (not part of the cube — no format multiplication)

These already vary on one axis; they don't multiply by field type or format.

```python
class MatchKeyTests(TestCase):
    def test_match_default_id(self): ...
    def test_match_default_natural_key(self): ...
    def test_match_param(self): ...
    def test_match_directive_csv(self): ...
    def test_match_document(self):            """JSON/YAML metadata match_fields (adapter-shared)."""
    def test_match_precedence_param_over_file(self): ...
    def test_match_composite(self): ...
    def test_match_db_unique(self): ...
    def test_match_user_unique_ok(self):      """Non-DB-unique but unique in data → matches."""
    def test_match_nonunique_dupe_in_file(self): ...
    def test_match_matches_multiple_existing(self): ...
    def test_match_missing_value_creates(self): ...

class ExportScopeTests(TestCase):
    def test_scope_full_default(self): ...
    def test_scope_filter(self): ...
    def test_scope_sort(self): ...
    def test_scope_saved_view(self): ...
    def test_scope_saved_view_stale(self): ...
    def test_scope_bad_sort_key(self): ...
    def test_scope_related_and_cf_sort(self): ...

class ExportFieldSelectionTests(TestCase):
    def test_select_all_default(self): ...
    def test_select_subset(self): ...
    def test_select_relation_natural_key(self): ...
    def test_select_partial_nested(self): ...
    def test_select_order_drag(self): ...
    def test_select_cf(self): ...
    def test_select_required_marker(self): ...
    def test_select_m2m_top_level_only(self): ...
    def test_select_depth_capped_at_3(self): ...

class ImportModeTests(TestCase):
    def test_mode_upsert_match_updates(self): ...
    def test_mode_create_only_nomatch_creates(self): ...
    @skip("Open Q2: create-only + existing match behavior undefined")
    def test_mode_create_only_match_exists(self): ...

class SentinelValueTests(TestCase):
    # representation sentinels are in Layer 1; these are the value-fidelity edges
    @expectedFailure  # §13 note: empty not coerced to null on non-nullable CharField
    def test_sentinel_empty_equiv_null_noobject(self): ...
    def test_value_special_chars_scalar(self): ...
    def test_value_special_chars_m2m_member(self): ...
    def test_value_unicode_and_bom(self): ...

class ImportErrorTests(TestCase):
    def test_error_unknown_field(self):        """#6464."""
    def test_error_related_not_found(self): ...
    def test_error_ambiguous_reference(self): ...
    def test_error_model_mismatch(self): ...
    def test_error_unsupported_format(self): ...
    def test_error_db_constraint_row_scoped(self): ...
    def test_error_empty_file(self): ...
    def test_error_no_data_no_file(self): ...

class RollbackTests(TestCase):
    def test_rollback_on_all_or_nothing(self): ...
    def test_rollback_off_partial(self): ...

class PermissionTests(TestCase):
    def test_perm_export_requires_view(self): ...
    def test_perm_export_button_disabled_without_run(self): ...
    def test_perm_import_button_disabled_without_run(self): ...
    def test_perm_import_create_requires_add(self): ...
    def test_perm_import_update_requires_change(self): ...
    def test_perm_import_change_restricted_match_unmatched(self): ...

class RestApiCsvTests(TestCase):
    def test_rest_csv_default_keeps_subset_omits_composite(self): ...
    def test_rest_csv_exclude_m2m_false_includes_composite(self): ...
    def test_rest_csv_exclude_m2m_true_removes_all(self): ...
    def test_rest_json_m2m_subset_unaffected(self): ...

class ManagementCommandTests(TestCase):
    def test_input_cli_export(self): ...
    def test_input_cli_import_autodetect(self): ...
    def test_input_cli_import_match_fields(self): ...
```

---

## Deferred — general M2M (see `design-m2m-import-export.md`)

```python
class DeferredM2MTests(TestCase):
    @skip("Deferred: picker does not offer read-only through-M2M")
    def test_core_export__m2m_through_join(self):   """VLAN.locations exportable."""
    @skip("Deferred: import cannot write through-model M2M")
    def test_core_import__m2m_through_join(self):    """VLAN.locations round-trips (Phase 2)."""
    @skip("Deferred: data-carrying through not representable by member NK")
    def test_core_import__m2m_through_data_warns(self): """SecretsGroup.secrets warned & skipped."""
```

---

## Open questions blocking specific cells

1. **GFK** (`*__gfk`) — which model exposes an importable GFK, and how is it represented (content-type +
   natural key? two columns)? Is import supported today, or behavior-TBD?
2. **Create-only + existing match** (`test_mode_create_only_match_exists`) — error, skip, or duplicate?
3. **Empty ≡ NULL ≡ NoObject** (`test_sentinel_empty_equiv_null_noobject`) — `@expectedFailure` until the
   coercion gap is closed in code.
4. **Deferred M2M** — keep `@skip` placeholders; activate per the design-note phases.
