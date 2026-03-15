# Custom Fields Cleanup Policy

Custom Field data can become inconsistent over time as definitions and policies evolve. Some examples include:

- Validation rules may change, select choices may be added or removed, or defaults may be introduced after data has already been stored.
- Scoping rules can also change — a field that once applied broadly may later apply only to specific device types, roles, or tenants.
- Inconsistencies can also arise from bulk imports, API writes, legacy data migrations, or manual database edits that bypass validation logic.

The cleanup process evaluates stored Custom Field data against current definitions and scoping rules, correcting inconsistencies. The goal is to align Custom Fields data with the latest configuration, making changes only when necessary.

The job will run and end up in one of the following conditions for each record.

1. No change
1. Log failure
1. Set to default
1. Set to empty value
1. Delete key

!!! warning
    The job will destruct, mutate, or otherwise change the data, do not run the job unless you understand the risk, review the output from a dry-run, and reviewed the data that will be change.

## Cleanup Decision Tree

The flow diagram shows how each field evaluation results in one of the defined outcomes. When running the job in safe mode, destructive actions (red paths) are skipped. In dry-run mode, no changes are committed, only the evaluation is performed. The diagram represents the full process when both safe mode and dry-run are disabled. Paths highlighted in purple or labeled "Log Failure" indicate validation issues that require manual correction, as the job cannot resolve them automatically.

```mermaid
flowchart TD
    %% =====================
    %% MAIN FLOW
    %% =====================

    cf_exists{CustomField exists?}
    cf_exists -- No --> orphan_delete[Delete key]
    cf_exists -- Yes --> in_scope{Field in scope?}

    %% OUT OF SCOPE BRANCH
    in_scope -- No --> oos_key_exists{Key exists?}
    oos_key_exists -- No --> oos_provision[Set to empty value]
    oos_key_exists -- Yes --> oos_value_empty{Value empty?}
    oos_value_empty -- Yes --> oos_noop[No change]
    oos_value_empty -- No --> oos_nullify[Set to empty value]

    %% IN SCOPE BRANCH
    in_scope -- Yes --> key_exists{Key exists?}

    %% KEY MISSING
    key_exists -- No --> missing_has_default{Default exists?}
    missing_has_default -- Yes --> missing_set_default[Set to default]
    missing_has_default -- No --> missing_required{Required?}
    missing_required -- Yes --> missing_set_empty_and_log[Set to empty value &<br>Log failure]
    missing_required -- No --> missing_set_empty[Set to empty value]

    %% KEY EXISTS
    key_exists -- Yes --> value_state{Value state?}

    value_state -- valid --> valid_noop[No change]

    value_state -- empty --> empty_req_and_default{Required and default?}
    empty_req_and_default -- Yes --> empty_set_default[Set to default]
    empty_req_and_default -- No --> empty_noop[No change]

    value_state -- invalid type --> wrong_type_has_default{Default exists?}
    wrong_type_has_default -- Yes --> wrong_type_set_default[Set to default]
    wrong_type_has_default -- No --> wrong_type_required{Required?}
    wrong_type_required -- Yes --> wrong_type_log_failure[Log failure]
    wrong_type_required -- No --> wrong_type_set_empty[Set to empty value]

    value_state -- fails validation --> invalid_log_failure[Log failure]

    %% =====================
    %% COLOR DEFINITIONS
    %% =====================

    classDef noop fill:#e6f4ea,stroke:#2e7d32,stroke-width:2px;
    classDef safe fill:#fff8e1,stroke:#f9a825,stroke-width:2px;
    classDef destructive fill:#fdecea,stroke:#c62828,stroke-width:2px;
    classDef log fill:#f3e5f5,stroke:#6a1b9a,stroke-width:2px;

    %% Apply styles to flow nodes
    class oos_noop,valid_noop,empty_noop noop;
    class oos_provision,missing_set_default,missing_set_empty,missing_set_empty_and_log,empty_set_default safe;
    class orphan_delete,oos_nullify,wrong_type_set_default,wrong_type_set_empty destructive;
    class wrong_type_log_failure,invalid_log_failure log;
```

```mermaid
flowchart TD
    %% =====================
    %% LEGEND (RIGHT)
    %% =====================

    subgraph Legend
        direction TB
            L1[No change]
            L2[Safe mutation<br/>inject default or empty]
            L3[Destructive mutation<br/>overwrite or delete]
            L4[Log failure]
        end
        style Legend fill:transparent,stroke-width:1px


    %% =====================
    %% COLOR DEFINITIONS
    %% =====================
    classDef noop fill:#e6f4ea,stroke:#2e7d32,stroke-width:2px;
    classDef safe fill:#fff8e1,stroke:#f9a825,stroke-width:2px;
    classDef destructive fill:#fdecea,stroke:#c62828,stroke-width:2px;
    classDef log fill:#f3e5f5,stroke:#6a1b9a,stroke-width:2px;

    %% LEGEND STYLES
    class L1 noop;
    class L2 safe;
    class L3 destructive;
    class L4 log;
```

The decision tree above covers many scenarios. The following sections break down each possible outcome in detail.

## No Change

The stored value is preserved exactly as-is.

This occurs when:

- The field exists, is in scope, and the value is valid.
- The value is empty and not required.
- The field is out of scope and already empty.

## Log Failure

No data is modified, but a validation issue is recorded.

This occurs when:

- A required field is missing and no default exists.
- A required field has an invalid type and no default exists.
- A required field fails validation rules, such as min/max, regex, or select value.

The job does not attempt to repair required fields without a default. Manual correction is required.

## Set to Default

The existing value (or missing key) is replaced with the field’s configured default.

This occurs when:

- A field is in scope and missing, and a default exists.
- A field is in scope and empty, required, and has a default.
- A field has an invalid type and a default exists.
- A multiselect becomes empty after filtering and a default exists.

The previous value is overwritten.

!!! note
    Setting a default value is considered safe only when the key is missing from the record.

## Set to Empty Value

The field is set to its normalized empty value:

- None for scalar fields
- [] for lists
- {} for dicts

This occurs when:

- A field is not in scope but contains a non-empty value.
- A field is in scope, optional, missing, and has no default.
- A field has an invalid type, is optional, and has no default.

If the key did not previously exist, it may be created with an empty value depending on configuration.

!!! note
    Setting an empty value is considered safe only when the key is missing from the record.

## Delete Key

The key is removed entirely from _custom_field_data.

This occurs when:

- The Custom Field definition no longer exists.

This removes both the key and its stored value.
