# Nautobot v1.3

This document describes all new features and changes in Nautobot 1.3.

If you are a user migrating from NetBox to Nautobot, please refer to the ["Migrating from NetBox"](../installation/migrating-from-netbox.md) documentation.

## Release Overview

### Added

#### Dynamic Group Model ([#896](https://github.com/nautobot/nautobot/issues/896))

A new data model for representing [dynamic groups](../models/extras/dynamicgroup.md) of objects has been implemented. Dynamic groups can be used to organize objects together by matching criteria such as their site location or region, for example, and are dynamically updated whenever new matching objects are created, or existing objects are updated.

For the initial release only dynamic groups of `Device` and `VirtualMachine` objects are supported. 

!!! note
  For this first 1.3 beta release, this feature is not yet documented. Dynamic Groups be found by navigating to **Organization** > **Dynamic Groups** in the web interface.

#### GraphQL Pagination ([#1109](https://github.com/nautobot/nautobot/issues/1109))

GraphQL list queries can now be paginated by specifying the filter parameters `limit` and `offset`. Refer to the [user guide](../user-guides/graphql.md#filtering-queries) for examples.

#### Job Database Model ([#1001](https://github.com/nautobot/nautobot/issues/1001))

Installed Jobs are now represented by a data model in the Nautobot database. This allows for new functionality including:

- The Jobs listing UI view can now be filtered and searched like most other Nautobot table/list views.
- Job attributes (name, description, approval requirements, etc.) can now be managed via the Nautobot UI by an administrator or user with appropriate permissions to customize or override the attributes defined in the Job source code.
- Jobs can now be identified by a `slug` as well as by their `class_path`.
- A new set of REST API endpoints have been added at `api/extras/job-models`. The existing `api/extras/jobs` REST API continues to work but should be considered as deprecated.

!!! warning
    The new Jobs REST API endpoint URL is likely to change before the final release of Nautobot 1.3.

- As a minor security measure, newly installed Jobs default to `enabled = False`, preventing them from being run until an administrator or user with appropriate permissions updates them to be enabled for running.

!!! note
    As a convenience measure, when initially upgrading to Nautobot 1.3.x, any existing Jobs that have been run or scheduled previously (i.e., have at least one associated JobResult and/or ScheduledJob record) will instead default to `enabled = True` so that they may continue to be run without requiring changes.

For more details please refer to the [Jobs feature documentation](../additional-features/jobs.md) as well as the [Job data model documentation](../models/extras/job.md).

#### Provider Network Model ([#724](https://github.com/nautobot/nautobot/issues/724))

A [data model](../models/circuits/providernetwork.md) has been added to support representing the termination of a circuit to an external provider's network.

#### Python 3.10 Support ([#1255](https://github.com/nautobot/nautobot/pull/1255))

Python 3.10 is officially supported by Nautobot now, and we are building and publishing Docker images with Python 3.10 now.

### Changed

#### Update Jinja2 to 3.x ([#1474](https://github.com/nautobot/nautobot/pull/1474))

We've updated the Jinja2 dependency from version 2.11 to version 3.0.3. This may affect the syntax of any `nautobot.extras.models.ComputedField` objects in your database... Specifically, the `template` attribute, which is parsed as a Jinja2 template. Please refer to [Jinja2 3.0.x's release notes](https://jinja.palletsprojects.com/en/3.0.x/changes/) to check if any changes might be required in your computed fields' templates.

#### Docker Images Now Default to Python 3.7 ([#1252](https://github.com/nautobot/nautobot/pull/1252))

As Python 3.6 has reached end-of-life, the default Docker images published for this release (i.e. `1.3.0`, `stable`, `latest`) have been updated to use Python 3.7 instead.

### Removed

#### Python 3.6 No Longer Supported ([#1268](https://github.com/nautobot/nautobot/issues/1268))

As Python 3.6 has reached end-of-life, and many of Nautobot's dependencies have already dropped support for Python 3.6 as a consequence, Nautobot 1.3 and later do not support installation under Python 3.6.

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
