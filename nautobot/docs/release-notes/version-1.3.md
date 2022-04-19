<!-- markdownlint-disable MD024 -->
# Nautobot v1.3

This document describes all new features and changes in Nautobot 1.3.

If you are a user migrating from NetBox to Nautobot, please refer to the ["Migrating from NetBox"](../installation/migrating-from-netbox.md) documentation.

## Release Overview

### Added

#### Dynamic Group Model ([#896](https://github.com/nautobot/nautobot/issues/896))

A new data model for representing [dynamic groups](../models/extras/dynamicgroup.md) of objects has been implemented. Dynamic groups can be used to organize objects together by matching criteria such as their site location or region, for example, and are dynamically updated whenever new matching objects are created, or existing objects are updated.

For the initial release only dynamic groups of `Device` and `VirtualMachine` objects are supported.

#### Extend FilterSets and Filter Forms via Plugins ([#1470](https://github.com/nautobot/nautobot/issues/1470))

Plugins can now extend existing FilterSets and Filter Forms. This allows plugins to provide alternative lookup methods or custom queries in the UI or API that may not already exist today.

You can refer to the [plugin development guide](../plugins/development.md#extending-filters) on how to create new filters and fields.

#### GraphQL Pagination ([#1109](https://github.com/nautobot/nautobot/issues/1109))

GraphQL list queries can now be paginated by specifying the filter parameters `limit` and `offset`. Refer to the [GraphQL user guide](../user-guides/graphql.md#filtering-queries) for examples.

#### Job Database Model ([#1001](https://github.com/nautobot/nautobot/issues/1001))

Installed Jobs are now represented by a data model in the Nautobot database. This allows for new functionality including:

- The Jobs listing UI view can now be filtered and searched like most other Nautobot table/list views.
- Job attributes (name, description, approval requirements, etc.) can now be managed via the Nautobot UI by an administrator or user with appropriate permissions to customize or override the attributes defined in the Job source code.
- Jobs can now be identified by a `slug` as well as by their `class_path`.
- A new set of REST API endpoints have been added to `/api/extras/jobs/<uuid>/`. The existing `/api/extras/jobs/<class_path>/` REST API endpoints continue to work but should be considered as deprecated.
    - A new version of the REST API `/api/extras/jobs/` list endpoint has been implemented as well, but by default this endpoint continues to demonstrate the pre-1.3 behavior unless the REST API client explicitly requests API `version=1.3`. See the section on REST API versioning, below, for more details.
- As a minor security measure, newly installed Jobs default to `enabled = False`, preventing them from being run until an administrator or user with appropriate permissions updates them to be enabled for running.

!!! note
    As a convenience measure, when initially upgrading to Nautobot 1.3.x, any existing Jobs that have been run or scheduled previously (i.e., have at least one associated JobResult and/or ScheduledJob record) will instead default to `enabled = True` so that they may continue to be run without requiring changes.

For more details please refer to the [Jobs feature documentation](../additional-features/jobs.md) as well as the [Job data model documentation](../models/extras/job.md).

#### JSON Type for Custom Fields ([#897](https://github.com/nautobot/nautobot/issues/897))

Custom fields can now have a type of "json". Fields of this type can be used to store arbitrary JSON data.

#### Natural Indexing for Common Lookups ([#1638](https://github.com/nautobot/nautobot/issues/1638))

Many fields have had indexing added to them as well as index togethers on `ObjectChange` fields. This should provide a noticeable performance improvement when filtering and doing lookups.

!!! note
    This is going to perform several migrations to add all of the indexes. On MySQL databases and tables with 1M+ records this can take a few minutes. Every environment is different but it should be expected for this upgrade to take some time.

#### Overlapping/Multiple NAT Support ([#630](https://github.com/nautobot/nautobot/issues/630))

IP addresses can now be associated with multiple outside NAT IP addresses. To do this, set more than one IP Address to have the same NAT inside IP address.

A new version of the REST API `/api/ipam/ip-addresses/*` endpoints have been implemented as well, but by default this endpoint continues to demonstrate the pre-1.3 behavior unless the REST API client explicitly requests API `version=1.3`. See the section on REST API versioning, below, for more details.

!!! note
    There are some guardrails on this feature to support backwards compatibility. If you consume the REST API without specifying the version header or query argument and start associating multiple IPs to have the same NAT inside IP address, an error will be reported, because the existing REST API schema returns `nat_outside` as a single object, where as 1.3 and beyond will return this as a list.

#### Provider Network Model ([#724](https://github.com/nautobot/nautobot/issues/724))

A [data model](../models/circuits/providernetwork.md) has been added to support representing the termination of a circuit to an external provider's network.

#### Python 3.10 Support ([#1255](https://github.com/nautobot/nautobot/pull/1255))

Python 3.10 is officially supported by Nautobot now, and we are building and publishing Docker images with Python 3.10 now.

#### Regular Expression Support in API Filtering ([#1525](https://github.com/nautobot/nautobot/issues/1525))

[New lookup expressions for using regular expressions](../rest-api/filtering.md#string-fields) to filter objects by string (char) fields in the API have been added to all core filters.

The expressions `re` (regex), `nre` (negated regex), `ire` (case-insensitive regex), and `nire` (negated case-insensitive regex) lookup expressions are now dynamically-generated for filter fields inherited by subclasses of `nautobot.utilities.filters.BaseFilterSet`.

#### REST API Token Provisioning ([#1374](https://github.com/nautobot/nautobot/issues/1374))

Nautobot now has an `/api/users/tokens/` REST API endpoint where a user can provision a new REST API token. This allows a user to gain REST API access without needing to first create a token via the web UI.

```bash
$ curl -X POST \
-H "Accept: application/json; indent=4" \
-u "hankhill:I<3C3H8" \
https://nautobot/api/users/tokens/
```

This endpoint specifically supports Basic Authentication in addition to the other REST API authentication methods.

#### REST API Versioning ([#1465](https://github.com/nautobot/nautobot/issues/1465))

Nautobot's REST API now supports multiple versions, which may be requested by modifying the HTTP Accept header on any requests sent by a REST API client. Details are in the [REST API documentation](../rest-api/overview.md#versioning), but in brief:

- The REST API endpoints that are versioned in the 1.3.0 release are
    - `/api/extras/jobs/` listing endpoint
    - `/api/extras/tags/` create/put/patch endpoints
    - all `/api/ipam/ip-addresses/` endpoints
- All other REST API endpoints are currently non-versioned. However, over time more versioned REST APIs will be developed, so this is important to understand for all REST API consumers.
- If a REST API client does not request a specific REST API version (in other words, requests `Accept: application/json` rather than `Accept: application/json; version=1.3`) the API behavior will be compatible with Nautobot 1.2, at a minimum for the remainder of the Nautobot 1.x release cycle.
- The API behavior may change to a newer default version in a Nautobot major release (such as 2.0).
- To request an updated (non-backwards-compatible) API endpoint, an API version must be requested corresponding at a minimum to the Nautobot `major.minor` version where the updated API endpoint was introduced (so to interact with the updated REST API endpoints mentioned above, `Accept: application/json; version=1.3`).

!!! tip
    As a best practice, when developing a Nautobot REST API integration, your client should _always_ request the current API version it is being developed against, rather than relying on the default API behavior (which may change with a new Nautobot major release, as noted, and which also may not include the latest and greatest API endpoints already available but not yet made default in the current release).

#### Webhook Pre/Post-change Data Added to Request Body ([#330](https://github.com/nautobot/nautobot/issues/330))

Webhooks now provide a snapshot of data before and after a change, as well as the differences between the old and new data. See the default request body section in the [webhook docs](../models/extras/webhook.md#default-request-body).

### Changed

#### Docker Images Now Default to Python 3.7 ([#1252](https://github.com/nautobot/nautobot/pull/1252))

As Python 3.6 has reached end-of-life, the default Docker images published for this release (i.e. `1.3.0`, `stable`, `latest`) have been updated to use Python 3.7 instead.

#### Job Approval Now Controlled By `extras.approve_job` Permission ([#1490](https://github.com/nautobot/nautobot/pull/1490))

Similar to the existing `extras.run_job` permission, a new `extras.approve_job` permission is now enforced by the UI and the REST API when approving scheduled jobs. Only users with this permission can approve or deny approval requests; additionally such users also now require the `extras.view_scheduledjob`, `extras.change_scheduledjob`, and `extras.delete_scheduledjob` permissions as well.

#### OpenAPI 3.0 REST API documentation ([#595](https://github.com/nautobot/nautobot/issues/595))

The online REST API Swagger documentation (`/api/docs/`) has been updated from OpenAPI 2.0 format to OpenAPI 3.0 format and now supports Nautobot's [REST API versioning](#rest-api-versioning-1465) as described above. Try `/api/docs/?api_version=1.3` as an example.

#### Tag restriction by content-type ([#872](https://github.com/nautobot/nautobot/issues/872))

When created, a `Tag` can be associated to one or more model content-types using a many-to-many relationship. The tag will then apply only to models belonging to those associated content-types.

For users migrating from an earlier Nautobot release, any existing tags will default to being enabled for all content-types for compatibility purposes. Individual tags may subsequently edited to remove any content-types that they do not need to apply to.

Note that a Tag created programmatically via the ORM without assigning any `content_types` will not be applicable to any model until content-types are assigned to it.

#### Update Jinja2 to 3.x ([#1474](https://github.com/nautobot/nautobot/pull/1474))

We've updated the Jinja2 dependency from version 2.11 to version 3.0.3. This may affect the syntax of any `nautobot.extras.models.ComputedField` objects in your database... Specifically, the `template` attribute, which is parsed as a Jinja2 template. Please refer to [Jinja2 3.0.x's release notes](https://jinja.palletsprojects.com/en/3.0.x/changes/) to check if any changes might be required in your computed fields' templates.

### Removed

#### Python 3.6 No Longer Supported ([#1268](https://github.com/nautobot/nautobot/issues/1268))

As Python 3.6 has reached end-of-life, and many of Nautobot's dependencies have already dropped support for Python 3.6 as a consequence, Nautobot 1.3 and later do not support installation under Python 3.6.

## v1.3.1 (2022-04-19)

### Changed

- [#1647](https://github.com/nautobot/nautobot/pull/1647) - Changed class inheritance of JobViewSet to be simpler and more self-consistent.

### Fixed

- [#1278](https://github.com/nautobot/nautobot/issues/1278) - Fixed several different errors that could be raised when working with RelationshipAssociations.
- [#1662](https://github.com/nautobot/nautobot/issues/1662) - Fixed nat_outside prefetch on Device API view, and displaying multiple nat_outside entries on VM detail view.

## v1.3.0 (2022-04-18)

### Added

- [#630](https://github.com/nautobot/nautobot/issues/630) - Added support for multiple NAT outside IP addresses.
- [#872](https://github.com/nautobot/nautobot/issues/872) - Added ability to scope tags to content types.
- [#896](https://github.com/nautobot/nautobot/issues/896) - Implemented support for Dynamic Groups objects.
- [#897](https://github.com/nautobot/nautobot/issues/897) - Added JSON type for custom fields.
- [#1374](https://github.com/nautobot/nautobot/issues/1374) - Added REST API Token Provisioning. (Port of [NetBox #6592](https://github.com/netbox-community/netbox/pull/6592) and subsequent fixes)
- [#1385](https://github.com/nautobot/nautobot/issues/1385) - Added MarkdownLint validation and enforcement to CI.
- [#1465](https://github.com/nautobot/nautobot/issues/1465) - Implemented REST API versioning.
- [#1525](https://github.com/nautobot/nautobot/issues/1525) - Implemented support for regex lookup expressions for `BaseFilterSet` filter fields in the API.
- [#1638](https://github.com/nautobot/nautobot/issues/1638) - Implemented numerous indexes on models natural lookup fields as well as some index togethers for `ObjectChange`.

### Changed

- [#595](https://github.com/nautobot/nautobot/issues/595) - Migrated from `drf-yasg` (OpenAPI 2.0) to `drf-spectacular` (OpenAPI 3.0) for REST API interactive Swagger documentation.
- [#792](https://github.com/nautobot/nautobot/issues/792) - Poetry-installed dependencies are now identical between `dev` and `final` images.
- [#814](https://github.com/nautobot/nautobot/issues/814) - Extended documentation for configuring Celery for use Redis Sentinel clustering.
- [#1225](https://github.com/nautobot/nautobot/issues/1225) - Relaxed uniqueness constraint on Webhook creation, allowing multiple webhooks to send to the same target address so long as their content-type(s) and action(s) do not overlap.
- [#1417](https://github.com/nautobot/nautobot/issues/1417) - CI scope improvements for streamlined performance.
- [#1478](https://github.com/nautobot/nautobot/issues/1478) - ScheduledJob REST API endpoints now enforce `extras.approve_job` permissions as appropriate.
- [#1479](https://github.com/nautobot/nautobot/issues/1479) - Updated Jobs documentation regarding the concrete Job database model.
- [#1502](https://github.com/nautobot/nautobot/issues/1502) Finalized Dynamic Groups implementation for 1.3 release (including documentation and integration tests).
- [#1521](https://github.com/nautobot/nautobot/pull/1521) - Consolidated Job REST API endpoints, taking advantage of REST API versioning.
- [#1556](https://github.com/nautobot/nautobot/issues/1556) - Cleaned up typos and formatting issues across docs, few code spots.

### Fixed

- [#794](https://github.com/nautobot/nautobot/issues/794) - Fixed health check issue when using Redis Sentinel for caching with Cacheops. The Redis health check backend is now aware of Redis Sentinel.
- [#1311](https://github.com/nautobot/nautobot/issues/1311) - Fixed a where it was not possible to set the rack height to `0` when performing a bulk edit of device types.
- [#1476](https://github.com/nautobot/nautobot/issues/1476) - Fixed a bug wherein a Job run via the REST API with a missing `schedule` would allow `approval_required` to be bypassed.
- [#1504](https://github.com/nautobot/nautobot/issues/1504) - Fixed an error that could be encountered when migrating from Nautobot 1.1 or earlier with JobResults with very long log entries.
- [#1515](https://github.com/nautobot/nautobot/issues/1515) - Fix Job Result rendering performance issue causing Bad Gateway errors.
- [#1516](https://github.com/nautobot/nautobot/issues/1516) - Fixed MySQL unit tests running in Docker environment and revised recommended MySQL encoding settings
- [#1562](https://github.com/nautobot/nautobot/issues/1562) - Fixed JobResult filter form UI pointing to the wrong endpoint.
- [#1563](https://github.com/nautobot/nautobot/issues/1563) - Fixed UI crash when trying to execute Jobs provided by disabled plugins. A friendly error message will now be displayed.
- [#1582](https://github.com/nautobot/nautobot/issues/1582) - Fixed a timing issue with editing a record while its custom field(s) are in the process of being cleaned up by a background task.
- [#1632](https://github.com/nautobot/nautobot/pull/1632) - Fixed issue accessing request attributes when request may be None.
- [#1637](https://github.com/nautobot/nautobot/pull/1637) - Fixed warnings logged during REST API schema generation.

## v1.3.0b1 (2022-03-11)

### Added

- [#5](https://github.com/nautobot/nautobot/issues/5) - Added the option to perform a "dry run" of Git repository syncing.
- [#330](https://github.com/nautobot/nautobot/issues/330) - Added pre-/post-change data to WebHooks leveraging snapshots.
- [#498](https://github.com/nautobot/nautobot/issues/498) - Added custom-validator support to the RelationshipAssociation model.
- [#724](https://github.com/nautobot/nautobot/issues/724) - Added Provider Network data model. (Partially based on [NetBox #5986](https://github.com/netbox-community/netbox/issues/5986).)
- [#795](https://github.com/nautobot/nautobot/issues/795) - Added ability to filter objects missing custom field values by using `null`.
- [#803](https://github.com/nautobot/nautobot/issues/803) - Added a `render_boolean` template filter, which renders computed boolean values as HTML in a consistent manner.
- [#863](https://github.com/nautobot/nautobot/issues/863) - Added the ability to hide a job in the UI by setting `hidden = True` in the Job's inner `Meta` class.
- [#881](https://github.com/nautobot/nautobot/issues/881) - Improved the UX of the main Jobs list by adding accordion style interface that can collapse/expand jobs provided by each module.
- [#885](https://github.com/nautobot/nautobot/issues/885) - Added the ability to define a `soft_time_limit` and `time_limit` in seconds as attributes of a Job's `Meta`.
- [#894](https://github.com/nautobot/nautobot/issues/894) - Added the ability to view computed fields in an object list.
- [#898](https://github.com/nautobot/nautobot/issues/898) - Added support for moving a CustomField, Relationship or ComputedField from the main tab of an object's detail page in the UI to the "Advanced" tab.
- [#1001](https://github.com/nautobot/nautobot/issues/1001) - Added Job database model and associated functionality.
- [#1109](https://github.com/nautobot/nautobot/issues/1109) - Added pagination support for GraphQL list queries.
- [#1255](https://github.com/nautobot/nautobot/pull/1255) - Added Python 3.10 support.
- [#1350](https://github.com/nautobot/nautobot/issues/1350) - Added missing methods on Circuit Termination detail view.
- [#1411](https://github.com/nautobot/nautobot/pull/1411) - Added concrete Job database model; added database signals to populate Job records in the database; added detail, edit, and delete views for Job records.
- [#1457](https://github.com/nautobot/nautobot/pull/1457) - Added new Jobs REST API, added control logic to use JobModel rather than JobClass where appropriate; improved permissions enforcement for Jobs.
- [#1470](https://github.com/nautobot/nautobot/issues/1470) - Added plugin framework for extending FilterSets and Filter Forms.

### Changed

- [#368](https://github.com/nautobot/nautobot/issues/368) - Added `nautobot.extras.forms.NautobotModelForm` and `nautobot.extras.filters.NautobotFilterSet` base classes. All form classes which inherited from all three of (`BootstrapMixin`, `CustomFieldModelForm`, and `RelationshipModelForm`) now inherit from `NautobotModelForm` as their base class. All filterset classes which inherited from all three of (`BaseFilterSet`, `CreatedUpdatedFilterSet`, and `CustomFieldModelFilterSet`) now inherit from `NautobotFilterSet` as their base class.
- [#443](https://github.com/nautobot/nautobot/issues/443) - The provided "Dummy Plugin" has been renamed to "Example Plugin".
- [#591](https://github.com/nautobot/nautobot/issues/591) - All uses of `type()` are now refactored to use `isinstance()` where applicable.
- [#880](https://github.com/nautobot/nautobot/issues/880) - Jobs menu items now form their own top-level menu instead of a sub-section under the Extensibility menu.
- [#909](https://github.com/nautobot/nautobot/issues/909) - Device, InventoryItem, and Rack serial numbers can now be up to 255 characters in length.
- [#916](https://github.com/nautobot/nautobot/issues/916) - A `Job.Meta.description` can now contain markdown-formatted multi-line text.
- [#1107](https://github.com/nautobot/nautobot/issues/1107) - Circuit Provider account numbers can now be up to 100 characters in length.
- [#1252](https://github.com/nautobot/nautobot/pull/1252) - As Python 3.6 has reached end-of-life, the default Docker images published for this release (i.e. `1.3.0`, `stable`, `latest`) have been updated to use Python 3.7 instead.
- [#1277](https://github.com/nautobot/nautobot/issues/1277) - Updated Django dependency to 3.2.X LTS.
- [#1307](https://github.com/nautobot/nautobot/pull/1307) - Updated various Python package dependencies to their latest compatible versions.
- [#1314](https://github.com/nautobot/nautobot/pull/1314) - Updated various development-only Python package dependencies to their latest compatible versions.
- [#1321](https://github.com/nautobot/nautobot/pull/1321) - Updates to various browser package dependencies. This includes updating from Material Design Icons 5.x to 6.x, which has a potential impact on plugins: a [small number of icons have been removed or renamed](https://dev.materialdesignicons.com/upgrade#5.9.55-to-6.1.95) as a result of this change.
- [#1367](https://github.com/nautobot/nautobot/pull/1367) - Extracted Job-related models to submodule `nautobot.extras.models.jobs`; refined Job testing best practices.
- [#1391](https://github.com/nautobot/nautobot/issues/1391) - Updated Jinja2 dependency to 3.0.X.
- [#1435](https://github.com/nautobot/nautobot/issues/1435) - Update to Selenium 4.X.

### Fixed

- [#1440](https://github.com/nautobot/nautobot/issues/1440) - Handle models missing serializer methods, dependent from adding pre-/post-change data to WebHooks.

### Removed

- [#1268](https://github.com/nautobot/nautobot/issues/1268) - Drop Support for Python 3.6.
