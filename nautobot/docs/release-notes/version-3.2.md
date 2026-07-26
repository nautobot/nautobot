# Nautobot v3.2

This document describes all new features and changes in Nautobot 3.2.

+**Security Note:** Several CVE fixes in this release introduce [Breaking Changes](#breaking-changes). These changes most commonly surface as unexpected `TypeError`, `AttributeError`, or `KeyError` responses for REST API and GraphQL clients.

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

#### Review Device Component Lookups

The behavior of the [Device component `device` foreign key](#device-component-device-foreign-key) has been changed, such that components (Interface, etc.) belonging to a Module installed in a Device's Module Bay now automatically set each component's `device` foreign key to point to the Device, instead of leaving it as `NULL`/`None` as it was in previous Nautobot versions. As a result, queries such as `Device.interfaces.all()` will now return records that belong to child Modules as well as those that belong directly to the Device, whereas in previous versions this query would only return records that belong directly to the Device. In many cases the new behavior will be more desirable and more intuitive to App and Job authors, but maintainers of existing App and Job code should review their logic to identify possible impacts.

#### Migrate Cable Termination Queries

To support [breakout cables](../user-guide/feature-guides/breakout-cables.md), the association between a [`Cable`](../user-guide/core-data-model/dcim/cable.md) and its terminations has been re-implemented. The `cable` `ForeignKey` that previously existed on each `CableTermination` subclass (`Interface`, `FrontPort`, `RearPort`, `CircuitTermination`, `PowerPort`, etc.) has been removed in favor of a new [`CableToCableTermination`](../user-guide/core-data-model/dcim/cabletocabletermination.md) join model, exposed on each termination via the `cable_termination` reverse one-to-one relationship. App and Job code that queries or traverses cables may need to be updated.

**The `cable` attribute is preserved** as a read-only property on each termination instance (e.g. `interface.cable`), so attribute access continues to work. Assignments to `Cable.termination_a` / `Cable.termination_b` (and their `*_type` / `*_type_id` / `*_id` counterparts) on **unsaved** `Cable` instances also continue to work and are materialized into `CableToCableTermination` rows on save.

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

**Querying `Cable` by its terminations:** in the same way, the legacy `termination_a_type` / `termination_a_id` (and b-side) fields are no longer database columns on `Cable` — the terminations now live on the `terminations` (`CableToCableTermination`) relation. `Cable.objects` translates lookups using the old `*_type` / `*_id` names into the equivalent `terminations__...` join paths (constrained to connector 1 to match the properties), emitting a `DeprecationWarning` for each, so `Cable.objects.filter(...)`, `.get(...)`, and `.get_or_create(...)` continue to work for legacy callers. The `*_type` `ContentType` may be supplied either as a `ContentType` instance (`termination_a_type=<ct>`) or as an integer `ContentType` PK (`termination_a_type_id=<ct.pk>`). The lookup half is translated by the queryset and, for `get_or_create()`, the same kwargs flow through `Cable(...)` and are materialized into `CableToCableTermination` rows on save.

| Deprecated | Translated to |
|------------|---------------|
| `Cable.objects.get(termination_a_type=<ct>, termination_a_id=<pk>)` | `terminations__<fk>_id=<pk>` with `terminations__cable_end="A"` |
| `.get(termination_a_type_id=<ct.pk>, termination_a_id=<pk>)` (integer `ContentType` PK) | same as above |
| `.filter(termination_a_id=<pk>)` (no `_type` / `_type_id` given) | `<pk>` matched against every per-type termination FK |
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

- The private `_cable_peer`, `_cable_peer_type`, and `_cable_peer_id` cache fields have been removed from `CableTermination`. The public peer accessors (`get_cable_peer()`, REST `cable_peer` / `cable_peer_type`, GraphQL `cable_peer_*`) are unchanged; `get_cable_peer()` now accepts an optional `peer_connector` argument for breakout-lane-specific lookups.
- New helpers are available for working with multi-termination cables: `Cable.add_termination(termination, cable_end, connector=1)`, the typed many-to-many reverse accessors on `Cable` (`cable.interfaces`, `cable.front_ports`, etc.), the singular `cable_termination` reverse accessor on each termination, and `PathEndpoint.get_connected_endpoints()` (returning the resolved destinations of all cable paths, one per breakout lane).

## Release Overview

### Breaking Changes

#### REST API Permissions Enforcement on Related Objects

As a part of the fix for security advisory [GHSA-h8rv-c7c8-cvmx](https://github.com/nautobot/nautobot/security/advisories/GHSA-h8rv-c7c8-cvmx), the REST API now enforces object-level `view` permissions when traversing from a requested object to its related objects via the [`?depth` query parameter](../user-guide/platform-functionality/rest-api/overview.md#depth-query-parameter). At `?depth=1` and beyond, a related object that the requesting user does not have permission to view is no longer serialized in full, but is instead restricted to a brief representation containing only its `id`, `object_type`, `url`, and `display` values. See [REST API Object Permissions](../user-guide/platform-functionality/rest-api/object-permissions.md) for full details.

REST API clients operating with limited permissions may now receive the brief representation where a fully serialized related object was previously returned, client code that assumes the presence of other nested fields will typically surface this as a `TypeError`, `AttributeError`, or `KeyError`.

For example, consider a user with `view` permission on `Devices` but not on `Locations` requesting `GET /api/dcim/devices/<uuid>/?depth=1`. Previously, the device's location was serialized in full:

```json
{
    "name": "device1",
    "location": {
        "id": "8badf00d-0000-0000-0000-000000000000",
        "object_type": "dcim.location",
        "url": "https://nautobot.example.com/api/dcim/locations/8badf00d-0000-0000-0000-000000000000/",
        "name": "AMER",
        "description": "North and South America",
        "...": "..."
    }
}
```

Now, because the user lacks permission to view the Location, only the brief representation is returned:

```json
{
    "name": "device1",
    "location": {
        "id": "8badf00d-0000-0000-0000-000000000000",
        "object_type": "dcim.location",
        "url": "https://nautobot.example.com/api/dcim/locations/8badf00d-0000-0000-0000-000000000000/",
        "display": "AMER"
    }
}
```

Client code such as `response["location"]["name"]` that previously worked will now raise a `KeyError`. To restore the previous behavior, grant the requesting user `view` permission on the related model (in this example, `dcim.location`), with [constraints](../user-guide/platform-functionality/users/objectpermission.md) as appropriate. Alternatively, update the client code to tolerate the brief representation, for example by falling back to the `display` value or by retrieving the related object separately via its `url`.

#### GraphQL Permissions Enforcement on Related Objects

As a part of the fix for security advisory [GHSA-mfwj-pjgx-22v2](https://github.com/nautobot/nautobot/security/advisories/GHSA-mfwj-pjgx-22v2), GraphQL queries now enforce object-level `view` permissions when traversing the object graph into related models, not just at the root of the query. A query field resolving to a single related object now returns `null` if the user lacks permission to view that object, and a field resolving to a list of objects now includes only the objects the user is permitted to view. See [GraphQL Permissions Enforcement](../user-guide/platform-functionality/graphql.md#permissions-enforcement) for full details.

GraphQL clients operating with limited permissions may now receive `null` values or shorter lists where full data was previously returned. Client code that assumes a related object is present will typically surface as a `TypeError`, `AttributeError`, or `KeyError`.

For example, consider a user with `view` permission on `Devices` but not on `Locations` or `Interfaces` running the following query:

```graphql
query {
  devices {
    name
    location {
      name
    }
    interfaces {
      name
    }
  }
}
```

Previously, the related objects were returned in full:

```json
{
  "data": {
    "devices": [
      {
        "name": "device1",
        "location": {
          "name": "AMER"
        },
        "interfaces": [
          {"name": "Ethernet1"},
          {"name": "Ethernet2"}
        ]
      }
    ]
  }
}
```

Now, the single related object resolves to `null` and the list contains only viewable objects:

```json
{
  "data": {
    "devices": [
      {
        "name": "device1",
        "location": null,
        "interfaces": []
      }
    ]
  }
}
```

Client code such as `devices[0]["location"]["name"]` that previously worked will now raise a `TypeError`. To restore the previous behavior, grant the requesting user `view` permission on the related models (in this example, `dcim.location` and `dcim.interface`), with [constraints](../user-guide/platform-functionality/users/objectpermission.md) as appropriate. Alternatively, update the client code to handle `null` related objects and filtered lists.

#### Jinja2 Template Rendering Restrictions

As a part of the fix for security advisory [GHSA-6jmc-h6f2-46j4](https://github.com/nautobot/nautobot/security/advisories/GHSA-6jmc-h6f2-46j4), Nautobot's Jinja rendering of user-configurable Jinja2 templates (computed fields, custom links, webhooks, etc.) is now more restrictive. Jinja template snippets may no longer read arbitrary values from the Django `settings` object.

#### Cable Data Model Changes

To support breakout cables (see below), the way a [`Cable`](../user-guide/core-data-model/dcim/cable.md) associates to its terminations has changed. The `cable` `ForeignKey` previously present on each `CableTermination` (`Interface`, `FrontPort`, etc.) has been replaced by a new [`CableToCableTermination`](../user-guide/core-data-model/dcim/cabletocabletermination.md) join model, allowing a cable to have more than two terminations. Similarly, the `Cable.termination_a` and `Cable.termination_b` `GenericForeignKey` fields have been similarly migrated to use the reverse-foreign-key-relation `Cable.terminations` to `CableToCableTermination` records.

Backward-compatibility shims are provided for the most common access patterns (including ongoing support for the REST API and UI query parameters `?termination_a_type=`, `?termination_a_id=`, etc.), but App and Job authors who interact with cables programmatically may need to make updates to support the updated data model. See [Upgrade Actions for App Developers](#app-developers) above for details.

### Added

#### Breakout Cables

Nautobot now models [breakout cables](../user-guide/feature-guides/breakout-cables.md) — multi-lane cable assemblies where a single physical cable splits into multiple individual connections (for example a 400G QSFP-DD port broken out into 4×100G SFP lanes). A new [`CableType`](../user-guide/core-data-model/dcim/cabletype.md) model defines the physical structure of a cable (connectors per side, internal lanes, and the connector-to-lane mapping), and a [`Cable`](../user-guide/core-data-model/dcim/cable.md) assigned a breakout cable type may have more than two terminations, each recorded as a [`CableToCableTermination`](../user-guide/core-data-model/dcim/cabletocabletermination.md). Breakout cables are fully supported across the UI (cable type and cable forms, connection tables, SVG lane-mapping and trace diagrams), the REST API, and lane-aware cable path tracing. `Interface` records gain an optional [`breakout_position`](../user-guide/core-data-model/dcim/interface.md) field to map a subinterface to a position on its parent interface's breakout trunk connector.

#### Partially-Connected, Disconnected, and Repurposed Cables

A [`Cable`](../user-guide/core-data-model/dcim/cable.md) is no longer required to have both of its endpoints defined, and its terminations are no longer fixed at creation time. A cable may now be partially-connected (a termination on only one side, or on a subset of a breakout cable's connectors) or fully-disconnected (no terminations at all), and a cable's terminations may be added, changed, or removed after the cable is created — through the UI, the REST API, or programmatically — without deleting and recreating the cable.

#### IP Address Ranges

A new [`IPAddressRange`](../user-guide/core-data-model/ipam/ipaddressrange.md) model represents a contiguous span of IP addresses within a parent Prefix without needing to create an individual `IPAddress` record for each address in the span. Views include standard (list, detail, edit, delete), "IP Address Ranges" tab on the Prefix detail view, and inline rendering of ranges within the Prefix "IP Addresses" tab.

`IPAddress.clean()` now rejects addresses that fall within an "exclusive" range, `Prefix.clean()` rejects network edits that would orphan a contained range, and `Prefix.save()` reparents contained ranges to the closest fully containing Prefix. Prefix utilization calculations now account for IP address ranges when "mark as utilized" is set.

!!! tip
    Setting a range to "exclusive" may change your workflow — for example, you will no longer be able to create an IP address that falls within an exclusive IP address range. This is by design, but may be surprising if the implications of enabling exclusivity were not considered.

#### Job Cancel

Jobs that are actively running, pending a run, or abandoned, can now be cancelled from both the UI and REST API, with support for both Celery and Kubernetes jobs. You will now be able to see a Job Cancel button on the job result list and detail views (for jobs not in a terminal state.)

The "Cancel Job" action will perform slightly different actions depending on the current state of the job, all of which end up with the Job Result in a terminal state. For technical details refer to the documentation for [Job cancel](../user-guide/platform-functionality/jobs/job-cancel.md).

Job Cancel requires the `extras.run_job` permission; additionally, non-staff users with this permission may cancel only jobs they submitted, while staff users with this permission may cancel any user's jobs.

#### Homepage Stickiness

The homepage now saves the location and collapsing of each panel. You can re-arrange them to your liking, and see it the same on any browser. Additionally, when resizing your browser window, the panels will be automatically and sanely rearranged to four, three, two, or one column as appropriate.

#### Search Enhancements

The header search bar gains two distinct capabilities. First, model-name typeahead: as you type an `in:` phrase, matching model names are suggested (e.g. typing `in:dev` suggests `in:devices`). Second, once you begin searching, live results appear as you type, showing up to the first 10 matches.

#### Object Metadata UI

`ObjectMetadata` records can now be created, edited, and deleted directly through the web UI (previously read-only). Metadata is added from the parent object's **Metadata** tab, which opens a pre-filled create form. The value input adapts to the selected `MetadataType` data type, and detail/list views render values appropriately for each type — clickable links for URLs, parsed HTML for Markdown, pretty-printed JSON for JSON, etc. The primary intent is still that metadata is managed by integrations (SSoTs, REST API), but users with the appropriate permissions can now manage individual records through the UI.

#### Other Additions

- Computed Fields can now optionally be rendered as Markdown.
- A reusable `copy_button` template tag renders hover copy-to-clipboard buttons.
- Added opt-in support for OpenTelemetry traces, metrics, and logs, disabled by default.

### Changed

#### Cable Termination REST API

The [`Cable`](../user-guide/core-data-model/dcim/cable.md) REST API serializer adds a single `terminations` field keyed by side (`a`/`b`) and then by 1-indexed connector number, mirroring the physical structure of the cable. This field is writable on POST and PATCH, and uncabled connectors on breakout cables are surfaced as explicit `null` slots. The legacy `termination_a` / `termination_b` (and `*_type` / `*_id`) fields remain for backward compatibility and refer to connector 1 on each side. The nested `terminations` field is omitted from CSV exports; use the [`CableToCableTermination`](../user-guide/core-data-model/dcim/cabletocabletermination.md) endpoint for per-connector CSV detail.

#### Device Component Default Ordering

The default sort ordering of device-component models (Interface, Front Port, Rear Port, Module Bay, etc.) has been changed to group and sort records by their associated `device_id` (UUID) rather than by the associated device's `name`, as the prior behavior (requiring a join across database tables) performed poorly at high data scale. This change affects the default behavior of the following:

- `/dcim/interfaces/` UI list view (and `/dcim/front-ports/`, `/dcim/rear-ports/`, etc.)
- `/api/dcim/interfaces/` REST API list view (and `/api/dcim/front-ports/`, `/api/dcim/rear-ports/`, etc.)
- GraphQL query responses that invole listing any of these models

For the UI and REST API list views, if ordering by device name is desired, the prior behavior may be achieved by explicitly specifying a `?sort=device` query parameter when requesting these views, but users are encouraged to be aware of the performance implications of doing so.

#### Device Component `device` Foreign Key

When device components (Interface, Front Port, Rear Port, Module Bay, etc.) belong to a Module, and that Module is installed in a Module Bay belonging to a Device, the `device` foreign key on each such device component is now automatically set to point to the Device in question. This is a behavior change from previous Nautobot versions, in which the `device` foreign key would remain as `NULL`/`None` for device components belonging to a Module even when that Module was installed into a Device's Module Bay. This change was made to improve the performance and self-consistency of Device component lookups, such as the `Device.all_interfaces()` method and `Device.interfaces.all()` queryset manager.

#### Device Module Bays Tree View

The Device detail view "Module Bays" tab now supports a hierarchical view with asynchronous loading of each nested module level as you expand it. Optionally, you can expand or collapse all levels to show or hide the entire nested structure.

### Dependencies

As usual for Nautobot minor-version releases, 3.2.0 includes updates to many of Nautobot's dependencies, including in some cases major-version updates to these dependencies. These updates should generally be transparent to end users, but Apps relying on these dependencies may in turn require minor updates for compatibility.

<!-- pyml disable-num-lines 2 blanks-around-headers -->

<!-- towncrier release notes start -->

## v3.2.0 (2026-07-27)

### Breaking Changes in v3.2.0

- [#GHSA-6jmc-h6f2-46j4](https://github.com/nautobot/nautobot/issues/GHSA-6jmc-h6f2-46j4) - It is no longer possible to pass an `app_name` argument to the `settings_or_config` **Jinja** template filter; this functionality is still supported in Django templates.

### Security in v3.2.0

- [#GHSA-h8rv-c7c8-cvmx](https://github.com/nautobot/nautobot/issues/GHSA-h8rv-c7c8-cvmx) - Fixed a REST API information-disclosure issue where the `?depth=N` query parameter exposed the full detail of related objects that the requesting user did not have permission to view. Related objects that the user cannot view are now rendered in a brief `{id, object_type, url, display}` form instead of full detail. The `display` value is included for parity with the UI, where a related object's display value is visible without requiring full view permission on that object. Additionally, the Notes REST API now enforces `view` permission on the object a note is being assigned to on write (POST/PATCH), consistent with other object references.
- [#GHSA-6jmc-h6f2-46j4](https://github.com/nautobot/nautobot/issues/GHSA-6jmc-h6f2-46j4) - Restricted the `settings_or_config` template filter and the template `settings` context to a non-sensitive allowlist of Django settings and Constance configuration values.
- [#GHSA-6jmc-h6f2-46j4](https://github.com/nautobot/nautobot/issues/GHSA-6jmc-h6f2-46j4) - Removed the ability to pass an `app_name` argument to the `settings_or_config` filter to retrieve values from an app's `PLUGINS_CONFIG` in Jinja templates (this is still supported in Django templates).
- [#GHSA-mfwj-pjgx-22v2](https://github.com/nautobot/nautobot/issues/GHSA-mfwj-pjgx-22v2) - Fixed GraphQL not enforcing object-level permissions when traversing to related objects: filtering related objects (e.g. `locations { racks(...) }`), traversing Relationship associations (e.g. `rel_*` fields), forward foreign-key traversal (e.g. `racks { location }`), reverse relations (reverse foreign keys such as `*_set` fields and reverse one-to-one relations such as `module_bay { installed_module }`), and other custom/property-backed related-object accessors (e.g. a Device's `all_interfaces`, cable/connection peers, dynamic group memberships, assigned tags, and legacy `location` accessors on `Prefix`/`VLAN`) now respect the requesting user's view permissions on the related model ([GHSA-mfwj-pjgx-22v2](https://github.com/nautobot/nautobot/security/advisories/GHSA-mfwj-pjgx-22v2)).
- [#GHSA-mfwj-pjgx-22v2](https://github.com/nautobot/nautobot/issues/GHSA-mfwj-pjgx-22v2) - Changed GraphQL schema to represent all forward foreign-key fields as nullable (even if not actually nullable as database fields), since a related object the user is not permitted to view is now returned as `null`.
- [#GHSA-p99c-c9qx-34fw](https://github.com/nautobot/nautobot/issues/GHSA-p99c-c9qx-34fw) - Fixed a Jinja2 template sandbox escape that allowed users to reach the database cursor via the Django ORM and execute arbitrary SQL.
- [#GHSA-p99c-c9qx-34fw](https://github.com/nautobot/nautobot/issues/GHSA-p99c-c9qx-34fw) - Fixed a Jinja2 template sandbox escape that allowed users to reach arbitrary models via the Django application registry.
- [#GHSA-qr7c-g3j2-hw5q](https://github.com/nautobot/nautobot/issues/GHSA-qr7c-g3j2-hw5q) - Added enforcement of the `run` permission on the Job Hook dispatch path, fixing a privilege escalation in which a user without the run permission could execute a Job by triggering a Job Hook.
- [#9293](https://github.com/nautobot/nautobot/issues/9293) - Updated development NPM dependency `postcss` to `^8.5.22` to mitigate GHSA-r28c-9q8g-f849.
- [#9294](https://github.com/nautobot/nautobot/issues/9294) - Updated dependency `gitpython` to `>=3.1.55,<3.2` to mitigate GHSA-94p4-4cq8-9g67.
- [#9294](https://github.com/nautobot/nautobot/issues/9294) - Updated documentation dependency `mkdocs-material` to `~9.7.7` to mitigate GHSA-xvg9-69gf-fjrf.

### Added in v3.2.0

- [#GHSA-mfwj-pjgx-22v2](https://github.com/nautobot/nautobot/issues/GHSA-mfwj-pjgx-22v2) - Added GraphQL type-definition helper methods `permission_safe_resolver` and `permission_safe_attribute_resolver`. Apps defining custom GraphQL type classes may need to use these methods in some cases to prevent object-permission enforcement gaps similar to GHSA-mfwj-pjgx-22v2.
- [#9281](https://github.com/nautobot/nautobot/issues/9281) - Added a loading spinner to HTMX-driven buttons while their request is in flight.

### Deprecated in v3.2.0

- [#9285](https://github.com/nautobot/nautobot/issues/9285) - Deprecated `check_and_call_git_repository_function` in favor of `git_repository_sync_view`.

### Fixed in v3.2.0

- [#9174](https://github.com/nautobot/nautobot/issues/9174) - Fixed the OpenAPI schema for the Cable `terminations` field.
- [#9252](https://github.com/nautobot/nautobot/issues/9252) - Fixed the action button showing a caret when `add` is present but neither `import` nor `export` is.
- [#9285](https://github.com/nautobot/nautobot/issues/9285) - Fixed GitRepository sync REST API endpoint not applying object-level permission restrictions (`restrict()`) when retrieving the repository.
- [#9295](https://github.com/nautobot/nautobot/issues/9295) - Fixed `contains` filter on IP Address Ranges matching ranges of the wrong IP family due to raw byte comparison without IP version scoping.
- [#9299](https://github.com/nautobot/nautobot/issues/9299) - Fixed an `IndentationError` in the generated `nautobot_config.py` caused by an uncommented `EMAIL_SSL_KEYFILE` line in the configuration template.
- [#9300](https://github.com/nautobot/nautobot/issues/9300) - Fixed `JobConsoleEntry` model incorrectly being flagged as supporting object-metadata and data-compliance features.

### Dependencies in v3.2.0

- [#9294](https://github.com/nautobot/nautobot/issues/9294) - Updated dependency `kubernetes` to `>=36.0.3,<37`.
- [#9294](https://github.com/nautobot/nautobot/issues/9294) - Updated dependency `packaging` to `>=23.2`.
- [#9294](https://github.com/nautobot/nautobot/issues/9294) - Updated dependency `regex` to `>=2026.7.19`.

### Documentation in v3.2.0

- [#GHSA-h8rv-c7c8-cvmx](https://github.com/nautobot/nautobot/issues/GHSA-h8rv-c7c8-cvmx) - Added documentation describing the behavior of the REST API with respect to object permissions.
- [#GHSA-qr7c-g3j2-hw5q](https://github.com/nautobot/nautobot/issues/GHSA-qr7c-g3j2-hw5q) - Added documentation clarifying that a Job Hook is only dispatched when the user responsible for the triggering change has permission to run the target Job.
- [#9285](https://github.com/nautobot/nautobot/issues/9285) - Clarified that managing a Git repository (create, change, sync) grants arbitrary code execution on the worker and that syncing repository-provided Jobs does not require the Job run permission.
- [#9291](https://github.com/nautobot/nautobot/issues/9291) - Fixed a minor documentation issue with the 3.2 release notes.
- [#9303](https://github.com/nautobot/nautobot/issues/9303) - Update `notices.md` release notes.

### Housekeeping in v3.2.0

- [#9285](https://github.com/nautobot/nautobot/issues/9285) - Refactored GitRepository sync/dry-run logic so that both the UI and REST API views share a common validation helper (`get_git_repository_for_sync()`) and enqueue jobs exclusively through the `GitRepository.sync()` model method, instead of calling the `enqueue_*` datasource functions directly.
- [#9293](https://github.com/nautobot/nautobot/issues/9293) - Updated development NPM dependencies `eslint` and `@eslint/js` to `^9.39.5`.
- [#9293](https://github.com/nautobot/nautobot/issues/9293) - Updated development NPM dependency `autoprefixer` to `^10.5.4`.
- [#9294](https://github.com/nautobot/nautobot/issues/9294) - Updated development dependency `coverage` to `~7.15.2`.
- [#9294](https://github.com/nautobot/nautobot/issues/9294) - Updated development dependency `faker` to `^40.35.0`.
- [#9294](https://github.com/nautobot/nautobot/issues/9294) - Updated documentation dependency `mkdocstrings` to `~1.0.6`.
- [#9294](https://github.com/nautobot/nautobot/issues/9294) - Updated development dependency `pymarkdownlnt` to `~0.9.39`.

## v3.2.0b2 (2026-07-23)

### Security in v3.2.0b2

- [#8930](https://github.com/nautobot/nautobot/issues/8930) - Updated npm development dependency `brace-expansion` to `1.1.16` to mitigate CVE-2026-13149.
- [#8930](https://github.com/nautobot/nautobot/issues/8930) - Updated npm development dependency `fast-uri` to `3.1.4` to mitigate CVE-2026-16221 and CVE-2026-13676.
- [#8930](https://github.com/nautobot/nautobot/issues/8930) - Updated npm development dependency `immutable` to `5.1.9` to mitigate CVE-2026-59879 and CVE-2026-59880.
- [#8930](https://github.com/nautobot/nautobot/issues/8930) - Updated npm development dependency `js-yaml` to `4.3.0` to mitigate CVE-2026-59869.
- [#8930](https://github.com/nautobot/nautobot/issues/8930) - Updated npm development dependency `shell-quote` to `1.10.0` to mitigate CVE-2026-13311.
- [#9218](https://github.com/nautobot/nautobot/issues/9218) - Updated dependency `django` to `>=5.2.16,<5.3` to mitigate CVE-2026-48588, CVE-2026-53877, and CVE-2026-53878.
- [#9219](https://github.com/nautobot/nautobot/issues/9219) - Updated dependency `Pillow` to `>=12.3.0,<13` to mitigate multiple CVEs.
- [#9278](https://github.com/nautobot/nautobot/issues/9278) - Updated dependency `gitpython` to `>=3.1.54,3.2.0` to mitigate multiple security vulnerabilities.

### Added in v3.2.0b2

- [#4783](https://github.com/nautobot/nautobot/issues/4783) - Added opt-in support for [OpenTelemetry](https://opentelemetry.io/) traces, metrics, and logs, disabled by default and enabled via the `OTEL_PYTHON_DJANGO_INSTRUMENT` setting.
- [#4783](https://github.com/nautobot/nautobot/issues/4783) - Added the `NAUTOBOT_OTEL_EXTRA_INSTRUMENTORS` setting to enable additional OpenTelemetry library instrumentors at startup.
- [#7494](https://github.com/nautobot/nautobot/issues/7494) - Added `source_version` property to the `Job` model, exposing the version of the source code providing the job — the Nautobot version for system Jobs, the App version for App-provided Jobs, or the `current_head` commit hash for Jobs provided by a Git repository.
- [#7494](https://github.com/nautobot/nautobot/issues/7494) - Added the Job's source version to the "Running job" log entry recorded at the start of each Job run.
- [#7494](https://github.com/nautobot/nautobot/issues/7494) - Added display of the Job source version to the Job detail view and as an optional column on the Jobs list view.
- [#8870](https://github.com/nautobot/nautobot/issues/8870) - Added ability to add VirtualDeviceContext objects to a ControllerManagedDeviceGroup.
- [#9045](https://github.com/nautobot/nautobot/issues/9045) - Added a `vm_interfaces` filter to `VLANFilterSet`, allowing VLANs to be filtered by the VM interface(s) they are assigned to (tagged or untagged).
- [#9221](https://github.com/nautobot/nautobot/issues/9221) - Added a link to the IP Address Range name column, falling back to the range's string representation for ranges without a name.
- [#9232](https://github.com/nautobot/nautobot/issues/9232) - Added a "Searchable Fields by Model" documentation page and a search bar tooltip, both listing the fields matched by each model's list-view search bar. The documentation page is generated from each model's `SearchFilter` via the new `generate_searchable_fields` management command, and the tooltip appears when hovering over the help icon in the search bar.
- [#9236](https://github.com/nautobot/nautobot/issues/9236) - Added `has_cable` filter to "basic" filter forms for all cable termination models.
- [#9243](https://github.com/nautobot/nautobot/issues/9243) - Added `kind` filter to Interface "basic" filter form.
- [#9245](https://github.com/nautobot/nautobot/issues/9245) - Added IP Address Ranges to Stats in Tenant detail view.
- [#9254](https://github.com/nautobot/nautobot/issues/9254) - Added Cloud as an edition of Nautobot.
- [#9255](https://github.com/nautobot/nautobot/issues/9255) - Added the ability to set Django email settings via `NAUTOBOT_EMAIL_*` environment variables.
- [#9262](https://github.com/nautobot/nautobot/issues/9262) - Added `size` Property To `IPAddressRange` Model And `IPAddressRangeUIViewSet`
- [#9265](https://github.com/nautobot/nautobot/issues/9265) - Added bulk edit to IP Address Ranges list view.
- [#9265](https://github.com/nautobot/nautobot/issues/9265) - Added `IP Address Ranges` tab to Namespace detail view.
- [#9271](https://github.com/nautobot/nautobot/issues/9271) - Added `SavedView` support to `ObjectChange` list view.

### Changed in v3.2.0b2

- [#9045](https://github.com/nautobot/nautobot/issues/9045) - Changed the device/module component bulk-create form (`name_pattern`/`label_pattern`) to render and validate custom fields, relationships, object notes, and dynamic group assignments by borrowing those fields onto the create form from the per-instance model form.
- [#9196](https://github.com/nautobot/nautobot/issues/9196) - Updated Device detail view "Module Bays" tab to render a tree view with interactive expanding and collapsing of child modules and module bays.
- [#9223](https://github.com/nautobot/nautobot/issues/9223) - Renamed the feature from `Job Revocation` to `Job Cancel`. All user-facing terminology now uses `cancel` instead of `revoke`.
- [#9223](https://github.com/nautobot/nautobot/issues/9223) - The cancel API preview (`GET` on the cancel endpoint) no longer returns the `action` and `action_description` fields.
- [#9223](https://github.com/nautobot/nautobot/issues/9223) - Reworked the Cancel Job confirmation popup.
- [#9223](https://github.com/nautobot/nautobot/issues/9223) - Renamed Job Result columns to use "cancel" terminology and Title Case.
- [#9223](https://github.com/nautobot/nautobot/issues/9223) - `ButtonsColumn` now treats `buttons=()` as "no buttons" instead of falling back to the default set.
- [#9236](https://github.com/nautobot/nautobot/issues/9236) - Changed behavior of Cable create/edit form to entirely omit endpoints that are already connected to a different cable, instead of the previous behavior of displaying them but disabling them as options.
- [#9241](https://github.com/nautobot/nautobot/issues/9241) - Job cancellation now requires the new `extras.cancel_job` permission instead of `extras.run_job`. The submitter of a job can still cancel their own job with only `extras.view_jobresult` (no `cancel_job` needed). Any other user needs `extras.cancel_job` scoped (object-level) to the specific Job. Staff status no longer grants the ability to cancel another user's job.
- [#9243](https://github.com/nautobot/nautobot/issues/9243) - Changed Cable create/edit form to not present "embedded search" options for the individual terminations (interface, front port, etc.).
- [#9245](https://github.com/nautobot/nautobot/issues/9245) - Changed the Add IP Address Range button to also pre-fill `end_address` (first three octets of start, IPv4 only).
- [#9265](https://github.com/nautobot/nautobot/issues/9265) - Changed ProtectedError message when Prefix is deleted and IP Address or IP Address Ranges are left without a parent.
- [#9277](https://github.com/nautobot/nautobot/issues/9277) - Changed `Prefix.get_available_ips()` to exclude only exclusive IP Address Ranges, aligning availability with IPAddress validation. The `/available-ips/` API endpoint now lists and allocates addresses inside non-exclusive ranges. Removed the unused `exclude_child_ips` parameter.
- [#9286](https://github.com/nautobot/nautobot/issues/9286) - Updated Marketplace entries for Apps introduced in 3.2.

### Removed in v3.2.0b2

- [#9223](https://github.com/nautobot/nautobot/issues/9223) - Removed the delete action button from running or pending Job Results. A running or pending job now offers only Cancel Job.

### Fixed in v3.2.0b2

- [#8677](https://github.com/nautobot/nautobot/issues/8677) - Fixed Provider `noc_contact` and `admin_contact` fields no longer being rendered as Markdown on the Provider detail view.
- [#9062](https://github.com/nautobot/nautobot/issues/9062) - Fixed duplicated parent form dropdowns when an embedded "Add a new ..." modal was submitted with a validation error and then dismissed.
- [#9120](https://github.com/nautobot/nautobot/issues/9120) - Fixed negation (`__n`) filtering of multi-select custom fields, which previously matched all records instead of excluding records containing the specified value.
- [#9194](https://github.com/nautobot/nautobot/issues/9194) - Fixed UI horizontal "wiggle" when opening/closing various modal dialogs.
- [#9208](https://github.com/nautobot/nautobot/issues/9208) - Fixed the Worker and Traceback sections on the Job Result "Advanced" tab not updating without a manual page refresh while a job runs or after it completes.
- [#9229](https://github.com/nautobot/nautobot/issues/9229) - Fixed a race condition in the cable type creation form where submitting immediately after changing the connector counts or total lanes could fail validation because the lane mapping table had not finished regenerating.
- [#9236](https://github.com/nautobot/nautobot/issues/9236) - Fixed inability to swap or reassign a saved cable's terminations in the cable edit form by filtering termination dropdowns server-side to endpoints that are uncabled or already on the cable being edited.
- [#9245](https://github.com/nautobot/nautobot/issues/9245) - Fixed IP Address Ranges from descendant Prefixes not displaying correctly on a parent Prefix.
- [#9245](https://github.com/nautobot/nautobot/issues/9245) - Fixed incorrect `start_address` pre-fill on the Add IP Address Range button.
- [#9246](https://github.com/nautobot/nautobot/issues/9246) - Fixed bulk IP address creation silently doing nothing (raising an uncaught `IntegrityError`) when a pattern collided with an existing address. The collision is now reported as a validation error on the form.
- [#9249](https://github.com/nautobot/nautobot/issues/9249) - Extended the `Cable.objects` backward-compatibility shims to also accept `termination_[a|b]_type_id` (integer `ContentType` PK) in lookups such as `filter()`, `get()`, and `get_or_create()`, as well as in `Cable(...)` construction, matching the existing `termination_[a|b]_type`/`termination_[a|b]_id` support.
- [#9253](https://github.com/nautobot/nautobot/issues/9253) - Fixed job cancel revoked jobs recovery on Redis Sentinel/cluster by using Celery's broker connection instead of parsing the broker URL.
- [#9263](https://github.com/nautobot/nautobot/issues/9263) - Improved performance of "live search" feature.
- [#9264](https://github.com/nautobot/nautobot/issues/9264) - Fixed bulk "Select All" delete and edit operations ignoring a view's implicit `alter_queryset()` scoping.
- [#9266](https://github.com/nautobot/nautobot/issues/9266) - Fixed `ComputedFieldColumn` rendering its fallback value on non-matching row types in interleaved tables (e.g. Prefix > IP Addresses). Such cells now render a placeholder.
- [#9273](https://github.com/nautobot/nautobot/issues/9273) - Fixed the worker liveness probe file to be updated based on the consumer's connection.
- [#9276](https://github.com/nautobot/nautobot/issues/9276) - Fixed an N+1 query problem on the Interfaces REST API.
- [#9277](https://github.com/nautobot/nautobot/issues/9277) - Improved performance of "ip address ranges" feature.
- [#9283](https://github.com/nautobot/nautobot/issues/9283) - Fixed docs link pointing to an authenticated link when on an unauthenticated page.

### Dependencies in v3.2.0b2

- [#8000](https://github.com/nautobot/nautobot/issues/8000) - Updated dependency `cryptography` to `>=49.0.0,<50`.
- [#8000](https://github.com/nautobot/nautobot/issues/8000) - Updated dependency `django-redis` to `>=7.0.0,<7.1`.
- [#8000](https://github.com/nautobot/nautobot/issues/8000) - Updated dependency `django-tables2` to `>=3.0.0,<3.1`. Note that this is a new major version of this dependency and includes a small number of breaking changes which may impact Nautobot Apps. Review the [change log](https://github.com/jieter/django-tables2/blob/v3.0.0/CHANGELOG.md#300-2026-04-13) for details.
- [#8264](https://github.com/nautobot/nautobot/issues/8264) - Updated dependency `django-celery-beat` to `==2.9.0`.
- [#8264](https://github.com/nautobot/nautobot/issues/8264) - Updated dependency `django-prometheus` to `>=2.5.0,<2.6`.
- [#8264](https://github.com/nautobot/nautobot/issues/8264) - Updated dependency `django-structlog` to `>=10.1.0,<10.2`.
- [#8264](https://github.com/nautobot/nautobot/issues/8264) - Updated dependency `django-tree-queries` to `>=0.24.0,<0.25`.
- [#8264](https://github.com/nautobot/nautobot/issues/8264) - Updated dependency `drf-spectacular` to `>=0.29.0,<0.30`.
- [#8264](https://github.com/nautobot/nautobot/issues/8264) - Updated dependency `kubernetes` to `>=36.0.2,<37`.
- [#8264](https://github.com/nautobot/nautobot/issues/8264) - Updated dependency `prometheus-client` to `>=0.25.0,<0.26`.
- [#8930](https://github.com/nautobot/nautobot/issues/8930) - Updated NPM dependency `echarts` to `^6.1.0`.
- [#9219](https://github.com/nautobot/nautobot/issues/9219) - Updated dependency `regex` to `>=2026.6.28`.

### Documentation in v3.2.0b2

- [#7319](https://github.com/nautobot/nautobot/issues/7319) - Added documentation clarifying that the `extras.view_fileproxy` permission is required to download a job's output files.
- [#7475](https://github.com/nautobot/nautobot/issues/7475) - Added documentation noting that app-provided `DatasourceContent` callbacks are always called when a Git repository is synced and should always check `repository_record.provided_contents` before taking action.
- [#9223](https://github.com/nautobot/nautobot/issues/9223) - Clarified that canceling a job is not a rollback. It does not add atomic transactions and does not undo work already completed.
- [#9239](https://github.com/nautobot/nautobot/issues/9239) - Updated HA documentation with recommendations for virtual chassis and device redundancy group models.
- [#9275](https://github.com/nautobot/nautobot/issues/9275) - Added workflows diagram to job cancel documention.
- [#9284](https://github.com/nautobot/nautobot/issues/9284) - Update release note docs for 3.2 to include OpenTelemetry and Module Bay view.

### Housekeeping in v3.2.0b2

- [#8000](https://github.com/nautobot/nautobot/issues/8000) - Updated development dependency `django-debug-toolbar` to `~7.0.0`.
- [#8000](https://github.com/nautobot/nautobot/issues/8000) - Updated development dependency `invoke` to `~3.0.3`.
- [#8000](https://github.com/nautobot/nautobot/issues/8000) - Updated development dependency `rich` to `~15.0.0`.
- [#8000](https://github.com/nautobot/nautobot/issues/8000) - Updated development dependency `requests` to `~2.34.2`.
- [#8264](https://github.com/nautobot/nautobot/issues/8264) - Updated development dependency `djlint` to `~1.40.4`.
- [#8264](https://github.com/nautobot/nautobot/issues/8264) - Updated development dependency `coverage` to `~7.15.0`.
- [#8264](https://github.com/nautobot/nautobot/issues/8264) - Updated development dependency `openapi-spec-validator` to `~0.9.0`.
- [#8930](https://github.com/nautobot/nautobot/issues/8930) - Updated development NPM dependency `autoprefixer` to `^10.5.2`.
- [#8930](https://github.com/nautobot/nautobot/issues/8930) - Updated development NPM dependency `postcss` to `^8.5.16`.
- [#8930](https://github.com/nautobot/nautobot/issues/8930) - Updated development NPM dependency `sass-loader` to `^16.0.8`.
- [#9045](https://github.com/nautobot/nautobot/issues/9045) - Refactored VMInterfaceUIViewSet model related UI views to use `NautobotUIViewSet` and `UI Component Framework`.
- [#9084](https://github.com/nautobot/nautobot/issues/9084) - Refactored Interface model related UI views to use `NautobotUIViewSet`.
- [#9143](https://github.com/nautobot/nautobot/issues/9143) - Refactored ScheduleJob model related UI views to use `UI component framework`.
- [#9170](https://github.com/nautobot/nautobot/issues/9170) - Refactored Interface model related UI views to use `UI component framework`.
- [#9219](https://github.com/nautobot/nautobot/issues/9219) - Updated development dependency `faker` to `^40.28.1`.
- [#9219](https://github.com/nautobot/nautobot/issues/9219) - Updated development dependency `mkdocstrings` to `~1.0.5`.
- [#9219](https://github.com/nautobot/nautobot/issues/9219) - Updated development dependency `ruff` to `~0.15.21`.
- [#9258](https://github.com/nautobot/nautobot/issues/9258) - Updated the CableTerminations migration to be bulk friendly.
- [#9265](https://github.com/nautobot/nautobot/issues/9265) - Refactored NamespaceUIViewSet - changed DistinctViewTab to use UI framework instead of as a separate HTML template.
- [#9287](https://github.com/nautobot/nautobot/issues/9287) - Fixed the development observability stack to work on a fresh clone.

## v3.2.0b1 (2026-07-09)

### Added in v3.2.0b1

- [#5743](https://github.com/nautobot/nautobot/issues/5743) - Added feature to optionally render Computed-Fields as Markdown
- [#8610](https://github.com/nautobot/nautobot/issues/8610) - Added UI views for creating, editing, and deleting `ObjectMetadata` records directly in the web UI.
- [#8610](https://github.com/nautobot/nautobot/issues/8610) - Added "Add metadata" entry point from a model's Metadata tab that opens a pre-filled create form, with the value input adapting to the selected `MetadataType` data type.
- [#8610](https://github.com/nautobot/nautobot/issues/8610) - Added type-aware value rendering in the `ObjectMetadata` list and detail views (linkified URLs, parsed Markdown, pretty-printed JSON, etc.).
- [#8902](https://github.com/nautobot/nautobot/issues/8902) - Added `CableBreakoutType` data model, initial UI, and tests.
- [#8910](https://github.com/nautobot/nautobot/issues/8910) - Added typeahead functionality to header search bar. Results for best matching models show when "in:{model}" search phrase is entered.
- [#8913](https://github.com/nautobot/nautobot/issues/8913) - Added `revoked_by`, `revoked_by_user_name` and `terminated_at` fields to `JobResult`.
- [#8913](https://github.com/nautobot/nautobot/issues/8913) - Added support for terminating running and pending jobs with backend-agnostic strategies for Celery and Kubernetes.
- [#8924](https://github.com/nautobot/nautobot/issues/8924) - Added `manufacturer`, `part_number`, and `has_embedded_transceivers` to `CableType` model.
- [#8927](https://github.com/nautobot/nautobot/issues/8927) - Implemented search bar live search per model.
- [#8935](https://github.com/nautobot/nautobot/issues/8935) - Added `Revocation` ObjectFieldsPanel to Advanced Tab in detail JobResult view.
- [#8935](https://github.com/nautobot/nautobot/issues/8935) - Added `revoke-job` endpoint to terminate a running or pending Job, or reap it if its worker is gone.
- [#8935](https://github.com/nautobot/nautobot/issues/8935) - Added column `Revocation Type` to JobResult list view to see what kind of revoke type was executed.
- [#8935](https://github.com/nautobot/nautobot/issues/8935) - Added filter `Revocation Type` to JobResult list view to permit filtering by revocation type Terminated or Reaped.
- [#8935](https://github.com/nautobot/nautobot/issues/8935) - Added `Revoke Job` button to JobResult detail view to execute revoke action.
- [#8946](https://github.com/nautobot/nautobot/issues/8946) - Added `GET` and `POST /api/extras/job-results/{id}/revoke/` API endpoints for revoking a running or pending job.
- [#8946](https://github.com/nautobot/nautobot/issues/8946) - Added `celery_kwargs` to `JobResultFactory`.
- [#8946](https://github.com/nautobot/nautobot/issues/8946) - Added `UnknownStrategy` for `RevokeFactory`. Jobs whose `queue_type` is not registered in `RevokeFactory.strategies` now fall back to a reap-only strategy that marks the `JobResult` as revoked without sending a backend signal.
- [#8946](https://github.com/nautobot/nautobot/issues/8946) - Added `Revoke Job` to `JOB_RESULT_BUTTONS`.
- [#8974](https://github.com/nautobot/nautobot/issues/8974) - Added the `CableToCableTermination` model (exposed via `nautobot.dcim.models`), a join table between `Cable` and `CableTermination` instances that allows a cable to have more than two terminations (breakout-cable support). The model is exposed at REST API endpoint `/api/dcim/cables-to-cable-terminations/`.
- [#8974](https://github.com/nautobot/nautobot/issues/8974) - Added an `is_disconnected` boolean filter to `CableFilterSet` for selecting cables with no termination on one or both sides.
- [#8974](https://github.com/nautobot/nautobot/issues/8974) - Added a "Cables" detail tab on `CableType` (`/dcim/cable-types/<pk>/cables/`) listing all cables of that type, and a `cable_count` column to `CableTypeTable`.
- [#8974](https://github.com/nautobot/nautobot/issues/8974) - Added `q` search filter support to `ConsoleConnectionFilterSet`, `InterfaceConnectionFilterSet`, and `PowerConnectionFilterSet`.
- [#8974](https://github.com/nautobot/nautobot/issues/8974) - Added `Cable.add_termination(termination, cable_end, connector=None)` for attaching a `CableTermination` to a saved `Cable` after creation (e.g. for additional breakout connectors that the single A/B `Cable.__init__` kwargs can't express).
- [#8974](https://github.com/nautobot/nautobot/issues/8974) - Added typed `ManyToManyField` reverse accessors to `Cable` (`cable.interfaces`, `cable.front_ports`, `cable.power_ports`, etc.), and a singular `cable_termination` reverse accessor on each `CableTermination` instance (e.g. `interface.cable_termination`) returning the connected join row.
- [#8974](https://github.com/nautobot/nautobot/issues/8974) - Added `PathEndpoint.get_connected_endpoints()`, returning the resolved destinations of all `CablePath` rows originating from the endpoint (one per breakout lane).
- [#8974](https://github.com/nautobot/nautobot/issues/8974) - Added a "Cable Status" row to the "Connection" panel on device-component detail views, and extended the "Edit cable / Detach / Delete cable / Mark connected/planned" dropdown (previously only on `Interface`) to the `ConsolePort`, `ConsoleServerPort`, `PowerPort`, `PowerOutlet`, `FrontPort`, and `RearPort` detail views.
- [#8974](https://github.com/nautobot/nautobot/issues/8974) - Added row-action dropdowns to the standalone list views for `ConsolePort`, `ConsoleServerPort`, `PowerPort`, `PowerOutlet`, `Interface`, `FrontPort`, `RearPort`, `DeviceBay`, and `ModuleBay` (previously only the per-device/per-module embedded tables exposed these actions).
- [#8991](https://github.com/nautobot/nautobot/issues/8991) - Added abstract `perform_reap` method to `JobRevokeStrategy` class.
- [#8991](https://github.com/nautobot/nautobot/issues/8991) - Added implementation for K8s revoke job.
- [#8991](https://github.com/nautobot/nautobot/issues/8991) - Added `revocation_type` to `JobResult` model to track which type of revocation was done.
- [#8991](https://github.com/nautobot/nautobot/issues/8991) - Added `TYPE_ABANDONED` to `JobRevocationTypeChoices`.
- [#9019](https://github.com/nautobot/nautobot/issues/9019) - Added a `select_related` on every per-type FK column to the `CableViewSet`, `CableToCableTerminationViewSet`, and `CableUIViewSet` querysets and switched `Cable._get_termination_attr` / `terminations_a` / `terminations_b` to iterate the prefetched `terminations` cache so listing cables (both REST API and UI) no longer runs an N+1 of queries per join row.
- [#9019](https://github.com/nautobot/nautobot/issues/9019) - Added a `Meta.default_m2m_fields` extension to `nautobot.core.api.serializers.OptInFieldsMixin`. Subclasses can list ListSerializer / ManyRelatedField source names that should be included in API responses by default (alongside the global `DEFAULT_M2M_FIELDS` of `tags`/`content_types`/`object_types`) without requiring callers to pass `?exclude_m2m=False`.
- [#9019](https://github.com/nautobot/nautobot/issues/9019) - Added writability to the `terminations` field on the `Cable` REST API serializer. POST and PATCH on `/api/dcim/cables/` now accept a `terminations` object keyed by side (`a`/`b`) then 1-indexed connector number; each slot value is either `{"object_type": "<app.model>", "id": "<uuid>"}` to plug in (or replace) that connector's termination, or `null` to delete the existing row at that connector. Sides and connectors omitted from the payload are left untouched (PATCH-style merge semantics, with explicit `null` as the delete sentinel). The entire payload is applied in a single transaction; per-row validation is delegated to `CableToCableTerminationSerializer` so model-level errors come back as 400.
- [#9051](https://github.com/nautobot/nautobot/issues/9051) - Added `nautobot-server create_breakout_demo_data` command.
- [#9065](https://github.com/nautobot/nautobot/issues/9065) - Added the `IPAddressRange` model to represent a contiguous span of IP addresses within a parent Prefix, without creating individual IPAddress records for each address.
- [#9078](https://github.com/nautobot/nautobot/issues/9078) - Reworked the "Connection" panel on `Interface`, `ConsolePort`, `ConsoleServerPort`, `PowerPort`, `PowerOutlet`, `FrontPort`, `RearPort`, `CircuitTermination`, and `PowerFeed` detail views to show *all* cable peers and *all* connected endpoints of a multi-termination ("breakout") cable rather than only the first. Each line shows a type icon and the resolved-path reachability where applicable.
- [#9078](https://github.com/nautobot/nautobot/issues/9078) - Added per-type `<Type> Endpoints` panels to the `Interface`, `ConsolePort`, `ConsoleServerPort`, `PowerPort`, and `PowerOutlet` detail views, listing the details of every connected endpoint grouped by type.
- [#9078](https://github.com/nautobot/nautobot/issues/9078) - Added a reusable `nautobot.apps.ui.ConnectionPanel` UI component that renders a `CableTermination`'s cable, cable peers, and connected endpoints as a detail panel.
- [#9078](https://github.com/nautobot/nautobot/issues/9078) - Added a reusable `nautobot.apps.ui.ConnectedEndpointsPanel` UI component, and used it to add per-type connected-endpoint tables to the `CircuitTermination` detail view.
- [#9093](https://github.com/nautobot/nautobot/issues/9093) - Added "Cable Peer" and "Connection" columns to `CircuitTerminationTable`.
- [#9095](https://github.com/nautobot/nautobot/issues/9095) - Added standard CRUD UI views (list, detail, add/edit, delete, bulk edit/delete) for the IPAddressRange model.
- [#9095](https://github.com/nautobot/nautobot/issues/9095) - Added an "IP Address Ranges" tab to the Prefix detail view listing the ranges contained within a Prefix.
- [#9095](https://github.com/nautobot/nautobot/issues/9095) - Added an IP Address Ranges panel to the Role detail view for roles associated with the IPAddressRange content type.
- [#9095](https://github.com/nautobot/nautobot/issues/9095) - Added REST API for the IPAddressRange model.
- [#9095](https://github.com/nautobot/nautobot/issues/9095) - Added IPAddressRange filtering by name, namespace, parent Prefix, start/end address, and by an address contained within a range.
- [#9105](https://github.com/nautobot/nautobot/issues/9105) - Added graphql type object `IPAddressRangeType`.
- [#9108](https://github.com/nautobot/nautobot/issues/9108) - Added a `breakout_position` field to `Interface` to map a child (sub-)interface to a specific position on its parent interface's breakout-cable trunk connector.
- [#9108](https://github.com/nautobot/nautobot/issues/9108) - Added indication of breakout child-interface position mapping in the cable-peer and connection table columns, the parent and child interface detail views, and the cable trace SVG renderer.
- [#9108](https://github.com/nautobot/nautobot/issues/9108) - Added support for path tracing from a trunk interface's subinterface.
- [#9110](https://github.com/nautobot/nautobot/issues/9110) - Added utilization reporting for IP Address Ranges, showing the percentage of addresses within a range occupied by IP Addresses.
- [#9121](https://github.com/nautobot/nautobot/issues/9121) - Added a reusable `copy_button` template tag for rendering hover copy-to-clipboard buttons.
- [#9126](https://github.com/nautobot/nautobot/issues/9126) - Added a `NAUTOBOT_EDITION` setting reflecting the installed edition (Community, Professional, or Enterprise).
- [#9126](https://github.com/nautobot/nautobot/issues/9126) - Added a `navbar_icon` branding key to `BRANDING_FILEPATHS` for customizing the navbar icon independently of the favicon.
- [#9147](https://github.com/nautobot/nautobot/issues/9147) - Added rendering of IP Ranges inline within the IP Addresses tab of the Prefix detail view, including nested available-IP blocks and subtree indentation for contained addresses.
- [#9158](https://github.com/nautobot/nautobot/issues/9158) - Added a utilization bar to the IP Address Range detail view, showing the percentage of addresses in the range that are assigned to IPAddress objects.
- [#9158](https://github.com/nautobot/nautobot/issues/9158) - Added a table of contained IP Addresses to the IP Address Range detail view, with an "Add IP Address" button pre-filled with the first available address in the range; the table is hidden for exclusive ranges and button "Add IP Address" is hidden when no addresses remain available.
- [#9171](https://github.com/nautobot/nautobot/issues/9171) - Added "More..." button to the live search results list if there are more entries to be displayed.
- [#9177](https://github.com/nautobot/nautobot/issues/9177) - Updated the login page appearance and added the Nautobot edition to the About page.

### Changed in v3.2.0b1

- [#8610](https://github.com/nautobot/nautobot/issues/8610) - Changed `ObjectMetadata.assigned_object_type` to `on_delete=CASCADE`; deleting a `ContentType` now cascades to its `ObjectMetadata` records instead of nulling them out.
- [#8911](https://github.com/nautobot/nautobot/issues/8911) - Moved `nautobot.dcim.elevations` module to `nautobot.dcim.svg.rack_elevation`.
- [#8911](https://github.com/nautobot/nautobot/issues/8911) - Moved `nautobot.dcim.breakout_diagram` module to `nautobot.dcim.svg.cable_breakout`.
- [#8911](https://github.com/nautobot/nautobot/issues/8911) - Changed `/dcim/cable-breakout-types/mapping-editor/` HTMX endpoint from GET to POST to avoid problems with complex mappingst.
- [#8921](https://github.com/nautobot/nautobot/issues/8921) - `job_kwargs` is now a required parameter for `create_schedule`, `enqueue_job`, `execute_job` and `run_job_for_testing`. Previously optional, this argument is now mandatory to ensure consistent job configuration and avoid implicit defaults. Calls that rely on `**extra_kwargs` to provide job inputs will still work, but will emit a warning. This fallback will be removed in a future release.
- [#8921](https://github.com/nautobot/nautobot/issues/8921) - Updated `runjob` command data behavior. The default value is now `{}` instead of allowing `None`.
- [#8921](https://github.com/nautobot/nautobot/issues/8921) - Added stricter validation for job inputs in `validate_job_and_job_data`. Now raises ValueError if `data=None`.
- [#8921](https://github.com/nautobot/nautobot/issues/8921) - Added stricter validation for job inputs in `apply_sync`. Now raises ValueError if `entry.kwargs=None`.
- [#8924](https://github.com/nautobot/nautobot/issues/8924) - Renamed `CableBreakoutType` model to `CableType` to reflect a broader scope; renamed associated classes, URL paths, and permissions accordingly.
- [#8935](https://github.com/nautobot/nautobot/issues/8935) - Recreated migrations file due to change filed `terminated_at` to `date_terminated` in JobResult model.
- [#8935](https://github.com/nautobot/nautobot/issues/8935) - Changed job result log level to FAILURE from INFO in revoke flow.
- [#8935](https://github.com/nautobot/nautobot/issues/8935) - Changed `job_label.html`. Added handling for all other current JobResultStatusChoices values.
- [#8935](https://github.com/nautobot/nautobot/issues/8935) - Changed `render_jobresult_status`. Added handling for all other current JobResultStatusChoices values.
- [#8935](https://github.com/nautobot/nautobot/issues/8935) - `Result Data` in `Summary of Result` panel on JobResult detail view is only rendered when job result status is SUCCESS.
- [#8935](https://github.com/nautobot/nautobot/issues/8935) - `Duration` in `Summary of Result` panel on JobResult detail view is only rendered when `date_done` and `date_started` are set.
- [#8946](https://github.com/nautobot/nautobot/issues/8946) - Job revocation (both UI and API) now requires the `extras.run_job` permission.
- [#8946](https://github.com/nautobot/nautobot/issues/8946) - All users must have the `extras.run_job` permission to revoke a job. Non-staff users can only revoke jobs they themselves submitted. Staff users can additionally revoke jobs submitted by other users.
- [#8946](https://github.com/nautobot/nautobot/issues/8946) - `RevokeFactory.get_strategy()` no longer raises `ValueError` for unknown queue types. It returns an `UnknownStrategy` instance instead.
- [#8963](https://github.com/nautobot/nautobot/issues/8963) - Changed homepage layout from CSS `columns` to Bootstrap grid.
- [#8974](https://github.com/nautobot/nautobot/issues/8974) - Replaced the `cable` `ForeignKey` on the `CableTermination` abstract model with a new `CableToCableTermination` join table, allowing more than two terminations per cable for breakout-cable support. The `cable` attribute is preserved as a read-only property; backward-compatibility query translation for `Interface.objects.filter(cable=...)`, `select_related("cable")`, etc. is provided with a `DeprecationWarning` pointing at the new `cable_termination__cable[...]` paths. Note: `Q(cable=...)`, `order_by("cable")`, and `values("cable")` are not translated. Assignments to `Cable.termination_a`/`Cable.termination_b` (and their `*_type`/`*_id` counterparts) on unsaved instances continue to work and are materialized into `CableToCableTermination` rows on save.
- [#8974](https://github.com/nautobot/nautobot/issues/8974) - Removed the private `_cable_peer`, `_cable_peer_type`, and `_cable_peer_id` cache fields from the `CableTermination` abstract model; cable peers are now resolved on demand via the `CableToCableTermination` join table. Public APIs (`get_cable_peer()`, REST `cable_peer`/`cable_peer_type`, GraphQL `cable_peer_*` fields) are unchanged.
- [#8974](https://github.com/nautobot/nautobot/issues/8974) - Replaced the private `_path` `ForeignKey` on the `PathEndpoint` abstract model with a `cable_paths` `GenericRelation` resolving through `CablePath.origin`. The public `path`, `trace()`, and `connected_endpoint` accessors are unchanged. Query usages of `_path__...` should be rewritten as `cable_paths__...` (a multi-row reverse relation, so `distinct()` is typically required for `filter()` / `count()` / `exclude()`).
- [#8974](https://github.com/nautobot/nautobot/issues/8974) - Extended `CablePath` to support breakout cables. Each row now records a `peer_connector` integer identifying which lane it represents, and `CablePath.from_origin()` / `get_cable_peer()` accept a `peer_connector=<int>` kwarg for lane-specific peer lookup. `disconnect_termination()` and `rebuild_paths()` are lane-aware. The `CableType.mapping`-driven fan-out was reworked to iterate distinct peer-side connectors, eliminating redundant `CablePath` rows for cable shapes like 1×N → M×K where multiple lanes land on the same peer-side connector.
- [#8974](https://github.com/nautobot/nautobot/issues/8974) - With the addition of breakout-cable support, `Cable.termination_a`/`termination_b` (and `connected_lanes`, `get_lanes()`) now specifically refer to connector 1 on each side rather than "the" termination on that side; for non-breakout cables this is the same termination as before. `Cable.total_lanes` returns `1` for non-breakout cables. Callers that need to enumerate every termination on a breakout cable should iterate `cable.terminations` (or the typed M2M fields like `cable.interfaces`) instead.
- [#8974](https://github.com/nautobot/nautobot/issues/8974) - Changed `CableType` to reject edits to `a_connectors`, `b_connectors`, or `total_lanes` (and related breakout attributes) once any `Cable` of that type exists, since changing the connector layout would invalidate existing terminations and paths. The fields remain editable while no cables reference the `CableType`.
- [#8974](https://github.com/nautobot/nautobot/issues/8974) - Reworked `InterfaceConnectionsListView` (UI), `InterfaceConnectionViewSet` (REST API), `InterfaceConnectionTable`, `InterfaceConnectionFilterSet`, and the homepage "Interfaces" connection counter to operate over `CablePath` rows rather than `Interface` rows. Each breakout-cable lane now surfaces as its own connection row (previously only the primary lane was shown), and filter parameters (`device_id`, `device`, `location`) now match either endpoint of a connection rather than only the canonical "A" side. The REST API JSON response shape (`interface_a`, `interface_b`, `connected_endpoint_reachable`) is unchanged.
- [#8974](https://github.com/nautobot/nautobot/issues/8974) - Replaced the per-component `ConnectCableTo*Form` classes (one per termination type) and the `dcim/cable_connect.html` template with a single unified `cable_add` form. The per-port `<port>_connect` URLs still exist but now redirect into `cable_add` with A-side identity and an optional B-side type pre-selection. The unified form is HTMX-driven (previously jQuery-based) and selects a B-side termination type compatible with the A-side as the default (e.g. `PowerPort` → `PowerOutlet`) rather than always defaulting to `Interface`.
- [#8974](https://github.com/nautobot/nautobot/issues/8974) - Consolidated the per-termination-type "Connect to …" entries in device-component row-action dropdowns and in the "Connection" panel of device-component, power-feed, and circuit-termination detail views into a single "Add Cable" action linking into the unified `cable_add` form. The cable-actions dropdown renames `Disconnect` to `Detach cable from <termination>` and refreshes icons to avoid clashes with the surrounding `Edit/Delete <component>` entries.
- [#8974](https://github.com/nautobot/nautobot/issues/8974) - Reworked the `Cable` list view's `CableTable`: added a `cable_type` column, added multi-termination `terminations_a`/`terminations_b` columns that render every termination on each side of the cable, and added an `actions` column. The single-termination columns `termination_a` (etc.) remain available for backwards compatibility as opt-in column choices.
- [#8974](https://github.com/nautobot/nautobot/issues/8974) - Changed the UI-framework `components/panel/footer_content_table.html` partial to default the `return_url` on footer-button bulk actions to the current page (preserving query string), so submitting a bulk action from a detail-view panel returns to that panel rather than the model's generic list view. Existing `action-url` values that already specify `return_url` are left untouched.
- [#8974](https://github.com/nautobot/nautobot/issues/8974) - Changed the seeded default "AOC Fanout" `CableType` records (1x2, 1x4, 1x8, 2x4) to set `has_embedded_transceivers=True`.
- [#8991](https://github.com/nautobot/nautobot/issues/8991) - Updated extras migration 0143 so that all changes related to the “revoke” action would be included in a single file.
- [#8991](https://github.com/nautobot/nautobot/issues/8991) - Changed `is_alive` to `liveness` with 3 state: `JobLiveness.RUNNING`, `JobLiveness.NOT_RUNNING` and `JobLiveness.UNKNOWN`.
- [#9019](https://github.com/nautobot/nautobot/issues/9019) - Replaced the per-type many-to-many fields (`interfaces`, `front_ports`, `rear_ports`, `circuit_terminations`, `console_ports`, `console_server_ports`, `power_feeds`, `power_outlets`, `power_ports`) on the `Cable` REST API serializer with a single `terminations` field keyed by side (`a`/`b`) then 1-indexed connector number, mirroring the physical structure of the cable. Each slot value is the brief representation (default depth) or the full nested serializer (`?depth>=1`) of the termination at that connector — polymorphic across Interface / CircuitTermination / ConsolePort / FrontPort / RearPort / PowerPort / PowerOutlet / PowerFeed — and uncabled connectors on breakout cables are surfaced as explicit `null` slots. `terminations` is suppressed in CSV exports (the format can't meaningfully flatten the nested per-slot structure); use `/api/dcim/cables-to-cable-terminations/?cable=<pk>` for per-row CSV detail. Extended `BaseModelSerializer.get_field_names` to drop reverse-FK (one-to-many) model accessors alongside many-to-many accessors when a serializer is rendered as nested or for CSV — previously only forward `ManyToManyDescriptor` fields were filtered.
- [#9051](https://github.com/nautobot/nautobot/issues/9051) - The cable path trace view now renders the trace as a single server-side SVG diagram, replacing the previous per-object-type HTML templates.
- [#9051](https://github.com/nautobot/nautobot/issues/9051) - Cable path trace diagrams now depict breakout cable fan-outs, rendering each downstream lane as its own branch, including unconnected lanes.
- [#9060](https://github.com/nautobot/nautobot/issues/9060) - Module Bays and Modular Components (Interfaces, FrontPorts, etc) set root device at every level in the hierarchy.
- [#9065](https://github.com/nautobot/nautobot/issues/9065) - Changed `IPAddress.clean()` to reject creating an IP address that falls within an exclusive IPAddressRange.
- [#9065](https://github.com/nautobot/nautobot/issues/9065) - Changed `Prefix.clean()` to reject network/prefix-length edits that would leave a contained IPAddressRange no longer fully within the Prefix.
- [#9093](https://github.com/nautobot/nautobot/issues/9093) - Improved rendering of `terminations_a` and `terminations_b` columns in `CableTable`.
- [#9093](https://github.com/nautobot/nautobot/issues/9093) - Adjusted rendering of `cable_peer` and `connection` columns in cable termination tables.
- [#9093](https://github.com/nautobot/nautobot/issues/9093) - Standardized device component icons across various tables and menus.
- [#9093](https://github.com/nautobot/nautobot/issues/9093) - Updated styling of populated rows in device DeviceBay and ModuleBay tables.
- [#9095](https://github.com/nautobot/nautobot/issues/9095) - Changed `related_name` on Tenant and Prefix models from `ip_ranges` to `ip_address_ranges`.
- [#9110](https://github.com/nautobot/nautobot/issues/9110) - Changed Prefix utilization to include IP Address Ranges marked as fully utilized, without double-counting IP Addresses that fall within such a range.
- [#9110](https://github.com/nautobot/nautobot/issues/9110) - Changed the Prefix available-IP calculation to exclude addresses covered by exclusive IP Address Ranges.
- [#9110](https://github.com/nautobot/nautobot/issues/9110) - Changed Prefix saves to reparent contained IP Address Ranges when a Prefix's network is created or modified, keeping each range attached to the closest Prefix that fully contains it.
- [#9126](https://github.com/nautobot/nautobot/issues/9126) - Changed the navbar icon and favicon to reflect the installed Nautobot edition when no custom branding is configured.
- [#9147](https://github.com/nautobot/nautobot/issues/9147) - Changed `add_available_ipaddresses` to interleave IP Range rows and to account for exclusive ranges when computing available IP blocks.
- [#9158](https://github.com/nautobot/nautobot/issues/9158) - Changed text in `ButtonsColumn` to include model verbose name in "details" and "change log" actions.
- [#9159](https://github.com/nautobot/nautobot/issues/9159) - Changed default sorting of ModularComponentModels to `device_id`, `module_id`, `_name` to avoid full table scan of `dcim_device`.
- [#9160](https://github.com/nautobot/nautobot/issues/9160) - Changed `Cable.get_lanes()` and `Interface.get_breakout_lane()` to return `CableLane` and `BreakoutLane` dataclasses instead of dicts.
- [#9160](https://github.com/nautobot/nautobot/issues/9160) - Removed redundant tooltip from Cable breakout diagram.
- [#9160](https://github.com/nautobot/nautobot/issues/9160) - Made the termination labels in the Cable breakout diagram clickable, linking each connector to its connected termination and its parent.
- [#9160](https://github.com/nautobot/nautobot/issues/9160) - Refined rendering of breakout cables in trace SVG.
- [#9167](https://github.com/nautobot/nautobot/issues/9167) - Updated homepage panels wrapping order in two-column layout, for screens between 1008px and 1440px.
- [#9169](https://github.com/nautobot/nautobot/issues/9169) - Improved performance of `IPAddress` and `IPAddressRange` validation by memoizing closest-parent Prefix lookups per namespace and host, avoiding redundant database queries between `clean()` and `save()`.
- [#9174](https://github.com/nautobot/nautobot/issues/9174) - Change `CableSerializer` `get_terminations` and `_parse_terminations_payload` Structure. New json structure pushes nested connectors up a level and combine with the side key.
- [#9180](https://github.com/nautobot/nautobot/issues/9180) - Updated the default breakout cable types to the most basic set.
- [#9187](https://github.com/nautobot/nautobot/issues/9187) - Changed how the active Nautobot edition is determined.
- [#9193](https://github.com/nautobot/nautobot/issues/9193) - Re-organized `result` field in JobResult UI to ensure consistency with the API.
- [#9197](https://github.com/nautobot/nautobot/issues/9197) - Changed the Interface Connections list view and REST API (`/dcim/interface-connections/`) to group a breakout cable's lanes together: the trunk interface is canonicalized onto the A side (shown once in the UI) and its fan-out endpoints are returned as consecutive rows on the B side, instead of being scattered. Added `origin_fans_out` and `destination_fans_out` fields to `CablePath` to support this without per-row queries, and standardized the shared queryset/ordering via `CablePath.interface_connections()`.

### Deprecated in v3.2.0b1

- [#8921](https://github.com/nautobot/nautobot/issues/8921) - Deprecated passing job parameters as loose `**extra_kwargs` to `JobResult.enqueue_job()`, `JobResult.execute_job()`, and `nautobot.apps.testing.run_job_for_testing()`. Job parameters must now be passed as a single `job_kwargs` dict argument. The legacy calling style still works for backward compatibility but logs a warning, and will be removed in a future release.

### Removed in v3.2.0b1

- [#8991](https://github.com/nautobot/nautobot/issues/8991) - Removed `should_reap` method from `JobRevokeStrategy` class.
- [#9199](https://github.com/nautobot/nautobot/issues/9199) - Removed `CableToCableTermination._termination_device`, not needed any more.

### Fixed in v3.2.0b1

- [#8454](https://github.com/nautobot/nautobot/issues/8454) - Fixed "Too many tables" exception when exporting certain models to CSV from MySQL.
- [#8911](https://github.com/nautobot/nautobot/issues/8911) - Fixed `BreakoutDiagramSVG` to render multiple lanes between a pair of connectors when appropriate.
- [#8911](https://github.com/nautobot/nautobot/issues/8911) - Fixed `BreakoutDiagramSVG` to better render wide lane labels.
- [#8913](https://github.com/nautobot/nautobot/issues/8913) - Fixed `store_result` writing null instead of empty collections for `task_args`, `task_kwargs`, and `celery_kwargs` when no arguments were provided.
- [#8982](https://github.com/nautobot/nautobot/issues/8982) - Fixed a case where the Revoke Job button on the Job Result detail view wouldn't correctly refresh once status is ready.
- [#9001](https://github.com/nautobot/nautobot/issues/9001) - Fixed the `GET` revoke API behavior for JobResult objects already in a terminal state. The endpoint now returns `200 OK` with a `None` preview instead of presenting a `REAP` or `TERMINATE` action. `POST` requests against completed jobs continue to return `409 Conflict`.
- [#9036](https://github.com/nautobot/nautobot/issues/9036) - Fixed missing `form-control` styling on the `Value` and `Assigned object` fields in the ObjectMetadata create/edit form.
- [#9051](https://github.com/nautobot/nautobot/issues/9051) - Fixed cable path tracing through a mid-path breakout cable so that a lane returning to a single trunk peer is followed through, rather than always reporting the path as split.
- [#9051](https://github.com/nautobot/nautobot/issues/9051) - Fixed the list of selectable next hops shown for a split cable path when the split originates at a front port; previously only splits at a rear port were handled.
- [#9093](https://github.com/nautobot/nautobot/issues/9093) - Fixed incorrect logic for selecting variant icons for Interfaces in `DeviceModuleInterfaceTable`.
- [#9130](https://github.com/nautobot/nautobot/issues/9130) - Fixed an error when trying to serialize a many-to-many relationship to a model that supports cable terminations.
- [#9160](https://github.com/nautobot/nautobot/issues/9160) - Fixed errors when creating extremely long cables.
- [#9160](https://github.com/nautobot/nautobot/issues/9160) - Fixed the `trace_paths` management command (run by `nautobot-server post_upgrade`) not regenerating missing breakout cable fan-out lane paths.
- [#9160](https://github.com/nautobot/nautobot/issues/9160) - Fixed the `trace_paths` management command aborting partway through when it encountered inconsistent existing cable data (such as a cabling loop); it now skips the affected origin and continues.
- [#9160](https://github.com/nautobot/nautobot/issues/9160) - Fixed layout of connection tables (in both the cable detail view and the HTMX connection-edit form) for breakout cables with a meshed connector mapping, such as a polarity-shuffled 2x2.
- [#9160](https://github.com/nautobot/nautobot/issues/9160) - Fixed missing validation that allowed a multi-connector (breakout) cable type to be attached to termination types that don't support breakout (such as console or power terminations).
- [#9160](https://github.com/nautobot/nautobot/issues/9160) - Fixed the cable edit form disallowing all cable types for cables with non-breakout-eligible terminations; single-connector cable types are now permitted.
- [#9160](https://github.com/nautobot/nautobot/issues/9160) - Fixed the per-row cable actions (mark cable connected/planned, detach cable) not working in the device-component list views (interfaces, console/power ports, front/rear ports).
- [#9160](https://github.com/nautobot/nautobot/issues/9160) - Fixed cable-status row coloring not being applied in the device-component list views.
- [#9160](https://github.com/nautobot/nautobot/issues/9160) - Fixed an exception when attempting to improperly create an Interface with a `breakout_position` but no `parent_interface`.
- [#9160](https://github.com/nautobot/nautobot/issues/9160) - Fixed missing `breakout_position` form field when editing an existing Interface.
- [#9160](https://github.com/nautobot/nautobot/issues/9160) - Fixed an exception when tracing a path including a partially-disconnected cable.
- [#9178](https://github.com/nautobot/nautobot/issues/9178) - Added backward-compatibility translation of legacy `termination_[a|b]_type`/`termination_[a|b]_id`) lookups on `Cable.objects` queries such as `filter()`, `get()`, and `get_or_create()`.
- [#9178](https://github.com/nautobot/nautobot/issues/9178) - Corrected incorrect `stacklevel` value for DeprecationWarnings emitted by cable-query backwards-compatibility logic.
- [#9185](https://github.com/nautobot/nautobot/issues/9185) - Fixed job revocation incorrectly overwriting an already-completed job's status (e.g. SUCCESS to REVOKED); the revoke write is now guarded against the job's terminal state under a row lock.
- [#9195](https://github.com/nautobot/nautobot/issues/9195) - Fixed an exception when rendering IP Address detail view "Interfaces" tab.
- [#9195](https://github.com/nautobot/nautobot/issues/9195) - Fixed missing interface-type icons in IP Address detail view "Interfaces" tab table.
- [#9195](https://github.com/nautobot/nautobot/issues/9195) - Fixed missing "actions" column in IP Address detail view "Interfaces" tab table.
- [#9195](https://github.com/nautobot/nautobot/issues/9195) - Fixed inability to scroll horizontally in IP Address detail view "Interfaces" and "VM Interfaces" tabs tables.
- [#9202](https://github.com/nautobot/nautobot/issues/9202) - Fixed `AttributeError` in `cable_status_color_css()` when rendering a virtual sub-interface whose parent has a cable but which is not a breakout child.

### Dependencies in v3.2.0b1

- [#8910](https://github.com/nautobot/nautobot/issues/8910) - Added Fuse.js as a UI dependency.
- [#8963](https://github.com/nautobot/nautobot/issues/8963) - Added `htmx-ext-json-enc` as a UI dependency.
- [#8991](https://github.com/nautobot/nautobot/issues/8991) - Updated dependency `kubernetes` to `>=36.0.1,<37`.

### Documentation in v3.2.0b1

- [#8991](https://github.com/nautobot/nautobot/issues/8991) - Replaced core development guide `Minikube Dev Environment for K8s Jobs` by `Running a Nautobot Job on a Local Kubernetes Cluster` that walks through running a Nautobot Job inside a Kubernetes job pod while the rest of the dev stack (Django, Postgres, Redis) runs locally in Docker Compose.
- [#9065](https://github.com/nautobot/nautobot/issues/9065) - Added documentation about new `IPAddressRange` model.
- [#9065](https://github.com/nautobot/nautobot/issues/9065) - Updated `Prefix` and `IPAddress` documentation.
- [#9164](https://github.com/nautobot/nautobot/issues/9164) - Added documentation and release-note content about the enhancements and changes to the cable data model.
- [#9167](https://github.com/nautobot/nautobot/issues/9167) - Added Homepage Panels documentation under User Guide → Getting Started.
- [#9200](https://github.com/nautobot/nautobot/issues/9200) - Update the 3.2 release documentation with the new features.

### Housekeeping in v3.2.0b1

- [#8610](https://github.com/nautobot/nautobot/issues/8610) - Refactored ObjectMetadataUIViewSet model related UI views to use `NautobotUIViewSet` and `UI Component Framework`.
- [#8789](https://github.com/nautobot/nautobot/issues/8789) - Refactored ConsolePortTemplate model related UI views to use `NautobotUIViewSet`.
- [#8936](https://github.com/nautobot/nautobot/issues/8936) - Refactored ConsolePort model related UI views to use `NautobotUIViewSet`.
- [#8974](https://github.com/nautobot/nautobot/issues/8974) - Added `get_display_verbose_name_plural()`, `get_instance_display_text_content(instance)`, and `get_instance_display_strings(instance)` override hooks to `ViewTestCases.ListObjectsViewTestCase` for test cases whose list view's underlying queryset is over a different model than `self.model`. All three default to the previous hard-coded behavior, so existing test cases need no changes.
- [#8991](https://github.com/nautobot/nautobot/issues/8991) - Added helper method `build_kubernetes_api_client` to `extras.utils` to avoid duplication.
- [#8991](https://github.com/nautobot/nautobot/issues/8991) - Added `--env`/`-e` option to `invoke start`, `invoke debug` and `invoke restart` to pass environment variables to docker compose (e.g. `-e KEY=VALUE`, can be repeated).
- [#8991](https://github.com/nautobot/nautobot/issues/8991) - Added internal `NAUTOBOT_KUBERNETES_VERIFY_SSL_INTERNAL` environment variable to opt out of TLS verification on the Kubernetes API connection during local development.
- [#8992](https://github.com/nautobot/nautobot/issues/8992) - Refactored ConsoleServerPortTemplate model related UI views to use `NautobotUIViewSet`.
- [#9023](https://github.com/nautobot/nautobot/issues/9023) - Refactored PowerPortTemplate model related UI views to use `NautobotUIViewSet`.
- [#9033](https://github.com/nautobot/nautobot/issues/9033) - Refactored InventoryItem model related UI views to use `NautobotUIViewSet` and `UI Component Framework`.
- [#9034](https://github.com/nautobot/nautobot/issues/9034) - Refactored DeviceBay and DeviceBayTemplate model related UI views to use `NautobotUIViewSet`, and migrated the DeviceBay detail view to the `UI component framework`.
- [#9051](https://github.com/nautobot/nautobot/issues/9051) - Enhanced `invoke cli` task to support an optional `--command 'command'` parameter.
- [#9053](https://github.com/nautobot/nautobot/issues/9053) - Moved the ObjectMetadata value-widget to a detail action on `MetadataTypeUIViewSet`.
- [#9064](https://github.com/nautobot/nautobot/issues/9064) - Refactored InterfaceTemplate model related UI views to use `NautobotUIViewSet`.
- [#9073](https://github.com/nautobot/nautobot/issues/9073) - Refactored PowerPort model related UI views to use `NautobotUIViewSet`.
- [#9074](https://github.com/nautobot/nautobot/issues/9074) - Refactored FrontPortTemplate model related UI views to use `NautobotUIViewSet`.
- [#9075](https://github.com/nautobot/nautobot/issues/9075) - Refactored ConsolePort model related UI views to use `UI component framework`.
- [#9076](https://github.com/nautobot/nautobot/issues/9076) - Refactored RearPortTemplate model related UI views to use `NautobotUIViewSet`
- [#9083](https://github.com/nautobot/nautobot/issues/9083) - Refactored PowerOutletTemplate model related UI views to use `NautobotUIViewSet`.
- [#9085](https://github.com/nautobot/nautobot/issues/9085) - Refactored ConsoleServerPort model related UI views to use `NautobotUIViewSet`.
- [#9087](https://github.com/nautobot/nautobot/issues/9087) - Refactored FrontPort model related UI views to use `NautobotUIViewSet`.
- [#9092](https://github.com/nautobot/nautobot/issues/9092) - Refactored PowerOutlet model related UI views to use `NautobotUIViewSet`.
- [#9093](https://github.com/nautobot/nautobot/issues/9093) - Consolidated most icon-selection logic for device component rendering in tables and menus.
- [#9093](https://github.com/nautobot/nautobot/issues/9093) - Changed `termination_type_icon` template-tag method from a tag to a filter for simpler usage.
- [#9104](https://github.com/nautobot/nautobot/issues/9104) - Refactored PowerPort model related UI views to use `UI component framework`.
- [#9106](https://github.com/nautobot/nautobot/issues/9106) - Refactored RearPort model related UI views to use `NautobotUIViewSet`.
- [#9109](https://github.com/nautobot/nautobot/issues/9109) - Refactored PowerOutlet model related UI views to use `UI component framework`.
- [#9112](https://github.com/nautobot/nautobot/issues/9112) - Updated `testing/views.py` logic to account for nullable name field.
- [#9137](https://github.com/nautobot/nautobot/issues/9137) - Fixed various causes of inconsistent factory data being produced by the `generate_test_data` management command.
- [#9163](https://github.com/nautobot/nautobot/issues/9163) - Fixed some incorrect logic in the generic bulk delete view test.
- [#9168](https://github.com/nautobot/nautobot/issues/9168) - Refactored ConsoleServerPort model related UI views to use `UI component framework`.
- [#9169](https://github.com/nautobot/nautobot/issues/9169) - Extracted shared namespace and parent-Prefix resolution logic from `IPAddress` and `IPAddressRange` into a reusable `NamespaceParentedModelMixin`.
- [#9169](https://github.com/nautobot/nautobot/issues/9169) - Improved performance of the prefix IP Addresses view for prefixes with many IP Address Ranges.
- [#9175](https://github.com/nautobot/nautobot/issues/9175) - Refactored RearPort model related UI views to use `UI component framework`.
- [#9184](https://github.com/nautobot/nautobot/issues/9184) - Refactored FrontPort model related UI views to use `UI component framework`.
