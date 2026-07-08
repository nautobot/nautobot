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

### App Developers

#### Migrate Cable Termination Queries

To support [breakout cables](../user-guide/feature-guides/breakout-cables.md), the association between a [`Cable`](../user-guide/core-data-model/dcim/cable.md) and its terminations has been re-implemented. The `cable` `ForeignKey` that previously existed on each `CableTermination` subclass (`Interface`, `FrontPort`, `RearPort`, `CircuitTermination`, `PowerPort`, etc.) has been removed in favor of a new [`CableToCableTermination`](../user-guide/core-data-model/dcim/cabletocabletermination.md) join model, exposed on each termination via the `cable_termination` reverse one-to-one relationship. App and Job code that queries or traverses cables may need to be updated.

**The `cable` attribute is preserved** as a read-only property on each termination instance (e.g. `interface.cable`), so attribute access continues to work. Assignments to `Cable.termination_a` / `Cable.termination_b` (and their `*_type` / `*_id` counterparts) on **unsaved** `Cable` instances also continue to work and are materialized into `CableToCableTermination` rows on save.

**ORM queries** filtering CableTermination subclasses by `cable` are automatically translated to the new `cable_termination__cable[...]` paths, emitting a `DeprecationWarning` for each. The following patterns are translated:

| Deprecated | Translated to |
|------------|---------------|
| `Interface.objects.filter(cable=...)` | `cable_termination__cable=...` |
| `.filter(cable=None)` | `cable_termination__isnull=True` |
| `.filter(cable_id=...)`, `.filter(cable__isnull=...)`, `.filter(cable__<lookup>=...)` | `cable_termination__cable...` equivalents |
| `.select_related("cable")`, `.select_related("cable__<field>")` | `cable_termination__cable...` equivalents |

The following patterns are **not** translated and will break — rewrite them explicitly:

| Not translated | Use instead |
|----------------|-------------|
| `Q(cable=...)` | `Q(cable_termination__cable=...)` |
| `.order_by("cable")` | `.order_by("cable_termination__cable")` |
| `.values("cable")` / `.values_list("cable")` | `cable_termination__cable` |

**Querying `Cable` by its terminations:** in the same way, the legacy `termination_a_type` / `termination_a_id` (and b-side) fields are no longer database columns on `Cable` — the terminations now live on the `terminations` (`CableToCableTermination`) relation. `Cable.objects` translates lookups using the old `*_type` / `*_id` names into the equivalent `terminations__...` join paths (constrained to connector 1 to match the properties), emitting a `DeprecationWarning` for each, so `Cable.objects.filter(...)`, `.get(...)`, and `.get_or_create(...)` continue to work for legacy callers. The lookup half is translated by the queryset and, for `get_or_create()`, the same kwargs flow through `Cable(...)` and are materialized into `CableToCableTermination` rows on save.

| Deprecated | Translated to |
|------------|---------------|
| `Cable.objects.get(termination_a_type=<ct>, termination_a_id=<pk>)` | `terminations__<fk>_id=<pk>` with `terminations__cable_end="A"` |
| `.filter(termination_a_id=<pk>)` (no `_type` given) | `<pk>` matched against every per-type termination FK |
| `Cable.objects.get_or_create(termination_a_type=..., termination_a_id=..., ...)` | lookup translated as above; creation flows through `Cable(...)` |

The following are **not** translated — rewrite them against the `terminations` relation explicitly:

| Not translated | Use instead |
|----------------|-------------|
| `Q(termination_a_id=...)`, `.order_by("termination_a_id")`, `.values("termination_a_id")` | `terminations__...` equivalents |
| transformed lookups, e.g. `.filter(termination_a_id__in=[...])` | `terminations__<fk>_id__in=[...]` with `terminations__cable_end="A"` |
| `.exclude(termination_a_id=..., termination_b_id=...)` combining **both** ends | separate `.exclude()` calls, or an explicit `terminations__...` `Q`. The shim applies each end independently (`exclude(A) AND exclude(B)`), which is **not** equivalent to negating the combined condition, because the A-side and B-side match different `CableToCableTermination` rows. Single-end `exclude()` is exact. |

!!! warning
    Queries using `termination_[a|b]_[id|type]` **only match the first connector on each side of a Cable by design**. Code that needs to support any additional connectors on a breakout cable **must** use the new access patterns.

**Cable paths:** the private `_path` `ForeignKey` on `PathEndpoint` has been replaced with a `cable_paths` `GenericRelation` (resolving through `CablePath.origin`). The public `path`, `trace()`, and `connected_endpoint` accessors are unchanged. Rewrite any `_path__...` query usages as `cable_paths__...`; because this is now a multi-row reverse relation (one `CablePath` per breakout lane), `distinct()` is typically required on `filter()` / `count()` / `exclude()`.

**Other notes:**

* The private `_cable_peer`, `_cable_peer_type`, and `_cable_peer_id` cache fields have been removed from `CableTermination`. The public peer accessors (`get_cable_peer()`, REST `cable_peer` / `cable_peer_type`, GraphQL `cable_peer_*`) are unchanged; `get_cable_peer()` now accepts an optional `peer_connector` argument for breakout-lane-specific lookups.
* New helpers are available for working with multi-termination cables: `Cable.add_termination(termination, cable_end, connector=1)`, the typed many-to-many reverse accessors on `Cable` (`cable.interfaces`, `cable.front_ports`, etc.), the singular `cable_termination` reverse accessor on each termination, and `PathEndpoint.get_connected_endpoints()` (returning the resolved destinations of all cable paths, one per breakout lane).

## Release Overview

### Breaking Changes

#### Cable Data Model Changes

To support breakout cables (see below), the way a [`Cable`](../user-guide/core-data-model/dcim/cable.md) associates to its terminations has changed. The `cable` `ForeignKey` previously present on each `CableTermination` (`Interface`, `FrontPort`, etc.) has been replaced by a new [`CableToCableTermination`](../user-guide/core-data-model/dcim/cabletocabletermination.md) join model, allowing a cable to have more than two terminations. Similarly, the `Cable.termination_a` and `Cable.termination_b` `GenericForeignKey` fields have been similarly migrated to use the reverse-foreign-key-relation `Cable.terminations` to `CableToCableTermination` records.

Backward-compatibility shims are provided for the most common access patterns (including ongoing support for the REST API and UI query parameters `?termination_a_type=`, `?termination_a_id=`, etc.), but App and Job authors who interact with cables programmatically may need to make updates to support the updated data model. See [Upgrade Actions for App Developers](#app-developers) above for details.

### Added

#### Breakout Cables

Nautobot now models [breakout cables](../user-guide/feature-guides/breakout-cables.md) — multi-lane cable assemblies where a single physical cable splits into multiple individual connections (for example a 400G QSFP-DD port broken out into 4×100G SFP lanes). A new [`CableType`](../user-guide/core-data-model/dcim/cabletype.md) model defines the physical structure of a cable (connectors per side, internal lanes, and the connector-to-lane mapping), and a [`Cable`](../user-guide/core-data-model/dcim/cable.md) assigned a breakout cable type may have more than two terminations, each recorded as a [`CableToCableTermination`](../user-guide/core-data-model/dcim/cabletocabletermination.md). Breakout cables are fully supported across the UI (cable type and cable forms, connection tables, SVG lane-mapping and trace diagrams), the REST API, and lane-aware cable path tracing. `Interface` records gain an optional [`breakout_position`](../user-guide/core-data-model/dcim/interface.md) field to map a subinterface to a position on its parent interface's breakout trunk connector.

#### Partially-Connected, Disconnected, and Repurposed Cables

A [`Cable`](../user-guide/core-data-model/dcim/cable.md) is no longer required to have both of its endpoints defined, and its terminations are no longer fixed at creation time. A cable may now be partially-connected (a termination on only one side, or on a subset of a breakout cable's connectors) or fully-disconnected (no terminations at all), and a cable's terminations may be added, changed, or removed after the cable is created — through the UI, the REST API, or programmatically — without deleting and recreating the cable.

#### IP Address Ranges

A new [`IPAddressRange`](../user-guide/core-data-model/ipam/ipaddressrange.md) model represents a contiguous span of IP addresses within a parent Prefix without creating an individual `IPAddress` record for each address in the span. Views include standard (list, detail, edit, delete), "IP Address Ranges" tab on the Prefix detail view, and inline rendering of ranges within the Prefix "IP Addresses" tab.

`IPAddress.clean()` now rejects addresses that fall within an exclusive range, `Prefix.clean()` rejects network edits that would orphan a contained range, and Prefix saves reparent contained ranges to the closest fully-containing Prefix. Utilization calculations of the Prefix is consumed when mark as utilized is set.

!!! tip
    Setting exclusive may change your workflow, such as expecting to be able to create an IP address that happens to fall into an exclusive IP Range. This is as designed, but may be surprising if the implications of setting this feature was not considered.

#### Job Cancel

Jobs that are running, pending, or abandoned, can now be cancelled, from both the US and REST API with backend-agnostic strategies for Celery and Kubernetes. You will not be able to see a Job Cancel button on the job run or job result page (for jobs not in a terminal state.)

The Job Cancel will perform slightly different actions depending on current state, all of which end up with the Job ending up in a terminal state. For technical details refer to the documentation for [Job cancel](../user-guide/platform-functionality/jobs/job-revocation.md).

Job Cancel requires the `extras.run_job` permission: non-staff users may revoke only jobs they submitted, while staff users may revoke any user's jobs.

#### Homepage Stickiness

The homepage now saves the location and collapsing of each panel. You can re-arrange them to your liking, and see it the same on any browser. The four column system sanely orders the panels as you collapse to three, two, or one column.

#### Modules Hierarchy

Module Bays and modular components (Interfaces, Front Ports, etc.) now set the root device at every level in the hierarchy, and the default sort ordering of modular component models was changed to `device_id`, `module_id`, `_name` for performance reasons.

#### Search Enhancements

The header search bar gains two distinct capabilities. First, model-name typeahead: as you type an `in:` phrase, matching model names are suggested (e.g. typing `in:dev` suggests `in:device`). Second, once you begin searching, live results appear as you type, showing up to the first 10 matches.

#### Object Metadata UI

`ObjectMetadata` records can now be created, edited, and deleted directly through the web UI (previously read-only). Metadata is added from the parent object's **Metadata** tab, which opens a pre-filled create form. The value input adapts to the selected `MetadataType` data type, and detail/list views render values appropriately for each type — clickable links for URLs, parsed HTML for Markdown, pretty-printed JSON for JSON, etc. The primary intent is still that metadata is managed by integrations (SSoTs, REST API), but users with the appropriate permissions can now manage individual records through the UI.

#### Other Additions

* Computed Fields can now optionally be rendered as Markdown.
* A reusable `copy_button` template tag renders hover copy-to-clipboard buttons.

### Changed

#### Cable Termination REST API

The [`Cable`](../user-guide/core-data-model/dcim/cable.md) REST API serializer adds a single `terminations` field keyed by side (`a`/`b`) and then by 1-indexed connector number, mirroring the physical structure of the cable. This field is writable on POST and PATCH, and uncabled connectors on breakout cables are surfaced as explicit `null` slots. The legacy `termination_a` / `termination_b` (and `*_type` / `*_id`) fields remain for backward compatibility and refer to connector 1 on each side. The nested `terminations` field is omitted from CSV exports; use the [`CableToCableTermination`](../user-guide/core-data-model/dcim/cabletocabletermination.md) endpoint for per-connector CSV detail.

#### Device Component Default Ordering

The default sort ordering of device-component models (Interface, Front Port, Rear Port, Console Port, etc.) has been changed to group and sort records by their associated `device_id` (UUID) rather than by the associated device's `name`, as the prior behavior (requiring a join across database tables) performed poorly at high data scale. This change affects the default behavior of the following:

* `/dcim/interfaces/` UI list view (and `/dcim/front-ports/`, `/dcim/rear-ports/`, etc.)
* `/api/dcim/interfaces/` REST API list view (and `/api/dcim/front-ports/`, `/api/dcim/rear-ports/`, etc.)
* GraphQL query responses that invole listing any of these models

For the UI and REST API list views, if ordering by device name is desired, the prior behavior may be achieved by explicitly specifying a `?sort=device` query parameter when requesting these views, but users are encouraged to be aware of the performance implications of doing so.

### Dependencies

TODO

<!-- pyml disable-num-lines 2 blanks-around-headers -->

<!-- towncrier release notes start -->
