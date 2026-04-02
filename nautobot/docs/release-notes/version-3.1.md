# Nautobot v3.1

This document describes all new features and changes in Nautobot 3.1.

## Upgrade Actions

### Administrators

#### Migrate From Legacy PostgreSQL Versions As Needed

Nautobot 3.1, as a consequence of the [Django 5.2 dependency upgrade](#django-52), drops support for PostgreSQL versions 12.x and 13.x and now requires a minimum of PostgreSQL 14.0. If you have an existing Nautobot deployment on these no-longer-supported versions of PostgreSQL, you will need to [upgrade and migrate your database](../user-guide/administration/upgrading/postgresql.md).

!!! tip
    In general we recommend that you upgrade PostgreSQL as a _separate_ step and change window from upgrading Nautobot in order to reduce the complexity of the upgrade and allow easier troubleshooting and recovery should anything go wrong in the process.

#### Migrate Configuration To `STORAGES` As Needed

As a consequence of the [Django 5.2 dependency upgrade](#django-52), Nautobot 3.1 drops support for the Django `DEFAULT_FILE_STORAGE` and `STATICFILES_STORAGE` settings variables in favor of a unified `STORAGES` setting. Additionally, support for the corresponding Nautobot-specific `STORAGE_BACKEND`, `STORAGE_CONFIG`, and `JOB_FILE_IO_STORAGE` settings variables has been removed and merged into the [`STORAGES`](https://docs.djangoproject.com/en/5.2/ref/settings/#std-setting-STORAGES) setting.

If your deployment of Nautobot had overridden any of the above settings (for example, to use [S3 storage](../user-guide/administration/guides/s3-django-storage.md)), you will need to update your `nautobot_config.py` file to use the `STORAGES` setting instead. More details are available in the Nautobot [documentation for `STORAGES`](../user-guide/administration/configuration/settings.md#storages).

#### Configure New Performance Settings As Appropriate

If you have a large number of Location and/or Prefix records, you can configure [`LOCATION_LIST_DEFAULT_MAX_DEPTH`](../user-guide/administration/configuration/settings.md#location_list_default_max_depth) and/or [`PREFIX_LIST_DEFAULT_MAX_DEPTH`](../user-guide/administration/configuration/settings.md#prefix_list_default_max_depth) to limit the depth of data that's initially retrieved and rendered when first accessing these list views, with the potential to significantly improve the performance of these enhanced views as a result.

### App Authors/Maintainers

#### Changes For Django 5.2 Compatibility

Nautobot's [dependency update to Django 5.2](#django-52), as typical of Django major version updates, included a small number of breaking changes to Django's Python APIs. For a comprehensive guide, refer to the "Backwards incompatible changes" and "Features removed" sections of Django's release-notes for versions [5.0](https://docs.djangoproject.com/en/5.2/releases/5.0/#backwards-incompatible-changes-in-5-0), [5.1](https://docs.djangoproject.com/en/5.2/releases/5.1/#backwards-incompatible-changes-in-5-1), and [5.2](https://docs.djangoproject.com/en/5.2/releases/5.2/#backwards-incompatible-changes-in-5-2). The most likely impacts we have identified to Nautobot Apps are the following:

- Support for `Model.Meta.index_together` (previously deprecated in Django 4.2) is removed; App models with custom indexes using `index_together` will need to migrate to use `Model.Meta.indexes` instead and create a database migration accordingly.
- Models using a `ManyToManyField` with an explicit `through` table (as is recommended by Nautobot) may need to run `nautobot-server makemigrations <app>` to generate a schema migration explicitly specifying the `through_fields` for each such `ManyToManyField`.
- The test method `assertQuerysetEqual()` (previously deprecated in Django 4.2) is removed; App tests using this method will need to migrate to use `assertQuerySetEqual()` (note capitalization) instead.
- Nautobot previously maintained a Django templatetag named `querystring`, which may conflict with the built-in [`querystring` templatetag introduced in Django 5.1](https://docs.djangoproject.com/en/5.1/ref/templates/builtins/#querystring). Additionally, [Django Tables2 has a similar namespace conflict](https://github.com/jieter/django-tables2/issues/976). It is recommended to use Django's built-in version where possible. If compatibility issues arise, use `nautobot.app.templatetags.legacy_querystring` instead.

#### Changes for HTMX

See [HTMX List View Rendering](#htmx-list-view-rendering) below.

#### Support Dependent Object Creation and Search In Forms

See [Dependent Object Creation and Search](#dependent-object-creation-and-search) below.

#### Bootstrap FileStyle Deprecation

The Bootstrap FileStyle library is now deprecated and will be removed in Nautobot 4.0. The `ClearableFileInput` widget, which previously depended on Bootstrap FileStyle, has already been migrated to the standard Bootstrap 5 file input.

If you do not directly reference the `bootstrap-filestyle-1.2.3/bootstrap-filestyle.min.js` script in your code, no action is required. Otherwise, we encourage you to transition to the Bootstrap 5 file input or import an external library of your choice.

## Release Overview

### Breaking Changes

#### Dropped Support for PostgreSQL Versions Less Than 14.0

As a consequence of the [dependency update to Django 5.2](#django-52), support for PostgreSQL versions before 14.0 has been removed from Nautobot.

#### Dropped Support for MySQL Versions Less Than 8.0.11

As a consequence of the [dependency update to Django 5.2](#django-52), support for MySQL versions before 8.0.11 has been removed from Nautobot.

#### Unified Storage Backend Configuration

As a consequence of the [dependency update to Django 5.2](#django-52), Nautobot 3.1 drops support for the Django `DEFAULT_FILE_STORAGE` and `STATICFILES_STORAGE` settings variables in favor of a unified `STORAGES` setting. Additionally, support for the corresponding Nautobot-specific `STORAGE_BACKEND`, `STORAGE_CONFIG`, and `JOB_FILE_IO_STORAGE` settings variables has been removed and merged into the [`STORAGES`](https://docs.djangoproject.com/en/5.2/ref/settings/#std-setting-STORAGES) setting. More details are available in the Nautobot [documentation for `STORAGES`](../user-guide/administration/configuration/settings.md#storages).

### Added

#### Dependent Object Creation and Search

Dependent objects can now be created directly from the current page using an embedded modal, without interrupting your workflow. Additionally, dependent object search supports advanced filtering, making it easier to find related records, especially in cases like interfaces where simple string matching was not sufficient.

Both creation and search are handled within a modal, so you don't have to leave the main form.

Form migration guide for App developers is available in [Embedded Actions](../development/apps/migration/embedded_actions.md).

#### Configurable Columns

Configurable Columns have been redesigned for improved usability. You can now easily toggle columns on and off via moveable checkboxes, while preserving the order of selected columns.

#### Job Console

When running jobs, Nautobot now optionally captures and displays all console output in the Job Console tab, including logs previously omitted due to log settings or C-program output. You can now see the complete console log as if running the job interactively, creating a clear separation between job troubleshooting (Job Console) and job reporting (Job Log Entries).

#### Custom Field Scoping

Custom Fields can now be scoped to display or edit only when specific, user-defined filtering conditions are met. Previously, all Custom Fields appeared on all objects. Common use cases include:

- Displaying SMARTnet details for `Device` objects only when the device is a Cisco model.
- Showing local contact information for `Location` objects only when the `LocationType` is `Site`.
- Presenting ATT billing account information for `Circuit` objects only when the circuit is an ATT circuit.

#### Python 3.14 Support

Added official support for Python 3.14.

### Changed

#### HTMX List View Rendering

In Nautobot 3.1, object list views (including both those derived from `generic.ObjectListView` and those using `NautobotUIViewSet`) now load in two stages (using [HTMX](https://htmx.org)) to improve the responsiveness of the UI. Custom implementations of these views, and/or custom test cases written for these views, may require some updates to handle this behavior correctly. Refer to the [developer documentation](../development/core/htmx.md#object-list-views-and-htmx) for more specific guidance.

#### Async Global Search

Global search is now loaded asynchronously. When performing a search, results are returned incrementally, so you see matches immediately without waiting for the slowest queries to complete.

#### Improved Location and Prefix List Views

In addition to the generalized list-view performance enhancements described above, the list views for Location and Prefix records specifically have been enhanced in several ways:

- The rendering of the "tree" data hierarchy for these records has in general been improved to visualize object relationships more clearly.
- An administrator can configure [`LOCATION_LIST_DEFAULT_MAX_DEPTH`](../user-guide/administration/configuration/settings.md#location_list_default_max_depth) and/or [`PREFIX_LIST_DEFAULT_MAX_DEPTH`](../user-guide/administration/configuration/settings.md#prefix_list_default_max_depth) to limit the depth of data that's initially retrieved and rendered when first accessing these list views, improving their responsiveness substantially at high data scale.
- Users can interactively "drill down" into deeper nested data as needed with a few quick clicks, incrementally loading additional "child" records on the fly.

### Deprecated

#### `assertQuerysetEqualAndNotEmpty()` Test Method

The Nautobot test method `assertQuerysetEqualAndNotEmpty()` has been deprecated in favor of the new `assertQuerySetEqualAndNotEmpty()` method (note change in capitalization) to align with Django's `assertQuerySetEqual()` test method. Support for `assertQuerysetEqualAndNotEmpty()` may be removed in a future Nautobot release.

### Dependencies

#### Django 5.2

Nautobot 3.1 upgrades the core `Django` dependency from 4.2.x LTS to 5.2.x LTS. Nautobot has been updated accordingly, but Apps and third-party dependencies may need to update to newer versions for compatibility with Django 5.2.

<!-- pyml disable-num-lines 2 blanks-around-headers -->

<!-- towncrier release notes start -->

## v3.1.0a3 (2026-02-25)

### Added in v3.1.0a3

- [#2516](https://github.com/nautobot/nautobot/issues/2516) - Enhanced Prefix list view to support dynamic expansion/collapsing of prefix subtrees.
- [#2516](https://github.com/nautobot/nautobot/issues/2516) - Added support for `prefix_and_descendants` filter on Prefix list view.
- [#2516](https://github.com/nautobot/nautobot/issues/2516) - Added option for `ButtonsColumn` in tables to be passed an explicit `return_url` in the render context in order to override its default behavior.
- [#2516](https://github.com/nautobot/nautobot/issues/2516) - Added `Prefix.next_sibling` property.
- [#2516](https://github.com/nautobot/nautobot/issues/2516) - Added `/ipam/prefixes/<uuid>/children/` URL endpoint in support of enhanced Prefix list view functionality.
- [#8516](https://github.com/nautobot/nautobot/issues/8516) - Added dynamically rendered scope filter fields to the Custom Field edit form.
- [#8524](https://github.com/nautobot/nautobot/issues/8524) - Added `Console Log` tab to Job Result detail view.
- [#8524](https://github.com/nautobot/nautobot/issues/8524) - Added `job_console_entries` action to `JobResultUIViewSet` to stream output from SQL into the UI in realtime.
- [#8524](https://github.com/nautobot/nautobot/issues/8524) - Modified `runjob_with_job_result.py` command to `run_job` instead of `execute_job`.
- [#8524](https://github.com/nautobot/nautobot/issues/8524) - Improved `job_result.js` and `job_level_filtering.js`.
- [#8546](https://github.com/nautobot/nautobot/issues/8546) - Implemented embedded create and search buttons accompanying dynamic model choice fields.
- [#8551](https://github.com/nautobot/nautobot/issues/8551) - Added `max_depth` filter support to the Location list view.
- [#8551](https://github.com/nautobot/nautobot/issues/8551) - Added `max_depth` filter to the Location basic filter form.
- [#8551](https://github.com/nautobot/nautobot/issues/8551) - Added support for the setting/Constance variable `LOCATION_LIST_DEFAULT_MAX_DEPTH`. Configuring this may improve the performance of the Location list view at scale.
- [#8559](https://github.com/nautobot/nautobot/issues/8559) - Implemented embedded object creation modal.
- [#8562](https://github.com/nautobot/nautobot/issues/8562) - Added tables of "Sibling Prefixes" and "Child Prefixes" to Prefix detail view.
- [#8562](https://github.com/nautobot/nautobot/issues/8562) - Added `TreeModel.siblings` convenience property.
- [#8562](https://github.com/nautobot/nautobot/issues/8562) - Added table of "Sibling Locations" to Location detail view.
- [#8571](https://github.com/nautobot/nautobot/issues/8571) - Added testing of `test_filter_form_fields_are_working` to catch more filter form issues.
- [#8579](https://github.com/nautobot/nautobot/issues/8579) - Added role-based precedence for `console_log` (Author -> Admin -> Runner).
- [#8579](https://github.com/nautobot/nautobot/issues/8579) - Added the ability to run scheduled jobs with the console log.

### Changed in v3.1.0a3

- [#8527](https://github.com/nautobot/nautobot/issues/8527) - Changed behavior of `PREFIX_LIST_DEFAULT_MAX_DEPTH` and `max_depth` Prefix filter to start at 1 instead of 0.
- [#8527](https://github.com/nautobot/nautobot/issues/8527) - Changed behavior of table paginator widget to automatically return to page 1 when changing the `per_page` selection.
- [#8527](https://github.com/nautobot/nautobot/issues/8527) - Renamed Prefix table column "Children" to "Descendants" for improved clarity.
- [#8527](https://github.com/nautobot/nautobot/issues/8527) - Changed hierarchy rendering in Prefix table to more clearly indicate parent, child, and sibling relations.
- [#8537](https://github.com/nautobot/nautobot/issues/8537) - Updated testing of `test_model_properties_as_table_columns_are_not_orderable` to catch more sortable issues.
- [#8551](https://github.com/nautobot/nautobot/issues/8551) - Changed Location list view behavior so that filtering by the filters `max_depth` and/or `subtree` (in the absence of any other filters) will not prevent the indentation of locations based on their nesting depth.
- [#8562](https://github.com/nautobot/nautobot/issues/8562) - Renamed "Child Prefixes" tab on Prefix detail view to "Descendant Prefixes" for clarity.
- [#8562](https://github.com/nautobot/nautobot/issues/8562) - Renamed "Parent Prefixes" table on Prefix detail view to "Ancestor Prefixes" for clarity.
- [#8564](https://github.com/nautobot/nautobot/issues/8564) - Updated the logic that determines which nav menu item is marked "active" to always prefer exact URL matches before falling back to introspecting the view and model.
- [#8579](https://github.com/nautobot/nautobot/issues/8579) - Job run form split into 3 separate sections: `Job Data`, `Job Execution` and `Job Schedule Type`.
- [#8579](https://github.com/nautobot/nautobot/issues/8579) - `Job.as_form()` no longer includes execution fields (`_profile`, `_console_log`, `_job_queue`, `_ignore_singleton_lock`). These have been moved to the new `Job.as_execution_form()`.
- [#8579](https://github.com/nautobot/nautobot/issues/8579) - `Job.as_execution_form()` added as a new classmethod returning a standalone `JobExecutionForm` populated with execution-related fields only.
- [#8579](https://github.com/nautobot/nautobot/issues/8579) - `JobRunView.post()` updated to validate `job_form`, `job_execution_form`, and `schedule_form` independently. Execution fields are now read from `job_execution_form.cleaned_data` and job data fields from `job_form.cleaned_data`.
- [#8579](https://github.com/nautobot/nautobot/issues/8579) - Template `nautobot/extras/templates/extras/job.html` updated to render three separate cards: `Job Data`, `Job Execution`, and `Job Schedule Type`.
- [#8596](https://github.com/nautobot/nautobot/issues/8596) - Changed behavior of model edit forms to hide custom fields that are out of scope.
- [#8596](https://github.com/nautobot/nautobot/issues/8596) - Improved unit test coverage for scope filter HTMX endpoint.
- [#8609](https://github.com/nautobot/nautobot/issues/8609) - Made embedded object create form footer sticky.
- [#8617](https://github.com/nautobot/nautobot/issues/8617) - Enhanced Location list view tree rendering to follow the same pattern as Prefix list view tree.
- [#8622](https://github.com/nautobot/nautobot/issues/8622) - Restored support for `DATE_FORMAT`, `DATETIME_FORMAT`, `SHORT_DATE_FORMAT`, `SHORT_DATETIME_FORMAT`, and `TIME_FORMAT` settings.
- [#8622](https://github.com/nautobot/nautobot/issues/8622) - Removed user-defined locale/language selection feature (previously introduced for 3.1 by #8417).
- [#8628](https://github.com/nautobot/nautobot/issues/8628) - Changed "global" search to load results incrementally with HTMX in order to avoid timing out when searching a large amount of data.

### Fixed in v3.1.0a3

- [#8527](https://github.com/nautobot/nautobot/issues/8527) - Fixed `per_page` list view dropdown not working in Chrome and similar browsers.
- [#8537](https://github.com/nautobot/nautobot/issues/8537), [#8571](https://github.com/nautobot/nautobot/issues/8571) - Fixed sorting on multiple tables.
- [#8562](https://github.com/nautobot/nautobot/issues/8562) - Fixed a warning appearing in Firefox when updating table configuration in a view that contained multiple instances of the same table class.
- [#8570](https://github.com/nautobot/nautobot/issues/8570) - Fixed an exception under Django 5.2 when bulk-editing or bulk-deleting certain types of records.
- [#8597](https://github.com/nautobot/nautobot/issues/8597) - Fixed initial HTMX loading of Job list view (table or tiles).
- [#8597](https://github.com/nautobot/nautobot/issues/8597) - Fixed rendering of "Descendants" column in Prefix table.
- [#8597](https://github.com/nautobot/nautobot/issues/8597) - Fixed duplicated messages when applying invalid filters to object list views.
- [#8602](https://github.com/nautobot/nautobot/issues/8602) - Fixed ECharts not resizing with their container.
- [#8617](https://github.com/nautobot/nautobot/issues/8617) - Reduced the number of database queries needed to render Location tree view.

### Dependencies in v3.1.0a3

- [#8563](https://github.com/nautobot/nautobot/issues/8563) - Added declared support for Python 3.14.

### Documentation in v3.1.0a3

- [#8527](https://github.com/nautobot/nautobot/issues/8527) - Improved developer documentation and release note content about HTMX.

### Housekeeping in v3.1.0a3

- [#8532](https://github.com/nautobot/nautobot/issues/8532) - Changed the Python API for the UI components to allow default values to be set directly as class attributes.
- [#8602](https://github.com/nautobot/nautobot/issues/8602) - Decoupled the EChartsPanel and EChartsBase classes.
- [#8602](https://github.com/nautobot/nautobot/issues/8602) - Removed the redundant `permission` attribute from the EChartsBase class.
- [#8622](https://github.com/nautobot/nautobot/issues/8622) - Removed leftover test case for `social-auth-app-django` patch.

## v3.1.0a2 (2026-02-10)

### Housekeeping in v3.1.0a2

- [#8538](https://github.com/nautobot/nautobot/issues/8538) - Fixed missing end of conditional in release CI.

## v3.1.0a1 (2026-02-10)

### Breaking Changes in v3.1.0a1

- [#694](https://github.com/nautobot/nautobot/issues/694) - Removed support for settings variables `DEFAULT_FILE_STORAGE`, `JOB_FILE_IO_STORAGE`, `STATICFILES_STORAGE`, `STORAGE_BACKEND`, and `STORAGE_CONFIG`. These are all now incorporated into the Django standard `STORAGES` settings variable.
- [#8459](https://github.com/nautobot/nautobot/issues/8459) - Dropped support for PostgreSQL versions 12 and 13 as a consequence of upgrading to Django 5.2.

### Security in v3.1.0a1

- [#8459](https://github.com/nautobot/nautobot/issues/8459) - Updated dependency `social-auth-app-django` to 5.6.0 in order to pick up the official fix for `CVE-2025-61783`, and removed the local patch previously implemented in Nautobot for that vulnerability.
- [#8507](https://github.com/nautobot/nautobot/issues/8507) - Updated dependency `django` to `>=5.2.11,<5.3` to mitigate several CVEs including CVE-2026-1287 and CVE-2026-1312.

### Added in v3.1.0a1

- [#7018](https://github.com/nautobot/nautobot/issues/7018) - Added support for per-user configuration of preferred language/locale through the User Preferences UI. Currently this configuration applies primarily to date/time display in the UI.
- [#7957](https://github.com/nautobot/nautobot/issues/7957) - Added `port_type` field to Interface and InterfaceTemplate models to track physical connector type.
- [#8410](https://github.com/nautobot/nautobot/issues/8410) - Added `scope_filter` field to `CustomField` model.
- [#8427](https://github.com/nautobot/nautobot/issues/8427) - Added checks for `CustomField.scope_filter` to show/hide custom fields on object detail view based on scope filters.
- [#8457](https://github.com/nautobot/nautobot/issues/8457) - Implemented table column config drag and drop.
- [#8458](https://github.com/nautobot/nautobot/issues/8458) - Added initial support for running jobs in a subprocess and asynchronously capturing console output.
- [#8461](https://github.com/nautobot/nautobot/issues/8461) - Implemented table column config saved ordering on unselected columns.
- [#8468](https://github.com/nautobot/nautobot/issues/8468) - Added `max_depth` filter support to the Prefix list view.
- [#8468](https://github.com/nautobot/nautobot/issues/8468) - Added `max_depth` and `namespace` filters to the Prefix basic filter form.
- [#8468](https://github.com/nautobot/nautobot/issues/8468) - Added support for the settings/Constance variables `PREFIX_LIST_DEFAULT_MAX_DEPTH` and `PREFIX_LIST_DEFAULT_CONTAINER_ONLY`. Configuring either or both of these may improve the performance of the Prefix list view at scale.
- [#8498](https://github.com/nautobot/nautobot/issues/8498) - Added saving output (stdout/stderr) line by line to `JobConsoleEntry` table.

### Changed in v3.1.0a1

- [#8446](https://github.com/nautobot/nautobot/issues/8446) - Changed object list views to render in two passes with HTMX, improving initial load times.
- [#8446](https://github.com/nautobot/nautobot/issues/8446) - Changed rendering of table sorting indicator arrows from client-side to server-side rendering.
- [#8450](https://github.com/nautobot/nautobot/issues/8450) - Converted table column config to checkboxes.
- [#8468](https://github.com/nautobot/nautobot/issues/8468) - Enhanced the "Max Length" dropdown in the Prefix list view to allow deselecting a previously selected value.
- [#8468](https://github.com/nautobot/nautobot/issues/8468) - Changed Prefix list view behavior so that filtering by the filters `ip_version`, `max_depth`, `namespace`, `prefix_length__lte`, and/or `type=container` (in the absence of any other filters) will not prevent the indentation of prefixes based on their nesting depth.

### Deprecated in v3.1.0a1

- [#8459](https://github.com/nautobot/nautobot/issues/8459) - Following upstream Django patterns, the test helper method `assertQuerysetEqualAndNotEmpty` has been renamed to `assertQuerySetEqualAndNotEmpty`. The old method name is still available but is deprecated and will be removed in a future release.

### Removed in v3.1.0a1

- [#7018](https://github.com/nautobot/nautobot/issues/7018) - As a consequence of upgrading to Django 5.2, necessarily removed support for customizing date/time display in the UI through `nautobot_config.py` settings `DATE_FORMAT`, `DATETIME_FORMAT`, `TIME_FORMAT`, `SHORT_DATE_FORMAT`, and `SHORT_DATETIME_FORMAT`. Formatting of date/time information is now controlled by the application-level `LANGUAGE_CODE` setting and/or by per-user language preferences.

### Fixed in v3.1.0a1

- [#7018](https://github.com/nautobot/nautobot/issues/7018) - Fixed rendering of "last sync time" and "last synced by" columns in Git Repository list view.
- [#8315](https://github.com/nautobot/nautobot/issues/8315) - Fixed bug in Interface template causing emdash to not be used for Port Type if no value was set.
- [#8349](https://github.com/nautobot/nautobot/issues/8349) - Fixed unit tests failing after upgrading to Django 5.2.
- [#8422](https://github.com/nautobot/nautobot/issues/8422) - Fixed incompatibilities with `django_celery_beat` v2.8.1.
- [#8468](https://github.com/nautobot/nautobot/issues/8468) - Fixed dynamic-group filter calculation for cases where the filter is using `exclude=True`.
- [#8479](https://github.com/nautobot/nautobot/issues/8479) - Fixed missing text on the trace action button.

### Dependencies in v3.1.0a1

- [#8459](https://github.com/nautobot/nautobot/issues/8459) - Updated dependency `django` to `>=5.2.10,<5.3`.
- [#8459](https://github.com/nautobot/nautobot/issues/8459) - Updated dependency `django-celery-beat` to `==2.8.1` for compatibility with Django 5.2; pinned to an exact version due to Nautobot's use of some internals of this dependency.

### Housekeeping in v3.1.0a1

- [#8327](https://github.com/nautobot/nautobot/issues/8327) - Updated `pyproject.toml` to be compatible with PEP 621.
- [#8327](https://github.com/nautobot/nautobot/issues/8327) - Updated Nautobot development environment to require Poetry 2.x.
- [#8377](https://github.com/nautobot/nautobot/issues/8377) - Fixed a bad merge in `pyproject.toml`.
- [#8502](https://github.com/nautobot/nautobot/issues/8502) - Improved the Docker build process and tagging in CI.
