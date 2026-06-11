# Nautobot v3.2

This document describes all new features and changes in Nautobot 3.2.

## Upgrade Actions

### Administrators

#### Migrate Job Execution and Scheduled Jobs

This release introduces a behavioral change to job execution APIs. The `job_kwargs` parameter is now required for the following functions: `create_schedule`, `enqueue_job`, `execute_job` and `run_job_for_testing`.

Previously, job arguments could be omitted or passed implicitly. This behavior is deprecated and will be removed in a future release. A temporary backward-compatible fallback remains in place but will emit warnings when used.

Action Required:

1. Update all job invocations to explicitly pass `job_kwargs` (e.g `job_kwargs={}`)
2. Recreate all Scheduled jobs which has `kwargs=None`, because now may fail at runtime due to stricter validation.

!!! tip
Treat any warnings `"Using deprecated **job_kwargs pattern, please instead switch to passing job_kwargs as a single parameter"` as indicators that your code should be updated to the new explicit pattern.

## Release Overview

### Breaking Changes

TODO

### Added

#### Object Metadata UI

`ObjectMetadata` records can now be created, edited, and deleted directly through the web UI (previously read-only). Metadata is added from the parent object's **Metadata** tab, which opens a pre-filled create form. The value input adapts to the selected `MetadataType` data type, and detail/list views render values appropriately for each type — clickable links for URLs, parsed HTML for Markdown, pretty-printed JSON for JSON, etc. The primary intent is still that metadata is managed by integrations (SSoTs, REST API), but users with the appropriate permissions can now manage individual records through the UI.

### Changed

TODO

### Dependencies

TODO

<!-- pyml disable-num-lines 2 blanks-around-headers -->

<!-- towncrier release notes start -->
