# Nautobot v3.1

This document describes all new features and changes in Nautobot 3.1.

## Upgrade Actions

### Administrators

#### Migrate from legacy PostgreSQL versions as needed

Nautobot 3.1, as a consequence of the [Django 5.2 dependency upgrade](#django-52), drops support for PostgreSQL versions 12.x and 13.x and now requires a minimum of PostgreSQL 14.0. If you have an existing Nautobot deployment on these no-longer-supported versions of PostgreSQL, you will need to [upgrade and migrate your database](../user-guide/administration/upgrading/postgresql.md).

!!! tip
    In general we recommend that you upgrade PostgreSQL as a _separate_ step and change window from upgrading Nautobot in order to reduce the complexity of the upgrade and allow easier troubleshooting and recovery should anything go wrong in the process.

#### Migrate Configuration to `STORAGES` as needed

As a consequence of the [Django 5.2 dependency upgrade](#django-52), Nautobot 3.1 drops support for the Django `DEFAULT_FILE_STORAGE` and `STATICFILES_STORAGE` settings variables in favor of a unified `STORAGES` setting. Additionally, support for the corresponding Nautobot-specific `STORAGE_BACKEND`, `STORAGE_CONFIG`, and `JOB_FILE_IO_STORAGE` settings variables has been removed and merged into the [`STORAGES`](https://docs.djangoproject.com/en/5.2/ref/settings/#std-setting-STORAGES) setting.

If your deployment of Nautobot had overridden any of the above settings (for example, to use [S3 storage](../user-guide/administration/guides/s3-django-storage.md)), you will need to update your `nautobot_config.py` file to use the `STORAGES` setting instead. More details are available in the Nautobot [documentation for `STORAGES`](../user-guide/administration/configuration/settings.md#storages).

### App Authors/Maintainers

Nautobot's [dependency update to Django 5.2](#django-52), as typical of Django major version updates, included a small number of breaking changes to Django's Python APIs. For a comprehensive guide, refer to the "Backwards incompatible changes" and "Features removed" sections of Django's release-notes for versions [5.0](https://docs.djangoproject.com/en/5.2/releases/5.0/#backwards-incompatible-changes-in-5-0), [5.1](https://docs.djangoproject.com/en/5.2/releases/5.1/#backwards-incompatible-changes-in-5-1), and [5.2](https://docs.djangoproject.com/en/5.2/releases/5.2/#backwards-incompatible-changes-in-5-2). The most likely impacts we have identified to Nautobot Apps are the following:

- Support for `Model.Meta.index_together` (previously deprecated in Django 4.2) is removed; App models with custom indexes using `index_together` will need to migrate to use `Model.Meta.indexes` instead and create a database migration accordingly.
- Models using a `ManyToManyField` with an explicit `through` table (as is recommended by Nautobot) may need to run `nautobot-server makemigrations <app>` to generate a schema migration explicitly specifying the `through_fields` for each such `ManyToManyField`.
- The test method `assertQuerysetEqual()` (previously deprecated in Django 4.2) is removed; App tests using this method will need to migrate to use `assertQuerySetEqual()` (note capitalization) instead.

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

### Deprecated

#### `assertQuerysetEqualAndNotEmpty()` Test Method

The Nautobot test method `assertQuerysetEqualAndNotEmpty()` has been deprecated in favor of the new `assertQuerySetEqualAndNotEmpty()` method (note change in capitalization) to align with Django's `assertQuerySetEqual()` test method. Support for `assertQuerysetEqualAndNotEmpty()` may be removed in a future Nautobot release.

### Dependencies

#### Django 5.2

Nautobot 3.1 upgrades the core `Django` dependency from 4.2.x LTS to 5.2.x LTS. Nautobot has been updated accordingly, but Apps and third-party dependencies may need to update to newer versions for compatibility with Django 5.2.

<!-- pyml disable-num-lines 2 blanks-around-headers -->

<!-- towncrier release notes start -->
