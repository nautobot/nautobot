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

### App Authors/Maintainers

#### Changes For Django 5.2 Compatibility

Nautobot's [dependency update to Django 5.2](#django-52), as typical of Django major version updates, included a small number of breaking changes to Django's Python APIs. For a comprehensive guide, refer to the "Backwards incompatible changes" and "Features removed" sections of Django's release-notes for versions [5.0](https://docs.djangoproject.com/en/5.2/releases/5.0/#backwards-incompatible-changes-in-5-0), [5.1](https://docs.djangoproject.com/en/5.2/releases/5.1/#backwards-incompatible-changes-in-5-1), and [5.2](https://docs.djangoproject.com/en/5.2/releases/5.2/#backwards-incompatible-changes-in-5-2). The most likely impacts we have identified to Nautobot Apps are the following:

- Support for `Model.Meta.index_together` (previously deprecated in Django 4.2) is removed; App models with custom indexes using `index_together` will need to migrate to use `Model.Meta.indexes` instead and create a database migration accordingly.
- Models using a `ManyToManyField` with an explicit `through` table (as is recommended by Nautobot) may need to run `nautobot-server makemigrations <app>` to generate a schema migration explicitly specifying the `through_fields` for each such `ManyToManyField`.
- The test method `assertQuerysetEqual()` (previously deprecated in Django 4.2) is removed; App tests using this method will need to migrate to use `assertQuerySetEqual()` (note capitalization) instead.

#### Changes for HTMX

In Nautobot 3.1, object list views (including both those derived from `generic.ObjectListView` and those using `NautobotUIViewSet`) now load in two stages (using [HTMX](https://htmx.org)) to improve the responsiveness of the UI. Custom implementations of these views, and/or custom test cases written for these views, may require some updates to handle this behavior correctly. Refer to the [developer documentation](../development/core/htmx.md#object-list-views-and-htmx) for more specific guidance.

## Release Overview

### Breaking Changes

#### Dropped Support for PostgreSQL Versions Less Than 14.0

As a consequence of the [dependency update to Django 5.2](#django-52), support for PostgreSQL versions before 14.0 has been removed from Nautobot.

#### Dropped Support for MySQL Versions Less Than 8.0.11

As a consequence of the [dependency update to Django 5.2](#django-52), support for MySQL versions before 8.0.11 has been removed from Nautobot.

#### Unified Storage Backend Configuration

As a consequence of the [dependency update to Django 5.2](#django-52), Nautobot 3.1 drops support for the Django `DEFAULT_FILE_STORAGE` and `STATICFILES_STORAGE` settings variables in favor of a unified `STORAGES` setting. Additionally, support for the corresponding Nautobot-specific `STORAGE_BACKEND`, `STORAGE_CONFIG`, and `JOB_FILE_IO_STORAGE` settings variables has been removed and merged into the [`STORAGES`](https://docs.djangoproject.com/en/5.2/ref/settings/#std-setting-STORAGES) setting. More details are available in the Nautobot [documentation for `STORAGES`](../user-guide/administration/configuration/settings.md#storages).

#### Dropped Support for Custom Date/Time Format Settings

As a consequence of the [dependency update to Django 5.2](#django-52), support for globally customizing date/time display in the UI via the settings variables `DATETIME_FORMAT` and `SHORT_DATETIME_FORMAT` (as well as the less-commonly-used `DATE_FORMAT`, `SHORT_DATE_FORMAT`, `TIME_FORMAT` settings) has been removed from Nautobot.

### Added

#### Per-User Language Preferences

Users can now specify their preferred language/locale through the User Preferences UI. Currently this configuration applies primarily to date/time display in the UI.

#### Python 3.14 Support

Added official support for Python 3.14.

### Deprecated

#### `assertQuerysetEqualAndNotEmpty()` Test Method

The Nautobot test method `assertQuerysetEqualAndNotEmpty()` has been deprecated in favor of the new `assertQuerySetEqualAndNotEmpty()` method (note change in capitalization) to align with Django's `assertQuerySetEqual()` test method. Support for `assertQuerysetEqualAndNotEmpty()` may be removed in a future Nautobot release.

### Dependencies

#### Django 5.2

Nautobot 3.1 upgrades the core `Django` dependency from 4.2.x LTS to 5.2.x LTS. Nautobot has been updated accordingly, but Apps and third-party dependencies may need to update to newer versions for compatibility with Django 5.2.

<!-- pyml disable-num-lines 2 blanks-around-headers -->

<!-- towncrier release notes start -->

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
