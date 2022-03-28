# Nautobot v1.3

This document describes all new features and changes in Nautobot 1.3.

If you are a user migrating from NetBox to Nautobot, please refer to the ["Migrating from NetBox"](../installation/migrating-from-netbox.md) documentation.

## Release Overview

### Added

#### Dynamic Group Model ([#896](https://github.com/nautobot/nautobot/issues/896))

A new data model for representing [dynamic groups](../models/extras/dynamicgroup.md) of objects has been implemented. Dynamic groups can be used to organize objects together by matching criteria such as their site location or region, for example, and are dynamically updated whenever new matching objects are created, or existing objects are updated.

For the initial release only dynamic groups of `Device` and `VirtualMachine` objects are supported. 

#### GraphQL Pagination ([#1109](https://github.com/nautobot/nautobot/issues/1109))

GraphQL list queries can now be paginated by specifying the filter parameters `limit` and `offset`. Refer to the [user guide](../user-guides/graphql.md#filtering-queries) for examples.

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

#### JSON Type for Custom Fields

Custom fields can now have a type of "json". Fields of this type can be used to store arbitrary JSON data.

#### Provider Network Model ([#724](https://github.com/nautobot/nautobot/issues/724))

A [data model](../models/circuits/providernetwork.md) has been added to support representing the termination of a circuit to an external provider's network.

#### Python 3.10 Support ([#1255](https://github.com/nautobot/nautobot/pull/1255))

Python 3.10 is officially supported by Nautobot now, and we are building and publishing Docker images with Python 3.10 now.

#### Regular Expression Support in API Filtering ([#1525](https://github.com/nautobot/nautobot/issues/1525))

[New lookup expressions for using regular expressions](../rest-api/filtering.md#string-fields) to filter objects by string (char) fields in the API have been added to all core filters.

The expressions `re` (regex), `nre` (negated regex), `ire` (case-insensitive regex), and `nire` (negated case-insensitive regex) lookup expressions are now dynamically-generated for filter fields inherited by subclasses of `nautobot.utilities.filters.BaseFilterSet`.

#### REST API Versioning ([#1465](https://github.com/nautobot/nautobot/issues/1465))

Nautobot's REST API now supports multiple versions, which may requested by modifying the HTTP Accept header on any requests sent by a REST API client. Details are in the [REST API documentation](../rest-api/overview.md#versioning), but in brief:

- The only REST API endpoint that is versioned in the 1.3.0 release is the `/api/extras/jobs/` listing endpoint, as described above. All others are currently un-versioned. However, over time more versioned REST APIs will be developed, so this is important to understand for all REST API consumers.
- If a REST API client does not request a specific REST API version (in other words, requests `Accept: application/json` rather than `Accept: application/json; version=1.3`) the API behavior will be compatible with Nautobot 1.2, at a minimum for the remainder of the Nautobot 1.x release cycle.
- The API behavior may change to a newer default version in a Nautobot major release (e.g. 2.0).
- To request an updated (non-backwards-compatible) API endpoint, an API version must be requested corresponding at a minimum to the Nautobot `major.minor` version where the updated API endpoint was introduced (so to interact with the new Jobs REST API, `Accept: application/json; version=1.3`).

!!! tip
    As a best practice, when developing a Nautobot REST API integration, your client should _always_ request the current API version it is being developed against, rather than relying on the default API behavior (which may change with a new Nautobot major release, as noted, and which also may not include the latest and greatest API endpoints already available but not yet made default in the current release).

#### Webhook Pre/Post-change Data Added to Request Body ([#330](https://github.com/nautobot/nautobot/issues/330))

Webhooks now provide a snapshot of data before and after a change. This also includes the differences between the old and new data. See the default request body section in webhook docs [here](../models/extras/webhook.md#default-request-body).

### Changed

#### Update Jinja2 to 3.x ([#1474](https://github.com/nautobot/nautobot/pull/1474))

We've updated the Jinja2 dependency from version 2.11 to version 3.0.3. This may affect the syntax of any `nautobot.extras.models.ComputedField` objects in your database... Specifically, the `template` attribute, which is parsed as a Jinja2 template. Please refer to [Jinja2 3.0.x's release notes](https://jinja.palletsprojects.com/en/3.0.x/changes/) to check if any changes might be required in your computed fields' templates.

#### Docker Images Now Default to Python 3.7 ([#1252](https://github.com/nautobot/nautobot/pull/1252))

As Python 3.6 has reached end-of-life, the default Docker images published for this release (i.e. `1.3.0`, `stable`, `latest`) have been updated to use Python 3.7 instead.

#### Job Approval Now Controlled By `extras.approve_job` Permission ([#1490](https://github.com/nautobot/nautobot/pull/1490))

Similar to the existing `extras.run_job` permission, a new `extras.approve_job` permission is now enforced by the UI and the REST API when approving scheduled jobs. Only users with this permission can approve or deny approval requests; additionally such users also now require the `extras.view_scheduledjob`, `extras.change_scheduledjob`, and `extras.delete_scheduledjob` permissions as well.

### Removed

#### Python 3.6 No Longer Supported ([#1268](https://github.com/nautobot/nautobot/issues/1268))

As Python 3.6 has reached end-of-life, and many of Nautobot's dependencies have already dropped support for Python 3.6 as a consequence, Nautobot 1.3 and later do not support installation under Python 3.6.

## v1.3.0b2 (2022-MM-DD)

### Added

- [#896](https://github.com/nautobot/nautobot/issues/896) - Implemented support for Dynamic Groups objects
- [#897](https://github.com/nautobot/nautobot/issues/897) - Added JSON type for custom fields.
- [#1465](https://github.com/nautobot/nautobot/issues/1465) - Implemented REST API versioning
- [#1525](https://github.com/nautobot/nautobot/issues/1525) - Implemented support for regex lookup expressions for `BaseFilterSet` filter fields in the API.

### Changed

- [#814](https://github.com/nautobot/nautobot/issues/814) - Extended documentation for configuring Celery for use Redis Sentinel clustering.
- [#1225](https://github.com/nautobot/nautobot/issues/1225) - Relaxed uniqueness constraint on Webhook creation, allowing multiple webhooks to send to the same target address so long as their content-type(s) and action(s) do not overlap.
- [#1478](https://github.com/nautobot/nautobot/issues/1478) - ScheduledJob REST API endpoints now enforce `extras.approve_job` permissions as appropriate.
- [#1479](https://github.com/nautobot/nautobot/issues/1479) - Updated Jobs documentation regarding the concrete Job database model.
- [#1502](https://github.com/nautobot/nautobot/issues/1502) Finalized Dynamic Groups implementation for 1.3 release (including documentation and integration tests)
- [#1521](https://github.com/nautobot/nautobot/pull/1521) - Consolidated Job REST API endpoints, taking advantage of REST API versioning.

### Fixed

- [#794](https://github.com/nautobot/nautobot/issues/794) - Fixed health check issue when using Redis Sentinel for caching with Cacheops. The Redis health check backend is now aware of Redis Sentinel.


## v1.3.0b1 (2022-03-11)

### Added

- [#5](https://github.com/nautobot/nautobot/issues/5) - Added the option to perform a "dry run" of Git repository syncing.
- [#330](https://github.com/nautobot/nautobot/issues/330) - Added pre-/post-change data to WebHooks leveraging snapshots
- [#498](https://github.com/nautobot/nautobot/issues/498) - Added custom-validator support to the RelationshipAssociation model.
- [#724](https://github.com/nautobot/nautobot/issues/724) - Added Provider Network data model. (Partially based on [NetBox #5986](https://github.com/netbox-community/netbox/issues/5986).)
- [#795](https://github.com/nautobot/nautobot/issues/795) - Added ability to filter objects missing custom field values by using `null`.
- [#803](https://github.com/nautobot/nautobot/issues/803) - Added a `render_boolean` template filter, which renders computed boolean values as HTML in a consistent manner.
- [#863](https://github.com/nautobot/nautobot/issues/863) - Added the ability to hide a job in the UI by setting `hidden = True` in the Job's inner `Meta` class
- [#881](https://github.com/nautobot/nautobot/issues/881) - Improved the UX of the main Jobs list by adding accordion style interface that can collapse/expand jobs provided by each module
- [#885](https://github.com/nautobot/nautobot/issues/885) - Added the ability to define a `soft_time_limit` and `time_limit` in seconds as attributes of a Job's `Meta`.
- [#894](https://github.com/nautobot/nautobot/issues/894) - Added the ability to view computed fields in an object list.
- [#898](https://github.com/nautobot/nautobot/issues/898) - Added support for moving a CustomField, Relationship or ComputedField from the main tab of an object's detail page in the UI to the "Advanced" tab.
- [#1001](https://github.com/nautobot/nautobot/issues/1001) - Added Job database model and associated functionality.
- [#1109](https://github.com/nautobot/nautobot/issues/1109) - Added pagination support for GraphQL list queries.
- [#1255](https://github.com/nautobot/nautobot/pull/1255) - Added Python 3.10 support.
- [#1350](https://github.com/nautobot/nautobot/issues/1350) - Added missing methods on Circuit Termination detail view.
- [#1411](https://github.com/nautobot/nautobot/pull/1411) - Added concrete Job database model; added database signals to populate Job records in the database; added detail, edit, and delete views for Job records.
- [#1457](https://github.com/nautobot/nautobot/pull/1457) - Added new Jobs REST API, added control logic to use JobModel rather than JobClass where appropriate; improved permissions enforcement for Jobs

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
- [#1435](https://github.com/nautobot/nautobot/issues/1435) - Update to Selenium 4.X

### Fixed

- [#1440](https://github.com/nautobot/nautobot/issues/1440) - Handle models missing serializer methods, dependent from adding pre-/post-change data to WebHooks.

### Removed

- [#1268](https://github.com/nautobot/nautobot/issues/1268) - Drop Support for Python 3.6.
